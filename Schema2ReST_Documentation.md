# Schema2ReST Project Specification

Schema2ReST is a project designed to streamline the process of creating RESTful APIs from high-level schema definitions. It uses an enhanced schema description format based on Mermaid Model Diagrams (MMD) with custom decorators to describe data entities, validations, inheritance, unique constraints, and relationships. This enhanced schema is then converted to YAML and subsequently used to generate both data models and REST API routers automatically.

## Table of Contents
- [1. Overview](#1-overview)
- [2. The Process](#2-the-process)
- [3. MMD Enhancements](#3-mmd-enhancements)
  - [3.1 Inheritance](#31-inheritance)
  - [3.2 Unique Constraints](#32-unique-constraints)
  - [3.3 Dictionaries](#33-dictionaries)
  - [3.4 Validations](#34-validations)
- [4. Relationships](#4-relationships)
- [5. MongoDB Dependency](#5-mongodb-dependency)
- [6. Model and Router Generation](#6-model-and-router-generation)
  - [6.1 Model Generator (gen_model)](#61-model-generator-gen_model)
  - [6.2 Router Generator (gen_router)](#62-router-generator-gen_router)
- [7. Run time environment](#7-run-time-environment)
- [8. Testing and Integration](#8-testing-and-integration)
- [9. Summary and Future Enhancements](#9-summary-and-future-enhancements)
- [10. Implementation Details](#10-implementation-details)

## 1. Overview

The primary goal of Schema2ReST is to allow developers to define their entire data schema in a single, concise format and automatically generate the underlying code for:

- **Models**: Pydantic/Beanie models that represent data objects in a MongoDB database, including all field definitions, validations, inheritance, and unique constraint enforcement.

- **Routers**: REST API endpoints that rely on the generated models to enforce consistent validation and business logic.

The system is tightly integrated with MongoDB as its back-end database. It uses the Beanie ODM for MongoDB, which provides Mongo-specific types (such as PydanticObjectId) and asynchronous query methods. This Mongo dependency influences several aspects of the project, from field type definitions to query logic for enforcing unique constraints.

The project consists of these major components:

- **Enhanced MMD Input**: A custom schema description language that extends standard Mermaid MMD by adding decorators for validations, inheritance, unique constraints, and relationships.

- **MMD-to-YAML Converter**: A converter that parses the Enhanced MMD file and produces a structured YAML file containing the full schema.

- **Model Generator (gen_model)**: A generator that reads the YAML file and creates Python model code. The generated models:
  - Merge field definitions with validation constraints.
  - Support inheritance by extending a BaseEntity (which contains Mongo-specific fields and behaviors).
  - Enforce unique constraints by overriding the save() method to perform runtime checks.
  
- **Router Generator (gen_router)**: A generator that creates REST API endpoint code. Since the unique constraint enforcement is handled at the model level, no changes are required in the router generation logic.

## 2. The Process

A Makefile is supplied that takes a schema and creates a running ReST server. Following are the specific steps:

1. Generate a yaml file
2. Create Base system files:
   - Main.py
   - Db.py
3. Generate models from the YAML schema
4. Generate routers for each model
5. Create the FastAPI application structure

## 3. MMD Enhancements

The following snippet of the MMD includes enhancements as described herein. All enhancements are noted by a comment (%%) followed by a decorator (@).

There are 4 types of decorators – Inheritance, Uniques, Dictionaries and Validators:

```yaml
erDiagram
    BaseEntity {
        ObjectId _id
        ISODate createdAt
        ISODate updatedAt
   
    %% @validate _id: { required: true, autoGenerate: true }
    %% @validate createdAt: { required: true, autoGenerate: true }
    %% @validate updatedAt: { required: true, autoUpdate: true }
    }

    Account {
        ISODate expiredAt
    
    %% @inherit BaseEntity
    %% @validate expiredAt: { required: false }
    }
```

### 3.1 Inheritance

- **Inheritance Decorator**:
  Entities can specify inheritance using a decorator such as:
  ```yaml
  %% @inherits BaseEntity
  ```

  This indicates that the entity inherits from a BaseEntity, which provides common fields (like _id, createdAt, and updatedAt) and Mongo-specific behavior. The YAML output includes an "inherits" key that is a list of parent entity names.

  @inherits must be defined within an entity

### 3.2 Unique Constraints

- **Unique Decorator**:
  Unique constraints can be defined via statements like:
  ```yaml
  %% @unique lastname
  %% @unique email + username
  ```

  Each unique statement specifies a set of fields that must be unique. In the example above, lastname must be unique and email combined with username must be unique.

- **YAML Representation**:
  In the YAML, unique constraints are represented by a key "uniques" whose value is a list of dictionaries. Each dictionary contains a key "fields" mapping to a list of field names (e.g., {"fields": ["email"]} or {"fields": ["email", "username"]}).

- **Model Enforcement**:
  The generated model code includes a method (validate_uniques()) that checks for duplicate records with the same field values before saving. If a duplicate is found, the model raises a custom exception (e.g., UniqueValidationError) with details about the violation.

  @uniques must be defined within an entity

### 3.3 Dictionaries

Dictionaries can be defined and are global in scope. Dictionaries have a name and a set of key/values as follows:

```yaml
%% @dictionary pattern {
      email: "^[a-zA-Z0-9._%-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", 
       url: "^https?://[^\s]+$"
  }
```

Note: Dictionary statements must be defined on a single physical line. It is broken up above for clarity. The same dictionary name can be used to extend a dictionary.

The above defines the dictionary named "pattern" which has 2 keys – email and url. These are shortcuts that are used as validation values using the format ```dictionary=pattern.email```

Dictionaries are defined outside of any entity definition

### 3.4 Validations

- **Validation**:
  The Enhanced MMD syntax uses explicit markers to define each validation. Within an entity definition, validations are specified by a series of validation lines, each following the format:
  
  ```yaml
  %% @validate url: { required: true, pattern: dictionary=pattern.url, pattern.message: "Bad URL format" }
  %% @validate recurrence: { required: false, enum: [daily, weekly, monthly, yearly] }
  ```

  Validation attributes include:
  - required (true/false)
  - minLength and maxLength (numeric limits)
  - pattern (regex patterns, which must be enclosed in quotes if containing colons or spaces)
  - enum (a list of allowed values, typically provided as a string that can be parsed into a list)

  A validation attribute may also be in the form <attribute>.message as in pattern and pattern.message shown above. There are default messages for every attribute, however certain attributes (pattern, minLength, maxLength, enum) can have an optional .message which will be used to override the default message.

  Validation values can be a simple value, an enum, a regex pattern string or a dictionary lookup. In the above, the url pattern gets its value from the url key in the pattern dictionary. Alternatively, patterns can be direct regex values – no dictionary lookup required.

- **Merging Logic**:
  The MMD-to-YAML converter merges the validations into the entity's field definitions so that each field's output includes its type along with its validation constraints.

## 4. Relationships

- **Relationship Parsing**:
  Relationships between entities are defined in the MMD and processed into:
  - A top-level _relationships list in the YAML (a list of dictionaries with keys "source" and "target", where "source" is the child entity and "target" is the parent).
  - Each entity also has a "relations" array that lists the parent entities for that entity.

  For example:
  ```yaml
  _relationships:
  - source: Account
    target: User
  - source: UserEvent
    target: User
  - source: UserEvent
    target: Event
  ```


## 5. MongoDB Dependency

Schema2ReST is built on top of MongoDB using the Beanie ODM. This introduces several Mongo-specific aspects:

- **Data Model Types**:
  Models inherit from Beanie's Document class. Fields such as _id are defined as PydanticObjectId, a type that represents MongoDB ObjectIds.

- **Default Factories and Timestamps**:
  The BaseEntity model automatically generates an _id using a default factory and manages timestamps (createdAt and updatedAt) using Mongo-specific behavior.

- **Asynchronous Operations**:
  Database operations (such as saving documents and querying for unique constraints) are performed asynchronously using MongoDB's async drivers as wrapped by Beanie.

- **Query Logic**:
  The unique constraint logic in the generated models uses Mongo-style queries (e.g., await self.__class__.find_one(query)) to enforce uniqueness.

Switching to a different back-end would require re-implementing these parts, as the current design is tightly coupled with MongoDB.

## 6. Model and Router Generation

### 6.1 Model Generator (gen_model)

- **Merging Fields and Validations**:
  The generator reads the YAML schema and merges the field definitions with their corresponding validations. It converts string representations of booleans and numbers appropriately and converts enum strings into lists.

- **Inheritance**:
  The generator uses the "inherits" key to extend the appropriate base class. For example, if an entity inherits from BaseEntity, the generated model imports BaseEntity and extends it.

- **Unique Constraints**:
  If unique constraints are defined (via the "uniques" key), the generator produces additional logic in the model:
  - A custom exception class (UniqueValidationError) is generated.
  - An asynchronous method validate_uniques() is created that, for each unique constraint, builds a query using the specified fields and checks the database for existing records. If a record is found, UniqueValidationError is raised.
  - The model's save() method is overridden to call validate_uniques() before saving.

### 6.2 Router Generator (gen_router)

- **Minimal Changes**:
  Since unique constraints are enforced in the model's save() method, the router generator does not need significant changes. The routers simply call the model methods, and any unique constraint violations are propagated as errors from the model layer.

## 7. Run time environment

There is a config.json file in the project root directory that includes the Mongo connection, database name and other relevant information as follows:

```json
{
    "mongo_uri": "mongodb://localhost:27017",
    "db_name": "eventMgr",
    "host": "127.0.0.1",
    "app_port": 5500,
    "log_level": "info",
    "environment": "development"
}
```

This data is loaded at runtime to establish the running environment.

## 8. Testing and Integration

- **REST API Testing**:
  The generated REST API (e.g., using FastAPI) automatically converts incoming JSON into the proper types using Pydantic. The integration of models with the REST API ensures that all validations (including unique constraint checks) are applied.

- **Direct Model Testing**:
  Unit tests can directly call model methods (using pytest and pytest-asyncio) to verify that validations, uniqueness, and inheritance behave as expected.

- **Interactive Testing**:
  With VSCode's Python extension and integrated pytest support, you can run and debug both model-level and API-level tests.

## 9. Summary and Future Enhancements

Schema2ReST provides a single source of truth for defining your data schema using an enhanced MMD syntax. It supports:

- **Field Validations**: Merging constraints such as required status, length limits, regex patterns, and allowed enumerations.
- **Inheritance**: Allowing entities to inherit common fields and behavior from a BaseEntity.
- **Unique Constraints**: Enforcing uniqueness through custom model logic and raising detailed errors when constraints are violated.
- **Relationships**: Capturing entity relationships both in a top-level _relationships key and within each entity's "relations" array.

Because the project is built on MongoDB using Beanie, it leverages Mongo-specific data types and asynchronous operations. This tight integration with MongoDB simplifies development for that back-end, although moving to a different persistence layer would require significant rework of the model and query logic.

Future enhancements might include support for additional validation types, more flexible back-end abstraction, and improved error reporting/logging.

## 10. Implementation Details

### Model Template Structure

The model generation uses a template-based approach with three key components:

1. **Main Template (model.j2)**: Controls the overall structure of the generated model files.
2. **Macros (macros.j2)**: Reusable code snippets for common patterns like field declarations and save methods.
3. **Validation (validation.j2)**: Contains validation logic for model fields.

### Key Implementation Features

1. **Dynamic Field Processing**: 
   - All field definitions come from the YAML schema
   - No hardcoded field names in templates
   - Field types are mapped dynamically to Python types

2. **Auto-Update Fields**:
   - Fields marked with `autoUpdate: true` in the schema are automatically updated during save operations
   - Uses `datetime.now(timezone.utc)` for timestamp updates
   - Supports multiple auto-update fields per entity

3. **Inheritance Implementation**:
   - Base entities define core fields and behaviors
   - Derived entities inherit these fields and can override methods
   - Proper class structure ensures all inherited fields are accessible

4. **Validation Logic**:
   - Comprehensive field validation based on schema constraints
   - Support for standard validation types: required, min/max length, regex patterns, enums
   - Custom error messages can be defined in the schema

5. **Unique Constraint Enforcement**:
   - Implemented in the save() method
   - Performs database queries to check for duplicates
   - Detailed error reporting when constraints are violated

### Design Considerations

1. **Template Modularity**:
   - Separation of concerns through template splitting
   - Macros for reusable code patterns
   - Easy to maintain and extend

2. **No Hardcoded Assumptions**:
   - All entity and field names derived from schema
   - Validation rules determined by schema definitions
   - Auto-update fields identified dynamically

3. **Clean Inheritance Model**:
   - Document models inherit properly from base entities
   - Create and Read models maintain consistent structure
   - Field inheritance properly managed

4. **Performance Considerations**:
   - Efficient database queries for unique constraints
   - Optimized auto-update field handling
   - Clean model structure for MongoDB integration