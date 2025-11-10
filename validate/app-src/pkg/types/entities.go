package types

import (
	"fmt"
	"math/rand"
	"strings"
	"time"

	"validate/pkg/core"
)

// Entity represents a dynamic entity built from metadata
type Entity map[string]interface{}

// defaultValueGenerators provides default values for each field type
var defaultValueGenerators = map[string]func() interface{}{
	"String":   func() interface{} { return "" },
	"Integer":  func() interface{} { return 0 },
	"Number":   func() interface{} { return 0.0 },
	"Currency": func() interface{} { return 0.0 },
	"Boolean":  func() interface{} { return false },
	"Date":     func() interface{} { return time.Now().Format("2006-01-02") },
	"Datetime": func() interface{} { return time.Now().Format(time.RFC3339) },
	"ObjectId": func() interface{} { return generatePlaceholderID() },
	"Array[String]": func() interface{} { return []string{} },
	"JSON":     func() interface{} { return map[string]interface{}{} },
}

// Init validates that metadata is loaded
// Metadata is already fetched by core.LoadMetadata() in main
func Init() error {
	entities := core.GetAllEntities()
	if len(entities) == 0 {
		return fmt.Errorf("metadata not loaded - call core.LoadMetadata() first")
	}
	return nil
}

// NewEntity creates a new entity instance with auto-populated required fields
// Only fields specified in 'fields' parameter need to be provided by caller
// All other required fields are auto-generated based on their type
// Optional 'omit' parameter specifies fields to skip during auto-population (useful for validation testing)
func NewEntity(entityName string, fields map[string]interface{}, omit ...string) (Entity, error) {
	// Get entity metadata
	metadata := core.GetEntityMetadata(entityName)
	if metadata == nil {
		return nil, fmt.Errorf("entity %s not found in metadata", entityName)
	}

	// Build omit set for fast lookup
	omitSet := make(map[string]bool)
	for _, field := range omit {
		omitSet[field] = true
	}

	// Start with provided fields
	entity := make(Entity)
	for k, v := range fields {
		entity[k] = v
	}

	// Auto-populate missing required fields
	requiredFields := core.GetRequiredFields(entityName)
	for _, fieldName := range requiredFields {
		// Skip if in omit list
		if omitSet[fieldName] {
			continue
		}

		// Skip if already provided
		if _, exists := entity[fieldName]; exists {
			continue
		}

		// Get field type
		fieldType := core.GetFieldType(entityName, fieldName)
		if fieldType == "" {
			continue // Skip unknown types
		}

		// Generate default value based on type
		if fieldType == "ObjectId" {
			// Special handling for foreign key fields - use known valid IDs
			entity[fieldName] = getValidForeignKeyID(entityName, fieldName)
		} else if generator, ok := defaultValueGenerators[fieldType]; ok {
			entity[fieldName] = generator()
		} else {
			// Unknown type - use empty string as fallback
			entity[fieldName] = ""
		}
	}

	return entity, nil
}

// generatePlaceholderID generates a placeholder ID for ObjectId fields
// In real usage, tests should provide valid IDs for foreign keys
func generatePlaceholderID() string {
	return fmt.Sprintf("placeholder_%d", rand.Intn(1000000))
}

// getValidForeignKeyID returns a valid ID for foreign key fields based on entity and field name
// This ensures that auto-populated foreign keys reference actual records in the database
// Uses metadata-driven approach: checks authn service delegates to find authz entity
func getValidForeignKeyID(entityName string, fieldName string) string {
	// Check if entity has authn service
	delegates := core.GetServiceDelegates(entityName, "authn")
	if delegates == nil {
		return generatePlaceholderID()
	}

	// Get authz entity from delegates
	authzEntity := getAuthzEntityFromDelegates(delegates)
	if authzEntity == "" {
		return generatePlaceholderID()
	}

	// Derive FK field name from authz entity: "Role" -> "roleId"
	expectedFKField := strings.ToLower(authzEntity) + "Id"

	// Check if this field matches the expected FK field
	if strings.ToLower(fieldName) == strings.ToLower(expectedFKField) {
		// Return bootstrap test ID: <entity_lowercase>_test
		return fmt.Sprintf("%s_test", strings.ToLower(authzEntity))
	}

	// For unknown foreign keys, generate a placeholder
	// Tests should explicitly provide valid IDs for these fields
	return generatePlaceholderID()
}

// getAuthzEntityFromDelegates extracts authz entity name from delegates list
func getAuthzEntityFromDelegates(delegates []map[string]interface{}) string {
	if len(delegates) == 0 {
		return ""
	}

	// delegates format: [{authz: Role}]
	for _, delegate := range delegates {
		if authzEntity, ok := delegate["authz"].(string); ok {
			return authzEntity
		}
	}
	return ""
}

// ToJSON converts entity to JSON-serializable map
func (e Entity) ToJSON() map[string]interface{} {
	return map[string]interface{}(e)
}

// GetString safely retrieves a string field
func (e Entity) GetString(field string) string {
	if val, ok := e[field]; ok {
		if str, ok := val.(string); ok {
			return str
		}
	}
	return ""
}

// GetInt safely retrieves an integer field
func (e Entity) GetInt(field string) int {
	if val, ok := e[field]; ok {
		if num, ok := val.(int); ok {
			return num
		}
	}
	return 0
}

// GetBool safely retrieves a boolean field
func (e Entity) GetBool(field string) bool {
	if val, ok := e[field]; ok {
		if b, ok := val.(bool); ok {
			return b
		}
	}
	return false
}

// GetFloat safely retrieves a float field
func (e Entity) GetFloat(field string) float64 {
	if val, ok := e[field]; ok {
		if f, ok := val.(float64); ok {
			return f
		}
	}
	return 0.0
}

// Set sets a field value
func (e Entity) Set(field string, value interface{}) {
	e[field] = value
}

// Has checks if a field exists
func (e Entity) Has(field string) bool {
	_, exists := e[field]
	return exists
}

// Merge merges another map into this entity
func (e Entity) Merge(other map[string]interface{}) {
	for k, v := range other {
		e[k] = v
	}
}
