#!/bin/bash

# Default credentials
user=${1:-mark}
password=${2:-12345678}

echo "=== Testing Redis Authentication ==="
echo "Using username: $user"
echo ""

# Login and extract session ID from Set-Cookie header
echo "1. Logging in..."
response=$(curl -s -i -X POST http://localhost:5500/user/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$user\", \"password\": \"$password\"}")

# Extract session ID from Set-Cookie header
session_id=$(echo "$response" | grep -i "set-cookie:" | sed -n 's/.*sessionId=\([^;]*\).*/\1/p')

http_status=$(echo "$response" | grep "HTTP/" | awk '{print $2}')
if [ "$http_status" = "200" ]; then
  if [ -z "$session_id" ]; then
    echo "   ❌ Login failed - no session ID in response"
    echo ""
    echo "Response body:"
    echo "$response" | sed -n '/^{/,/^}/p'
    exit 1
  fi
  echo "   ✅ Login successful - Session: $session_id"
else
  echo "   ❌ Login failed - HTTP $http_status"
  echo ""
  echo "Error details:"
  echo "$response" | sed -n '/^{/,/^}/p'
  exit 1
fi
echo ""

# Check session in Redis
echo "2. Checking session in Redis..."
session_data=$(redis-cli GET "$session_id" 2>&1)
if [ $? -ne 0 ]; then
  echo "   ❌ Redis error"
  echo ""
  echo "Error details:"
  echo "$session_data"
  exit 1
fi

if [ -n "$session_data" ] && [ "$session_data" != "(nil)" ]; then
  echo "   ✅ Session found in Redis"
else
  echo "   ❌ Session not found in Redis"
  exit 1
fi
echo ""

# Logout
echo "3. Logging out..."
logout_response=$(curl -s -i -X POST http://localhost:5500/user/auth/logout \
  -H "Cookie: sessionId=$session_id")

logout_status=$(echo "$logout_response" | grep "HTTP/" | awk '{print $2}')
if [ "$logout_status" = "200" ]; then
  echo "   ✅ Logout successful"
else
  echo "   ❌ Logout failed - HTTP $logout_status"
  echo ""
  echo "Error details:"
  echo "$logout_response" | sed -n '/^{/,/^}/p'
  exit 1
fi
echo ""

# Verify session deleted
echo "4. Verifying session deleted from Redis..."
result=$(redis-cli GET "$session_id" 2>&1)
if [ $? -ne 0 ]; then
  echo "   ❌ Redis error"
  echo ""
  echo "Error details:"
  echo "$result"
  exit 1
fi

if [ -z "$result" ] || [ "$result" = "(nil)" ]; then
  echo "   ✅ Session deleted from Redis"
else
  echo "   ❌ Session still exists in Redis"
  echo ""
  echo "Unexpected data:"
  echo "$result"
  exit 1
fi

echo ""
echo "=== All tests passed! ✅ ==="
