"""
Test package for Homeschool Application
Provides comprehensive testing framework for AI Agent, function calling, and application features
"""

import os
import sys
from pathlib import Path

# Add the app directory to the Python path for testing
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "app"))

# Test configuration
TEST_DATABASE_URL = "sqlite:///./test_homeschool.db"
TEST_USER_ID = 1
TEST_ADMIN_USER_ID = 2

__version__ = "1.0.0" 