"""
Base scraper class defining the interface for all job portal scrapers.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import time
import logging


class BaseScraper(ABC):
    """Abstract base class for all job scrapers"""
    
    def __init__(self, delay: float = 2.0):
        """
        Initialize the base scraper.
        
        Args:
            delay: Delay between requests in seconds
        """
        self.delay = delay
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the name of the job platform"""
        pass
    
    @abstractmethod
    def build_search_url(self, search_term: str, location: str, page: int = 0) -> str:
        """
        Build the search URL for the job platform.
        
        Args:
            search_term: Job title or keywords to search for
            location: Location to search in
            page: Page number (0-indexed)
            
        Returns:
            Complete search URL
        """
        pass
    
    @abstractmethod
    def extract_job_cards(self, soup: BeautifulSoup) -> List:
        """
        Extract job card elements from the page.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of job card elements
        """
        pass
    
    @abstractmethod
    def extract_job_info(self, job_card) -> Optional[Dict]:
        """
        Extract job information from a job card element.
        
        Args:
            job_card: Job card element
            
        Returns:
            Dictionary with job information or None if extraction fails
        """
        pass
    
    def make_request(self, url: str, timeout: int = 15) -> Optional[requests.Response]:
        """
        Make HTTP request with error handling.
        
        Args:
            url: URL to request
            timeout: Request timeout in seconds
            
        Returns:
            Response object or None if request fails
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            return None
    
    def scrape_jobs(self, search_term: str = "", location: str = "", 
                   num_pages: int = 1, **kwargs) -> List[Dict]:
        """
        Scrape jobs from the platform.
        
        Args:
            search_term: Job title or keywords to search for
            location: Location to search in
            num_pages: Number of pages to scrape
            **kwargs: Additional platform-specific parameters
            
        Returns:
            List of job dictionaries
        """
        jobs_data = []
        
        for page in range(num_pages):
            try:
                url = self.build_search_url(search_term, location, page)
                self.logger.info(f"Scraping {self.platform_name} page {page + 1}: {url}")
                
                response = self.make_request(url)
                if not response:
                    continue
                
                soup = BeautifulSoup(response.text, 'lxml')
                job_cards = self.extract_job_cards(soup)
                
                self.logger.info(f"Found {len(job_cards)} job cards on {self.platform_name} page {page + 1}")
                
                for card in job_cards:
                    job_info = self.extract_job_info(card)
                    if job_info and job_info.get('title') != 'N/A':
                        job_info['source'] = self.platform_name
                        job_info['scraped_at'] = time.time()
                        jobs_data.append(job_info)
                
                # Respectful delay between requests
                if page < num_pages - 1:  # Don't delay after the last page
                    time.sleep(self.delay)
                
            except Exception as e:
                self.logger.error(f"Error scraping {self.platform_name} page {page + 1}: {e}")
                continue
        
        self.logger.info(f"{self.platform_name} scraping completed. Found {len(jobs_data)} jobs.")
        return jobs_data
    
    def validate_job_data(self, job_data: Dict) -> bool:
        """
        Validate if job data contains required fields.
        
        Args:
            job_data: Job data dictionary
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['title', 'company', 'location']
        return all(field in job_data and job_data[field] not in [None, 'N/A', ''] 
                  for field in required_fields)
