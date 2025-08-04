"""
LinkedIn job scraper implementation.
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from .base_scraper import BaseScraper


class LinkedInScraper(BaseScraper):
    """LinkedIn job scraper with enhanced features"""
    
    @property
    def platform_name(self) -> str:
        return "LinkedIn"
    
    def __init__(self, delay: float = 3.0):
        """Initialize LinkedIn scraper with longer delay for respect"""
        super().__init__(delay)
        self.base_url = "https://www.linkedin.com"
    
    def build_search_url(self, search_term: str, location: str, page: int = 0) -> str:
        """Build LinkedIn job search URL"""
        encoded_term = quote_plus(search_term) if search_term else ""
        encoded_location = quote_plus(location) if location else ""
        
        url = f"{self.base_url}/jobs/search"
        params = []
        
        if encoded_term:
            params.append(f"keywords={encoded_term}")
        if encoded_location:
            params.append(f"location={encoded_location}")
        if page > 0:
            params.append(f"start={page * 25}")
        
        # Add time filter for recent jobs (last 24 hours)
        params.append("f_TPR=r86400")
        
        if params:
            url += "?" + "&".join(params)
        
        return url
    
    def extract_job_cards(self, soup: BeautifulSoup) -> List:
        """Extract job card elements from LinkedIn page"""
        # Try multiple selectors as LinkedIn's structure may vary
        selectors = [
            'div.base-card',
            'div.job-search-card',
            'li.result-card',
            'div[data-entity-urn*="jobPosting"]'
        ]
        
        job_cards = []
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                job_cards = cards
                break
        
        return job_cards
    
    def extract_job_info(self, job_card) -> Optional[Dict]:
        """Extract job information from a LinkedIn job card"""
        try:
            job_info = {}
            
            # Job title - try multiple selectors
            title_selectors = [
                'h3.base-search-card__title a',
                'h4.base-search-card__title a',
                'a.base-card__full-link',
                '.job-title a'
            ]
            
            title_elem = None
            for selector in title_selectors:
                title_elem = job_card.select_one(selector)
                if title_elem:
                    break
            
            job_info['title'] = title_elem.get_text(strip=True) if title_elem else 'N/A'
            
            # Company name
            company_selectors = [
                'h4.base-search-card__subtitle a',
                'a.hidden-nested-link',
                '.job-result-card__company-name',
                'span.job-result-card__company-name'
            ]
            
            company_elem = None
            for selector in company_selectors:
                company_elem = job_card.select_one(selector)
                if company_elem:
                    break
            
            job_info['company'] = company_elem.get_text(strip=True) if company_elem else 'N/A'
            
            # Location
            location_selectors = [
                'span.job-search-card__location',
                '.job-result-card__location',
                'span.job-result-card__location'
            ]
            
            location_elem = None
            for selector in location_selectors:
                location_elem = job_card.select_one(selector)
                if location_elem:
                    break
            
            job_info['location'] = location_elem.get_text(strip=True) if location_elem else 'N/A'
            
            # Job link
            if title_elem and title_elem.get('href'):
                href = title_elem.get('href')
                if href.startswith('http'):
                    job_info['link'] = href
                else:
                    job_info['link'] = f"{self.base_url}{href}"
            else:
                job_info['link'] = 'N/A'
            
            # Posted date
            date_selectors = [
                'time.job-search-card__listdate',
                'time[datetime]',
                '.job-result-card__listdate'
            ]
            
            date_elem = None
            for selector in date_selectors:
                date_elem = job_card.select_one(selector)
                if date_elem:
                    break
            
            if date_elem:
                # Try to get datetime attribute first, then text
                posted_date = date_elem.get('datetime') or date_elem.get_text(strip=True)
                job_info['posted_date'] = posted_date
            else:
                job_info['posted_date'] = 'N/A'
            
            # Additional LinkedIn-specific fields
            # Job level/seniority
            seniority_elem = job_card.select_one('.job-flavors__item')
            job_info['seniority'] = seniority_elem.get_text(strip=True) if seniority_elem else 'N/A'
            
            # Salary (if available)
            salary_elem = job_card.select_one('.job-search-card__salary-info')
            job_info['salary'] = salary_elem.get_text(strip=True) if salary_elem else 'N/A'
            
            return job_info if self.validate_job_data(job_info) else None
            
        except Exception as e:
            self.logger.error(f"Error extracting LinkedIn job info: {e}")
            return None


def test_linkedin_scraper():
    """Test function for LinkedIn scraper"""
    scraper = LinkedInScraper()
    jobs = scraper.scrape_jobs("Python Developer", "New York", 1)
    
    print(f"\n🧪 LinkedIn Test Results: Found {len(jobs)} jobs")
    for i, job in enumerate(jobs[:3], 1):
        print(f"\n{i}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   Posted: {job['posted_date']}")
        print(f"   Seniority: {job.get('seniority', 'N/A')}")
        print(f"   Link: {job['link']}")


if __name__ == "__main__":
    test_linkedin_scraper()
