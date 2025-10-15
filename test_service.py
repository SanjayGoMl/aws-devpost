#!/usr/bin/env python3
"""
Test script for the AWS Image and Excel Analysis Service
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.aws_service import AWSService
from utils.logger import get_logger
from utils.exceptions import ServiceException

logger = get_logger("test_service")

async def test_service_initialization():
    """Test AWS service initialization"""
    try:
        logger.info("Testing AWS service initialization...")
        aws_service = AWSService()
        logger.info("✅ AWS service initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ AWS service initialization failed: {str(e)}")
        return False

async def test_folder_name_generation():
    """Test folder name generation"""
    try:
        logger.info("Testing folder name generation...")
        aws_service = AWSService()
        
        # Test with title
        folder_name = aws_service._generate_folder_name("Test Project")
        assert folder_name.endswith("_Test_Project"), f"Expected folder name to end with '_Test_Project', got {folder_name}"
        
        # Test without title
        folder_name_no_title = aws_service._generate_folder_name()
        assert len(folder_name_no_title) > 0, "Folder name should not be empty"
        
        logger.info("✅ Folder name generation tests passed")
        return True
    except Exception as e:
        logger.error(f"❌ Folder name generation test failed: {str(e)}")
        return False

async def test_title_sanitization():
    """Test title sanitization"""
    try:
        logger.info("Testing title sanitization...")
        aws_service = AWSService()
        
        test_cases = [
            ("Hello World!", "Hello_World_"),
            ("Test@#$%^&*()", "Test_"),
            ("Normal_Title", "Normal_Title"),
            ("  Spaces  ", "Spaces")
        ]
        
        for input_title, expected in test_cases:
            result = aws_service._sanitize_title(input_title)
            assert result == expected, f"Expected '{expected}', got '{result}' for input '{input_title}'"
        
        logger.info("✅ Title sanitization tests passed")
        return True
    except Exception as e:
        logger.error(f"❌ Title sanitization test failed: {str(e)}")
        return False

async def test_logging_functionality():
    """Test logging functionality"""
    try:
        logger.info("Testing logging functionality...")
        
        # Test different log levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        logger.info("✅ Logging functionality tests passed")
        return True
    except Exception as e:
        logger.error(f"❌ Logging functionality test failed: {str(e)}")
        return False

async def run_all_tests():
    """Run all tests"""
    logger.info("🚀 Starting AWS Image and Excel Analysis Service Tests")
    
    tests = [
        test_service_initialization,
        test_folder_name_generation,
        test_title_sanitization,
        test_logging_functionality
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
    
    passed = sum(results)
    total = len(results)
    
    logger.info(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during testing: {str(e)}")
        sys.exit(1)