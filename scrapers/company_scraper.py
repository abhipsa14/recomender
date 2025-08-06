"""
Generic company career page scraper.
"""

from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .base_scraper import BaseScraper


class CompanyScraper(BaseScraper):
    """Generic scraper for company career pages"""
    
    def __init__(self, company_name: str, career_url: str, delay: float = 2.0):
        """
        Initialize company scraper.
        
        Args:
            company_name: Name of the company
            career_url: URL to the company's career page
            delay: Delay between requests
        """
        super().__init__(delay)
        self.company_name = company_name
        self.career_url = career_url
        self.base_domain = f"{urlparse(career_url).scheme}://{urlparse(career_url).netloc}"
    
    @property
    def platform_name(self) -> str:
        return f"{self.company_name} Careers"
    
    def build_search_url(self, search_term: str, location: str, page: int = 0) -> str:
        """Build company career page URL"""
        # For most company career pages, we'll start with the base URL
        # and handle pagination if supported
        url = self.career_url
        
        # Add page parameter if supported (this varies by company)
        if page > 0:
            # Common pagination patterns
            if '?' in url:
                url += f"&page={page + 1}"
            else:
                url += f"?page={page + 1}"
        
        return url
    
    def extract_job_cards(self, soup: BeautifulSoup) -> List:
        """Extract job card elements from company career page"""
        # Common selectors for job listings on career pages
        job_selectors = [
            'div[class*="job"]',
            'li[class*="job"]',
            'article[class*="job"]',
            'div[class*="position"]',
            'li[class*="position"]',
            'div[class*="opening"]',
            'li[class*="opening"]',
            'div[class*="career"]',
            'tr[class*="job"]',  # Table rows
            'a[href*="/job"]',
            'a[href*="/career"]',
            'a[href*="/position"]'
        ]
        
        job_cards = []
        for selector in job_selectors:
            cards = soup.select(selector)
            if cards and len(cards) > 1:  # Make sure we found actual job listings
                job_cards = cards
                break
        
        return job_cards
    
    def extract_job_info(self, job_card) -> Optional[Dict]:
        """Extract job information from a company career page job card"""
        try:
            job_info = {}
            
            # Job title - try multiple approaches
            title_selectors = [
                'h1', 'h2', 'h3', 'h4',
                '[class*="title"]',
                '[class*="name"]',
                '[class*="position"]',
                'a'
            ]
            
            title_elem = None
            for selector in title_selectors:
                title_elem = job_card.select_one(selector)
                if title_elem and title_elem.get_text(strip=True):
                    break
            
            if title_elem:
                job_info['title'] = title_elem.get_text(strip=True)
            else:
                # If job_card is a link itself, use its text
                job_info['title'] = job_card.get_text(strip=True) if hasattr(job_card, 'get_text') else 'N/A'
            
            # Company name (we know this from initialization)
            job_info['company'] = self.company_name
            
            # Location - try to find location info
            location_selectors = [
                '[class*="location"]',
                '[class*="city"]',
                '[class*="office"]',
                '[class*="region"]'
            ]
            
            location_elem = None
            for selector in location_selectors:
                location_elem = job_card.select_one(selector)
                if location_elem:
                    break
            
            if location_elem:
                job_info['location'] = location_elem.get_text(strip=True)
            else:
                # Look for common location patterns in text
                card_text = job_card.get_text(strip=True).lower()
                common_locations = [
                    'remote', 'san francisco', 'new york', 'seattle', 'austin',
                    'chicago', 'boston', 'los angeles', 'denver', 'atlanta'
                ]
                
                found_location = None
                for loc in common_locations:
                    if loc in card_text:
                        found_location = loc.title()
                        break
                
                job_info['location'] = found_location or 'Not specified'
            
            # Job link
            link_elem = job_card if job_card.name == 'a' else job_card.find('a')
            if link_elem and link_elem.get('href'):
                href = link_elem.get('href')
                if href.startswith('http'):
                    job_info['link'] = href
                else:
                    job_info['link'] = urljoin(self.base_domain, href)
            else:
                job_info['link'] = self.career_url
            
            # Posted date (often not available on company pages)
            date_selectors = [
                '[class*="date"]',
                '[class*="posted"]',
                'time'
            ]
            
            date_elem = None
            for selector in date_selectors:
                date_elem = job_card.select_one(selector)
                if date_elem:
                    break
            
            job_info['posted_date'] = date_elem.get_text(strip=True) if date_elem else 'N/A'
            
            # Department/team (common on company pages)
            dept_selectors = [
                '[class*="department"]',
                '[class*="team"]',
                '[class*="division"]'
            ]
            
            dept_elem = None
            for selector in dept_selectors:
                dept_elem = job_card.select_one(selector)
                if dept_elem:
                    break
            
            job_info['department'] = dept_elem.get_text(strip=True) if dept_elem else 'N/A'
            
            # Job type (full-time, contract, etc.)
            type_selectors = [
                '[class*="type"]',
                '[class*="employment"]'
            ]
            
            type_elem = None
            for selector in type_selectors:
                type_elem = job_card.select_one(selector)
                if type_elem:
                    break
            
            job_info['job_type'] = type_elem.get_text(strip=True) if type_elem else 'N/A'
            
            return job_info if self.validate_job_data(job_info) else None
            
        except Exception as e:
            self.logger.error(f"Error extracting {self.company_name} job info: {e}")
            return None


# Predefined company scrapers for popular tech companies
class GoogleCareers(CompanyScraper):
    def __init__(self):
        super().__init__(
            company_name="Google",
            career_url="https://careers.google.com/jobs/results/"
        )


class MetaCareers(CompanyScraper):
    def __init__(self):
        super().__init__(
            company_name="Meta",
            career_url="https://www.metacareers.com/jobs/"
        )


class MicrosoftCareers(CompanyScraper):
    def __init__(self):
        super().__init__(
            company_name="Microsoft",
            career_url="https://careers.microsoft.com/us/en/search-results"
        )


def test_company_scraper():
    """Test function for company scraper"""
    # Test with Google careers
    scraper = GoogleCareers()
    jobs = scraper.scrape_jobs("", "", 1)
    
    print(f"\n🧪 {scraper.platform_name} Test Results: Found {len(jobs)} jobs")
    for i, job in enumerate(jobs[:3], 1):
        print(f"\n{i}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   Department: {job.get('department', 'N/A')}")
        print(f"   Type: {job.get('job_type', 'N/A')}")
        print(f"   Link: {job['link']}")


if __name__ == "__main__":
    test_company_scraper()
