"""
Tests for the ScraperManager class
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manager.scraper_manager import ScraperManager


class TestScraperManager(unittest.TestCase):
    """Test cases for ScraperManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = ScraperManager(max_workers=2, default_delay=1.0)
    
    def test_initialization(self):
        """Test manager initialization"""
        self.assertIsInstance(self.manager, ScraperManager)
        self.assertEqual(self.manager.max_workers, 2)
        self.assertEqual(self.manager.default_delay, 1.0)
    
    def test_get_available_scrapers(self):
        """Test getting available scrapers"""
        scrapers = self.manager.get_available_scrapers()
        self.assertIsInstance(scrapers, list)
        self.assertTrue(len(scrapers) > 0)
        self.assertIn('linkedin', scrapers)
        self.assertIn('indeed', scrapers)
    
    def test_get_platform_info(self):
        """Test getting platform information"""
        info = self.manager.get_platform_info()
        self.assertIsInstance(info, dict)
        self.assertTrue(len(info) > 0)
    
    def test_validate_scrapers(self):
        """Test scraper validation"""
        results = self.manager.validate_scrapers()
        self.assertIsInstance(results, dict)
        self.assertTrue(len(results) > 0)
        
        # All results should be boolean
        for status in results.values():
            self.assertIsInstance(status, bool)
    
    def test_stats_tracking(self):
        """Test statistics tracking"""
        initial_stats = self.manager.get_scraping_stats()
        expected_keys = ['total_jobs', 'jobs_by_source', 'scraping_duration', 'failed_scrapers']
        
        for key in expected_keys:
            self.assertIn(key, initial_stats)
        
        # Reset stats
        self.manager.reset_stats()
        reset_stats = self.manager.get_scraping_stats()
        self.assertEqual(reset_stats['total_jobs'], 0)
        self.assertEqual(len(reset_stats['jobs_by_source']), 0)


if __name__ == '__main__':
    unittest.main()