package generator

import (
	"fmt"
	"math/rand"
	"strings"
	"time"

	"data-generator/pkg/models"
)

// DataGen handles data generation for entities based on metadata
type DataGen struct {
	entity   string
	metadata models.EntityMetadata
	verbose  bool
	rand     *rand.Rand
}

// NewDataGen creates a new data generator for the specified entity
func NewDataGen(entity string, verbose bool) *DataGen {
	allMetadata := models.GetAllEntityMetadata()
	metadata, exists := allMetadata[entity]
	if !exists {
		panic(fmt.Sprintf("No metadata found for entity: %s", entity))
	}

	return &DataGen{
		entity:   entity,
		metadata: metadata,
		verbose:  verbose,
		rand:     rand.New(rand.NewSource(time.Now().UnixNano())),
	}
}

// GenerateValidValue generates a valid value for the specified field
func (dg *DataGen) GenerateValidValue(fieldName string, fieldMeta models.FieldMetadata) interface{} {
	switch fieldMeta.Type {
	case models.FieldTypeString:
		return dg.generateValidString(fieldName, fieldMeta)
	case models.FieldTypeBoolean:
		return dg.rand.Intn(2) == 1
	case models.FieldTypeDate:
		return dg.generateValidDate()
	case models.FieldTypeDatetime:
		return dg.generateValidDatetime()
	case models.FieldTypeCurrency:
		return dg.generateValidCurrency(fieldMeta)
	case models.FieldTypeObjectID:
		return dg.generateValidObjectID()
	default:
		return nil
	}
}

// GenerateInvalidValue generates an invalid value for the specified field
func (dg *DataGen) GenerateInvalidValue(fieldName string, fieldMeta models.FieldMetadata) interface{} {
	switch fieldMeta.Type {
	case models.FieldTypeString:
		return dg.generateInvalidString(fieldName, fieldMeta)
	case models.FieldTypeBoolean:
		return nil // Invalid but sortable
	case models.FieldTypeDate:
		return "1800-01-01T00:00:00Z" // Very old date - parseable but logically invalid
	case models.FieldTypeDatetime:
		return "1800-01-01T00:00:00Z" // Very old datetime - parseable but logically invalid
	case models.FieldTypeCurrency:
		return dg.generateInvalidCurrency(fieldMeta)
	case models.FieldTypeObjectID:
		return "short" // Too short for ObjectID
	default:
		return nil
	}
}

// generateValidString generates valid string values based on field metadata
func (dg *DataGen) generateValidString(fieldName string, fieldMeta models.FieldMetadata) string {
	// Handle enum fields
	if fieldMeta.Enum != nil {
		return fieldMeta.Enum.Values[dg.rand.Intn(len(fieldMeta.Enum.Values))]
	}

	minLen := 1
	if fieldMeta.MinLength != nil {
		minLen = *fieldMeta.MinLength
	}

	maxLen := 100
	if fieldMeta.MaxLength != nil {
		maxLen = *fieldMeta.MaxLength
	}

	// Ensure maxLen is reasonable for testing
	if maxLen > 100 {
		maxLen = 100
	}

	// Handle special field types
	switch strings.ToLower(fieldName) {
	case "email":
		return dg.generateValidEmail(minLen, maxLen)
	case "url":
		return dg.generateValidURL(minLen, maxLen)
	default:
		return dg.generateRandomString(minLen, maxLen)
	}
}

// generateInvalidString generates invalid string values
func (dg *DataGen) generateInvalidString(fieldName string, fieldMeta models.FieldMetadata) string {
	// Handle enum fields - return invalid enum value
	if fieldMeta.Enum != nil {
		return "invalid_enum_value"
	}

	minLen := 0
	if fieldMeta.MinLength != nil {
		minLen = *fieldMeta.MinLength
	}

	maxLen := 100
	if fieldMeta.MaxLength != nil {
		maxLen = *fieldMeta.MaxLength
	}

	// 50% chance to generate too short, 50% too long
	if dg.rand.Intn(2) == 0 && minLen > 0 {
		// Generate string that's too short
		if minLen <= 1 {
			return ""
		}
		tooShortLen := dg.rand.Intn(minLen)
		if tooShortLen == 0 {
			return ""
		}
		return dg.generateRandomString(1, tooShortLen)
	} else {
		// Generate string that's too long
		return dg.generateRandomString(maxLen+1, maxLen+10)
	}
}

// generateRandomString generates a random string of specified length range
func (dg *DataGen) generateRandomString(minLen, maxLen int) string {
	if maxLen < minLen {
		maxLen = minLen
	}

	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	length := minLen + dg.rand.Intn(maxLen-minLen+1)

	result := make([]byte, length)
	for i := range result {
		result[i] = charset[dg.rand.Intn(len(charset))]
	}

	return string(result)
}

// generateValidEmail generates a valid email address
func (dg *DataGen) generateValidEmail(minLen, maxLen int) string {
	for attempts := 0; attempts < 10; attempts++ {
		localPart := dg.generateRandomString(3, 10)
		domain := dg.generateRandomString(3, 8)
		email := fmt.Sprintf("%s@%s.com", localPart, domain)

		if len(email) >= minLen && len(email) <= maxLen {
			return email
		}
	}

	// Fallback if we can't generate within constraints
	return "test@example.com"
}

// generateValidURL generates a valid URL
func (dg *DataGen) generateValidURL(minLen, maxLen int) string {
	if minLen < 22 {
		minLen = 22 // Minimum for "http://www.x.y.com"
	}

	for attempts := 0; attempts < 10; attempts++ {
		subdomain := dg.generateRandomString(3, 8)
		domain := dg.generateRandomString(3, 6)
		url := fmt.Sprintf("http://www.%s.%s.com", subdomain, domain)

		if len(url) >= minLen && len(url) <= maxLen {
			return url
		}
	}

	// Fallback
	return "http://www.example.test.com"
}

// generateValidDate generates a valid date
func (dg *DataGen) generateValidDate() time.Time {
	// Generate dates between 1950 and 2050 for comprehensive testing
	start := time.Date(1950, 1, 1, 0, 0, 0, 0, time.UTC)
	end := time.Date(2050, 12, 31, 0, 0, 0, 0, time.UTC)

	delta := end.Sub(start)
	randomDuration := time.Duration(dg.rand.Int63n(int64(delta)))

	return start.Add(randomDuration)
}

// generateValidDatetime generates a valid datetime
func (dg *DataGen) generateValidDatetime() time.Time {
	return time.Now().UTC()
}

// generateValidCurrency generates a valid currency value
func (dg *DataGen) generateValidCurrency(fieldMeta models.FieldMetadata) float64 {
	min := 0.0
	if fieldMeta.GreaterEqual != nil {
		min = *fieldMeta.GreaterEqual
	}

	max := 1000000.0
	if fieldMeta.LessEqual != nil {
		max = *fieldMeta.LessEqual
	}

	value := min + dg.rand.Float64()*(max-min)
	return float64(int(value*100)) / 100 // Round to 2 decimal places
}

// generateInvalidCurrency generates an invalid currency value
func (dg *DataGen) generateInvalidCurrency(fieldMeta models.FieldMetadata) float64 {
	max := 1000000.0
	if fieldMeta.LessEqual != nil {
		max = *fieldMeta.LessEqual
	}

	// Generate value that exceeds maximum
	return max + float64(dg.rand.Intn(10000)+1)
}

// generateValidObjectID generates a valid-looking ObjectID (24 hex characters)
func (dg *DataGen) generateValidObjectID() string {
	const hexChars = "0123456789abcdef"
	result := make([]byte, 24)
	for i := range result {
		result[i] = hexChars[dg.rand.Intn(len(hexChars))]
	}
	return string(result)
}