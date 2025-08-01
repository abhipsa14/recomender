from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
import time
import json
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import dateutil.parser

def parse_posting_date(date_str):
    """Parse various date formats and return datetime object"""
    if not date_str or date_str == 'N/A':
        return None
    
    # Clean the date string
    date_str = date_str.strip().lower()
    now = datetime.now()
    
    # Handle relative dates (e.g., "2 days ago", "1 hour ago")
    if 'ago' in date_str:
        if 'hour' in date_str:
            hours = re.search(r'(\d+)', date_str)
            if hours:
                return now - timedelta(hours=int(hours.group(1)))
        elif 'day' in date_str:
            days = re.search(r'(\d+)', date_str)
            if days:
                return now - timedelta(days=int(days.group(1)))
        elif 'week' in date_str:
            weeks = re.search(r'(\d+)', date_str)
            if weeks:
                return now - timedelta(weeks=int(weeks.group(1)))
        elif 'month' in date_str:
            months = re.search(r'(\d+)', date_str)
            if months:
                return now - timedelta(days=int(months.group(1)) * 30)
    
    # Handle "today" and "yesterday"
    if 'today' in date_str:
        return now
    elif 'yesterday' in date_str:
        return now - timedelta(days=1)
    
    # Try to parse absolute dates
    try:
        return dateutil.parser.parse(date_str)
    except:
        pass
    
    return None

def is_within_time_filter(posted_date, hours_limit=36):
    """Check if job was posted within the specified hours"""
    if not posted_date:
        return False
    
    now = datetime.now()
    time_diff = now - posted_date
    return time_diff.total_seconds() / 3600 <= hours_limit

def filter_by_company(jobs, include_companies=None, exclude_companies=None):
    """Filter jobs by company names"""
    if not include_companies and not exclude_companies:
        return jobs
    
    filtered_jobs = []
    
    for job in jobs:
        company_name = job.get('company', '').lower().strip()
        
        # Check exclude list first
        if exclude_companies:
            exclude_list = [comp.lower().strip() for comp in exclude_companies]
            if any(excluded in company_name for excluded in exclude_list):
                continue
        
        # Check include list
        if include_companies:
            include_list = [comp.lower().strip() for comp in include_companies]
            if not any(included in company_name for included in include_list):
                continue
        
        filtered_jobs.append(job)
    
    return filtered_jobs

def detect_experience_level(job_title, company=""):
    """Detect experience level from job title and company"""
    title_lower = job_title.lower()
    company_lower = company.lower()
    
    # Entry level keywords
    entry_keywords = [
        'junior', 'trainee', 'intern', 'entry', 'graduate', 'fresher', 
        'associate', 'beginner', 'apprentice', '0-1 year', '0-2 year',
        'new grad', 'recent graduate'
    ]
    
    # Mid level keywords
    mid_keywords = [
        'mid', 'intermediate', 'regular', '2-5 year', '3-6 year',
        'experienced', 'specialist'
    ]
    
    # Senior level keywords
    senior_keywords = [
        'senior', 'sr.', 'lead', 'principal', 'architect', 'manager',
        'head', 'director', 'chief', 'expert', '5+ year', '7+ year',
        'team lead', 'tech lead', 'technical lead'
    ]
    
    # Check for entry level
    if any(keyword in title_lower for keyword in entry_keywords):
        return 'entry'
    
    # Check for senior level
    if any(keyword in title_lower for keyword in senior_keywords):
        return 'senior'
    
    # Check for mid level
    if any(keyword in title_lower for keyword in mid_keywords):
        return 'mid'
    
    # Default to mid if no clear indicators
    return 'mid'

def filter_by_experience(jobs, experience_levels=None):
    """Filter jobs by experience level"""
    if not experience_levels:
        return jobs
    
    filtered_jobs = []
    
    for job in jobs:
        # Detect experience level for this job
        job_experience = detect_experience_level(job.get('title', ''), job.get('company', ''))
        job['experience_level'] = job_experience
        
        # Check if this job matches the desired experience levels
        if job_experience in experience_levels:
            filtered_jobs.append(job)
    
    return filtered_jobs

class JobScraper(ABC):
    """Abstract base class for job scrapers"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
    
    @abstractmethod
    def build_search_url(self, search_term, location, page=0):
        """Build search URL for the job site"""
        pass
    
    @abstractmethod
    def extract_job_cards(self, soup):
        """Extract job card elements from the page"""
        pass
    
    @abstractmethod
    def extract_job_info(self, job_card):
        """Extract job information from a job card"""
        pass
    
    def scrape_jobs(self, search_term="", location="", num_pages=1, use_time_filter=False, hours_limit=36):
        """Generic scraping method with optional time filtering"""
        jobs_data = []
        filtered_count = 0
        
        for page in range(num_pages):
            try:
                url = self.build_search_url(search_term, location, page)
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'lxml')
                job_cards = self.extract_job_cards(soup)
                
                print(f"Found {len(job_cards)} job cards on page {page + 1} from {self.__class__.__name__}")
                
                for card in job_cards:
                    job_info = self.extract_job_info(card)
                    if job_info:
                        job_info['source'] = self.__class__.__name__.replace('Scraper', '')
                        
                        # Apply time filter if enabled
                        if use_time_filter:
                            posted_date = parse_posting_date(job_info.get('posted_date', ''))
                            if posted_date and is_within_time_filter(posted_date, hours_limit):
                                jobs_data.append(job_info)
                            else:
                                filtered_count += 1
                        else:
                            jobs_data.append(job_info)
                
                time.sleep(2)  # Be respectful
                
            except requests.RequestException as e:
                print(f"Error fetching page {page + 1} from {self.__class__.__name__}: {e}")
                continue
        
        if use_time_filter and filtered_count > 0:
            print(f"Filtered out {filtered_count} jobs older than {hours_limit} hours from {self.__class__.__name__}")
        
        return jobs_data

class LinkedInScraper(JobScraper):
    """LinkedIn job scraper"""
    
    def build_search_url(self, search_term, location, page=0):
        base_url = "https://www.linkedin.com/jobs/search"
        # Add time filter parameter for LinkedIn (f_TPR=r86400 for 24 hours, r172800 for 48 hours)
        return f"{base_url}?keywords={search_term}&location={location}&start={page * 25}&f_TPR=r172800"
    
    def extract_job_cards(self, soup):
        job_cards = soup.find_all('div', class_='base-card')
        if not job_cards:
            job_cards = soup.find_all('div', class_='job-search-card')
        return job_cards
    
    def extract_job_info(self, job_card):
        try:
            job_info = {}
            
            title_elem = job_card.find('h3', class_='base-search-card__title') or \
                        job_card.find('a', class_='base-card__full-link')
            job_info['title'] = title_elem.get_text(strip=True) if title_elem else 'N/A'
            
            company_elem = job_card.find('h4', class_='base-search-card__subtitle') or \
                          job_card.find('a', class_='hidden-nested-link')
            job_info['company'] = company_elem.get_text(strip=True) if company_elem else 'N/A'
            
            location_elem = job_card.find('span', class_='job-search-card__location')
            job_info['location'] = location_elem.get_text(strip=True) if location_elem else 'N/A'
            
            link_elem = job_card.find('a', class_='base-card__full-link')
            job_info['link'] = link_elem.get('href') if link_elem else 'N/A'
            
            date_elem = job_card.find('time', class_='job-search-card__listdate')
            job_info['posted_date'] = date_elem.get_text(strip=True) if date_elem else 'N/A'
            
            return job_info
        except Exception as e:
            print(f"Error extracting LinkedIn job info: {e}")
            return None

class IndeedScraper(JobScraper):
    """Indeed job scraper"""
    
    def build_search_url(self, search_term, location, page=0):
        base_url = "https://www.indeed.com/jobs"
        # Add fromage parameter for Indeed (1 for 1 day, 3 for 3 days, etc.)
        return f"{base_url}?q={search_term}&l={location}&start={page * 10}&fromage=2"
    
    def extract_job_cards(self, soup):
        return soup.find_all('div', class_='job_seen_beacon') or soup.find_all('div', class_='jobsearch-SerpJobCard')
    
    def extract_job_info(self, job_card):
        try:
            job_info = {}
            
            title_elem = job_card.find('h2', class_='jobTitle') or job_card.find('a', {'data-jk': True})
            job_info['title'] = title_elem.get_text(strip=True) if title_elem else 'N/A'
            
            company_elem = job_card.find('span', class_='companyName') or job_card.find('a', class_='companyName')
            job_info['company'] = company_elem.get_text(strip=True) if company_elem else 'N/A'
            
            location_elem = job_card.find('div', class_='companyLocation')
            job_info['location'] = location_elem.get_text(strip=True) if location_elem else 'N/A'
            
            link_elem = job_card.find('h2', class_='jobTitle').find('a') if job_card.find('h2', class_='jobTitle') else None
            job_info['link'] = f"https://www.indeed.com{link_elem.get('href')}" if link_elem else 'N/A'
            
            date_elem = job_card.find('span', class_='date')
            job_info['posted_date'] = date_elem.get_text(strip=True) if date_elem else 'N/A'
            
            return job_info
        except Exception as e:
            print(f"Error extracting Indeed job info: {e}")
            return None

class GlassdoorScraper(JobScraper):
    """Glassdoor job scraper"""
    
    def build_search_url(self, search_term, location, page=0):
        base_url = "https://www.glassdoor.com/Job/jobs.htm"
        return f"{base_url}?sc.keyword={search_term}&locT=C&locId=1&p={page + 1}"
    
    def extract_job_cards(self, soup):
        return soup.find_all('li', class_='react-job-listing') or soup.find_all('div', class_='jobContainer')
    
    def extract_job_info(self, job_card):
        try:
            job_info = {}
            
            title_elem = job_card.find('a', class_='jobTitle')
            job_info['title'] = title_elem.get_text(strip=True) if title_elem else 'N/A'
            
            company_elem = job_card.find('div', class_='employerName')
            job_info['company'] = company_elem.get_text(strip=True) if company_elem else 'N/A'
            
            location_elem = job_card.find('div', class_='employerLocation')
            job_info['location'] = location_elem.get_text(strip=True) if location_elem else 'N/A'
            
            link_elem = job_card.find('a', class_='jobTitle')
            job_info['link'] = f"https://www.glassdoor.com{link_elem.get('href')}" if link_elem else 'N/A'
            
            job_info['posted_date'] = 'N/A'  # Glassdoor doesn't always show posting date
            
            return job_info
        except Exception as e:
            print(f"Error extracting Glassdoor job info: {e}")
            return None

class UniversalJobScraper:
    """Universal job scraper that handles multiple job websites"""
    
    def __init__(self):
        self.scrapers = {
            'linkedin': LinkedInScraper(),
            'indeed': IndeedScraper(),
            'glassdoor': GlassdoorScraper(),
        }
    
    def scrape_all_sites(self, search_term="", location="", num_pages=1, sites=None, 
                        use_time_filter=False, hours_limit=36, 
                        include_companies=None, exclude_companies=None,
                        experience_levels=None):
        """Scrape jobs from all specified sites with optional filtering"""
        if sites is None:
            sites = list(self.scrapers.keys())
        
        all_jobs = []
        
        for site in sites:
            if site in self.scrapers:
                print(f"\nScraping {site.title()}...")
                if use_time_filter:
                    print(f"Filtering for jobs posted within last {hours_limit} hours...")
                jobs = self.scrapers[site].scrape_jobs(search_term, location, num_pages, use_time_filter, hours_limit)
                all_jobs.extend(jobs)
            else:
                print(f"Scraper for {site} not available")
        
        # Apply company filters
        if include_companies or exclude_companies:
            original_count = len(all_jobs)
            all_jobs = filter_by_company(all_jobs, include_companies, exclude_companies)
            filtered_count = original_count - len(all_jobs)
            
            if include_companies:
                print(f"\nFiltered to include only companies: {', '.join(include_companies)}")
            if exclude_companies:
                print(f"Excluded companies: {', '.join(exclude_companies)}")
            if filtered_count > 0:
                print(f"Filtered out {filtered_count} jobs based on company criteria")
        
        # Apply experience level filters
        if experience_levels:
            original_count = len(all_jobs)
            all_jobs = filter_by_experience(all_jobs, experience_levels)
            filtered_count = original_count - len(all_jobs)
            
            experience_labels = {
                'entry': 'Entry Level',
                'mid': 'Mid Level', 
                'senior': 'Senior Level'
            }
            level_names = [experience_labels.get(level, level) for level in experience_levels]
            print(f"\nFiltered for experience levels: {', '.join(level_names)}")
            if filtered_count > 0:
                print(f"Filtered out {filtered_count} jobs based on experience criteria")
        else:
            # Still detect experience levels for display
            for job in all_jobs:
                job['experience_level'] = detect_experience_level(job.get('title', ''), job.get('company', ''))
        
        return all_jobs
    
    def get_available_sites(self):
        """Get list of available job sites"""
        return list(self.scrapers.keys())

def save_jobs_to_file(jobs_data, filename='universal_jobs.json'):
    """Save jobs data to a JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(jobs_data, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(jobs_data)} jobs to {filename}")

def display_jobs_summary(jobs):
    """Display summary of scraped jobs"""
    if not jobs:
        print("No jobs found.")
        return
    
    # Group by source
    sources = {}
    for job in jobs:
        source = job.get('source', 'Unknown')
        sources[source] = sources.get(source, 0) + 1
    
    # Group by experience level
    experience_levels = {}
    for job in jobs:
        level = job.get('experience_level', 'Unknown')
        experience_levels[level] = experience_levels.get(level, 0) + 1
    
    print(f"\nFound {len(jobs)} total jobs:")
    for source, count in sources.items():
        print(f"  {source}: {count} jobs")
    
    print(f"\nBy experience level:")
    experience_labels = {
        'entry': 'Entry Level',
        'mid': 'Mid Level',
        'senior': 'Senior Level'
    }
    for level, count in experience_levels.items():
        level_name = experience_labels.get(level, level.title())
        print(f"  {level_name}: {count} jobs")
    
    print("\nFirst 10 jobs:")
    print("-" * 80)
    
    for i, job in enumerate(jobs[:10], 1):
        level_name = experience_labels.get(job.get('experience_level', ''), 'Unknown')
        print(f"{i}. {job['title']}")
        print(f"   Company: {job['company']}")
        print(f"   Location: {job['location']}")
        print(f"   Experience: {level_name}")
        print(f"   Source: {job.get('source', 'Unknown')}")
        print(f"   Posted: {job['posted_date']}")
        print(f"   Link: {job['link']}")
        print()

def main():
    print("Universal Job Scraper")
    print("=" * 30)
    
    scraper = UniversalJobScraper()
    available_sites = scraper.get_available_sites()
    
    print(f"Available job sites: {', '.join(available_sites)}")
    
    # Get user input
    search_term = input("Enter job search term (e.g., 'Python Developer'): ").strip()
    location = input("Enter location (e.g., 'New York, NY'): ").strip()
    
    # Time filter option
    use_filter = input("Filter jobs posted within last 36 hours? (y/n): ").strip().lower() == 'y'
    hours_limit = 36
    
    if use_filter:
        try:
            custom_hours = input("Enter custom hours limit (default 36): ").strip()
            if custom_hours:
                hours_limit = max(1, min(int(custom_hours), 168))  # Limit between 1 hour and 1 week
        except ValueError:
            hours_limit = 36
    
    # Company filter options
    include_companies = None
    exclude_companies = None
    
    company_filter = input("Apply company filters? (y/n): ").strip().lower() == 'y'
    
    if company_filter:
        print("\nCompany Filter Options:")
        print("1. Include specific companies only")
        print("2. Exclude specific companies")
        print("3. Both include and exclude")
        
        filter_choice = input("Choose option (1-3): ").strip()
        
        if filter_choice in ['1', '3']:
            include_input = input("Enter companies to INCLUDE (comma-separated): ").strip()
            if include_input:
                include_companies = [comp.strip() for comp in include_input.split(',') if comp.strip()]
        
        if filter_choice in ['2', '3']:
            exclude_input = input("Enter companies to EXCLUDE (comma-separated): ").strip()
            if exclude_input:
                exclude_companies = [comp.strip() for comp in exclude_input.split(',') if comp.strip()]
    
    # Experience level filter
    experience_levels = None
    experience_filter = input("Filter by experience level? (y/n): ").strip().lower() == 'y'
    
    if experience_filter:
        print("\nExperience Level Options:")
        print("1. Entry Level (Junior, Trainee, Intern, Graduate)")
        print("2. Mid Level (Regular, Intermediate, Specialist)")
        print("3. Senior Level (Senior, Lead, Principal, Manager)")
        print("4. Multiple levels")
        
        exp_choice = input("Choose option (1-4): ").strip()
        
        if exp_choice == '1':
            experience_levels = ['entry']
        elif exp_choice == '2':
            experience_levels = ['mid']
        elif exp_choice == '3':
            experience_levels = ['senior']
        elif exp_choice == '4':
            exp_input = input("Enter levels (entry,mid,senior - comma-separated): ").strip().lower()
            if exp_input:
                valid_levels = ['entry', 'mid', 'senior']
                experience_levels = [level.strip() for level in exp_input.split(',') 
                                   if level.strip() in valid_levels]
    
    # Site selection
    print(f"\nSelect sites to scrape (comma-separated) or 'all' for all sites:")
    print(f"Options: {', '.join(available_sites)}")
    site_input = input("Sites: ").strip().lower()
    
    if site_input == 'all':
        selected_sites = available_sites
    else:
        selected_sites = [s.strip() for s in site_input.split(',') if s.strip() in available_sites]
    
    if not selected_sites:
        print("No valid sites selected. Using all sites.")
        selected_sites = available_sites
    
    try:
        num_pages = int(input("Enter number of pages per site (1-3): ").strip())
        num_pages = min(max(num_pages, 1), 3)  # Limit to 1-3 pages per site
    except ValueError:
        num_pages = 1
    
    # Build description of filters
    filter_desc = []
    if use_filter:
        filter_desc.append(f"time: last {hours_limit} hours")
    if include_companies:
        filter_desc.append(f"include companies: {', '.join(include_companies)}")
    if exclude_companies:
        filter_desc.append(f"exclude companies: {', '.join(exclude_companies)}")
    if experience_levels:
        exp_labels = {'entry': 'Entry', 'mid': 'Mid', 'senior': 'Senior'}
        exp_names = [exp_labels.get(level, level) for level in experience_levels]
        filter_desc.append(f"experience: {', '.join(exp_names)}")
    
    filter_text = f" (filters: {'; '.join(filter_desc)})" if filter_desc else ""
    print(f"\nScraping jobs for '{search_term}' in '{location}' from: {', '.join(selected_sites)}{filter_text}")
    
    # Scrape jobs
    jobs = scraper.scrape_all_sites(search_term, location, num_pages, selected_sites, 
                                   use_filter, hours_limit, include_companies, exclude_companies,
                                   experience_levels)
    
    # Display results
    display_jobs_summary(jobs)
    
    # Save to file
    if jobs:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"jobs_{timestamp}.json"
        save_jobs_to_file(jobs, filename)
    else:
        print("No jobs found. Try different search terms or adjust filters.")

if __name__ == "__main__":
    main()
