"""
Indeed job scraper implementation.
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from .base_scraper import BaseScraper


class IndeedScraper(BaseScraper):
    """Indeed job scraper with enhanced features"""
    
    @property
    def platform_name(self) -> str:
        return "Indeed"
    
    def __init__(self, delay: float = 2.0):
        """Initialize Indeed scraper"""
        super().__init__(delay)
        self.base_url = "https://www.indeed.com"
    
    def build_search_url(self, search_term: str, location: str, page: int = 0) -> str:
        """Build Indeed job search URL"""
        encoded_term = quote_plus(search_term) if search_term else ""
        encoded_location = quote_plus(location) if location else ""
        
        url = f"{self.base_url}/jobs"
        params = []
        
        if encoded_term:
            params.append(f"q={encoded_term}")
        if encoded_location:
            params.append(f"l={encoded_location}")
        if page > 0:
            params.append(f"start={page * 10}")
        
        # Add time filter for recent jobs (last 3 days)
        params.append("fromage=3")
        
        if params:
            url += "?" + "&".join(params)
        
        return url
    
    def extract_job_cards(self, soup: BeautifulSoup) -> List:
        """Extract job card elements from Indeed page"""
        # Try multiple selectors as Indeed's structure may vary
        selectors = [
            'div.job_seen_beacon',
            'div[data-jk]',
            'div.jobsearch-SerpJobCard',
            'div.slider_container div.slider_item'
        ]
        
        job_cards = []
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                job_cards = cards
                break
        
        return job_cards
    
    def extract_job_info(self, job_card) -> Optional[Dict]:
        """Extract job information from an Indeed job card"""
        try:
            job_info = {}
            
            # Job title - try multiple selectors
            title_selectors = [
                'h2.jobTitle a[data-jk]',
                'h2 a[data-jk]',
                'a[data-jk] span[title]',
                '.jobTitle a'
            ]
            
            title_elem = None
            for selector in title_selectors:
                title_elem = job_card.select_one(selector)
                if title_elem:
                    break
            
            # Get title text
            if title_elem:
                # Try span with title attribute first
                title_span = title_elem.select_one('span[title]')
                if title_span:
                    job_info['title'] = title_span.get('title')
                else:
                    job_info['title'] = title_elem.get_text(strip=True)
            else:
                job_info['title'] = 'N/A'
            
            # Company name
            company_selectors = [
                'span.companyName a',
                'span.companyName',
                'a[data-testid="company-name"]',
                '.companyName'
            ]
            
            company_elem = None
            for selector in company_selectors:
                company_elem = job_card.select_one(selector)
                if company_elem:
                    break
            
            job_info['company'] = company_elem.get_text(strip=True) if company_elem else 'N/A'
            
            # Location
            location_selectors = [
                'div.companyLocation',
                '[data-testid="job-location"]',
                '.companyLocation'
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
                # Try to get data-jk attribute for building link
                data_jk = job_card.get('data-jk')
                if data_jk:
                    job_info['link'] = f"{self.base_url}/viewjob?jk={data_jk}"
                else:
                    job_info['link'] = 'N/A'
            
            # Posted date
            date_selectors = [
                'span.date',
                '[data-testid="myJobsStateDate"]',
                '.date'
            ]
            
            date_elem = None
            for selector in date_selectors:
                date_elem = job_card.select_one(selector)
                if date_elem:
                    break
            
            job_info['posted_date'] = date_elem.get_text(strip=True) if date_elem else 'N/A'
            
            # Salary (if available)
            salary_selectors = [
                '.salary-snippet',
                '.salaryText',
                '[data-testid="attribute_snippet_testid"]'
            ]
            
            salary_elem = None
            for selector in salary_selectors:
                salary_elem = job_card.select_one(selector)
                if salary_elem:
                    break
            
            job_info['salary'] = salary_elem.get_text(strip=True) if salary_elem else 'N/A'
            
            # Job snippet/description
            snippet_selectors = [
                '.job-snippet',
                '[data-testid="job-snippet"]',
                '.summary'
            ]
            
            snippet_elem = None
            for selector in snippet_selectors:
                snippet_elem = job_card.select_one(selector)
                if snippet_elem:
                    break
            
            job_info['snippet'] = snippet_elem.get_text(strip=True) if snippet_elem else 'N/A'
            
            # Job type (full-time, part-time, etc.)
            job_type_elem = job_card.select_one('[data-testid="attribute_snippet_testid"]')
            job_info['job_type'] = job_type_elem.get_text(strip=True) if job_type_elem else 'N/A'
            
            return job_info if self.validate_job_data(job_info) else None
            
        except Exception as e:
            self.logger.error(f"Error extracting Indeed job info: {e}")
            return None


def test_indeed_scraper():
    """Test function for Indeed scraper"""
    scraper = IndeedScraper()
    jobs = scraper.scrape_jobs("Python Developer", "San Francisco", 1)
    
    print(f"\n🧪 Indeed Test Results: Found {len(jobs)} jobs")
    for i, job in enumerate(jobs[:3], 1):
        print(f"\n{i}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   Posted: {job['posted_date']}")
        print(f"   Salary: {job['salary']}")
        print(f"   Type: {job.get('job_type', 'N/A')}")
        print(f"   Snippet: {job['snippet'][:100]}...")
        print(f"   Link: {job['link']}")


if __name__ == "__main__":
    test_indeed_scraper()
