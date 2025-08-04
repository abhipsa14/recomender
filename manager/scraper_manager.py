"""
Scraper Manager - Orchestrates and unifies all job scrapers.
"""

import logging
from typing import List, Dict, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime

from scrapers import LinkedInScraper, IndeedScraper, CompanyScraper
from scrapers.company_scraper import GoogleCareers, MetaCareers, MicrosoftCareers


class ScraperManager:
    """Manages and orchestrates multiple job scrapers"""
    
    def __init__(self, max_workers: int = 3, default_delay: float = 2.0):
        """
        Initialize the scraper manager.
        
        Args:
            max_workers: Maximum number of concurrent scrapers
            default_delay: Default delay between requests
        """
        self.max_workers = max_workers
        self.default_delay = default_delay
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize available scrapers
        self.scrapers = {
            'linkedin': LinkedInScraper(delay=default_delay),
            'indeed': IndeedScraper(delay=default_delay),
            'google': GoogleCareers(),
            'meta': MetaCareers(),
            'microsoft': MicrosoftCareers()
        }
        
        # Track scraping statistics
        self.stats = {
            'total_jobs': 0,
            'jobs_by_source': {},
            'scraping_duration': 0,
            'failed_scrapers': []
        }
    
    def add_custom_scraper(self, name: str, scraper):
        """
        Add a custom scraper to the manager.
        
        Args:
            name: Unique name for the scraper
            scraper: Scraper instance (must inherit from BaseScraper)
        """
        self.scrapers[name] = scraper
        self.logger.info(f"Added custom scraper: {name}")
    
    def get_available_scrapers(self) -> List[str]:
        """Get list of available scraper names"""
        return list(self.scrapers.keys())
    
    def scrape_single_source(self, scraper_name: str, search_term: str = "", 
                           location: str = "", num_pages: int = 1, **kwargs) -> List[Dict]:
        """
        Scrape jobs from a single source.
        
        Args:
            scraper_name: Name of the scraper to use
            search_term: Job search term
            location: Location to search in
            num_pages: Number of pages to scrape
            **kwargs: Additional scraper-specific parameters
            
        Returns:
            List of job dictionaries
        """
        if scraper_name not in self.scrapers:
            self.logger.error(f"Scraper '{scraper_name}' not found")
            return []
        
        try:
            scraper = self.scrapers[scraper_name]
            self.logger.info(f"Starting scrape with {scraper.platform_name}")
            
            start_time = time.time()
            jobs = scraper.scrape_jobs(search_term, location, num_pages, **kwargs)
            duration = time.time() - start_time
            
            self.logger.info(f"Completed {scraper.platform_name} scrape: "
                           f"{len(jobs)} jobs in {duration:.2f}s")
            
            # Update statistics
            self.stats['jobs_by_source'][scraper_name] = len(jobs)
            
            return jobs
            
        except Exception as e:
            self.logger.error(f"Error scraping {scraper_name}: {e}")
            self.stats['failed_scrapers'].append(scraper_name)
            return []
    
    def scrape_multiple_sources(self, scraper_names: List[str], search_term: str = "",
                              location: str = "", num_pages: int = 1, 
                              parallel: bool = True, **kwargs) -> List[Dict]:
        """
        Scrape jobs from multiple sources.
        
        Args:
            scraper_names: List of scraper names to use
            search_term: Job search term
            location: Location to search in
            num_pages: Number of pages to scrape per source
            parallel: Whether to scrape in parallel
            **kwargs: Additional scraper-specific parameters
            
        Returns:
            Combined list of job dictionaries
        """
        all_jobs = []
        start_time = time.time()
        
        if parallel and len(scraper_names) > 1:
            # Parallel scraping
            self.logger.info(f"Starting parallel scraping with {len(scraper_names)} scrapers")
            
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(scraper_names))) as executor:
                # Submit scraping tasks
                future_to_scraper = {
                    executor.submit(
                        self.scrape_single_source, 
                        scraper_name, search_term, location, num_pages, **kwargs
                    ): scraper_name
                    for scraper_name in scraper_names
                }
                
                # Collect results
                for future in as_completed(future_to_scraper):
                    scraper_name = future_to_scraper[future]
                    try:
                        jobs = future.result()
                        all_jobs.extend(jobs)
                    except Exception as e:
                        self.logger.error(f"Parallel scraping failed for {scraper_name}: {e}")
                        self.stats['failed_scrapers'].append(scraper_name)
        else:
            # Sequential scraping
            self.logger.info(f"Starting sequential scraping with {len(scraper_names)} scrapers")
            
            for scraper_name in scraper_names:
                jobs = self.scrape_single_source(scraper_name, search_term, location, num_pages, **kwargs)
                all_jobs.extend(jobs)
                
                # Add delay between scrapers to be respectful
                if scraper_name != scraper_names[-1]:  # Don't delay after last scraper
                    time.sleep(self.default_delay)
        
        # Update final statistics
        self.stats['total_jobs'] = len(all_jobs)
        self.stats['scraping_duration'] = time.time() - start_time
        
        self.logger.info(f"Scraping completed: {len(all_jobs)} total jobs from "
                        f"{len(scraper_names)} sources in {self.stats['scraping_duration']:.2f}s")
        
        return all_jobs
    
    def scrape_all_sources(self, search_term: str = "", location: str = "", 
                          num_pages: int = 1, parallel: bool = True, **kwargs) -> List[Dict]:
        """
        Scrape jobs from all available sources.
        
        Args:
            search_term: Job search term
            location: Location to search in
            num_pages: Number of pages to scrape per source
            parallel: Whether to scrape in parallel
            **kwargs: Additional scraper-specific parameters
            
        Returns:
            Combined list of job dictionaries
        """
        return self.scrape_multiple_sources(
            list(self.scrapers.keys()), search_term, location, num_pages, parallel, **kwargs
        )
    
    def get_scraping_stats(self) -> Dict:
        """Get scraping statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset scraping statistics"""
        self.stats = {
            'total_jobs': 0,
            'jobs_by_source': {},
            'scraping_duration': 0,
            'failed_scrapers': []
        }
    
    def validate_scrapers(self) -> Dict[str, bool]:
        """
        Validate that all scrapers are working properly.
        
        Returns:
            Dictionary mapping scraper names to their status (True = working)
        """
        results = {}
        
        for name, scraper in self.scrapers.items():
            try:
                # Try to build a URL and check if scraper is responsive
                url = scraper.build_search_url("test", "test", 0)
                results[name] = bool(url)  # Simple validation
            except Exception as e:
                self.logger.error(f"Validation failed for {name}: {e}")
                results[name] = False
        
        return results
    
    def get_platform_info(self) -> Dict[str, str]:
        """Get information about all available platforms"""
        return {name: scraper.platform_name for name, scraper in self.scrapers.items()}


def main():
    """Test the scraper manager"""
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
    
    # Initialize manager
    manager = ScraperManager(max_workers=2)
    
    print("🚀 Job Scraper Manager Test")
    print("=" * 40)
    
    # Show available scrapers
    print(f"Available scrapers: {', '.join(manager.get_available_scrapers())}")
    print(f"Platform info: {manager.get_platform_info()}")
    
    # Validate scrapers
    print("\n🔍 Validating scrapers...")
    validation_results = manager.validate_scrapers()
    for name, status in validation_results.items():
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {name}")
    
    # Test scraping
    print("\n🔄 Testing scraping (limited to 1 page)...")
    jobs = manager.scrape_multiple_sources(
        ['linkedin', 'indeed'], 
        search_term="Python Developer",
        location="San Francisco",
        num_pages=1,
        parallel=True
    )
    
    # Show results
    print(f"\n📊 Results:")
    stats = manager.get_scraping_stats()
    print(f"  Total jobs: {stats['total_jobs']}")
    print(f"  Duration: {stats['scraping_duration']:.2f}s")
    print(f"  Jobs by source: {stats['jobs_by_source']}")
    if stats['failed_scrapers']:
        print(f"  Failed scrapers: {stats['failed_scrapers']}")
    
    # Show sample jobs
    if jobs:
        print(f"\n📋 Sample jobs (first 3):")
        for i, job in enumerate(jobs[:3], 1):
            print(f"  {i}. {job.get('title', 'N/A')} at {job.get('company', 'N/A')}")
            print(f"     📍 {job.get('location', 'N/A')} | 🌐 {job.get('source', 'N/A')}")


if __name__ == "__main__":
    main()
