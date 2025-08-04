# Configuration file for job recommender system
import yaml
import os

def load_yaml_config(config_path: str = "configs/settings.yaml") -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        return {}

# Load YAML config if available
YAML_CONFIG = load_yaml_config()

# Email configuration (can be overridden by YAML)
EMAIL_CONFIG = YAML_CONFIG.get('email', {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'use_tls': True,
    'sender_email': 'your-email@gmail.com',
    'sender_password': 'your-app-password',
})

# User preferences template
DEFAULT_USER_PREFERENCES = {
    'job_titles': YAML_CONFIG.get('search', {}).get('terms', []),
    'locations': YAML_CONFIG.get('search', {}).get('locations', []),
    'experience_levels': ['entry', 'mid', 'senior'],
    'companies_to_include': [],
    'companies_to_exclude': [],
    'keywords': [],
    'max_age_hours': 72,
    'sites_to_scrape': YAML_CONFIG.get('scrapers', {}).get('enabled', ['linkedin', 'indeed', 'glassdoor']),
    'pages_per_site': YAML_CONFIG.get('search', {}).get('pages_per_source', 2),
    'email': '',
    'notification_frequency': 'daily',
    'output_format': YAML_CONFIG.get('output', {}).get('format', 'csv'),
}

# Scoring weights for job recommendations
SCORING_WEIGHTS = {
    'title_match': 0.3,
    'location_match': 0.2,
    'company_preference': 0.2,
    'experience_match': 0.15,
    'keyword_match': 0.1,
    'freshness': 0.05,
}