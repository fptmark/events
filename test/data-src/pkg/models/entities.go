package models

import (
	"time"
)

// User represents a user entity
type User struct {
	ID              string    `json:"id" bson:"_id"`
	Username        string    `json:"username" bson:"username"`
	Email           string    `json:"email" bson:"email"`
	FirstName       string    `json:"firstName" bson:"firstName"`
	LastName        string    `json:"lastName" bson:"lastName"`
	Password        string    `json:"password,omitempty" bson:"password,omitempty"`
	AccountID       string    `json:"accountId,omitempty" bson:"accountId,omitempty"`
	Gender          string    `json:"gender" bson:"gender"`
	NetWorth        float64   `json:"netWorth" bson:"netWorth"`
	IsAccountOwner  bool      `json:"isAccountOwner" bson:"isAccountOwner"`
	DOB             time.Time `json:"dob" bson:"dob"`
	CreatedAt       time.Time `json:"createdAt" bson:"createdAt"`
	UpdatedAt       time.Time `json:"updatedAt" bson:"updatedAt"`
}

// Account represents an account entity
type Account struct {
	ID        string     `json:"id" bson:"_id"`
	Name      string     `json:"name" bson:"name"`
	CreatedAt time.Time  `json:"createdAt" bson:"createdAt"`
	UpdatedAt time.Time  `json:"updatedAt" bson:"updatedAt"`
	ExpiredAt *time.Time `json:"expiredAt,omitempty" bson:"expiredAt,omitempty"`
}

// FieldType represents different field types for validation
type FieldType string

const (
	FieldTypeString   FieldType = "String"
	FieldTypeBoolean  FieldType = "Boolean"
	FieldTypeDate     FieldType = "Date"
	FieldTypeDatetime FieldType = "Datetime"
	FieldTypeCurrency FieldType = "Currency"
	FieldTypeObjectID FieldType = "ObjectId"
)

// FieldMetadata represents validation metadata for a field
type FieldMetadata struct {
	Type         FieldType              `json:"type"`
	Required     bool                   `json:"required,omitempty"`
	MinLength    *int                   `json:"min_length,omitempty"`
	MaxLength    *int                   `json:"max_length,omitempty"`
	Enum         *EnumMetadata          `json:"enum,omitempty"`
	GreaterEqual *float64               `json:"ge,omitempty"`
	LessEqual    *float64               `json:"le,omitempty"`
	AutoGenerate bool                   `json:"autoGenerate,omitempty"`
	AutoUpdate   bool                   `json:"autoUpdate,omitempty"`
	ForeignKey   *ForeignKeyMetadata    `json:"foreignKey,omitempty"`
}

// EnumMetadata represents enum field constraints
type EnumMetadata struct {
	Values []string `json:"values"`
}

// ForeignKeyMetadata represents foreign key relationships
type ForeignKeyMetadata struct {
	Entity string `json:"entity"`
	Field  string `json:"field"`
}

// EntityMetadata represents complete metadata for an entity
type EntityMetadata struct {
	Name   string                    `json:"name"`
	Fields map[string]FieldMetadata  `json:"fields"`
}

// GetUserMetadata returns metadata for User entity
func GetUserMetadata() EntityMetadata {
	minLen1, maxLen50, maxLen100 := 1, 50, 100
	ge0, le10000000 := 0.0, 10000000.0

	return EntityMetadata{
		Name: "User",
		Fields: map[string]FieldMetadata{
			"id": {
				Type:     FieldTypeString,
				Required: true,
				MinLength: &minLen1,
				MaxLength: &maxLen50,
			},
			"username": {
				Type:     FieldTypeString,
				Required: true,
				MinLength: &minLen1,
				MaxLength: &maxLen50,
			},
			"email": {
				Type:     FieldTypeString,
				Required: true,
				MinLength: &minLen1,
				MaxLength: &maxLen100,
			},
			"firstName": {
				Type:     FieldTypeString,
				Required: true,
				MinLength: &minLen1,
				MaxLength: &maxLen50,
			},
			"lastName": {
				Type:     FieldTypeString,
				Required: true,
				MinLength: &minLen1,
				MaxLength: &maxLen50,
			},
			"password": {
				Type:     FieldTypeString,
				Required: true,
				MinLength: &minLen1,
				MaxLength: &maxLen100,
			},
			"accountId": {
				Type:     FieldTypeString,
				Required: true,
				ForeignKey: &ForeignKeyMetadata{
					Entity: "Account",
					Field:  "id",
				},
			},
			"gender": {
				Type:     FieldTypeString,
				Required: true,
				Enum: &EnumMetadata{
					Values: []string{"male", "female", "other"},
				},
			},
			"netWorth": {
				Type:         FieldTypeCurrency,
				Required:     false,
				GreaterEqual: &ge0,
				LessEqual:    &le10000000,
			},
			"isAccountOwner": {
				Type:     FieldTypeBoolean,
				Required: false,
			},
			"dob": {
				Type:     FieldTypeDate,
				Required: false,
			},
			"createdAt": {
				Type:         FieldTypeDatetime,
				Required:     true,
				AutoGenerate: true,
			},
			"updatedAt": {
				Type:       FieldTypeDatetime,
				Required:   true,
				AutoUpdate: true,
			},
		},
	}
}

// GetAccountMetadata returns metadata for Account entity
func GetAccountMetadata() EntityMetadata {
	minLen1, maxLen100 := 1, 100

	return EntityMetadata{
		Name: "Account",
		Fields: map[string]FieldMetadata{
			"id": {
				Type:     FieldTypeString,
				Required: true,
				MinLength: &minLen1,
				MaxLength: &maxLen100,
			},
			"name": {
				Type:     FieldTypeString,
				Required: true,
				MinLength: &minLen1,
				MaxLength: &maxLen100,
			},
			"createdAt": {
				Type:         FieldTypeDatetime,
				Required:     true,
				AutoGenerate: true,
			},
			"updatedAt": {
				Type:       FieldTypeDatetime,
				Required:   true,
				AutoUpdate: true,
			},
			"expiredAt": {
				Type:     FieldTypeDatetime,
				Required: false,
			},
		},
	}
}

// GetAllEntityMetadata returns metadata for all entities
func GetAllEntityMetadata() map[string]EntityMetadata {
	return map[string]EntityMetadata{
		"User":    GetUserMetadata(),
		"Account": GetAccountMetadata(),
	}
}