package core

import (
	"encoding/json"
	"sync"
)

// Metadata cache
var (
	metadataCache  map[string]EntityMetadata
	metadataMutex  sync.RWMutex
	metadataLoaded bool
)

// EntityMetadata represents metadata for an entity
type EntityMetadata struct {
	Fields   map[string]FieldMetadata           `json:"fields"`
	Services map[string]map[string]interface{} `json:"services,omitempty"`
}

// FieldMetadata represents metadata for a field
type FieldMetadata struct {
	Type     string                 `json:"type"`
	Required bool                   `json:"required"`
	Enum     map[string]interface{} `json:"enum,omitempty"` // Enum constraint if present
}

// MetadataResponse represents the full metadata response
type MetadataResponse struct {
	Entities map[string]EntityMetadata `json:"entities"`
}

// LoadMetadata fetches and caches metadata from the server using core.ExecuteGet
func LoadMetadata() error {
	metadataMutex.Lock()
	defer metadataMutex.Unlock()

	// Fetch metadata from server using ExecuteGet (reuses HTTP client)
	response, err := ExecuteGet("/api/metadata")
	if err != nil {
		return err
	}

	// Use GetFromResponse to navigate to entities (reuse existing code)
	// Pass empty string as default; if not found, GetFromResponse returns the default
	entitiesData := GetFromResponse(response, "entities", "")
	if entitiesData == "" || entitiesData == nil {
		return nil // No entities in response
	}

	// Convert to JSON and back to struct (easiest way to handle nested maps)
	jsonData, err := json.Marshal(entitiesData)
	if err != nil {
		return err
	}

	var entities map[string]EntityMetadata
	if err := json.Unmarshal(jsonData, &entities); err != nil {
		return err
	}

	metadataCache = entities
	metadataLoaded = true

	return nil
}

// GetFieldType returns the type of a field for an entity
// Returns empty string if not found
func GetFieldType(entity string, field string) string {
	metadataMutex.RLock()
	defer metadataMutex.RUnlock()

	if !metadataLoaded {
		return ""
	}

	entityMeta, exists := metadataCache[entity]
	if !exists {
		return ""
	}

	fieldMeta, exists := entityMeta.Fields[field]
	if !exists {
		return ""
	}

	return fieldMeta.Type
}

// IsDateTimeField checks if a field is a Date or Datetime type
func IsDateTimeField(entity string, field string) bool {
	fieldType := GetFieldType(entity, field)
	// Check for both "Date" and "Datetime" (capital D)
	return fieldType == "Date" || fieldType == "Datetime"
}

// IsEnumField checks if a field has enum constraints
func IsEnumField(entity string, field string) bool {
	metadataMutex.RLock()
	defer metadataMutex.RUnlock()

	if !metadataLoaded {
		return false
	}

	entityMeta, exists := metadataCache[entity]
	if !exists {
		return false
	}

	fieldMeta, exists := entityMeta.Fields[field]
	if !exists {
		return false
	}

	return len(fieldMeta.Enum) > 0
}

// GetAllEntities returns a list of all entity names from metadata
func GetAllEntities() []string {
	metadataMutex.RLock()
	defer metadataMutex.RUnlock()

	if !metadataLoaded {
		return nil
	}

	entities := make([]string, 0, len(metadataCache))
	for entityName := range metadataCache {
		entities = append(entities, entityName)
	}

	return entities
}

// GetRequiredFields returns a list of required field names for an entity
func GetRequiredFields(entity string) []string {
	metadataMutex.RLock()
	defer metadataMutex.RUnlock()

	if !metadataLoaded {
		return nil
	}

	entityMeta, exists := metadataCache[entity]
	if !exists {
		return nil
	}

	requiredFields := make([]string, 0)
	for fieldName, fieldMeta := range entityMeta.Fields {
		if fieldMeta.Required {
			requiredFields = append(requiredFields, fieldName)
		}
	}

	return requiredFields
}

// GetEntityMetadata returns the full metadata for an entity
func GetEntityMetadata(entity string) *EntityMetadata {
	metadataMutex.RLock()
	defer metadataMutex.RUnlock()

	if !metadataLoaded {
		return nil
	}

	entityMeta, exists := metadataCache[entity]
	if !exists {
		return nil
	}

	return &entityMeta
}

// GetServiceOutputs returns the outputs array from a service for an entity
// Returns nil if entity has no such service
func GetServiceOutputs(entity string, serviceType string) []string {
	metadataMutex.RLock()
	defer metadataMutex.RUnlock()

	if !metadataLoaded {
		return nil
	}

	entityMeta, exists := metadataCache[entity]
	if !exists {
		return nil
	}

	// Get service from entity services
	service, hasService := entityMeta.Services[serviceType]
	if !hasService {
		return nil
	}

	// Extract outputs array
	if outputs, ok := service["outputs"].([]interface{}); ok {
		result := make([]string, 0, len(outputs))
		for _, output := range outputs {
			if outputStr, ok := output.(string); ok {
				result = append(result, outputStr)
			}
		}
		return result
	}

	return nil
}

// GetServiceDelegates returns the delegates array from a service for an entity
// Returns nil if entity has no such service or no delegates
func GetServiceDelegates(entity string, serviceType string) []map[string]interface{} {
	metadataMutex.RLock()
	defer metadataMutex.RUnlock()

	if !metadataLoaded {
		return nil
	}

	entityMeta, exists := metadataCache[entity]
	if !exists {
		return nil
	}

	// Get service from entity services
	service, hasService := entityMeta.Services[serviceType]
	if !hasService {
		return nil
	}

	// Extract delegates array
	if delegates, ok := service["delegates"].([]interface{}); ok {
		result := make([]map[string]interface{}, 0, len(delegates))
		for _, delegate := range delegates {
			if delegateMap, ok := delegate.(map[string]interface{}); ok {
				result = append(result, delegateMap)
			}
		}
		return result
	}

	return nil
}
