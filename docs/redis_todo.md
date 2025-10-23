# Redis Authentication - Remaining Tasks
**Status**: ✅ Working (login/logout/session management functional)
**Last Updated**: 2025-10-22

---

## High Priority (Security & Functionality)

### 1. Password Hashing ⚠️ CRITICAL
**Current Issue**: Passwords stored and compared as plaintext in database.

**File**: `app/services/auth/cookies/redis_provider.py:129`
```python
# Current (INSECURE):
if user.get("password") != password:
    return None
```

**Required Changes**:
- Add `bcrypt` dependency to requirements
- Hash passwords in User create/update endpoints
- Update login to use `bcrypt.checkpw(password.encode(), user["password"].encode())`
- Add migration script to hash existing passwords
- Never return password field in API responses

---

### 2. Cookie Configuration ⚠️ BLOCKS LOCAL DEV
**Current Issue**: `secure: True` requires HTTPS but local dev uses HTTP.

**File**: `app/services/auth/cookies/redis_provider.py:60-65`
```python
# Current (hardcoded):
cookie_options = {
    "httponly": True,
    "secure": True,    # Breaks HTTP localhost
    "samesite": "lax"
}
```

**Required Changes**:
- Add to `mongo.json`:
  ```json
  "auth.cookies.redis": {
    "host": "127.0.0.1",
    "port": 6379,
    "db": 0,
    "cookie_secure": false,     // false for dev, true for prod
    "cookie_domain": null,
    "cookie_samesite": "lax"
  }
  ```
- Read settings in `CookiesAuth.initialize()` and set `cls.cookie_options`

---

### 3. Error Handling
**Current Issue**: No graceful handling of Redis connection failures or security issues.

**Required Changes**:
- Wrap Redis operations in try/except and return proper HTTP errors
- Distinguish "user not found" vs "wrong password" in logs (NOT in response - security)
- Add rate limiting on login endpoint (e.g., 5 attempts per minute per IP)
- Handle Redis connection errors: return 503 Service Unavailable

---

## Medium Priority (Configuration & Testing)

### 4. Session Management
**Current Issue**: SESSION_TTL hardcoded to 3600 seconds.

**File**: `app/services/auth/cookies/redis_provider.py:10`

**Required Changes**:
- Make SESSION_TTL configurable in `mongo.json` (default: 3600)
- Consider implementing sliding window (refresh TTL on each request)
- Add session cleanup job for expired sessions
- Support concurrent sessions / multiple devices (user_id → [session_id1, session_id2])

---

### 5. Testing Integration
**Current Status**: Manual testing via `redis.sh` only.

**Required Changes**:
- Add auth tests to `test/validate-src` framework:
  - Test successful login
  - Test invalid credentials
  - Test authenticated endpoint access
  - Test session expiration
  - Test logout
  - Test concurrent sessions

---

### 6. Documentation
**Required**:
- Update API docs with auth flow diagram
- Document cookie handling for UI developers
- Create developer guide for adding new auth methods (JWT, OAuth)
- Document Redis configuration options

---

## Low Priority (Enhancements)

### 7. Login Response Enhancement
**Current**: Returns only `{"success": true, "message": "Login successful"}`

**Consider Adding**:
- User info in response: `{"success": true, "user": {"id": "...", "username": "...", "roles": [...]}}`
- Session expiration time: `{"expires_in": 3600}`

---

### 8. Monitoring & Logging
**Required**:
- Log successful/failed login attempts with username (not password)
- Track active sessions count
- Alert on suspicious activity (multiple failed attempts, unusual access patterns)
- Add metrics: login rate, session duration, active users

---

## Current Configuration

**File**: `mongo.json`
```json
{
  "auth.cookies.redis": {
    "host": "127.0.0.1",
    "port": 6379,
    "db": 0
  }
}
```

**Hardcoded in**: `app/services/auth/cookies/redis_provider.py`
- `SESSION_TTL = 3600` (1 hour)
- `cookie_name = "sessionId"`
- `cookie_options = {"httponly": True, "secure": True, "samesite": "lax"}`

---

## Testing

**Manual Test Script**: `redis.sh`
```bash
./redis.sh                    # Uses defaults: mark/12345678
./redis.sh john               # Uses john/12345678
./redis.sh john secretpass    # Uses john/secretpass
```

**Test Flow**: Login → Verify Redis → Logout → Verify Deletion

---

## Files Reference

1. `app/services/auth/cookies/redis_provider.py` - Core auth logic
2. `app/services/redis_user.py` - Generated router (will be regenerated from template)
3. `app/services_init.py` - Service initialization
4. `app/main.py` - Integration point
5. `redis.sh` - Test script
6. `mongo.json` - Configuration

---

## Next Steps

**Immediate** (before production):
1. Implement password hashing (bcrypt)
2. Make cookie security configurable
3. Add basic error handling

**Short term** (next sprint):
4. Add to test framework
5. Make SESSION_TTL configurable
6. Improve error handling and rate limiting

**Future** (as needed):
7. Implement ServiceRegistry pattern (see `service.md`)
8. Add OAuth support
9. Multi-service deployment considerations
