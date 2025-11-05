#!/bin/bash

# Default credentials
user=${1:-mark}
password=${2:-12345678}

echo "=== Testing Authentication & Authorization Flow ==="
echo "Using username: $user"
echo ""

# ============================================================================
# Step 1: Login and create session
# ============================================================================
echo "1. Login - Create session"
response=$(curl -s -i -X POST http://localhost:5500/api/login \
  -H "Content-Type: application/json" \
  -d "{\"login\": \"$user\", \"password\": \"$password\"}")

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
  echo "   ✅ Login successful"
  echo "   Session ID: $session_id"
else
  echo "   ❌ Login failed - HTTP $http_status"
  echo ""
  echo "Error details:"
  echo "$response" | sed -n '/^{/,/^}/p'
  exit 1
fi
echo ""

# ============================================================================
# Step 2: Check initial session (no permissions cached yet)
# ============================================================================
echo "2. Check initial session in Redis (before RBAC)"
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

  # Extract and display key fields
  user_id=$(echo "$session_data" | jq -r '.Id // empty' 2>/dev/null)
  role_id=$(echo "$session_data" | jq -r '.roleId // empty' 2>/dev/null)
  permissions=$(echo "$session_data" | jq -c '.permissions // empty' 2>/dev/null)

  echo "   Key fields:"
  [ -n "$user_id" ] && echo "     • userId: $user_id"
  [ -n "$role_id" ] && echo "     • roleId: $role_id"
  if [ -z "$permissions" ] || [ "$permissions" = "null" ]; then
    echo "     • permissions: (not cached yet)"
  else
    echo "     • permissions: $permissions"
  fi
else
  echo "   ❌ Session not found in Redis"
  exit 1
fi
echo ""

# ============================================================================
# Step 3: First API call - loads permissions from Role and caches them
# ============================================================================
echo "3. First API call - Load permissions from Role entity"
api_response=$(curl -s -i -X GET "http://localhost:5500/api/user?pageSize=1" \
  -H "Cookie: sessionId=$session_id")

api_status=$(echo "$api_response" | grep "HTTP/" | awk '{print $2}')
if [ "$api_status" = "200" ]; then
  echo "   ✅ API call successful"
  echo "   (Permissions loaded from Role entity and cached in session)"
elif [ "$api_status" = "403" ]; then
  echo "   ❌ Permission denied"
  echo ""
  echo "Error details:"
  echo "$api_response" | sed -n '/^{/,/^}/p'
  exit 1
elif [ "$api_status" = "401" ]; then
  echo "   ❌ Not authenticated"
  echo ""
  echo "Error details:"
  echo "$api_response" | sed -n '/^{/,/^}/p'
  exit 1
else
  echo "   ⚠️  Unexpected HTTP status: $api_status"
  echo ""
  echo "Error details:"
  echo "$api_response" | sed -n '/^{/,/^}/p'
  exit 1
fi
echo ""

# ============================================================================
# Step 4: Check session again (permissions should now be cached)
# ============================================================================
echo "4. Check session after RBAC (permissions now cached)"
session_data=$(redis-cli GET "$session_id" 2>&1)
if [ -n "$session_data" ] && [ "$session_data" != "(nil)" ]; then
  echo "   ✅ Session found in Redis"

  # Extract and display permissions
  permissions=$(echo "$session_data" | jq -c '.permissions // empty' 2>/dev/null)

  if [ -n "$permissions" ] && [ "$permissions" != "null" ]; then
    echo "   ✅ Permissions cached: $permissions"
  else
    echo "   ⚠️  Permissions not cached (unexpected)"
  fi
else
  echo "   ❌ Session not found in Redis"
fi
echo ""

# ============================================================================
# Step 5: Second API call - uses cached permissions (no DB lookup)
# ============================================================================
echo "5. Second API call - Use cached permissions"
api_response=$(curl -s -i -X GET "http://localhost:5500/api/user?pageSize=1" \
  -H "Cookie: sessionId=$session_id")

api_status=$(echo "$api_response" | grep "HTTP/" | awk '{print $2}')
if [ "$api_status" = "200" ]; then
  echo "   ✅ API call successful"
  echo "   (Used cached permissions - no Role entity lookup)"
elif [ "$api_status" = "403" ]; then
  echo "   ❌ Permission denied"
  echo ""
  echo "Error details:"
  echo "$api_response" | sed -n '/^{/,/^}/p'
  exit 1
elif [ "$api_status" = "401" ]; then
  echo "   ❌ Not authenticated"
  echo ""
  echo "Error details:"
  echo "$api_response" | sed -n '/^{/,/^}/p'
  exit 1
else
  echo "   ⚠️  Unexpected HTTP status: $api_status"
fi
echo ""

# ============================================================================
# Step 6: Logout
# ============================================================================
echo "6. Logout - Delete session"
logout_response=$(curl -s -i -X POST http://localhost:5500/api/logout \
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

# ============================================================================
# Step 7: Verify session deleted from Redis
# ============================================================================
echo "7. Verify session deleted from Redis"
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
echo ""
