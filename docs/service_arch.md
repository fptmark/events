# Service Architecture - Configuration-Driven Approach

**Date**: 2025-10-22
**Status**: Architectural Decision

---

## Overview

Services are **configuration-driven** rather than code-generated. A single provider implementation (e.g., `redis_provider.py`) serves multiple entities by reading entity-specific configuration from `schema.yaml`.

---

## Core Principle

**One Provider + Configuration = Multiple Entity Services**

Instead of generating entity-specific code, services:
1. Implement generic operations (login/logout, upload/download, send, etc.)
2. Read configuration at runtime to customize behavior per entity
3. Register routes dynamically based on schema configuration

---

## Example: Redis Authentication

### Schema Configuration

```yaml
User:
  services:
    auth.cookies.redis:
      fields:
        login: username
        password: password

Customer:
  services:
    auth.cookies.redis:
      fields:
        login: email
        password: password

Admin:
  services:
    auth.cookies.redis:
      fields:
        login: admin_id
        password: password
```

### Provider Implementation

**File**: `app/services/auth/cookies/redis_provider.py`

```python
class CookiesAuth:
    @classmethod
    async def initialize(cls, config: dict):
        # Initialize Redis connection
        store = RedisCookieStore(...)
        await store.connect()
        cls.cookie_store = store

    async def login(self, entity_name: str, field_map: dict, credentials: dict) -> str | None:
        # Generic implementation using config
        login_field = field_map["login"]
        password_field = field_map["password"]

        login_value = credentials.get(login_field)
        password_value = credentials.get(password_field)

        # Query database with entity-specific field names
        db = DatabaseFactory.get_instance()
        user_docs, count = await db.documents.get_all(
            entity_name,
            filter={login_field: login_value},
            pageSize=1
        )

        if count == 0 or user.get(password_field) != password_value:
            return None

        # Create session (generic)
        session_id = str(uuid.uuid4())
        session_data = {
            "user_id": str(user.get("id")),
            "entity": entity_name,
            "created": time.time()
        }

        await self.cookie_store.set_session(session_id, session_data, SESSION_TTL)
        return session_id
```

### Route Registration

Routes are registered dynamically at startup based on schema configuration:

```python
# services_init.py
async def initialize(app=None):
    schema = load_schema("schema.yaml")

    for entity_name, entity_def in schema.entities.items():
        services = entity_def.get("services", {})

        for service_name, service_config in services.items():
            if service_name == "auth.cookies.redis":
                # Register routes for this entity
                register_auth_routes(app, entity_name, service_config)
```

---

## When This Pattern Works

### ✅ **Auth Services** (JWT, OAuth, LDAP, Cookies)
- **Operations**: login, logout, refresh, validate
- **What varies**: Field names, validation rules, storage backend
- **Configuration**: Field mappings, session TTL, cookie settings
- **Verdict**: **Perfect fit**

### ✅ **Storage Services** (S3, Azure Blob, Local File)
- **Operations**: upload, download, delete, list
- **What varies**: Bucket/container names, path templates, credentials
- **Configuration**: Storage location, naming patterns, access credentials
- **Verdict**: **Perfect fit**

### ✅ **Email/Notification Services** (SendGrid, SES, SMTP)
- **Operations**: send, send_template, send_bulk
- **What varies**: API keys, from addresses, template IDs
- **Configuration**: Provider credentials, default templates, rate limits
- **Verdict**: **Perfect fit**

### ✅ **Audit/Logging Services**
- **Operations**: log_change, get_history, get_audit_trail
- **What varies**: Which fields to track, retention policy, destination
- **Configuration**: Tracked fields, storage location, filters
- **Verdict**: **Perfect fit**

### ⚠️ **Payment Services** (Stripe, PayPal)
- **Operations**: create_payment, refund, get_status
- **What varies**: Product types, pricing logic, refund policies
- **Configuration**: API keys, webhook URLs, currency
- **Concerns**: Entity-specific business logic may be complex
- **Verdict**: **Works with careful configuration design**

### ⚠️ **Search/Indexing Services** (Elasticsearch, Algolia)
- **Operations**: index, search, suggest
- **What varies**: Indexed fields, search weights, ranking algorithms
- **Configuration**: Field mappings, boost values, facets
- **Concerns**: Configuration can get verbose
- **Verdict**: **Works but may need thoughtful config structure**

### ❌ **Workflow/State Machine Services**
- **Operations**: Vary completely per entity
- **Examples**:
  - Order: `pending → paid → shipped → delivered → closed`
  - Ticket: `open → assigned → in_progress → resolved → closed`
  - Approval: `draft → submitted → approved/rejected → published`
- **What varies**: States, transitions, validation rules, actions
- **Concerns**: Too entity-specific for configuration alone
- **Verdict**: **Needs code generation or entity-specific implementations**

---

## Architecture Benefits

### 1. **No Code Generation** (for most services)
- Single provider implementation
- Reduces complexity
- Easier to maintain and debug

### 2. **Configuration-Driven**
- All customization in `schema.yaml`
- Clear separation of behavior vs configuration
- Easy to add new entities

### 3. **Runtime Flexibility**
- Services can be added/removed without regeneration
- Configuration changes don't require rebuild
- Dynamic route registration

### 4. **Consistent Pattern**
- Same approach across all services
- Predictable structure
- Easy to understand

---

## Implementation Strategy

### Phase 1: Config-Driven Services (Current)
1. Implement generic providers (auth, storage, notifications)
2. Read configuration from `schema.yaml`
3. Register routes dynamically at startup
4. **No code generation needed**

### Phase 2: Complex Services (Future)
If we encounter services that need entity-specific code:
1. Identify the pattern (e.g., workflows, complex business logic)
2. Design a template system for that specific service type
3. Generate entity-specific implementations
4. **Only generate when configuration isn't sufficient**

---

## Decision: No Service Generator (For Now)

**Reasoning**:
- 90% of services fit the config-driven pattern
- Simpler architecture
- Less code to maintain
- Faster development

**If we need generation later**:
- Add it for specific service types that require it
- Don't over-engineer upfront
- YAGNI (You Aren't Gonna Need It)

---

## Current Implementation Status

### Completed ✅
- Redis provider implementation (`redis_provider.py`)
- Service initialization pattern (`services_init.py`)
- Schema configuration format
- Working login/logout/refresh endpoints for User entity

### Next Steps
1. **Refactor redis_provider.py** to be config-driven (not hardcoded to User entity)
2. **Dynamic route registration** based on schema
3. **Test with multiple entities** (User, Customer, Admin)
4. **Implement other services** following the same pattern

---

## Configuration Schema Reference

### Service Definition in schema.yaml

```yaml
EntityName:
  services:
    service.type.provider:
      fields:
        field1: entity_field_name
        field2: entity_field_name
      options:
        option1: value
        option2: value
```

### Example: Multiple Services on One Entity

```yaml
User:
  services:
    # Authentication
    auth.cookies.redis:
      fields:
        login: username
        password: password
      options:
        session_ttl: 3600
        cookie_secure: false

    # File storage
    storage.s3:
      fields:
        id_field: id
      options:
        bucket: user-uploads
        path_template: "users/{id}/{filename}"

    # Email notifications
    notifications.sendgrid:
      fields:
        email: email
        name: username
      options:
        from_email: noreply@example.com
        template_welcome: d-abc123
```

---

## File Organization

```
app/services/
├── auth/
│   ├── cookies/
│   │   └── redis_provider.py      # Generic implementation
│   ├── jwt/
│   │   └── provider.py            # Generic implementation
│   └── oauth/
│       └── provider.py            # Generic implementation
├── storage/
│   ├── s3_provider.py             # Generic implementation
│   └── local_provider.py          # Generic implementation
├── notifications/
│   ├── sendgrid_provider.py       # Generic implementation
│   └── ses_provider.py            # Generic implementation
└── services_init.py               # Dynamic registration

# No generated files needed!
```

---

## Comparison: Old vs New Approach

### Old Approach (Code Generation)
```
redis_provider.py (template)
  ↓ (generator reads, customizes)
redis_user.py (generated)
redis_customer.py (generated)
redis_admin.py (generated)
```

**Issues**:
- More files
- Regeneration required
- Template complexity
- Harder to maintain

### New Approach (Configuration-Driven)
```
redis_provider.py (generic implementation)
  ↓ (reads config at runtime)
schema.yaml (configuration)
  ↓ (dynamic route registration)
Routes registered for User, Customer, Admin
```

**Benefits**:
- Single implementation
- No regeneration
- Clear configuration
- Simpler maintenance

---

## References

- **Schema**: `schema.yaml` - Service configurations
- **Config**: `mongo.json` - Runtime settings (Redis host, etc.)
- **Provider**: `app/services/auth/cookies/redis_provider.py`
- **Initialization**: `app/services/services_init.py`
- **Planning Docs**: `redis_todo.md`, `service.md`

---

## Open Questions

1. **How to handle entity-specific validation?**
   - Option A: Validation rules in schema
   - Option B: Validation decorators on entity models
   - **Decision**: TBD

2. **How to handle service dependencies?**
   - Example: Storage service needs auth to determine upload permissions
   - **Decision**: TBD

3. **How to version service APIs?**
   - If auth v2 needs different behavior
   - **Decision**: TBD

---

## Success Criteria

A service architecture is successful when:
- ✅ Adding a new entity to an existing service requires only configuration changes
- ✅ Adding a new service requires one provider implementation
- ✅ Service behavior is predictable and testable
- ✅ Configuration is clear and validates at startup
- ✅ No code generation needed for 90% of services
