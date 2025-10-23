# Service Architecture Implementation Plan

## Overview

This document details the plan to implement a schema-driven service architecture that allows entities to declare services via `@service` decorators in the MMD schema. The first service type is authentication (`auth.cookies.redis`), with plans to support OAuth, notifications, storage, and analytics in the future.

---

## Current State

### What Exists
```
app/services/
├── auth/
│   ├── base_router.py          # BaseAuth, BaseCookieStore abstractions
│   └── cookies/
│       └── redis_provider.py   # CookiesAuth, RedisCookieStore implementations
├── redis_user.py               # Generated router for User auth endpoints
├── metadata.py                 # Entity metadata service
├── model.py                    # Model service
├── notify.py                   # Notification service
└── request_context.py          # Request context management
```

### Schema Declaration
```mermaid
User {
    String username
    String email
    String password
    %% @service auth.cookies.redis
}
```

### Configuration (mongo.json)
```json
{
    "auth.cookies.redis": {
        "host": "127.0.0.1",
        "port": 6379,
        "db": 0
    }
}
```

---

## Architecture Principles

### 1. **Schema-Driven Service Binding**
Services are declared in the schema using `@service <type>.<method>.<provider>` syntax:
- **type**: Service category (auth, notifications, storage, analytics)
- **method**: Implementation method (cookies, oauth, email, s3)
- **provider**: Specific provider (redis, google, sendgrid, aws)

### 2. **Explicit Configuration Required**
All service field mappings must be explicitly defined in schema - no conventions:
- **Why**: Different service implementations need different fields (OAuth vs cookies vs SAML)
- **Why**: Non-auth services (notifications, storage, analytics) have completely different configs
- **Why**: Enables service-specific validation via config schemas
- **Result**: Schema is self-documenting and unambiguous

### 3. **Code Generation**
Parser generates router files and wiring code from schema declarations, avoiding boilerplate.

### 4. **Separation of Concerns**
```
Schema (@service)
  ↓
Service Registry (maps entity → service)
  ↓
Generated Router (FastAPI endpoints)
  ↓
Service Implementation (business logic)
  ↓
Provider Backend (Redis, Google, S3, etc.)
```

---

## Why Explicit Configuration is Essential

### Different Auth Implementations Need Different Fields

**Cookie-based auth:**
```mermaid
User {
    String email
    String password
    %% @service auth.cookies.redis {
    %%   loginField: "email",
    %%   passwordField: "password",
    %%   sessionIdentifier: "id"
    %% }
}
```

**OAuth auth (completely different fields):**
```mermaid
User {
    String email
    String googleId       ← NEW field for OAuth
    String profilePicture ← NEW field OAuth can populate
    %% @service auth.oauth.google {
    %%   emailField: "email",
    %%   providerIdField: "googleId",  ← OAuth-specific
    %%   avatarField: "profilePicture" ← OAuth-specific
    %% }
}
```

**SAML enterprise auth (even more different):**
```mermaid
User {
    String workEmail
    String companyId
    Array[String] permissions
    %% @service auth.saml.okta {
    %%   emailField: "workEmail",        ← Different field name
    %%   tenantIdField: "companyId",     ← SAML-specific
    %%   rolesField: "permissions"       ← Maps SAML attributes
    %% }
}
```

**Conventions cannot handle this diversity.**

---

### Non-Auth Services Have Completely Different Configs

**Notifications (email):**
```mermaid
Event {
    String title
    Array[String] attendeeEmails
    Date eventDate
    %% @service notifications.email.sendgrid {
    %%   recipientField: "attendeeEmails",
    %%   subjectTemplate: "{{title}} Reminder",
    %%   bodyFields: ["description", "eventDate"],
    %%   triggerOn: "create",
    %%   templateId: "event-reminder-v2"
    %% }
}
```

**Storage (file uploads):**
```mermaid
Profile {
    Binary avatarData
    String avatarUrl
    %% @service storage.files.s3 {
    %%   fileField: "avatarData",
    %%   urlField: "avatarUrl",
    %%   bucket: "profile-avatars",
    %%   acl: "public-read",
    %%   maxSize: "5MB",
    %%   allowedTypes: ["image/jpeg", "image/png"]
    %% }
}
```

**Analytics (event tracking):**
```mermaid
UserEvent {
    String userId
    String eventId
    Boolean attended
    Integer rating
    %% @service analytics.tracking.mixpanel {
    %%   eventName: "event_attended",
    %%   userIdField: "userId",
    %%   propertiesFields: ["eventId", "rating"],
    %%   triggerOn: "update",
    %%   conditionalField: "attended",
    %%   conditionalValue: true
    %% }
}
```

**Each service type has unique configuration requirements.**

---

### Multiple Services on Same Entity

```mermaid
User {
    String email
    String password
    String googleId
    String githubId

    %% Standard password auth
    %% @service auth.cookies.redis {
    %%   name: "standard",
    %%   loginField: "email",
    %%   passwordField: "password"
    %% }

    %% Google OAuth
    %% @service auth.oauth.google {
    %%   name: "google",
    %%   emailField: "email",
    %%   providerIdField: "googleId"
    %% }

    %% GitHub OAuth
    %% @service auth.oauth.github {
    %%   name: "github",
    %%   emailField: "email",
    %%   providerIdField: "githubId"
    %% }
}
```

**Three auth services on one entity - conventions are impossible.**

---

### Service Configuration Schemas

Each service type defines its own configuration schema that the parser validates:

**auth.service.schema.yaml:**
```yaml
type: auth
required_fields:
  - loginField
  - passwordField
optional_fields:
  sessionIdentifier:
    type: string
    default: "id"
  name:
    type: string
    description: "Name if entity has multiple auth services"
```

**notifications.service.schema.yaml:**
```yaml
type: notifications
required_fields:
  - recipientField
  - subjectTemplate
  - triggerOn
optional_fields:
  bodyFields:
    type: array
    default: []
  templateId:
    type: string
```

**storage.service.schema.yaml:**
```yaml
type: storage
required_fields:
  - fileField
  - urlField
  - bucket
optional_fields:
  maxSize:
    type: string
    default: "10MB"
  allowedTypes:
    type: array
    default: []
  acl:
    type: string
    default: "private"
```

**Parser validates service configs against these schemas during code generation.**

---

## Implementation Phases

## Phase 1: Foundation (Immediate - Week 1)

### 1.1 Service Registry
**File:** `app/services/service_registry.py`

**Purpose:** Central registry mapping entities to service implementations

**Implementation:**
```python
from typing import Dict, Any, Optional, Type
import logging

class ServiceRegistry:
    """
    Central registry for entity services.
    Maps (entity, service_type) → service implementation class
    """
    _registry: Dict[tuple[str, str], Type] = {}
    _service_metadata: Dict[tuple[str, str], dict] = {}

    @classmethod
    def register(cls, entity: str, service_type: str,
                 implementation: Type, metadata: Optional[dict] = None):
        """
        Register a service implementation for an entity.

        Args:
            entity: Entity name (e.g., "User")
            service_type: Service type (e.g., "auth")
            implementation: Service class (e.g., CookiesAuth)
            metadata: Optional service configuration/field mappings
        """
        key = (entity.lower(), service_type)
        cls._registry[key] = implementation
        cls._service_metadata[key] = metadata or {}
        logging.info(f"Registered service: {entity}.{service_type} → {implementation.__name__}")

    @classmethod
    def get(cls, entity: str, service_type: str) -> Optional[Type]:
        """Get service implementation for entity"""
        return cls._registry.get((entity.lower(), service_type))

    @classmethod
    def get_metadata(cls, entity: str, service_type: str) -> dict:
        """Get service metadata (field mappings, config)"""
        return cls._service_metadata.get((entity.lower(), service_type), {})

    @classmethod
    def list_services(cls, entity: Optional[str] = None) -> list:
        """List all registered services, optionally filtered by entity"""
        if entity:
            return [
                {"entity": ent, "service_type": svc_type, "implementation": impl.__name__}
                for (ent, svc_type), impl in cls._registry.items()
                if ent == entity.lower()
            ]
        return [
            {"entity": ent, "service_type": svc_type, "implementation": impl.__name__}
            for (ent, svc_type), impl in cls._registry.items()
        ]
```

---

### 1.2 Service Lifecycle Manager
**File:** `app/services/service_lifecycle.py`

**Purpose:** Manage service initialization/shutdown (Redis connections, etc.)

**Implementation:**
```python
from typing import Dict, Any
import logging
from app.services.service_registry import ServiceRegistry
from app.config import Config

class ServiceLifecycle:
    """
    Manages service lifecycle (startup/shutdown).
    Initializes services that need async setup (Redis, OAuth clients, etc.)
    """
    _initialized_services: Dict[str, Any] = {}

    @classmethod
    async def startup(cls):
        """
        Initialize all registered services at app startup.
        Calls initialize() on service classes that need async setup.
        """
        logging.info("=== Service Lifecycle: Starting ===")

        for (entity, service_type), service_class in ServiceRegistry._registry.items():
            service_key = f"{entity}.{service_type}"

            # Check if service needs initialization
            if not hasattr(service_class, 'initialize'):
                logging.debug(f"Service {service_key} does not need initialization")
                continue

            # Get service config from mongo.json
            # Format: "auth.cookies.redis" → Config.get("auth.cookies.redis")
            service_metadata = ServiceRegistry.get_metadata(entity, service_type)
            provider_path = service_metadata.get("provider", "")  # e.g., "auth.cookies.redis"
            service_config = Config.get(provider_path, {})

            if not service_config:
                logging.warning(f"No config found for {service_key} (provider: {provider_path})")
                continue

            # Initialize service
            try:
                logging.info(f"Initializing service: {service_key}")
                initialized_service = await service_class.initialize(service_config)
                cls._initialized_services[service_key] = initialized_service
                logging.info(f"✓ Service initialized: {service_key}")
            except Exception as e:
                logging.error(f"✗ Failed to initialize {service_key}: {e}")
                raise

        logging.info(f"=== Service Lifecycle: Started {len(cls._initialized_services)} services ===")

    @classmethod
    async def shutdown(cls):
        """Cleanup services at app shutdown"""
        logging.info("=== Service Lifecycle: Shutting down ===")

        for service_key, service in cls._initialized_services.items():
            if hasattr(service, 'close'):
                try:
                    await service.close()
                    logging.info(f"✓ Closed service: {service_key}")
                except Exception as e:
                    logging.error(f"✗ Error closing {service_key}: {e}")

        cls._initialized_services.clear()
        logging.info("=== Service Lifecycle: Shutdown complete ===")

    @classmethod
    def get_service(cls, entity: str, service_type: str) -> Any:
        """Get initialized service instance"""
        return cls._initialized_services.get(f"{entity.lower()}.{service_type}")
```

---

### 1.3 Wire into FastAPI
**File:** `app/main.py`

**Add startup/shutdown hooks:**
```python
from app.services.service_lifecycle import ServiceLifecycle

@app.on_event("startup")
async def startup_event():
    # ... existing database init ...

    # Initialize services
    await ServiceLifecycle.startup()

@app.on_event("shutdown")
async def shutdown_event():
    # Shutdown services
    await ServiceLifecycle.shutdown()

    # ... existing database close ...
```

---

### 1.4 Reorganize Directory Structure
**New structure:**
```
app/services/
├── __init__.py
├── service_registry.py          # NEW: Registry
├── service_lifecycle.py         # NEW: Lifecycle manager
├── generated/                   # NEW: Generated service routers
│   └── user_auth.py            # MOVED from redis_user.py
├── auth/
│   ├── __init__.py
│   ├── base_router.py          # Base abstractions
│   └── cookies/
│       └── redis_provider.py   # Redis implementation
├── framework/                   # Framework utilities
├── metadata.py
├── model.py
├── notify.py
└── request_context.py
```

**Action:** Move `redis_user.py` → `generated/user_auth.py`

---

## Phase 2: Field Mapping & Enhanced Code Generation (Week 2)

### 2.1 Schema Parser Enhancement
**File:** `test/query-src/pkg/parser/service_parser.go` (or Python equivalent)

**Extract service declarations with field mappings:**

**Schema syntax:**
```mermaid
User {
    String email      %% @unique
    String password
    %% @service auth.cookies.redis { loginField: "email" }
}
```

**Parser output (JSON/YAML):**
```json
{
  "entities": {
    "User": {
      "services": [
        {
          "type": "auth",
          "method": "cookies",
          "provider": "redis",
          "provider_path": "auth.cookies.redis",
          "config": {
            "loginField": "email",
            "passwordField": "password",
            "sessionIdentifier": "id"
          }
        }
      ]
    }
  }
}
```

**All fields must be explicitly specified in schema - no conventions.**

---

### 2.2 Enhanced Code Generator
**File:** `test/query-src/pkg/generator/service_generator.go` (or Python)

**Generate improved router:**

**Template:** `templates/service_auth_router.py.tmpl`
```python
# GENERATED FILE - DO NOT EDIT
# Generated from schema @service declaration for {{.Entity}}

from fastapi import APIRouter, Request, Response, HTTPException
from typing import Dict, Any
from app.services.service_registry import ServiceRegistry
from app.services.service_lifecycle import ServiceLifecycle
from app.db.factory import get_database
from app.models.{{.entity}}_model import {{.Entity}}
import logging

router = APIRouter()

# Service metadata from schema
LOGIN_FIELD = "{{.LoginField}}"
PASSWORD_FIELD = "{{.PasswordField}}"
SESSION_ID_FIELD = "{{.SessionIdentifier}}"

@router.post("/login", summary="Login")
async def login_endpoint(request: Request, response: Response):
    """
    Login using {{.Entity}} credentials.

    Expected payload:
    {
        "{{.LoginField}}": "user@example.com",
        "{{.PasswordField}}": "password123"
    }
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    # Validate required fields
    login_value = payload.get(LOGIN_FIELD)
    password = payload.get(PASSWORD_FIELD)

    if not login_value or not password:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {LOGIN_FIELD}, {PASSWORD_FIELD}"
        )

    # Query database for user
    db = get_database()
    query = {LOGIN_FIELD: login_value}

    try:
        user_docs, count = await db.documents.get_all("{{.Entity}}", filter=query, pageSize=1)
    except Exception as e:
        logging.error(f"Database error during login: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    if count == 0:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = user_docs[0]

    # TODO: Verify password using bcrypt (currently placeholder)
    # In production: bcrypt.checkpw(password.encode(), user[PASSWORD_FIELD].encode())
    if user.get(PASSWORD_FIELD) != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Get initialized auth service
    auth_service = ServiceLifecycle.get_service("{{.Entity}}", "auth")
    if not auth_service:
        raise HTTPException(status_code=500, detail="Auth service not initialized")

    # Create session
    session_data = {
        "user_id": user[SESSION_ID_FIELD],
        "login_field": LOGIN_FIELD,
        "login_value": login_value
    }

    session_id = await auth_service.create_session(session_data)

    # Set cookie
    response.set_cookie(
        key=auth_service.cookie_name,
        value=session_id,
        **auth_service.cookie_options
    )

    return {
        "success": True,
        "user_id": user[SESSION_ID_FIELD],
        "message": "Login successful"
    }

@router.post("/logout", summary="Logout")
async def logout_endpoint(request: Request, response: Response):
    """Logout user and clear session"""
    auth_service = ServiceLifecycle.get_service("{{.Entity}}", "auth")
    if not auth_service:
        raise HTTPException(status_code=500, detail="Auth service not initialized")

    success = await auth_service.logout(request)

    if success:
        response.delete_cookie(key=auth_service.cookie_name)
        return {"success": True, "message": "Logout successful"}
    else:
        raise HTTPException(status_code=400, detail="No active session")

@router.post("/refresh", summary="Refresh session")
async def refresh_endpoint(request: Request, response: Response):
    """Refresh user session"""
    auth_service = ServiceLifecycle.get_service("{{.Entity}}", "auth")
    if not auth_service:
        raise HTTPException(status_code=500, detail="Auth service not initialized")

    success = await auth_service.refresh(request)

    if success:
        return {"success": True, "message": "Session refreshed"}
    else:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

@router.get("/metadata", summary="Get {{.Entity}} metadata")
async def get_metadata():
    """Get metadata for {{.Entity}} entity"""
    return {{.Entity}}.get_metadata()

def init_router(app):
    """Register router with FastAPI app"""
    app.include_router(router, prefix="/{{.entity}}/auth", tags=["{{.Entity}} Auth"])

    # Register service in registry
    from app.services.auth.cookies.redis_provider import CookiesAuth
    ServiceRegistry.register(
        entity="{{.Entity}}",
        service_type="auth",
        implementation=CookiesAuth,
        metadata={
            "provider": "{{.ProviderPath}}",
            "loginField": LOGIN_FIELD,
            "passwordField": PASSWORD_FIELD,
            "sessionIdentifier": SESSION_ID_FIELD
        }
    )
```

---

### 2.3 Update Auth Provider Interface
**File:** `app/services/auth/cookies/redis_provider.py`

**Add `create_session()` method:**
```python
async def create_session(self, session_data: dict) -> str:
    """
    Create a new session and return session ID.

    Args:
        session_data: Data to store in session (user_id, etc.)

    Returns:
        session_id: UUID session identifier
    """
    session_id = str(uuid.uuid4())
    session_data["created"] = time.time()

    await self.cookie_store.set_session(session_id, session_data, SESSION_TTL)

    return session_id
```

---

## Phase 3: Configuration & Multi-Service Support (Week 3)

### 3.1 Enhanced Configuration Format
**File:** `mongo.json` (or `config.json`)

**Current:**
```json
{
    "auth.cookies.redis": {
        "host": "127.0.0.1",
        "port": 6379,
        "db": 0
    }
}
```

**Enhanced (structured by entity + service):**
```json
{
    "services": {
        "User.auth": {
            "provider": "auth.cookies.redis",
            "config": {
                "host": "127.0.0.1",
                "port": 6379,
                "db": 0,
                "session_ttl": 3600,
                "cookie_name": "user_session"
            }
        }
    }
}
```

**Backward compatibility:** Keep flat `"auth.cookies.redis"` config, but add `Config.get_service_config()`:

**File:** `app/config.py`
```python
@classmethod
def get_service_config(cls, entity: str, service_type: str, provider: str) -> dict:
    """
    Get service configuration for entity.

    Tries hierarchical lookup:
    1. services.{Entity}.{service_type}.config
    2. {provider} (flat format for backward compat)

    Args:
        entity: Entity name (e.g., "User")
        service_type: Service type (e.g., "auth")
        provider: Provider path (e.g., "auth.cookies.redis")

    Returns:
        Configuration dict or empty dict
    """
    # Try new structured format
    services = cls._config.get('services', {})
    service_key = f"{entity}.{service_type}"

    if service_key in services:
        return services[service_key].get('config', {})

    # Fall back to flat format (backward compat)
    return cls._config.get(provider, {})
```

---

### 3.2 Multi-Service Support
**Schema with multiple services:**
```mermaid
Event {
    String title
    String description
    %% @service notifications.email.sendgrid
    %% @service analytics.tracking.mixpanel
}
```

**Registry supports multiple services per entity:**
```python
ServiceRegistry.register("Event", "notifications", SendgridService)
ServiceRegistry.register("Event", "analytics", MixpanelService)
```

**Generated routers:** `generated/event_notifications.py`, `generated/event_analytics.py`

---

## Phase 4: OAuth & Additional Auth Methods (Week 4)

### 4.1 OAuth Provider
**File:** `app/services/auth/oauth/google_provider.py`

**Implementation:**
```python
from authlib.integrations.starlette_client import OAuth
from app.services.auth.base_router import BaseAuth, AuthContext

class GoogleOAuth(BaseAuth):
    """Google OAuth2 authentication provider"""

    oauth = OAuth()

    @classmethod
    async def initialize(cls, config: dict):
        """Initialize OAuth client"""
        cls.oauth.register(
            name='google',
            client_id=config['client_id'],
            client_secret=config['client_secret'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )
        return cls

    async def login(self, username: str, password: str) -> AuthContext:
        """Not used for OAuth - handled by redirect flow"""
        raise NotImplementedError("OAuth uses redirect flow")

    async def authenticate(self, request: Request) -> AuthContext:
        """Validate OAuth token"""
        token = request.session.get('user')
        if token:
            return AuthContext(
                authenticated=True,
                user_id=token['email'],
                session_data=token
            )
        return AuthContext(authenticated=False)
```

**Schema:**
```mermaid
User {
    String email
    %% @service auth.oauth.google
}
```

**Config:**
```json
{
    "auth.oauth.google": {
        "client_id": "xxx",
        "client_secret": "yyy",
        "redirect_uri": "http://localhost:5500/user/auth/callback"
    }
}
```

---

## Phase 5: Testing & Documentation (Week 5)

### 5.1 Service Testing Framework
**File:** `test/services/test_auth_service.py`

**Mock service for testing:**
```python
class MockAuthService(BaseAuth):
    """Mock auth for testing without Redis"""

    _sessions = {}  # In-memory session store

    async def login(self, username: str, password: str) -> AuthContext:
        if username == "testuser" and password == "testpass":
            session_id = "mock-session-123"
            self._sessions[session_id] = {"user_id": "test-user-id"}
            return AuthContext(authenticated=True, user_id="test-user-id")
        return AuthContext(authenticated=False, error="Invalid credentials")
```

**Register mock in tests:**
```python
@pytest.fixture
def mock_auth():
    ServiceRegistry.register("User", "auth", MockAuthService)
    yield
    ServiceRegistry._registry.clear()
```

---

### 5.2 Documentation Generation
**File:** `docs/services.md` (auto-generated)

**Generator script:**
```python
def generate_service_docs():
    """Generate service documentation from registry"""
    services = ServiceRegistry.list_services()

    output = "# Active Services\n\n"

    for service in services:
        entity = service['entity']
        service_type = service['service_type']
        impl = service['implementation']
        metadata = ServiceRegistry.get_metadata(entity, service_type)

        output += f"## {entity}.{service_type}\n"
        output += f"- **Implementation:** {impl}\n"
        output += f"- **Provider:** {metadata.get('provider', 'N/A')}\n"
        output += f"- **Endpoints:** `/api/{entity.lower()}/{service_type}/...`\n\n"

    return output
```

---

## Testing Strategy

### Unit Tests
1. **Service Registry:** Test register/get/list operations
2. **Lifecycle Manager:** Test startup/shutdown with mock services
3. **Auth Providers:** Test login/logout/refresh logic with mock stores

### Integration Tests
1. **Full auth flow:** Login → authenticated request → logout
2. **Multiple services:** Entity with both auth + notifications
3. **Service initialization:** Verify Redis connection, OAuth client setup

### End-to-End Tests
1. Use existing `test/validate` framework
2. Add auth-specific test cases (login, authenticated CRUD, logout)

---

## Migration Path

### Step 1: Current → Phase 1 (No Breaking Changes)
- Keep `redis_user.py` working
- Add registry + lifecycle alongside existing code
- Wire startup hooks (no-op if no services registered)

### Step 2: Phase 1 → Phase 2 (Generate New Code)
- Generate `user_auth.py` with new template
- Keep old `redis_user.py` for backward compat
- Test both routers in parallel

### Step 3: Phase 2 → Phase 3 (Deprecate Old)
- Remove `redis_user.py`
- Update schema parser to generate new format
- Migrate all configs to new structure

---

## Success Metrics

### Phase 1 Complete When:
- ✅ ServiceRegistry implemented and tested
- ✅ ServiceLifecycle manages Redis connection
- ✅ FastAPI startup/shutdown hooks wire services
- ✅ Existing auth functionality still works

### Phase 2 Complete When:
- ✅ Schema parser extracts `@service` with field mappings
- ✅ Generator creates auth router using template
- ✅ Generated code authenticates against database
- ✅ Field conventions (username/email/password) work

### Phase 3 Complete When:
- ✅ Multiple services can be declared per entity
- ✅ Config supports hierarchical service settings
- ✅ Backward compatibility with flat config maintained

### Phase 4 Complete When:
- ✅ OAuth provider implemented (Google)
- ✅ Can switch auth method via schema change
- ✅ Both cookie and OAuth auth coexist

### Phase 5 Complete When:
- ✅ Mock services enable testing without Redis
- ✅ Service documentation auto-generated
- ✅ Integration tests cover all auth flows

---

## Future Service Types

### Notifications
```mermaid
Event {
    %% @service notifications.email.sendgrid { recipientField: "attendees" }
}
```

### Storage
```mermaid
Profile {
    String avatarUrl
    %% @service storage.files.s3 { bucket: "profile-avatars" }
}
```

### Analytics
```mermaid
UserEvent {
    %% @service analytics.tracking.mixpanel { event: "event_attended" }
}
```

---

## Open Questions

1. **Password Hashing:** Should we auto-hash password field in DocumentManager or leave to auth service?
2. **Session Storage:** Support multiple stores (Redis, Memcached, Database)?
3. **Multi-Tenancy:** How do services handle tenant isolation?
4. **Service Dependencies:** Can services depend on other services (e.g., auth requires notifications)?

---

## References

- Schema: `schema.mmd`
- Config: `mongo.json`
- Parser: `test/query-src/pkg/parser/`
- Current implementation: `app/services/auth/cookies/redis_provider.py`
