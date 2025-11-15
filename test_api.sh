#!/bin/bash
# Test script for Handbook Chatbot API endpoints

API_BASE="http://localhost:8000"

echo "=========================================="
echo "Testing Handbook Chatbot API Endpoints"
echo "=========================================="
echo ""

# Test 1: Health check
echo "1. Testing Health Endpoint..."
echo "   GET $API_BASE/health"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_BASE/health")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" = "200" ]; then
    echo "   ✅ Status: $http_code"
    echo "   Response: $body"
else
    echo "   ❌ Status: $http_code"
    echo "   Response: $body"
    echo ""
    echo "   Make sure the API server is running:"
    echo "   python src/api_server.py"
    exit 1
fi

echo ""
echo "2. Testing Courses Endpoint..."
echo "   GET $API_BASE/api/chatbot/courses/"
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$API_BASE/api/chatbot/courses/")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" = "200" ]; then
    echo "   ✅ Status: $http_code"
    course_count=$(echo "$body" | grep -o '"code"' | wc -l)
    echo "   Found $course_count courses"
    echo "   First course:"
    echo "$body" | python3 -m json.tool 2>/dev/null | head -10 || echo "$body" | head -5
else
    echo "   ❌ Status: $http_code"
    echo "   Response: $body"
fi

echo ""
echo "3. Testing Chat Endpoint (Basic)..."
echo "   POST $API_BASE/api/chatbot/chat/"
payload='{"message": "What courses are available?", "concise": true}'
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$payload" \
    "$API_BASE/api/chatbot/chat/")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" = "200" ]; then
    echo "   ✅ Status: $http_code"
    echo "   Response preview:"
    echo "$body" | python3 -m json.tool 2>/dev/null | head -15 || echo "$body" | head -5
else
    echo "   ❌ Status: $http_code"
    echo "   Response: $body"
fi

echo ""
echo "4. Testing Chat Endpoint (With Course Code)..."
# First get a course code
course_response=$(curl -s "$API_BASE/api/chatbot/courses/")
course_code=$(echo "$course_response" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('courses', [{}])[0].get('code', 'C10302'))" 2>/dev/null || echo "C10302")

if [ -n "$course_code" ] && [ "$course_code" != "None" ]; then
    echo "   Using course code: $course_code"
    payload="{\"message\": \"What are the admission requirements?\", \"course_code\": \"$course_code\", \"concise\": true}"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$API_BASE/api/chatbot/chat/")
    http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE/d')
    
    if [ "$http_code" = "200" ]; then
        echo "   ✅ Status: $http_code"
        echo "   Response preview:"
        echo "$body" | python3 -m json.tool 2>/dev/null | head -15 || echo "$body" | head -5
    else
        echo "   ❌ Status: $http_code"
        echo "   Response: $body"
    fi
else
    echo "   ⚠️  Could not get course code, skipping this test"
fi

echo ""
echo "=========================================="
echo "Tests completed!"
echo "=========================================="

