"""
Email service for sending job recommendations.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import List, Dict, Optional
from datetime import datetime
import logging


class EmailService:
    """Professional email service for job recommendations"""
    
    def __init__(self, smtp_server: str, smtp_port: int, sender_email: str, 
                 sender_password: str, use_tls: bool = True):
        """
        Initialize email service.
        
        Args:
            smtp_server: SMTP server address
            smtp_port: SMTP server port
            sender_email: Sender's email address
            sender_password: Sender's email password (use app password for Gmail)
            use_tls: Whether to use TLS encryption
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.use_tls = use_tls
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def create_job_report_html(self, jobs: List[Dict], user_preferences: Optional[Dict] = None) -> str:
        """Create beautiful HTML email content with job recommendations"""
        prefs = user_preferences or {}
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background-color: #f5f5f5;
                    line-height: 1.6;
                }}
                .container {{ 
                    max-width: 800px; 
                    margin: 0 auto; 
                    background-color: white; 
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    overflow: hidden;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; 
                    padding: 30px; 
                    text-align: center; 
                }}
                .header h1 {{ margin: 0; font-size: 28px; }}
                .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
                
                .summary {{ 
                    background-color: #f8f9fa; 
                    padding: 25px; 
                    margin: 0;
                    border-left: 4px solid #667eea;
                }}
                .summary h2 {{ margin: 0 0 15px 0; color: #333; }}
                .summary ul {{ margin: 0; padding-left: 20px; }}
                .summary li {{ margin: 8px 0; }}
                
                .job-card {{ 
                    border: 1px solid #e0e0e0; 
                    margin: 0 20px 20px 20px; 
                    padding: 25px; 
                    border-radius: 8px;
                    background-color: white;
                    transition: box-shadow 0.3s ease;
                }}
                .job-card:hover {{ box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1); }}
                
                .job-header {{ display: flex; justify-content: space-between; align-items: flex-start; }}
                .job-title {{ 
                    color: #2c5aa0; 
                    font-size: 20px; 
                    font-weight: 600; 
                    margin: 0;
                    text-decoration: none;
                }}
                .job-title:hover {{ text-decoration: underline; }}
                
                .company {{ 
                    color: #555; 
                    font-size: 16px; 
                    margin: 8px 0; 
                    font-weight: 500;
                }}
                .location {{ 
                    color: #777; 
                    font-size: 14px;
                    margin: 5px 0;
                }}
                .posted-date {{ 
                    color: #999; 
                    font-size: 12px; 
                    margin: 10px 0;
                }}
                
                .job-meta {{ margin: 15px 0; }}
                .job-link {{ margin-top: 15px; }}
                .job-link a {{ 
                    display: inline-block;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 10px 20px;
                    border-radius: 5px;
                    text-decoration: none;
                    font-weight: 500;
                    transition: transform 0.2s ease;
                }}
                .job-link a:hover {{ transform: translateY(-2px); }}
                
                .experience-badge {{ 
                    display: inline-block; 
                    padding: 5px 12px; 
                    border-radius: 15px; 
                    font-size: 12px; 
                    color: white; 
                    margin: 8px 8px 8px 0; 
                    font-weight: 500;
                }}
                .entry {{ background: linear-gradient(135deg, #28a745, #20c997); }}
                .mid {{ background: linear-gradient(135deg, #ffc107, #fd7e14); color: #333; }}
                .senior {{ background: linear-gradient(135deg, #dc3545, #e83e8c); }}
                
                .score {{ 
                    background: linear-gradient(135deg, #17a2b8, #6f42c1);
                    color: white; 
                    padding: 8px 15px; 
                    border-radius: 20px; 
                    font-size: 14px; 
                    font-weight: 600;
                    text-align: center;
                    min-width: 60px;
                }}
                
                .footer {{ 
                    padding: 30px; 
                    background-color: #f8f9fa; 
                    text-align: center; 
                    border-top: 1px solid #e0e0e0;
                }}
                .footer p {{ margin: 5px 0; color: #666; }}
                
                .no-jobs {{ 
                    text-align: center; 
                    padding: 60px 30px; 
                    color: #666;
                }}
                .no-jobs h2 {{ color: #999; }}
                
                @media (max-width: 600px) {{
                    .container {{ margin: 10px; }}
                    .job-header {{ flex-direction: column; }}
                    .score {{ margin-top: 10px; }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎯 Your Personalized Job Recommendations</h1>
                    <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
                
                <div class="summary">
                    <h2>📊 Summary</h2>
                    <ul>
                        <li><strong>Total Jobs Found:</strong> {len(jobs)}</li>
                        <li><strong>Search Criteria:</strong> {', '.join(prefs.get('job_titles', ['Any']))}</li>
                        <li><strong>Locations:</strong> {', '.join(prefs.get('locations', ['Any']))}</li>
                        <li><strong>Experience Levels:</strong> {', '.join(prefs.get('experience_levels', ['All']))}</li>
                        <li><strong>Sites Searched:</strong> {', '.join(prefs.get('sites_to_scrape', []))}</li>
                    </ul>
                </div>
        """
        
        if not jobs:
            html_content += """
                <div class="no-jobs">
                    <h2>😔 No jobs found matching your criteria</h2>
                    <p>Try adjusting your search parameters or check back later!</p>
                </div>
            """
        else:
            for i, job in enumerate(jobs[:25], 1):  # Limit to top 25 jobs
                experience = job.get('experience_level', 'unknown')
                score = job.get('recommendation_score', 0)
                
                html_content += f"""
                <div class="job-card">
                    <div class="job-header">
                        <div>
                            <a href="{job.get('link', '#')}" class="job-title">{job.get('title', 'N/A')}</a>
                            <div class="company">🏢 {job.get('company', 'N/A')}</div>
                            <div class="location">📍 {job.get('location', 'N/A')}</div>
                        </div>
                        <div class="score">Match: {score:.1f}%</div>
                    </div>
                    
                    <div class="job-meta">
                        <span class="experience-badge {experience}">{experience.title()} Level</span>
                        <div class="posted-date">📅 Posted: {job.get('posted_date', 'N/A')} | Source: {job.get('source', 'N/A')}</div>
                    </div>
                    
                    <div class="job-link">
                        <a href="{job.get('link', '#')}" target="_blank">🔗 View Job Details</a>
                    </div>
                </div>
                """
        
        html_content += """
                <div class="footer">
                    <p><strong>Happy job hunting! 🎉</strong></p>
                    <p style="font-size: 12px; color: #999;">
                        This is an automated job recommendation email generated by your Job Recommender System.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def send_job_recommendations(self, recipient_email: str, jobs: List[Dict], 
                               user_preferences: Optional[Dict] = None, 
                               attach_files: Optional[List[str]] = None) -> bool:
        """
        Send job recommendations via email.
        
        Args:
            recipient_email: Recipient's email address
            jobs: List of job dictionaries
            user_preferences: User preferences for personalization
            attach_files: List of file paths to attach
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('mixed')
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = f"🎯 {len(jobs)} New Job Recommendations - {datetime.now().strftime('%B %d, %Y')}"
            
            # Create HTML content
            html_content = self.create_job_report_html(jobs, user_preferences)
            
            # Create alternative part for email body
            msg_alternative = MIMEMultipart('alternative')
            
            # Plain text version (fallback)
            text_content = f"""
Job Recommendations - {datetime.now().strftime('%B %d, %Y')}

Found {len(jobs)} job recommendations for you:

"""
            for i, job in enumerate(jobs[:10], 1):
                text_content += f"""
{i}. {job.get('title', 'N/A')}
   Company: {job.get('company', 'N/A')}
   Location: {job.get('location', 'N/A')}
   Link: {job.get('link', 'N/A')}

"""
            
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            
            msg_alternative.attach(text_part)
            msg_alternative.attach(html_part)
            msg.attach(msg_alternative)
            
            # Attach files if provided
            if attach_files:
                for file_path in attach_files:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                        
                        encoders.encode_base64(part)
                        filename = os.path.basename(file_path)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {filename}',
                        )
                        msg.attach(part)
            
            # Send email
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            self.logger.info(f"Job recommendations sent successfully to {recipient_email}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email to {recipient_email}: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test email server connection"""
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls(context=context)
                server.login(self.sender_email, self.sender_password)
            
            self.logger.info("Email connection test successful")
            return True
        except Exception as e:
            self.logger.error(f"Email connection test failed: {e}")
            return False


def main():
    """Test the email service"""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Sample configuration (use environment variables in production)
    email_config = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'sender_email': 'your-email@gmail.com',
        'sender_password': 'your-app-password',  # Use app password for Gmail
        'use_tls': True
    }
    
    # Sample job data
    sample_jobs = [
        {
            'title': 'Senior Python Developer',
            'company': 'Google',
            'location': 'San Francisco, CA',
            'posted_date': '2 days ago',
            'source': 'LinkedIn',
            'experience_level': 'senior',
            'recommendation_score': 95.5,
            'link': 'https://example.com/job1'
        },
        {
            'title': 'Data Scientist',
            'company': 'Microsoft',
            'location': 'Remote',
            'posted_date': '1 day ago',
            'source': 'Indeed',
            'experience_level': 'mid',
            'recommendation_score': 87.2,
            'link': 'https://example.com/job2'
        }
    ]
    
    sample_preferences = {
        'job_titles': ['Python Developer', 'Data Scientist'],
        'locations': ['San Francisco', 'Remote'],
        'experience_levels': ['mid', 'senior'],
        'sites_to_scrape': ['LinkedIn', 'Indeed']
    }
    
    print("📧 Testing Email Service")
    print("=" * 30)
    
    # Initialize service
    try:
        email_service = EmailService(**email_config)
        
        # Test connection
        if email_service.test_connection():
            print("✅ Email connection successful")
            
            # Uncomment to actually send test email
            # recipient = "test-recipient@example.com"
            # success = email_service.send_job_recommendations(
            #     recipient, sample_jobs, sample_preferences
            # )
            # print(f"📧 Email sent: {success}")
        else:
            print("❌ Email connection failed")
            
    except Exception as e:
        print(f"❌ Error initializing email service: {e}")


if __name__ == "__main__":
    main()
