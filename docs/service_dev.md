# Service Architecture - Development Summary

## Core Decisions Made

### 1. What is a Service?
- **Definition**: External capability added to an entity beyond CRUD
- **Examples**: authentication, notifications, file storage, analytics
- **Not attached to entity until declared in schema via `@service`**

### 2. Service Naming
- **Variable parts** (not fixed structure): `type.method.provider.etc`
- **Examples**:
  - `auth.cookies.redis` (3 parts)
  - `notifications.email` (2 parts)
  - `storage.s3.aws.us-east-1` (4 parts)
- Parts describe service path/hierarchy

### 3. Implementation Class Naming
- **Convention**: `{Type}{Method}{Provider}` (matches service path)
- **Examples**:
  - `auth.cookies.redis` → `AuthCookiesRedis`
  - `auth.oauth.google` → `AuthOAuthGoogle`
  - `notifications.email.sendgrid` → `NotificationsEmailSendgrid`

### 4. Field Roles vs Field Names
- **Service defines field ROLES** (what purpose each field serves)
- **Schema maps entity FIELDS to those roles**
- **Example**:
  ```
  Service defines: "loginField" role
  Schema maps: loginField → "email" field
  ```

### 5. Registry Location & Format
- **File**: `app/services/services_registry.json`
- **Format**: JSON listing all available services with:
  - Description
  - Required fields (with validation rules)
  - Optional fields (with defaults)
  - Implementation (module + class)
- **Manually authored** (not auto-generated)
- **Purpose**: Documents available services, validates schema `@service` directives

### 6. Field Validation
- **Parser validates** that mapped fields meet service requirements
- **Example validation**:
  ```
  Registry: loginField must be { type: "string", unique: true }
  Schema: maps loginField → "email"
  Parser checks: email is String ✓, has @unique ✓
  ```

### 7. Generated Artifacts
**Generate BOTH:**
1. **`service_bindings.json`** - For tooling/inspection (shows all entity→service mappings)
2. **Python routers with embedded field constants** - For runtime (no file I/O)

---

## Files & Structure

```
app/
├── services/
│   ├── services_registry.json          # ALL available services (manual)
│   ├── generated/
│   │   ├── service_bindings.json       # Entity→service mappings (generated)
│   │   ├── user_auth.py                # Router with embedded field constants (generated)
│   │   └── event_notifications.py      # Router (generated)
│   ├── auth/
│   │   └── cookies/
│   │       └── redis_provider.py       # AuthCookiesRedis implementation
│   └── notifications/
│       └── email/
│           └── sendgrid_provider.py    # NotificationsEmailSendgrid implementation
```

---

## Service Registry Format

**File**: `app/services/services_registry.json`

```json
{
  "services": {
    "auth.cookies.redis": {
      "description": "Cookie-based authentication with Redis session store",
      "category": "auth",
      "required_fields": {
        "loginField": {
          "type": "string",
          "unique": true,
          "description": "Field containing username or email for login"
        },
        "passwordField": {
          "type": "string",
          "description": "Field containing password"
        }
      },
      "optional_fields": {
        "sessionIdentifier": {
          "type": "string",
          "default": "id",
          "description": "Field to use as session identifier"
        }
      },
      "implementation": {
        "module": "app.services.auth.cookies.redis_provider",
        "class": "AuthCookiesRedis"
      }
    },

    "auth.oauth.google": {
      "description": "Google OAuth2 authentication",
      "category": "auth",
      "required_fields": {
        "emailField": {
          "type": "string",
          "unique": true,
          "description": "Field to store user email from Google"
        },
        "providerIdField": {
          "type": "string",
          "unique": true,
          "description": "Field to store Google user ID"
        }
      },
      "optional_fields": {
        "avatarField": {
          "type": "string",
          "description": "Field to store profile picture URL"
        }
      },
      "implementation": {
        "module": "app.services.auth.oauth.google_provider",
        "class": "AuthOAuthGoogle"
      }
    },

    "notifications.email.sendgrid": {
      "description": "Email notifications via Sendgrid",
      "category": "notifications",
      "required_fields": {
        "recipientField": {
          "type": "string",
          "description": "Field containing recipient email(s)"
        },
        "subjectTemplate": {
          "type": "string",
          "description": "Email subject template (supports {{field}} syntax)"
        },
        "triggerOn": {
          "type": "enum",
          "values": ["create", "update", "delete"],
          "description": "When to send notification"
        }
      },
      "optional_fields": {
        "bodyFields": {
          "type": "array",
          "default": [],
          "description": "Fields to include in email body"
        },
        "templateId": {
          "type": "string",
          "description": "Sendgrid template ID"
        }
      },
      "implementation": {
        "module": "app.services.notifications.email.sendgrid_provider",
        "class": "NotificationsEmailSendgrid"
      }
    }
  }
}
```

---

## Schema Usage

**File**: `schema.mmd`

```mermaid
User {
    String email      %% @unique
    String password
    String googleId   %% @unique

    %% Cookie auth
    %% @service auth.cookies.redis {
    %%   loginField: "email",
    %%   passwordField: "password"
    %% }

    %% Can have multiple services
    %% @service auth.oauth.google {
    %%   name: "google",
    %%   emailField: "email",
    %%   providerIdField: "googleId"
    %% }
}

Event {
    String title
    Array[String] attendeeEmails
    Date eventDate

    %% @service notifications.email.sendgrid {
    %%   recipientField: "attendeeEmails",
    %%   subjectTemplate: "{{title}} Reminder",
    %%   bodyFields: ["eventDate"],
    %%   triggerOn: "create"
    %% }
}
```

---

## Parser Workflow

```
1. Parser reads schema.mmd
2. Extracts @service directives
3. For each @service:
   - Looks up service in services_registry.json
   - Validates service exists
   - Validates all required_fields are mapped
   - Validates mapped fields exist in entity
   - Validates field types/constraints match registry requirements
4. Generates service_bindings.json (all entity→service mappings)
5. Generates Python routers (embedded field constants)
```

---

## Generated service_bindings.json

**File**: `app/services/generated/service_bindings.json` (generated)

```json
{
  "User": {
    "services": {
      "auth.cookies.redis": {
        "field_mappings": {
          "loginField": "email",
          "passwordField": "password",
          "sessionIdentifier": "id"
        }
      },
      "auth.oauth.google": {
        "name": "google",
        "field_mappings": {
          "emailField": "email",
          "providerIdField": "googleId"
        }
      }
    }
  },
  "Event": {
    "services": {
      "notifications.email.sendgrid": {
        "field_mappings": {
          "recipientField": "attendeeEmails",
          "subjectTemplate": "{{title}} Reminder",
          "bodyFields": ["eventDate"],
          "triggerOn": "create"
        }
      }
    }
  }
}
```

---

## Generated Python Router

**File**: `app/services/generated/user_auth.py` (generated)

```python
# GENERATED FILE - DO NOT EDIT
# Service: auth.cookies.redis
# Entity: User

from fastapi import APIRouter, Request, Response, HTTPException
from app.services.auth.cookies.redis_provider import AuthCookiesRedis
from app.db.factory import get_database

router = APIRouter()

# Field mappings (embedded from schema)
LOGIN_FIELD = "email"
PASSWORD_FIELD = "password"
SESSION_ID_FIELD = "id"

@router.post("/login")
async def login(request: Request, response: Response):
    payload = await request.json()
    login_value = payload.get(LOGIN_FIELD)
    password = payload.get(PASSWORD_FIELD)

    # Query database using mapped field
    db = get_database()
    query = {LOGIN_FIELD: login_value}
    users, count = await db.documents.get_all("User", filter=query, pageSize=1)

    if count == 0:
        raise HTTPException(401, "Invalid credentials")

    user = users[0]

    # Verify password (TODO: use bcrypt)
    if user.get(PASSWORD_FIELD) != password:
        raise HTTPException(401, "Invalid credentials")

    # Create session
    auth_service = AuthCookiesRedis()
    session_id = await auth_service.create_session({
        "user_id": user[SESSION_ID_FIELD],
        "login_value": login_value
    })

    response.set_cookie(key="session", value=session_id)
    return {"success": True, "user_id": user[SESSION_ID_FIELD]}

def init_router(app):
    app.include_router(router, prefix="/user/auth", tags=["User Auth"])
```

---

## TODO: Implementation Tasks

### Phase 1: Foundation
1. ✅ **Create** `app/services/services_registry.json` with `auth.cookies.redis` defined
2. ✅ **Rename** existing implementation: `CookiesAuth` → `AuthCookiesRedis`
3. ✅ **Add validation tool**: `tools/validate_services.py` (validates registry against actual code)

### Phase 2: Parser Enhancement
4. **Update parser** to:
   - Load `services_registry.json`
   - Extract `@service` directives from schema
   - Validate service exists in registry
   - Validate field mappings against registry requirements
   - Generate `service_bindings.json`
   - Generate Python routers with embedded field constants

### Phase 3: Runtime Integration
5. **Create** `ServiceLifecycle` class (loads service_bindings.json at startup)
6. **Create** `ServiceRegistry` class (runtime lookup of initialized services)
7. **Wire** into FastAPI startup/shutdown hooks

### Phase 4: Testing
8. **Add tests** for service validation
9. **Add tests** for generated routers
10. **Update** existing `test/validate` to include auth flow

---

## Field Validation Rules

**Supported field properties in registry:**

```json
{
  "type": "string|integer|boolean|array|date|datetime",
  "unique": true|false,
  "required": true|false,
  "enum": ["value1", "value2"],
  "default": "value",
  "description": "text"
}
```

**Parser validates:**
- Field exists in entity
- Field type matches
- Field has required decorators (@unique, etc.)
- Enum values match if specified

---

## Open Questions

1. **Service initialization config**: Where does runtime config come from (Redis host/port, Sendgrid API key)?
   - Currently: `mongo.json` has `"auth.cookies.redis": { "host": "127.0.0.1", ... }`
   - Should this move to `services_registry.json` or stay separate?

2. **Multiple services of same type**: How to name endpoints?
   - User has both `auth.cookies.redis` and `auth.oauth.google`
   - Endpoints: `/user/auth/login` (which one?) vs `/user/auth/standard/login` + `/user/auth/google/login`?

3. **Service dependencies**: Can a service depend on another service?
   - Example: `notifications.email` needs `auth` to know who to email

---

## Next Step

**Immediate:** Create actual `services_registry.json` with `auth.cookies.redis` fully defined and validate against current implementation.
