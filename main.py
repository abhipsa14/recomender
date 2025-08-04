#!/usr/bin/env python3
"""
Job Scraper Project - Main Entry Point
Orchestrates job scraping from multiple sources with filtering and export capabilities.
"""

import logging
import argparse
import yaml
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from manager.scraper_manager import ScraperManager
    from filters.job_filter import MainJobFilter, deduplicate_jobs
    from utils.exporter import CSVExporter, JSONExporter, ExcelExporter  # Fixed import
    from utils.logger import setup_logger
    # Email sender commented out as it's not implemented yet
    # from utils.emailer import EmailSender
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all required modules are in place.")
    sys.exit(1)


def load_config(config_path: str = "configs/settings.yaml") -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
            print(f"✅ Configuration loaded from {config_path}")
            return config
    except FileNotFoundError:
        print(f"⚠️  Config file {config_path} not found. Using default settings.")
        return get_default_config()
    except yaml.YAMLError as e:
        print(f"❌ Error reading config file: {e}. Using default settings.")
        return get_default_config()


def get_default_config() -> dict:
    """Get default configuration"""
    return {
        'search': {
            'terms': ['Python Developer', 'Data Scientist'],
            'locations': ['San Francisco', 'New York'],
            'pages_per_source': 2
        },
        'scrapers': {
            'enabled': ['linkedin', 'indeed', 'google'],
            'parallel': True,
            'max_workers': 3,
            'delay': 2.0
        },
        'filters': {
            'min_salary': None,
            'max_salary': None,
            'experience_levels': ['entry', 'mid', 'senior'],
            'exclude_companies': [],
            'include_companies': [],
            'keywords': ['python', 'programming'],
            'exclude_keywords': ['sales', 'marketing'],
            'max_age_days': 30,
            'remote_only': False,
            'full_time_only': False
        },
        'output': {
            'format': 'csv',
            'filename': 'jobs_{timestamp}.csv',
            'include_duplicates': False,
            'sort_by': 'posted_date',
            'sort_order': 'desc'
        },
        'email': {
            'enabled': False,
            'recipient': 'your-email@example.com',
            'sender': 'scraper@example.com',
            'sender_password': 'your-app-password',
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'subject_template': 'Job Alert: {job_count} new jobs found',
            'include_attachments': True,
            'max_jobs_in_email': 20
        },
        'logging': {
            'level': 'INFO',
            'file': 'logs/scraper.log'
        }
    }


def ensure_directories_exist():
    """Create necessary directories if they don't exist"""
    directories = ['logs', 'data', 'data/output']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def validate_config(config: dict) -> bool:
    """Validate configuration structure"""
    required_sections = ['search', 'scrapers', 'filters', 'output']
    
    for section in required_sections:
        if section not in config:
            print(f"❌ Missing required config section: {section}")
            return False
    
    # Validate search terms
    if not config['search'].get('terms'):
        print("❌ No search terms specified")
        return False
    
    # Validate locations
    if not config['search'].get('locations'):
        print("❌ No locations specified")
        return False
    
    # Validate enabled scrapers
    if not config['scrapers'].get('enabled'):
        print("❌ No scrapers enabled")
        return False
    
    return True


def display_config_summary(config: dict):
    """Display configuration summary"""
    print("\n📋 Configuration Summary:")
    print("=" * 50)
    print(f"🔍 Search Terms: {', '.join(config['search']['terms'][:3])}")
    if len(config['search']['terms']) > 3:
        print(f"    ... and {len(config['search']['terms']) - 3} more")
    
    print(f"📍 Locations: {', '.join(config['search']['locations'][:3])}")
    if len(config['search']['locations']) > 3:
        print(f"    ... and {len(config['search']['locations']) - 3} more")
    
    print(f"🌐 Scrapers: {', '.join(config['scrapers']['enabled'])}")
    print(f"📄 Pages per source: {config['search']['pages_per_source']}")
    print(f"📊 Output format: {config['output']['format']}")
    print(f"📧 Email enabled: {'Yes' if config['email']['enabled'] else 'No'}")
    print("=" * 50)


def display_sample_jobs(jobs: List[Dict], max_display: int = 5):
    """Display sample job results"""
    if not jobs:
        print("No jobs to display")
        return
    
    print(f"\n📋 Sample Jobs (showing {min(len(jobs), max_display)} of {len(jobs)}):")
    print("=" * 80)
    
    for i, job in enumerate(jobs[:max_display], 1):
        title = job.get('title', 'N/A')
        company = job.get('company', 'N/A')
        location = job.get('location', 'N/A')
        source = job.get('source', 'N/A')
        salary = job.get('salary', '')
        posted_date = job.get('posted_date', '')
        
        print(f"{i}. {title}")
        print(f"   🏢 {company}")
        print(f"   📍 {location}")
        print(f"   🌐 Source: {source}")
        
        if salary:
            print(f"   💰 {salary}")
        if posted_date:
            print(f"   📅 Posted: {posted_date}")
        
        if job.get('url'):
            print(f"   🔗 {job['url']}")
        
        print("-" * 80)


def main():
    """Main function to orchestrate job scraping"""
    parser = argparse.ArgumentParser(
        description='Job Scraper - Multi-platform job aggregator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py                                    # Run with default config
  python3 main.py --test --verbose                   # Quick test run
  python3 main.py --search "Python Developer"        # Override search term
  python3 main.py --location "Remote"                # Override location
  python3 main.py --scrapers linkedin indeed         # Use specific scrapers
  python3 main.py --output "my_jobs.csv"            # Custom output file
  python3 main.py --no-email                        # Disable email
        """
    )
    
    parser.add_argument('--config', '-c', default='configs/settings.yaml', 
                       help='Path to configuration file')
    parser.add_argument('--search', '-s', help='Search term override')
    parser.add_argument('--location', '-l', help='Location override')
    parser.add_argument('--pages', '-p', type=int, help='Pages per source override')
    parser.add_argument('--scrapers', nargs='+', help='Specific scrapers to use')
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--no-email', action='store_true', help='Disable email sending')
    parser.add_argument('--test', action='store_true', help='Run in test mode (minimal scraping)')
    parser.add_argument('--show-config', action='store_true', help='Show configuration and exit')
    
    args = parser.parse_args()
    
    # Ensure required directories exist
    ensure_directories_exist()
    
    # Load configuration
    config = load_config(args.config)
    
    if not validate_config(config):
        print("❌ Configuration validation failed. Exiting.")
        sys.exit(1)
    
    # Override config with command line arguments
    if args.search:
        config['search']['terms'] = [args.search]
    if args.location:
        config['search']['locations'] = [args.location]
    if args.pages:
        config['search']['pages_per_source'] = args.pages
    if args.scrapers:
        config['scrapers']['enabled'] = args.scrapers
    if args.no_email:
        config['email']['enabled'] = False
    if args.test:
        config['search']['pages_per_source'] = 1
        config['scrapers']['enabled'] = config['scrapers']['enabled'][:2]  # Use only first 2 scrapers
        print("🧪 Running in TEST MODE - limited scraping")
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else getattr(logging, config['logging']['level'].upper())
    logger = setup_logger("my_logger", level=log_level)
    
    # Display configuration
    display_config_summary(config)
    
    if args.show_config:
        print("\n🔧 Full Configuration:")
        print(yaml.dump(config, default_flow_style=False, indent=2))
        return
    
    print(f"\n🚀 Starting Job Scraper")
    
    try:
        # Initialize components
        logger.info("Initializing scraper components...")
        scraper_manager = ScraperManager(
            max_workers=config['scrapers']['max_workers'],
            default_delay=config['scrapers']['delay']
        )
        
        job_filter = MainJobFilter()  # Changed from JobFilter() to MainJobFilter()
        
        # Validate scrapers
        print("🔍 Validating scrapers...")
        validation_results = scraper_manager.validate_scrapers()
        
        valid_scrapers = []
        for name, status in validation_results.items():
            if name in config['scrapers']['enabled']:
                status_icon = "✅" if status else "❌"
                print(f"  {status_icon} {name}")
                if status:
                    valid_scrapers.append(name)
        
        if not valid_scrapers:
            print("❌ No valid scrapers available. Exiting.")
            sys.exit(1)
        
        config['scrapers']['enabled'] = valid_scrapers
        
        # Scrape jobs
        all_jobs = []
        total_combinations = len(config['search']['terms']) * len(config['search']['locations'])
        current_combination = 0
        
        print(f"\n🔄 Starting scraping process...")
        start_time = datetime.now()
        
        for search_term in config['search']['terms']:
            for location in config['search']['locations']:
                current_combination += 1
                print(f"\n📍 [{current_combination}/{total_combinations}] Scraping: '{search_term}' in '{location}'")
                
                jobs = scraper_manager.scrape_multiple_sources(
                    scraper_names=config['scrapers']['enabled'],
                    search_term=search_term,
                    location=location,
                    num_pages=config['search']['pages_per_source'],
                    parallel=config['scrapers']['parallel']
                )
                
                if jobs:
                    print(f"  Found {len(jobs)} jobs")
                    all_jobs.extend(jobs)
                else:
                    print("  No jobs found")
        
        scraping_duration = (datetime.now() - start_time).total_seconds()
        
        # Display statistics
        stats = scraper_manager.get_scraping_stats()
        print(f"\n📊 Scraping Summary:")
        print(f"  Total jobs found: {len(all_jobs)}")
        print(f"  Jobs by source: {stats['jobs_by_source']}")
        print(f"  Duration: {scraping_duration:.2f}s")
        
        if stats['failed_scrapers']:
            print(f"  ⚠️  Failed scrapers: {stats['failed_scrapers']}")
        
        if not all_jobs:
            print("❌ No jobs found. Try adjusting your search terms or locations.")
            return
        
        # Filter and deduplicate jobs
        print("\n🔧 Processing jobs...")
        
        # Apply filters
        print("  Applying filters...")
        filtered_jobs = job_filter.filter_jobs(all_jobs, config['filters'])  # This method exists in MainJobFilter
        print(f"  After filtering: {len(filtered_jobs)} jobs")
        
        # Deduplicate
        if not config['output']['include_duplicates']:
            print("  Removing duplicates...")
            unique_jobs = deduplicate_jobs(filtered_jobs)
            print(f"  After deduplication: {len(unique_jobs)} jobs")
            final_jobs = unique_jobs
        else:
            final_jobs = filtered_jobs
        
        if not final_jobs:
            print("❌ No jobs remaining after filtering. Try adjusting your filter criteria.")
            return
        
        # Sort jobs
        sort_by = config['output'].get('sort_by', 'posted_date')
        sort_order = config['output'].get('sort_order', 'desc')
        
        if sort_by and sort_by in ['title', 'company', 'location', 'posted_date', 'salary']:
            reverse = (sort_order == 'desc')
            final_jobs.sort(key=lambda x: x.get(sort_by, ''), reverse=reverse)
        
        # Export data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if args.output:
            output_file = args.output
        else:
            filename_template = config['output']['filename']
            output_file = filename_template.format(timestamp=timestamp)
        
        # Ensure output directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"\n💾 Exporting to {output_file}")
        
        exporter = ['CSVExporter', 'JSONExporter', 'ExcelExporter'][0]  # Default to CSVExporter
        if config['output']['format'] == 'csv':
            csvexporter = CSVExporter()
        elif config['output']['format'] == 'json':
            jsonexporter = JSONExporter()
        elif config['output']['format'] == 'excel':
            excelexporter = ExcelExporter()

        try:
            if config['output']['format'] == 'csv' or output_file.endswith('.csv'):
                csvexporter.export(final_jobs, output_file)
            elif config['output']['format'] == 'json' or output_file.endswith('.json'):
                json_file = output_file.replace('.csv', '.json') if output_file.endswith('.csv') else output_file
                jsonexporter.export(final_jobs, json_file)
                output_file = json_file
            elif config['output']['format'] == 'excel' or output_file.endswith('.xlsx'):
                excel_file = output_file.replace('.csv', '.xlsx') if output_file.endswith('.csv') else output_file
                excelexporter.export(final_jobs, excel_file)
                output_file = excel_file
            else:
                # Default to CSV
                csvexporter.export(final_jobs, output_file)

            print(f"  ✅ Successfully exported {len(final_jobs)} jobs")
            
        except Exception as e:
            print(f"  ❌ Export failed: {e}")
            logger.error(f"Export failed: {e}")
        
        # Send email if enabled
        if config['email']['enabled'] and not args.no_email:
            print("\n📧 Sending email notification...")
            print("  ❌ Email sending is not available (EmailSender not found).")
            logger.warning("Email sending skipped: EmailSender not found.")
        
        # Display sample results
        display_sample_jobs(final_jobs, max_display=5)
        
        print(f"\n✅ Job scraping completed successfully!")
        print(f"📁 Results saved to: {output_file}")
        print(f"📊 Total jobs: {len(final_jobs)}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Scraping interrupted by user")
        logger.info("Scraping interrupted by user")
        
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        
        if args.verbose:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()