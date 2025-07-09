Metadata-Driven Angular UI for Backend Data Management

  This Angular-based frontend application provides a complete metadata-driven UI system for managing data entities through REST APIs. The system is designed to
  dynamically adapt to any data model by consuming metadata from the backend.

  Key Features

  1. Metadata-driven architecture: The UI adapts its display and behavior based on metadata returned from the server, enabling automatic UI generation for different
  data models without code changes.
  2. CRUD operations support: Full Create, Read, Update, Delete functionality through REST endpoints.
  3. Dynamic form generation: Forms are automatically generated based on field types, validation rules, and display configurations defined in the metadata.
  4. Entity relationships: Support for foreign key relationships between entities via ObjectId references, with a selector modal for picking related entities.
  5. Consistent styling: Standardized button colors and UI elements across all views (View: light blue, Edit: dark blue, Create: green, Delete: red).
  6. Field type support: Handles various field types including:
    - Text fields, emails, passwords
    - Checkboxes for boolean values
    - Date inputs
    - Dropdown selects for enum values
    - Foreign key references with selection UI
    - Arrays and JSON objects
  7. Comprehensive validation: Client-side validation based on metadata rules with clear error messaging.
  8. Responsive layout: Forms use a 2-column grid layout with left-aligned labels, adaptable to different screen sizes.
  9. Error handling: Detailed error display from server responses for debugging and user feedback.

  Entity Structure

  Entities are represented by three components:

  1. Summary list view: Displays entity records in a tabular format with action buttons (View, Edit, Delete)
  2. Detail view: Shows all fields of a single entity in read-only mode
  3. Edit/Create view: Form for creating new entities or editing existing ones

  Each entity can define its UI presentation through metadata including:
  - Which fields to display in each view
  - Field types and validation rules
  - Custom field display names
  - Special field handling (auto-generated fields, read-only fields, etc.)

  Technical Details

  - Built with Angular framework
  - Uses reactive forms with validation
  - Implements Bootstrap for styling and responsive design
  - Connects to REST backends (supporting both MongoDB and Elasticsearch)
  - Configuration-driven with minimal hardcoded logic

  This UI system is ideal for admin panels, data management tools, and any application requiring dynamic forms based on a flexible data model.
