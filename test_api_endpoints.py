#!/usr/bin/env python3
"""
Test script for Handbook Chatbot API endpoints
Tests both GET /api/chatbot/courses/ and POST /api/chatbot/chat/
"""
import requests
import json
import sys

API_BASE = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("=" * 70)
    print("Testing Health Endpoint")
    print("=" * 70)
    try:
        response = requests.get(f"{API_BASE}/health", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server")
        print("   Make sure the API server is running:")
        print("   python src/api_server.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_courses_endpoint():
    """Test GET /api/chatbot/courses/ endpoint"""
    print("\n" + "=" * 70)
    print("Testing GET /api/chatbot/courses/")
    print("=" * 70)
    try:
        response = requests.get(f"{API_BASE}/api/chatbot/courses/", timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            courses = data.get('courses', [])
            print(f"Number of courses: {len(courses)}")
            
            if courses:
                print("\nFirst 5 courses:")
                for course in courses[:5]:
                    print(f"  - {course.get('code', 'N/A')}: {course.get('name', 'N/A')[:60]}")
            
            if len(courses) > 5:
                print(f"\n... and {len(courses) - 5} more courses")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_chat_endpoint_basic():
    """Test POST /api/chatbot/chat/ with basic query"""
    print("\n" + "=" * 70)
    print("Testing POST /api/chatbot/chat/ (Basic Query)")
    print("=" * 70)
    try:
        payload = {
            "message": "What courses are available?",
            "concise": True
        }
        
        print(f"Request: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{API_BASE}/api/chatbot/chat/",
            json=payload,
            timeout=30
        )
        
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success', False)}")
            response_text = data.get('response', '')
            print(f"\nResponse (first 200 chars):")
            print(response_text[:200] + ("..." if len(response_text) > 200 else ""))
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_chat_endpoint_with_course_code():
    """Test POST /api/chatbot/chat/ with course code filter"""
    print("\n" + "=" * 70)
    print("Testing POST /api/chatbot/chat/ (With Course Code Filter)")
    print("=" * 70)
    try:
        # First get a course code from the courses endpoint
        courses_response = requests.get(f"{API_BASE}/api/chatbot/courses/", timeout=10)
        if courses_response.status_code == 200:
            courses_data = courses_response.json()
            courses = courses_data.get('courses', [])
            
            if not courses:
                print("⚠️  No courses available, skipping course code filter test")
                return True
            
            # Use first course code
            test_course_code = courses[0].get('code')
            print(f"Using course code: {test_course_code}")
            
            payload = {
                "message": "What are the admission requirements?",
                "course_code": test_course_code,
                "concise": True
            }
            
            print(f"Request: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                f"{API_BASE}/api/chatbot/chat/",
                json=payload,
                timeout=30
            )
            
            print(f"\nStatus: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Success: {data.get('success', False)}")
                response_text = data.get('response', '')
                print(f"\nResponse (first 200 chars):")
                print(response_text[:200] + ("..." if len(response_text) > 200 else ""))
                return True
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text}")
                return False
        else:
            print("⚠️  Could not get courses list, skipping course code filter test")
            return True
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to API server")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("Handbook Chatbot API Endpoint Tests")
    print("=" * 70)
    print("\nMake sure the API server is running:")
    print("  python src/api_server.py")
    print("\nPress Enter to continue or Ctrl+C to cancel...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return
    
    results = []
    
    # Test 1: Health check
    results.append(("Health Check", test_health()))
    
    if not results[0][1]:
        print("\n❌ Health check failed. Please start the API server first.")
        return
    
    # Test 2: Courses endpoint
    results.append(("Courses Endpoint", test_courses_endpoint()))
    
    # Test 3: Chat endpoint (basic)
    results.append(("Chat Endpoint (Basic)", test_chat_endpoint_basic()))
    
    # Test 4: Chat endpoint (with course code)
    results.append(("Chat Endpoint (Course Filter)", test_chat_endpoint_with_course_code()))
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    print("\n" + ("✅ All tests passed!" if all_passed else "❌ Some tests failed"))
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())

