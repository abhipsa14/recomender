from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus

from scrapers.company_scraper import CompanyScraper
from .base_scraper import BaseScraper
from urllib.parse import urljoin

class GoogleCareers(CompanyScraper):
    """Google Careers scraper with enhanced features"""
    
    @property
    def platform_name(self) -> str:
        return "Google Careers"
    
    def __init__(self, delay: float = 2.0):
        """Initialize Google Careers scraper"""
        self.base_url = "https://careers.google.com"
        super().__init__(company_name="Google", career_url=self.base_url, delay=delay)
    
    def build_search_url(self, search_term: str, location: str, page: int = 0) -> str:
        """Build Google Careers job search URL"""
        encoded_term = quote_plus(search_term) if search_term else ""
        encoded_location = quote_plus(location) if location else ""
        
        url = f"{self.base_url}/jobs"
        params = []
        
        if encoded_term:
            params.append(f"q={encoded_term}")
        if encoded_location:
            params.append(f"location={encoded_location}")
        if page > 0:
            params.append(f"start={page * 10}")
        
        if params:
            url += "?" + "&".join(params)
        
        return url
    
    def extract_job_cards(self, soup: BeautifulSoup) -> List:
        """Extract job card elements from Google Careers page"""
        # Try multiple selectors as Google's structure may vary
        selectors = [
            'div.job-card',
            'div[data-job-id]',
            'li.job-listing',
            'div[class*="job-listing"]'
        ]
        
        job_cards = []
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                job_cards = cards
                break
        
        return job_cards
    def extract_job_info(self, job_card: BeautifulSoup) -> Dict:
        """Extract job information from a Google Careers job card"""
        try:
            job_info = {}
            
            # Job title - try multiple selectors
            title_selectors = [
                'h2.job-title',
                'a.job-title-link',
                'div[data-job-title]'
            ]
            
            title_elem = None
            for selector in title_selectors:
                title_elem = job_card.select_one(selector)
                if title_elem:
                    break
            
            if title_elem:
                job_info['title'] = title_elem.get_text(strip=True)
            
            # Job location
            location_elem = job_card.select_one('div.job-location')
            if location_elem:
                job_info['location'] = location_elem.get_text(strip=True)
            
            # Job link
            link_elem = job_card.select_one('a.job-link')
            if link_elem and 'href' in link_elem.attrs:
                href = link_elem['href']
                if isinstance(href, list):
                    href = href[0] if href else ""
                job_info['link'] = urljoin(self.base_url, href)
            
            return job_info
        
        except Exception as e:
            self.logger.error(f"Error extracting job info: {e}")
            return {}
        return {}   
