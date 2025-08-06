"""
Job filtering and deduplication utilities.
"""

import re
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Set, Optional, Any
from datetime import datetime, timedelta
import logging

# Try to import dateutil, fallback to basic datetime parsing if not available
try:
    import dateutil.parser
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


class JobFilter(ABC):
    """Abstract base class for job filters"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def filter(self, jobs: List[Dict]) -> List[Dict]:
        """
        Filter jobs based on specific criteria.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            Filtered list of job dictionaries
        """
        pass
    
    def get_stats(self) -> Dict:
        """Get filtering statistics"""
        return getattr(self, '_stats', {})


class MainJobFilter(JobFilter):
    """Main concrete job filter that combines multiple filtering criteria"""
    
    def __init__(self, filter_config: Optional[Dict[str, Any]] = None):
        """
        Initialize main job filter.
        
        Args:
            filter_config: Dictionary containing filter configuration
        """
        super().__init__()
        self.config = filter_config or {}
        self._stats = {
            'original_count': 0,
            'after_experience_filter': 0,
            'after_company_filter': 0,
            'after_location_filter': 0,
            'after_keyword_filter': 0,
            'after_date_filter': 0,
            'after_salary_filter': 0,
            'final_count': 0
        }
    
    def filter(self, jobs: List[Dict]) -> List[Dict]:
        """Apply all configured filters"""
        self._stats['original_count'] = len(jobs)
        filtered_jobs = jobs
        
        # Apply experience level filter
        if self.config.get('experience_levels'):
            experience_filter = ExperienceFilter(self.config['experience_levels'])
            filtered_jobs = experience_filter.filter(filtered_jobs)
            self._stats['after_experience_filter'] = len(filtered_jobs)
        
        # Apply company filter
        if self.config.get('include_companies') or self.config.get('exclude_companies'):
            company_filter = CompanyFilter(
                include_companies=self.config.get('include_companies'),
                exclude_companies=self.config.get('exclude_companies')
            )
            filtered_jobs = company_filter.filter(filtered_jobs)
            self._stats['after_company_filter'] = len(filtered_jobs)
        
        # Apply keyword filter
        if self.config.get('keywords') or self.config.get('exclude_keywords'):
            keyword_filter = KeywordFilter(
                required_keywords=self.config.get('keywords', []),
                excluded_keywords=self.config.get('exclude_keywords', [])
            )
            filtered_jobs = keyword_filter.filter(filtered_jobs)
            self._stats['after_keyword_filter'] = len(filtered_jobs)
        
        # Apply date filter
        if self.config.get('max_age_days'):
            date_filter = DateFilter(max_age_hours=self.config['max_age_days'] * 24)
            filtered_jobs = date_filter.filter(filtered_jobs)
            self._stats['after_date_filter'] = len(filtered_jobs)
        
        # Apply salary filter
        if self.config.get('min_salary') or self.config.get('max_salary'):
            salary_filter = SalaryFilter(
                min_salary=self.config.get('min_salary'),
                max_salary=self.config.get('max_salary')
            )
            filtered_jobs = salary_filter.filter(filtered_jobs)
            self._stats['after_salary_filter'] = len(filtered_jobs)
        
        # Apply remote/full-time filters
        if self.config.get('remote_only') or self.config.get('full_time_only'):
            job_type_filter = JobTypeFilter(
                remote_only=self.config.get('remote_only', False),
                full_time_only=self.config.get('full_time_only', False)
            )
            filtered_jobs = job_type_filter.filter(filtered_jobs)
        
        self._stats['final_count'] = len(filtered_jobs)
        
        self.logger.info(f"Main filter: {self._stats['original_count']} → {self._stats['final_count']} jobs")
        return filtered_jobs
    
    def filter_jobs(self, jobs: List[Dict], filter_config: Dict[str, Any]) -> List[Dict]:
        """
        Filter jobs based on configuration (for backward compatibility).
        
        Args:
            jobs: List of job dictionaries
            filter_config: Filter configuration
            
        Returns:
            Filtered list of job dictionaries
        """
        self.config = filter_config
        return self.filter(jobs)


class DuplicateRemover(JobFilter):
    """Remove duplicate job postings"""
    
    def __init__(self, similarity_threshold: float = 0.9):
        """
        Initialize duplicate remover.
        
        Args:
            similarity_threshold: Threshold for considering jobs as duplicates (0.0-1.0)
        """
        super().__init__()
        self.similarity_threshold = similarity_threshold
        self._stats = {'original_count': 0, 'duplicates_removed': 0, 'final_count': 0}
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        if not text or text == 'N/A':
            return ""
        
        # Convert to lowercase and remove extra whitespace
        text = re.sub(r'\s+', ' ', text.lower().strip())
        
        # Remove common variations
        text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
        text = re.sub(r'\b(inc|corp|ltd|llc|co)\b', '', text)  # Remove company suffixes
        
        return text
    
    def _create_job_signature(self, job: Dict) -> str:
        """Create a unique signature for a job"""
        title = self._normalize_text(job.get('title', ''))
        company = self._normalize_text(job.get('company', ''))
        location = self._normalize_text(job.get('location', ''))
        
        # Create a hash of the normalized fields
        signature_text = f"{title}|{company}|{location}"
        return hashlib.md5(signature_text.encode()).hexdigest()
    
    def _calculate_similarity(self, job1: Dict, job2: Dict) -> float:
        """Calculate similarity between two jobs"""
        # Simple Jaccard similarity based on word sets
        def get_words(job: Dict) -> Set[str]:
            title = self._normalize_text(job.get('title', ''))
            company = self._normalize_text(job.get('company', ''))
            return set(f"{title} {company}".split())
        
        words1 = get_words(job1)
        words2 = get_words(job2)
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def filter(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate jobs"""
        self._stats['original_count'] = len(jobs)
        
        if not jobs:
            return jobs
        
        unique_jobs = []
        seen_signatures = set()
        
        for job in jobs:
            signature = self._create_job_signature(job)
            
            if signature not in seen_signatures:
                # Check for similar jobs using similarity threshold
                is_duplicate = False
                
                for existing_job in unique_jobs:
                    similarity = self._calculate_similarity(job, existing_job)
                    if similarity >= self.similarity_threshold:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_jobs.append(job)
                    seen_signatures.add(signature)
        
        self._stats['duplicates_removed'] = len(jobs) - len(unique_jobs)
        self._stats['final_count'] = len(unique_jobs)
        
        self.logger.info(f"Removed {self._stats['duplicates_removed']} duplicates "
                        f"from {self._stats['original_count']} jobs")
        
        return unique_jobs


class ExperienceFilter(JobFilter):
    """Filter jobs by experience level"""
    
    def __init__(self, allowed_levels: List[str]):
        """
        Initialize experience filter.
        
        Args:
            allowed_levels: List of allowed experience levels ('entry', 'mid', 'senior')
        """
        super().__init__()
        self.allowed_levels = [level.lower() for level in allowed_levels] if allowed_levels else []
        self._stats = {'original_count': 0, 'filtered_out': 0, 'final_count': 0}
    
    def _detect_experience_level(self, job_title: str, company: str = "") -> str:
        """Detect experience level from job title and company"""
        if not job_title:
            return 'mid'
            
        title_lower = job_title.lower()
        
        # Entry level keywords
        entry_keywords = [
            'junior', 'trainee', 'intern', 'entry', 'graduate', 'fresher',
            'associate', 'beginner', 'apprentice', '0-1 year', '0-2 year',
            'new grad', 'recent graduate', 'jr.', 'jr '
        ]
        
        # Senior level keywords
        senior_keywords = [
            'senior', 'sr.', 'sr ', 'lead', 'principal', 'architect', 'manager',
            'head', 'director', 'chief', 'expert', '5+ year', '7+ year',
            'team lead', 'tech lead', 'technical lead', 'staff', 'principal'
        ]
        
        # Mid level keywords
        mid_keywords = [
            'mid', 'intermediate', 'regular', '2-5 year', '3-6 year',
            'experienced', 'specialist', 'developer ii', 'engineer ii'
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
    
    def filter(self, jobs: List[Dict]) -> List[Dict]:
        """Filter jobs by experience level"""
        self._stats['original_count'] = len(jobs)
        
        if not self.allowed_levels:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            # Detect or use existing experience level
            if 'experience_level' not in job:
                job['experience_level'] = self._detect_experience_level(
                    job.get('title', ''), job.get('company', '')
                )
            
            if job['experience_level'].lower() in self.allowed_levels:
                filtered_jobs.append(job)
        
        self._stats['filtered_out'] = len(jobs) - len(filtered_jobs)
        self._stats['final_count'] = len(filtered_jobs)
        
        self.logger.info(f"Experience filter: kept {len(filtered_jobs)} jobs "
                        f"(filtered out {self._stats['filtered_out']})")
        
        return filtered_jobs


class CompanyFilter(JobFilter):
    """Filter jobs by company preferences"""
    
    def __init__(self, include_companies: Optional[List[str]] = None,
                 exclude_companies: Optional[List[str]] = None):
        """
        Initialize company filter.
        
        Args:
            include_companies: List of companies to include (None = include all)
            exclude_companies: List of companies to exclude
        """
        super().__init__()
        self.include_companies = [c.lower().strip() for c in include_companies] if include_companies else None
        self.exclude_companies = [c.lower().strip() for c in exclude_companies] if exclude_companies else []
        self._stats = {'original_count': 0, 'filtered_out': 0, 'final_count': 0}
    
    def filter(self, jobs: List[Dict]) -> List[Dict]:
        """Filter jobs by company preferences"""
        self._stats['original_count'] = len(jobs)
        
        if not self.include_companies and not self.exclude_companies:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            company_name = job.get('company', '').lower().strip()
            
            # Check exclude list first
            if self.exclude_companies:
                if any(excluded in company_name for excluded in self.exclude_companies):
                    continue
            
            # Check include list
            if self.include_companies:
                if not any(included in company_name for included in self.include_companies):
                    continue
            
            filtered_jobs.append(job)
        
        self._stats['filtered_out'] = len(jobs) - len(filtered_jobs)
        self._stats['final_count'] = len(filtered_jobs)
        
        self.logger.info(f"Company filter: kept {len(filtered_jobs)} jobs "
                        f"(filtered out {self._stats['filtered_out']})")
        
        return filtered_jobs


class KeywordFilter(JobFilter):
    """Filter jobs by keywords in title and description"""
    
    def __init__(self, required_keywords: List[str], excluded_keywords: List[str]):
        """
        Initialize keyword filter.
        
        Args:
            required_keywords: List of keywords that must be present
            excluded_keywords: List of keywords that must not be present
        """
        super().__init__()
        self.required_keywords = [k.lower().strip() for k in required_keywords] if required_keywords else []
        self.excluded_keywords = [k.lower().strip() for k in excluded_keywords] if excluded_keywords else []
        self._stats = {'original_count': 0, 'filtered_out': 0, 'final_count': 0}
    
    def filter(self, jobs: List[Dict]) -> List[Dict]:
        """Filter jobs by keywords"""
        self._stats['original_count'] = len(jobs)
        
        if not self.required_keywords and not self.excluded_keywords:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            title = job.get('title', '').lower()
            description = job.get('description', '').lower()
            content = f"{title} {description}"
            
            # Check required keywords
            if self.required_keywords:
                if not any(keyword in content for keyword in self.required_keywords):
                    continue
            
            # Check excluded keywords
            if self.excluded_keywords:
                if any(keyword in content for keyword in self.excluded_keywords):
                    continue
            
            filtered_jobs.append(job)
        
        self._stats['filtered_out'] = len(jobs) - len(filtered_jobs)
        self._stats['final_count'] = len(filtered_jobs)
        
        self.logger.info(f"Keyword filter: kept {len(filtered_jobs)} jobs "
                        f"(filtered out {self._stats['filtered_out']})")
        
        return filtered_jobs


class SalaryFilter(JobFilter):
    """Filter jobs by salary range"""
    
    def __init__(self, min_salary: Optional[int] = None, max_salary: Optional[int] = None):
        """
        Initialize salary filter.
        
        Args:
            min_salary: Minimum salary requirement
            max_salary: Maximum salary requirement
        """
        super().__init__()
        self.min_salary = min_salary
        self.max_salary = max_salary
        self._stats = {'original_count': 0, 'filtered_out': 0, 'final_count': 0}
    
    def _extract_salary_numbers(self, salary_str: str) -> Optional[int]:
        """Extract numeric salary from salary string"""
        if not salary_str or salary_str == 'N/A':
            return None
        
        # Remove common prefixes and suffixes
        salary_str = salary_str.replace('$', '').replace(',', '').replace('k', '000').replace('K', '000')
        
        # Extract numbers
        numbers = re.findall(r'\d+', salary_str)
        if numbers:
            # Take the first number (often the minimum or average)
            return int(numbers[0])
        
        return None
    
    def filter(self, jobs: List[Dict]) -> List[Dict]:
        """Filter jobs by salary range"""
        self._stats['original_count'] = len(jobs)
        
        if not self.min_salary and not self.max_salary:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            salary_str = job.get('salary', '')
            salary_num = self._extract_salary_numbers(salary_str)
            
            # If no salary info, include the job (better to be inclusive)
            if salary_num is None:
                filtered_jobs.append(job)
                continue
            
            # Check salary range
            if self.min_salary and salary_num < self.min_salary:
                continue
            if self.max_salary and salary_num > self.max_salary:
                continue
            
            filtered_jobs.append(job)
        
        self._stats['filtered_out'] = len(jobs) - len(filtered_jobs)
        self._stats['final_count'] = len(filtered_jobs)
        
        self.logger.info(f"Salary filter: kept {len(filtered_jobs)} jobs "
                        f"(filtered out {self._stats['filtered_out']})")
        
        return filtered_jobs


class JobTypeFilter(JobFilter):
    """Filter jobs by type (remote, full-time, etc.)"""
    
    def __init__(self, remote_only: bool = False, full_time_only: bool = False):
        """
        Initialize job type filter.
        
        Args:
            remote_only: Only include remote jobs
            full_time_only: Only include full-time jobs
        """
        super().__init__()
        self.remote_only = remote_only
        self.full_time_only = full_time_only
        self._stats = {'original_count': 0, 'filtered_out': 0, 'final_count': 0}
    
    def filter(self, jobs: List[Dict]) -> List[Dict]:
        """Filter jobs by type"""
        self._stats['original_count'] = len(jobs)
        
        if not self.remote_only and not self.full_time_only:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            location = job.get('location', '').lower()
            job_type = job.get('job_type', '').lower()
            title = job.get('title', '').lower()
            
            # Check remote requirement
            if self.remote_only:
                if 'remote' not in location and 'remote' not in job_type:
                    continue
            
            # Check full-time requirement
            if self.full_time_only:
                if 'full' not in job_type and 'full-time' not in title:
                    # If no job type info, assume it's full-time
                    if job_type and 'part' in job_type:
                        continue
            
            filtered_jobs.append(job)
        
        self._stats['filtered_out'] = len(jobs) - len(filtered_jobs)
        self._stats['final_count'] = len(filtered_jobs)
        
        self.logger.info(f"Job type filter: kept {len(filtered_jobs)} jobs "
                        f"(filtered out {self._stats['filtered_out']})")
        
        return filtered_jobs


class DateFilter(JobFilter):
    """Filter jobs by posting date"""
    
    def __init__(self, max_age_hours: int = 72):
        """
        Initialize date filter.
        
        Args:
            max_age_hours: Maximum age of jobs in hours
        """
        super().__init__()
        self.max_age_hours = max_age_hours
        self._stats = {'original_count': 0, 'filtered_out': 0, 'final_count': 0}
    
    def _parse_posting_date(self, date_str: str) -> Optional[datetime]:
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
        
        # Try to parse absolute dates using dateutil if available
        if HAS_DATEUTIL:
            try:
                return dateutil.parser.parse(date_str)
            except:
                pass
        
        # Basic date parsing fallback
        try:
            # Try common formats
            for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        except:
            pass
        
        return None
    
    def _is_within_time_filter(self, posted_date: datetime) -> bool:
        """Check if job was posted within the specified hours"""
        if not posted_date:
            return False
        
        now = datetime.now()
        time_diff = now - posted_date
        return time_diff.total_seconds() / 3600 <= self.max_age_hours
    
    def filter(self, jobs: List[Dict]) -> List[Dict]:
        """Filter jobs by posting date"""
        self._stats['original_count'] = len(jobs)
        
        filtered_jobs = []
        
        for job in jobs:
            posted_date = self._parse_posting_date(job.get('posted_date', ''))
            
            if posted_date is None:
                # If we can't parse the date, include the job (better to be inclusive)
                filtered_jobs.append(job)
            elif self._is_within_time_filter(posted_date):
                filtered_jobs.append(job)
        
        self._stats['filtered_out'] = len(jobs) - len(filtered_jobs)
        self._stats['final_count'] = len(filtered_jobs)
        
        self.logger.info(f"Date filter: kept {len(filtered_jobs)} jobs posted within "
                        f"{self.max_age_hours} hours (filtered out {self._stats['filtered_out']})")
        
        return filtered_jobs


class LocationFilter(JobFilter):
    """Filter jobs by location preferences"""
    
    def __init__(self, preferred_locations: Optional[List[str]] = None, 
                 excluded_locations: Optional[List[str]] = None,
                 allow_remote: bool = True,
                 exact_match: bool = False):
        """
        Initialize location filter.
        
        Args:
            preferred_locations: List of preferred locations (None = include all)
            excluded_locations: List of locations to exclude
            allow_remote: Whether to include remote jobs
            exact_match: Whether to require exact location match (vs substring match)
        """
        super().__init__()
        self.preferred_locations = [loc.lower().strip() for loc in preferred_locations] if preferred_locations else None
        self.excluded_locations = [loc.lower().strip() for loc in excluded_locations] if excluded_locations else []
        self.allow_remote = allow_remote
        self.exact_match = exact_match
        self._stats = {'original_count': 0, 'filtered_out': 0, 'final_count': 0}
    
    def _normalize_location(self, location: str) -> str:
        """Normalize location string for comparison"""
        if not location or location == 'N/A':
            return ""
        
        # Convert to lowercase and remove extra whitespace
        location = location.lower().strip()
        
        # Remove common location suffixes and prefixes
        location = re.sub(r'\b(usa|us|united states)\b', '', location)
        location = re.sub(r'\b(ca|california)\b', 'california', location)
        location = re.sub(r'\b(ny|new york)\b', 'new york', location)
        location = re.sub(r'\b(fl|florida)\b', 'florida', location)
        location = re.sub(r'\b(tx|texas)\b', 'texas', location)
        
        # Remove common separators and extra spaces
        location = re.sub(r'[,\-\(\)]', ' ', location)
        location = re.sub(r'\s+', ' ', location).strip()
        
        return location
    
    def _is_remote_job(self, location: str) -> bool:
        """Check if job is remote"""
        if not location:
            return False
        
        location_lower = location.lower()
        remote_keywords = [
            'remote', 'work from home', 'wfh', 'telecommute', 
            'distributed', 'anywhere', 'virtual', 'home-based'
        ]
        
        return any(keyword in location_lower for keyword in remote_keywords)
    
    def _location_matches(self, job_location: str, preferred_location: str) -> bool:
        """Check if job location matches preferred location"""
        if not job_location or not preferred_location:
            return False
        
        job_loc = self._normalize_location(job_location)
        pref_loc = self._normalize_location(preferred_location)
        
        if self.exact_match:
            return job_loc == pref_loc
        else:
            # Check if preferred location is contained in job location or vice versa
            return pref_loc in job_loc or job_loc in pref_loc
    
    def filter(self, jobs: List[Dict]) -> List[Dict]:
        """Filter jobs by location preferences"""
        self._stats['original_count'] = len(jobs)
        
        # If no location preferences set, return all jobs
        if not self.preferred_locations and not self.excluded_locations:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            location = job.get('location', '')
            
            # Check if it's a remote job
            is_remote = self._is_remote_job(location)
            
            # If it's remote and remote jobs are allowed, include it
            if is_remote and self.allow_remote:
                filtered_jobs.append(job)
                continue
            
            # Check excluded locations first
            if self.excluded_locations:
                excluded = False
                for excluded_loc in self.excluded_locations:
                    if self._location_matches(location, excluded_loc):
                        excluded = True
                        break
                if excluded:
                    continue
            
            # Check preferred locations
            if self.preferred_locations:
                matched = False
                for preferred_loc in self.preferred_locations:
                    if self._location_matches(location, preferred_loc):
                        matched = True
                        break
                if matched:
                    filtered_jobs.append(job)
            else:
                # If no preferred locations specified, include the job
                # (assuming it passed the excluded locations check)
                filtered_jobs.append(job)
        
        self._stats['filtered_out'] = len(jobs) - len(filtered_jobs)
        self._stats['final_count'] = len(filtered_jobs)
        
        self.logger.info(f"Location filter: kept {len(filtered_jobs)} jobs "
                        f"(filtered out {self._stats['filtered_out']})")
        
        return filtered_jobs


# Convenience functions for backward compatibility
def deduplicate_jobs(jobs: List[Dict], similarity_threshold: float = 0.9) -> List[Dict]:
    """Remove duplicate jobs from a list"""
    deduplicator = DuplicateRemover(similarity_threshold)
    return deduplicator.filter(jobs)


def filter_jobs_by_criteria(jobs: List[Dict], criteria: Dict[str, Any]) -> List[Dict]:
    """Filter jobs by multiple criteria"""
    main_filter = MainJobFilter(criteria)
    return main_filter.filter(jobs)


class FilterPipeline:
    """Pipeline for applying multiple filters in sequence"""
    
    def __init__(self):
        self.filters = []
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def add_filter(self, filter_instance: JobFilter):
        """Add a filter to the pipeline"""
        self.filters.append(filter_instance)
    
    def apply_filters(self, jobs: List[Dict]) -> List[Dict]:
        """Apply all filters in the pipeline"""
        self.logger.info(f"Starting filter pipeline with {len(jobs)} jobs")
        
        filtered_jobs = jobs
        total_stats = {}
        
        for i, filter_instance in enumerate(self.filters):
            filter_name = filter_instance.__class__.__name__
            before_count = len(filtered_jobs)
            
            filtered_jobs = filter_instance.filter(filtered_jobs)
            after_count = len(filtered_jobs)
            
            filtered_out = before_count - after_count
            total_stats[filter_name] = {
                'before': before_count,
                'after': after_count,
                'filtered_out': filtered_out
            }
            
            self.logger.info(f"Filter {i+1}/{len(self.filters)} ({filter_name}): "
                           f"{before_count} → {after_count} jobs")
        
        self.logger.info(f"Filter pipeline completed: {len(jobs)} → {len(filtered_jobs)} jobs")
        return filtered_jobs
    
    def get_pipeline_stats(self) -> Dict:
        """Get statistics for all filters in the pipeline"""
        return {f.__class__.__name__: f.get_stats() for f in self.filters}


if __name__ == "__main__":
    # Test the filtering system
    import logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')
    
    # Sample job data for testing
    sample_jobs = [
        {
            'title': 'Senior Python Developer',
            'company': 'Google Inc',
            'location': 'San Francisco, CA',
            'posted_date': '1 day ago',
            'source': 'LinkedIn',
            'salary': '$120,000'
        },
        {
            'title': 'Senior Python Developer',  # Duplicate
            'company': 'Google',
            'location': 'San Francisco',
            'posted_date': '2 days ago',
            'source': 'Indeed',
            'salary': '$115,000'
        },
        {
            'title': 'Junior Software Engineer',
            'company': 'Meta',
            'location': 'Remote',
            'posted_date': '3 hours ago',
            'source': 'LinkedIn',
            'salary': '$80,000'
        },
        {
            'title': 'Data Scientist',
            'company': 'BadCompany Ltd',
            'location': 'New York, NY',
            'posted_date': '1 week ago',
            'source': 'Indeed',
            'salary': '$100,000'
        }
    ]
    
    print("🔍 Testing Job Filters")
    print("=" * 30)
    print(f"Starting with {len(sample_jobs)} sample jobs")
    
    # Test main filter
    filter_config = {
        'experience_levels': ['senior', 'entry'],
        'exclude_companies': ['BadCompany'],
        'keywords': ['python', 'software'],
        'max_age_days': 2
    }
    
    main_filter = MainJobFilter(filter_config)
    filtered_jobs = main_filter.filter(sample_jobs)
    
    print(f"\n📊 Final Results: {len(filtered_jobs)} jobs")
    for i, job in enumerate(filtered_jobs, 1):
        print(f"{i}. {job['title']} at {job['company']} ({job['location']})")
    
    # Test deduplication
    print(f"\n🔄 Testing deduplication...")
    deduplicated_jobs = deduplicate_jobs(sample_jobs)
    print(f"After deduplication: {len(deduplicated_jobs)} jobs")
