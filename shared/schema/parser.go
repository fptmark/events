package schema

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"
)

// FieldType represents a schema field type
type FieldType string

const (
	StringType   FieldType = "String"
	NumberType   FieldType = "Number"
	IntegerType  FieldType = "Integer"
	CurrencyType FieldType = "Currency"
	DateType     FieldType = "Date"
	DatetimeType FieldType = "Datetime"
	BooleanType  FieldType = "Boolean"
	ObjectIdType FieldType = "ObjectId"
	JSONType     FieldType = "JSON"
	ArrayType    FieldType = "Array"
)

// FieldConstraints represents validation constraints for a field
type FieldConstraints struct {
	MinLength *int         `yaml:"min_length"`
	MaxLength *int         `yaml:"max_length"`
	Ge        *float64     `yaml:"ge"` // greater than or equal
	Le        *float64     `yaml:"le"` // less than or equal
	Required  bool         `yaml:"required"`
	Enum      *EnumInfo    `yaml:"enum"`
	Pattern   *PatternInfo `yaml:"pattern"`
}

// EnumInfo represents enum constraints
type EnumInfo struct {
	Values  []string `yaml:"values"`
	Message string   `yaml:"message"`
}

// PatternInfo represents pattern constraints
type PatternInfo struct {
	Regex   string `yaml:"regex"`
	Message string `yaml:"message"`
}

// Field represents a field definition in the schema
type Field struct {
	Type         string           `yaml:"type"`
	Required     bool             `yaml:"required"`
	MinLength    *int             `yaml:"min_length"`
	MaxLength    *int             `yaml:"max_length"`
	Ge           *float64         `yaml:"ge"`
	Le           *float64         `yaml:"le"`
	Enum         *EnumInfo        `yaml:"enum"`
	Pattern      *PatternInfo     `yaml:"pattern"`
	AutoGenerate bool             `yaml:"autoGenerate"`
	AutoUpdate   bool             `yaml:"autoUpdate"`
	UI           interface{}      `yaml:"ui"`
}

// GetConstraints returns the constraints for this field
func (f *Field) GetConstraints() FieldConstraints {
	return FieldConstraints{
		MinLength: f.MinLength,
		MaxLength: f.MaxLength,
		Ge:        f.Ge,
		Le:        f.Le,
		Required:  f.Required,
		Enum:      f.Enum,
		Pattern:   f.Pattern,
	}
}

// Entity represents an entity definition in the schema
type Entity struct {
	Fields        map[string]Field `yaml:"fields"`
	Relationships []string         `yaml:"relationships"`
	Abstract      bool             `yaml:"abstract"`
	UI            interface{}      `yaml:"ui"`
	Unique        [][]string       `yaml:"unique"`
	Service       []string         `yaml:"service"`
	Operations    string           `yaml:"operations"`
}

// Schema represents the parsed schema
type Schema struct {
	Entities      map[string]Entity `yaml:"_entities"`
	Relationships []interface{}     `yaml:"_relationships"`
	Dictionaries  interface{}       `yaml:"_dictionaries"`
	Services      []string          `yaml:"_services"`
	Included      []string          `yaml:"_included_entities"`
}

// SchemaCache holds the parsed schema for field type lookups and constraints
type SchemaCache struct {
	fieldTypes           map[string]FieldType        // key: "EntityType.fieldName"
	fieldConstraints     map[string]FieldConstraints // key: "EntityType.fieldName"
	canonicalFieldNames  map[string]string           // key: "entitytype.fieldname" (lowercase) -> "actualFieldName"
	schema               *Schema
}

// NewSchemaCache creates a new schema cache by parsing the schema file
func NewSchemaCache(schemaPath string) (*SchemaCache, error) {
	// Read schema file
	data, err := os.ReadFile(schemaPath)
	if err != nil {
		return nil, fmt.Errorf("failed to read schema file %s: %w", schemaPath, err)
	}

	// Parse YAML
	var schema Schema
	if err := yaml.Unmarshal(data, &schema); err != nil {
		return nil, fmt.Errorf("failed to parse schema YAML: %w", err)
	}

	// Build field type, constraint, and canonical name lookup maps
	cache := &SchemaCache{
		fieldTypes:          make(map[string]FieldType),
		fieldConstraints:    make(map[string]FieldConstraints),
		canonicalFieldNames: make(map[string]string),
		schema:              &schema,
	}

	for entityName, entity := range schema.Entities {
		for fieldName, field := range entity.Fields {
			key := fmt.Sprintf("%s.%s", entityName, fieldName)
			cache.fieldTypes[key] = FieldType(field.Type)
			cache.fieldConstraints[key] = field.GetConstraints()

			// Build case-insensitive lookup: "entitytype.fieldname" -> "actualFieldName"
			canonicalKey := fmt.Sprintf("%s.%s", strings.ToLower(entityName), strings.ToLower(fieldName))
			cache.canonicalFieldNames[canonicalKey] = fieldName
		}
	}

	return cache, nil
}

// GetFieldType returns the field type for a given entity and field
func (sc *SchemaCache) GetFieldType(entityType, fieldName string) FieldType {
	key := fmt.Sprintf("%s.%s", entityType, fieldName)
	if fieldType, exists := sc.fieldTypes[key]; exists {
		return fieldType
	}

	// Check BaseEntity for inherited fields like createdAt, updatedAt
	baseKey := fmt.Sprintf("BaseEntity.%s", fieldName)
	if fieldType, exists := sc.fieldTypes[baseKey]; exists {
		return fieldType
	}

	// Default to String if type not found
	return StringType
}

// GetFieldConstraints returns the constraints for a given entity and field
func (sc *SchemaCache) GetFieldConstraints(entityType, fieldName string) (FieldConstraints, bool) {
	key := fmt.Sprintf("%s.%s", entityType, fieldName)
	if constraints, exists := sc.fieldConstraints[key]; exists {
		return constraints, true
	}

	// Check BaseEntity for inherited fields
	baseKey := fmt.Sprintf("BaseEntity.%s", fieldName)
	if constraints, exists := sc.fieldConstraints[baseKey]; exists {
		return constraints, true
	}

	return FieldConstraints{}, false
}

// GetEntity returns the entity definition for a given entity type
func (sc *SchemaCache) GetEntity(entityType string) (Entity, bool) {
	entity, exists := sc.schema.Entities[entityType]
	return entity, exists
}

// GetAllEntities returns all entity definitions
func (sc *SchemaCache) GetAllEntities() map[string]Entity {
	return sc.schema.Entities
}

// GetCanonicalFieldName returns the correct case field name for a case-insensitive lookup
func (sc *SchemaCache) GetCanonicalFieldName(entityType, fieldName string) string {
	canonicalKey := fmt.Sprintf("%s.%s", strings.ToLower(entityType), strings.ToLower(fieldName))
	if canonical, exists := sc.canonicalFieldNames[canonicalKey]; exists {
		return canonical
	}

	// Check BaseEntity for inherited fields
	baseKey := fmt.Sprintf("baseentity.%s", strings.ToLower(fieldName))
	if canonical, exists := sc.canonicalFieldNames[baseKey]; exists {
		return canonical
	}

	// Return original field name if not found
	return fieldName
}

// FindSchemaFile attempts to find the schema.yaml file relative to the current directory
func FindSchemaFile() (string, error) {
	// Try common locations relative to different tools
	candidates := []string{
		"../../../schema.yaml",  // From test/query-src or test/data-src
		"../../schema.yaml",     // From test
		"schema.yaml",           // Current directory
		"../schema.yaml",        // Parent directory
	}

	for _, candidate := range candidates {
		if absPath, err := filepath.Abs(candidate); err == nil {
			if _, err := os.Stat(absPath); err == nil {
				return absPath, nil
			}
		}
	}

	return "", fmt.Errorf("schema.yaml not found in any expected location")
}