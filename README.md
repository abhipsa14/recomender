# 🎯 Job Recommender System

An AI-powered job recommendation system that scrapes multiple job sites, applies intelligent filtering and ranking, and sends personalized job recommendations via email.

## ✨ Features

- **Multi-Site Scraping**: Scrapes jobs from LinkedIn, Indeed, and Glassdoor
- **AI-Powered Recommendations**: Intelligent scoring based on user preferences
- **Email Notifications**: Beautiful HTML emails with job recommendations
- **Multiple Export Formats**: CSV, JSON, and Excel exports
- **Smart Filtering**: Filter by experience level, companies, keywords, and posting date
- **User Preferences**: Save and customize your job search criteria
- **Duplicate Detection**: Automatically removes duplicate job postings

## 🚀 Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd recomender
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your email configuration:
```bash
# Edit config.py and add your email credentials
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'use_tls': True,
    'sender_email': 'your-email@gmail.com',
    'sender_password': 'your-app-password',  # Use app password for Gmail
}
```

### Basic Usage

1. **Setup your preferences** (first time):
```bash
python job_recommender.py --setup
```

2. **Run job search** with email and export:
```bash
python job_recommender.py --search
```

3. **Run job search** without email:
```bash
python job_recommender.py --search --no-email
```

4. **Show detailed results** for top 10 jobs:
```bash
python job_recommender.py --search --show-details 10
```

## 📋 Command Line Options

```bash
python job_recommender.py [OPTIONS]

Options:
  --setup              Setup user preferences interactively
  --search             Run job search (default if no args)
  --no-email           Skip sending email notifications
  --no-export          Skip exporting data to files
  --show-details N     Show detailed info for top N jobs
  --config FILE        Use custom configuration file (default: user_preferences.json)
```

## ⚙️ Configuration

### User Preferences

The system uses a `user_preferences.json` file to store your settings:

```json
{
  "job_titles": ["Python Developer", "Data Scientist", "Software Engineer"],
  "locations": ["San Francisco", "New York", "Remote"],
  "experience_levels": ["entry", "mid", "senior"],
  "companies_to_include": ["Google", "Microsoft", "Apple"],
  "companies_to_exclude": ["BadCompany Inc"],
  "keywords": ["python", "machine learning", "api"],
  "max_age_hours": 72,
  "sites_to_scrape": ["linkedin", "indeed", "glassdoor"],
  "pages_per_site": 2,
  "email": "your-email@example.com",
  "notification_frequency": "daily",
  "output_format": "csv"
}
```

### Email Configuration

Update `config.py` with your email settings:

```python
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',  # Change based on your provider
    'smtp_port': 587,
    'use_tls': True,
    'sender_email': 'your-email@gmail.com',
    'sender_password': 'your-app-password',
}
```

**Gmail Setup:**
1. Enable 2-factor authentication
2. Generate an app-specific password
3. Use the app password in the configuration

## 🧠 AI Recommendation Engine

The system uses a sophisticated scoring algorithm that considers:

- **Title Match** (30%): How well the job title matches your preferences
- **Location Match** (20%): Geographic preference matching
- **Company Preference** (20%): Preferred or excluded companies
- **Experience Match** (15%): Alignment with your experience level
- **Keyword Match** (10%): Presence of your specified keywords
- **Freshness** (5%): How recently the job was posted

Each job receives a score from 0-100%, with higher scores indicating better matches.

## 📊 Output Formats

### CSV Export
```csv
Title,Company,Location,Experience Level,Posted Date,Source,Link,Recommendation Score
Senior Python Developer,Google,San Francisco,senior,2 days ago,LinkedIn,https://...,92.5
```

### JSON Export
```json
{
  "generated_at": "2025-01-01T10:00:00",
  "total_jobs": 50,
  "jobs": [
    {
      "title": "Senior Python Developer",
      "company": "Google",
      "location": "San Francisco",
      "experience_level": "senior",
      "recommendation_score": 92.5,
      "score_breakdown": {
        "title_match": 0.9,
        "location_match": 1.0,
        "company_preference": 1.0
      }
    }
  ]
}
```

### Email Report
Beautiful HTML emails with:
- Executive summary
- Top job matches with scores
- Direct apply links
- Company ratings and salary info (when available)

## 🔧 Advanced Usage

### Custom Scrapers

Add new job sites by creating scrapers in the `scrapper_module/` directory:

```python
class NewSiteScraper:
    def __init__(self):
        # Initialize scraper
        pass
    
    def scrape_jobs(self, search_term, location, num_pages):
        # Implement scraping logic
        return jobs_list
```

### Programmatic Usage

```python
from job_recommender import JobRecommenderSystem

# Initialize system
system = JobRecommenderSystem('my_preferences.json')

# Run job search
jobs = system.run_job_search(send_email=False, export_data=True)

# Get top recommendations
top_jobs = jobs[:10]

# Export specific format
system.export_jobs(jobs, 'excel')
```

## 📁 Project Structure

```
recomender/
├── main.py                     # Core scraping logic and base classes
├── job_recommender.py          # Main application entry point
├── recommendation_engine.py    # AI recommendation system
├── email_sender.py            # Email functionality and data export
├── config.py                  # Configuration settings
├── requirements.txt           # Python dependencies
├── user_preferences.json      # User settings (generated)
└── scrapper_module/
    ├── linkedin.py            # LinkedIn scraper
    ├── indeed.py              # Indeed scraper
    └── glassdoor.py           # Glassdoor scraper
```

## 🤖 Automation

### Cron Job Setup

Run automated job searches daily:

```bash
# Add to crontab (crontab -e)
0 9 * * * /usr/bin/python3 /path/to/recomender/job_recommender.py --search
```

### Systemd Timer (Linux)

Create a systemd service and timer for more robust scheduling:

```bash
# /etc/systemd/system/job-recommender.service
[Unit]
Description=Job Recommender Service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /path/to/recomender/job_recommender.py --search
WorkingDirectory=/path/to/recomender
```

## 🚨 Rate Limiting & Best Practices

- Built-in delays between requests (2-3 seconds)
- Respect robots.txt and terms of service
- Use reasonable page limits (1-3 pages per site)
- Monitor for IP blocking and implement rotation if needed

## 🐛 Troubleshooting

### Common Issues

1. **Email not sending**: Check email configuration and app passwords
2. **No jobs found**: Verify search terms and site availability
3. **Scraping errors**: Sites may have changed their HTML structure
4. **Import errors**: Ensure all dependencies are installed

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new scrapers
4. Submit a pull request

### Adding New Job Sites

1. Create a new scraper in `scrapper_module/`
2. Implement the required methods
3. Add the scraper to `UniversalJobScraper`
4. Test thoroughly

## 📜 License

This project is for educational and personal use. Respect the terms of service of job sites.

## ⚠️ Disclaimer

This tool is for personal job searching purposes. Users are responsible for:
- Complying with job site terms of service
- Respecting rate limits
- Using scraped data ethically

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the configuration guide
3. Open an issue on GitHub

---

**Happy Job Hunting! 🎉**
