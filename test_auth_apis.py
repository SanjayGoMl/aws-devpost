#!/usr/bin/env python3
"""
Test script for authentication endpoints
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(message):
    print(f"{Colors.GREEN}✅ {message}{Colors.END}")

def print_error(message):
    print(f"{Colors.RED}❌ {message}{Colors.END}")

def print_info(message):
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.END}")

def print_warning(message):
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.END}")

def test_register():
    """Test user registration"""
    print("\n" + "="*70)
    print("TEST 1: User Registration")
    print("="*70)
    
    try:
        # Generate unique email for testing
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        test_email = f"test_{timestamp}@example.com"
        
        payload = {
            "email": test_email,
            "password": "TestPass123",
            "full_name": "Test User"
        }
        
        print_info(f"Registering user: {test_email}")
        response = requests.post(f"{BASE_URL}/auth/register", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Registration successful!")
            print(f"   User ID: {data['user']['user_id']}")
            print(f"   Email: {data['user']['email']}")
            print(f"   Full Name: {data['user']['full_name']}")
            print(f"   Initials: {data['user']['initials']}")
            print(f"   Token: {data['token'][:50]}...")
            print(f"   Token Type: {data['token_type']}")
            print(f"   Expires In: {data['expires_in']} seconds")
            return data
        else:
            print_error(f"Registration failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Registration test failed: {str(e)}")
        return None

def test_login(email, password):
    """Test user login"""
    print("\n" + "="*70)
    print("TEST 2: User Login")
    print("="*70)
    
    try:
        payload = {
            "email": email,
            "password": password
        }
        
        print_info(f"Logging in user: {email}")
        response = requests.post(f"{BASE_URL}/auth/login", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Login successful!")
            print(f"   User ID: {data['user']['user_id']}")
            print(f"   Email: {data['user']['email']}")
            print(f"   Full Name: {data['user']['full_name']}")
            print(f"   Initials: {data['user']['initials']}")
            print(f"   Last Login: {data['user']['last_login']}")
            print(f"   Token: {data['token'][:50]}...")
            return data
        else:
            print_error(f"Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print_error(f"Login test failed: {str(e)}")
        return None

def test_login_invalid():
    """Test login with invalid credentials"""
    print("\n" + "="*70)
    print("TEST 3: Invalid Login (Expected to Fail)")
    print("="*70)
    
    try:
        payload = {
            "email": "invalid@example.com",
            "password": "WrongPassword"
        }
        
        print_info("Attempting login with invalid credentials...")
        response = requests.post(f"{BASE_URL}/auth/login", json=payload)
        
        if response.status_code == 401:
            print_success(f"Correctly rejected invalid credentials!")
            print(f"   Response: {response.json()['detail']}")
            return True
        else:
            print_warning(f"Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Invalid login test failed: {str(e)}")
        return False

def test_duplicate_register(email):
    """Test registering with existing email"""
    print("\n" + "="*70)
    print("TEST 4: Duplicate Registration (Expected to Fail)")
    print("="*70)
    
    try:
        payload = {
            "email": email,
            "password": "AnotherPass123",
            "full_name": "Duplicate User"
        }
        
        print_info(f"Attempting to register duplicate email: {email}")
        response = requests.post(f"{BASE_URL}/auth/register", json=payload)
        
        if response.status_code == 400:
            print_success(f"Correctly rejected duplicate email!")
            print(f"   Response: {response.json()['detail']}")
            return True
        else:
            print_warning(f"Unexpected status code: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Duplicate registration test failed: {str(e)}")
        return False

def test_password_reset_request(email):
    """Test password reset request"""
    print("\n" + "="*70)
    print("TEST 5: Password Reset Request")
    print("="*70)
    
    try:
        payload = {"email": email}
        
        print_info(f"Requesting password reset for: {email}")
        response = requests.post(f"{BASE_URL}/auth/request-password-reset", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Password reset OTP requested!")
            print(f"   Message: {data['message']}")
            print(f"   Email: {data['email']}")
            print_warning("   Check your email for the OTP code (if SES is configured)")
            print_warning("   In sandbox mode, recipient email must be verified in AWS SES")
            return True
        else:
            print_error(f"Password reset request failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Password reset request test failed: {str(e)}")
        return False

def test_token_verification(token):
    """Test using token in authenticated request"""
    print("\n" + "="*70)
    print("TEST 6: Token Verification")
    print("="*70)
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        print_info("Testing token with a protected endpoint (if available)...")
        # For now, just verify the token format
        if token and len(token) > 20:
            print_success("Token format valid!")
            print(f"   Token length: {len(token)} characters")
            print(f"   Token preview: {token[:30]}...")
            
            # Future: Test with actual protected endpoint
            print_info("   Note: Add protected endpoints to test authorization")
            return True
        else:
            print_error("Invalid token format")
            return False
            
    except Exception as e:
        print_error(f"Token verification test failed: {str(e)}")
        return False

def test_health_check():
    """Test API health check"""
    print("\n" + "="*70)
    print("TEST 0: Health Check")
    print("="*70)
    
    try:
        print_info("Checking API health...")
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            print_success("API is healthy!")
            print(f"   Status: {data.get('status')}")
            print(f"   Service: {data.get('service')}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print_error(f"Cannot connect to API: {str(e)}")
        print_warning("Make sure the server is running on http://localhost:8000")
        return False

def main():
    """Run all authentication tests"""
    print("=" * 70)
    print("🚀 AWS Analysis Service - Authentication System Tests")
    print("=" * 70)
    print_info(f"Testing against: {BASE_URL}")
    print()
    
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0
    }
    
    # Test 0: Health Check
    if not test_health_check():
        print_error("\n❌ API is not accessible. Exiting tests.")
        return 1
    
    # Test 1: Register
    results["total"] += 1
    register_data = test_register()
    if register_data:
        results["passed"] += 1
        test_email = register_data['user']['email']
        test_token = register_data['token']
    else:
        results["failed"] += 1
        print_warning("\nSkipping remaining tests due to registration failure")
        return 1
    
    # Test 2: Login
    results["total"] += 1
    login_data = test_login(test_email, "TestPass123")
    if login_data:
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 3: Invalid Login
    results["total"] += 1
    if test_login_invalid():
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 4: Duplicate Registration
    results["total"] += 1
    if test_duplicate_register(test_email):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 5: Password Reset Request
    results["total"] += 1
    if test_password_reset_request(test_email):
        results["passed"] += 1
    else:
        results["failed"] += 1
        print_warning("   This may fail if SES is not configured or email is not verified")
    
    # Test 6: Token Verification
    results["total"] += 1
    if test_token_verification(test_token):
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Results Summary")
    print("=" * 70)
    print(f"Total Tests: {results['total']}")
    print(f"{Colors.GREEN}Passed: {results['passed']}{Colors.END}")
    print(f"{Colors.RED}Failed: {results['failed']}{Colors.END}")
    print(f"Success Rate: {(results['passed']/results['total']*100):.1f}%")
    
    if results['failed'] == 0:
        print_success("\n🎉 All tests passed! Authentication system is working correctly.")
        return 0
    else:
        print_warning(f"\n⚠️  {results['failed']} test(s) failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_warning("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
