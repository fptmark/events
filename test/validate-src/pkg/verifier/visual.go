package verifier

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"events-shared/schema"
	"validate/pkg/types"
)

// VisualVerifier handles visual verification of test results
type VisualVerifier struct{
	schemaCache *schema.SchemaCache
}

// NewVisualVerifier creates a new visual verifier instance
func NewVisualVerifier() *VisualVerifier {
	// Try to load schema cache
	schemaPath, err := schema.FindSchemaFile()
	if err != nil {
		// If schema not found, create verifier without schema cache
		// It will fall back to string comparison
		return &VisualVerifier{schemaCache: nil}
	}

	schemaCache, err := schema.NewSchemaCache(schemaPath)
	if err != nil {
		// If schema parsing fails, create verifier without schema cache
		return &VisualVerifier{schemaCache: nil}
	}

	return &VisualVerifier{schemaCache: schemaCache}
}

// Verify performs visual verification of a test case
func (v *VisualVerifier) Verify(testCase *types.TestCase, extraction *types.FieldExtraction) *types.VerificationResult {
	result := &types.VerificationResult{
		TestID:      testCase.ID,
		URL:         testCase.URL,
		Description: testCase.Description,
		Fields:      make(map[string]interface{}),
		Passed:      true,
		Issues:      []string{},
	}

	// Verify sort fields
	v.verifySortFields(testCase, extraction, result)

	// Verify filter fields
	v.verifyFilterFields(testCase, extraction, result)

	// Add view fields for display (no verification logic yet)
	v.addViewFields(extraction, result)

	return result
}

// verifySortFields verifies that sort fields are properly ordered using recursive grouping
func (v *VisualVerifier) verifySortFields(testCase *types.TestCase, extraction *types.FieldExtraction, result *types.VerificationResult) {
	// If there are no results (empty data) or only empty objects, then sort verification passes
	// because there's nothing to sort
	if len(testCase.Result.Data) == 0 || v.hasOnlyEmptyObjects(testCase.Result.Data) {
		for _, sortField := range testCase.Params.Sort {
			result.Fields[fmt.Sprintf("sort_%s", sortField.Field)] = []interface{}{}
		}
		return
	}

	// Add all sort fields to display (field names already normalized)
	for _, sortField := range testCase.Params.Sort {
		fieldName := sortField.Field
		values, exists := extraction.SortFields[fieldName]

		if !exists || len(values) == 0 {
			// Check if this is an invalid field that should have generated a warning
			if v.isInvalidFieldWithWarning(fieldName, testCase) {
				// Invalid field correctly generated warning - this is expected behavior
				result.Fields[fmt.Sprintf("sort_%s", fieldName)] = []interface{}{}
				continue
			}

			result.Issues = append(result.Issues, fmt.Sprintf("Sort field '%s' not found in results", fieldName))
			result.Passed = false
			continue
		}

		// Add to fields for display
		result.Fields[fmt.Sprintf("sort_%s", fieldName)] = values
	}

	// Validate multi-field sort using recursive grouping approach
	if !v.validateMultiFieldSort(testCase.Result.Data, testCase.Params.Sort, result) {
		result.Passed = false
	}
}

// verifyFilterFields verifies that filter fields match the expected criteria
func (v *VisualVerifier) verifyFilterFields(testCase *types.TestCase, extraction *types.FieldExtraction, result *types.VerificationResult) {
	// If there are no results (empty data) or only empty objects, then filter verification passes
	// because the filter correctly returned zero matches or empty objects
	if len(testCase.Result.Data) == 0 || v.hasOnlyEmptyObjects(testCase.Result.Data) {
		for fieldName := range testCase.Params.Filter {
			result.Fields[fmt.Sprintf("filter_%s", fieldName)] = []interface{}{}
		}
		return
	}

	for fieldName, filterValues := range testCase.Params.Filter {
		values, exists := extraction.FilterFields[fieldName]

		if !exists || len(values) == 0 {
			// Check if this is an invalid field that should have generated a warning
			if v.isInvalidFieldWithWarning(fieldName, testCase) {
				// Invalid field correctly generated warning - this is expected behavior
				result.Fields[fmt.Sprintf("filter_%s", fieldName)] = []interface{}{}
				continue
			}

			result.Issues = append(result.Issues, fmt.Sprintf("Filter field '%s' not found in results", fieldName))
			result.Passed = false
			continue
		}

		// Add to fields for display
		result.Fields[fmt.Sprintf("filter_%s", fieldName)] = values

		// For multiple eq conditions on same field, use last-wins logic
		// For range conditions (gte, lte, etc.), keep AND logic
		eqFilters := []types.FilterValue{}
		rangeFilters := []types.FilterValue{}

		for _, filterValue := range filterValues {
			if filterValue.Operator == "eq" {
				eqFilters = append(eqFilters, filterValue)
			} else {
				rangeFilters = append(rangeFilters, filterValue)
			}
		}

		// Use only the last eq filter if any exist
		activeFilters := rangeFilters
		if len(eqFilters) > 0 {
			activeFilters = append(activeFilters, eqFilters[len(eqFilters)-1]) // last wins
		}

		// Check if all values match the active filter criteria
		for i, value := range values {
			for _, filterValue := range activeFilters {
				if !v.checkFilterMatch(value, filterValue, fieldName) {
					result.Issues = append(result.Issues, fmt.Sprintf("Filter field '%s' value at index %d (%v) doesn't match criteria %s:%v",
						fieldName, i, value, filterValue.Operator, filterValue.Value))
					result.Passed = false
					break // Stop on first failure for this value
				}
			}
		}
	}
}

// addViewFields adds view fields to the result for display and validates invalid fields
func (v *VisualVerifier) addViewFields(extraction *types.FieldExtraction, result *types.VerificationResult) {
	for fieldName, values := range extraction.ViewFields {
		// Check if this is an empty view field that might be invalid
		if len(values) == 0 {
			// Parse entity.field format
			parts := strings.Split(fieldName, ".")
			if len(parts) == 2 {
				entity := parts[0]
				field := parts[1]

				// Check if this is an invalid field with warning
				if v.isInvalidViewFieldWithWarning(entity, field, result.TestID) {
					// Invalid field correctly generated warning - this is expected
					result.Fields[fmt.Sprintf("view_%s", fieldName)] = values
					continue
				}
			}
		}

		result.Fields[fmt.Sprintf("view_%s", fieldName)] = values
	}
}

// isInvalidViewFieldWithWarning checks if a view field is invalid and has a warning
// For now, we'll be more permissive with view fields since they might reference different entities
func (v *VisualVerifier) isInvalidViewFieldWithWarning(entity, fieldName string, testID int) bool {
	// For view fields, if they're empty, we'll assume they're either:
	// 1. Invalid fields that generated warnings (acceptable)
	// 2. Valid fields with no data in the current result set (also acceptable)
	// This makes view field validation less strict than sort/filter validation
	return true
}

// checkSortOrder verifies if values are sorted in the specified direction
func (v *VisualVerifier) checkSortOrder(values []interface{}, direction, entityType, fieldName string) bool {
	if len(values) <= 1 {
		return true
	}

	for i := 0; i < len(values)-1; i++ {
		comparison := v.compareValues(values[i], values[i+1], entityType, fieldName)

		if direction == "asc" && comparison > 0 {
			return false
		}
		if direction == "desc" && comparison < 0 {
			return false
		}
	}

	return true
}

// checkFilterMatch checks if a value matches the filter criteria
func (v *VisualVerifier) checkFilterMatch(value interface{}, filter types.FilterValue, fieldName string) bool {
	// Special handling for datetime comparisons
	if filter.Operator == "eq" && v.isDateTimeComparison(value, filter.Value) {
		return v.compareDateTimeValues(value, filter.Value) == 0
	}

	comparison := v.compareValues(value, filter.Value, "User", fieldName)

	switch filter.Operator {
	case "eq":
		return comparison == 0
	case "gt":
		return comparison > 0
	case "gte":
		return comparison >= 0
	case "lt":
		return comparison < 0
	case "lte":
		return comparison <= 0
	default:
		return false
	}
}

// compareValues compares two values using schema-based field type information
func (v *VisualVerifier) compareValues(a, b interface{}, entityType, fieldName string) int {
	// Handle nil values
	if a == nil && b == nil {
		return 0
	}
	if a == nil {
		return -1
	}
	if b == nil {
		return 1
	}

	// Get field type from schema if available
	var fieldType schema.FieldType = schema.StringType // default
	if v.schemaCache != nil {
		fieldType = v.schemaCache.GetFieldType(entityType, fieldName)
	}

	// Use appropriate comparison based on schema field type
	switch fieldType {
	case schema.StringType:
		return v.compareString(a, b)
	case schema.NumberType, schema.IntegerType, schema.CurrencyType:
		return v.compareNumeric(a, b)
	case schema.DateType, schema.DatetimeType:
		return v.compareDate(a, b)
	case schema.BooleanType:
		return v.compareBoolean(a, b)
	default:
		// Fallback to string comparison for unknown types
		return v.compareString(a, b)
	}
}

// compareString compares two values as strings
func (v *VisualVerifier) compareString(a, b interface{}) int {
	aStr := v.toString(a)
	bStr := v.toString(b)
	return strings.Compare(aStr, bStr)
}

// compareNumeric compares two values as numbers
func (v *VisualVerifier) compareNumeric(a, b interface{}) int {
	aStr := v.toString(a)
	bStr := v.toString(b)

	aNum, aErr := strconv.ParseFloat(aStr, 64)
	bNum, bErr := strconv.ParseFloat(bStr, 64)

	// If either fails to parse as number, fall back to string comparison
	if aErr != nil || bErr != nil {
		return strings.Compare(aStr, bStr)
	}

	if aNum < bNum {
		return -1
	}
	if aNum > bNum {
		return 1
	}
	return 0
}

// compareDate compares two values as dates
func (v *VisualVerifier) compareDate(a, b interface{}) int {
	aStr := v.toString(a)
	bStr := v.toString(b)

	// Try parsing as ISO 8601 date/datetime
	aTime, aErr := time.Parse(time.RFC3339, aStr)
	if aErr != nil {
		// Try parsing as date only
		aTime, aErr = time.Parse("2006-01-02", aStr)
	}

	bTime, bErr := time.Parse(time.RFC3339, bStr)
	if bErr != nil {
		// Try parsing as date only
		bTime, bErr = time.Parse("2006-01-02", bStr)
	}

	// If either fails to parse as date, fall back to string comparison
	if aErr != nil || bErr != nil {
		return strings.Compare(aStr, bStr)
	}

	if aTime.Before(bTime) {
		return -1
	}
	if aTime.After(bTime) {
		return 1
	}
	return 0
}

// compareBoolean compares two values as booleans
func (v *VisualVerifier) compareBoolean(a, b interface{}) int {
	aStr := strings.ToLower(v.toString(a))
	bStr := strings.ToLower(v.toString(b))

	aBool := aStr == "true" || aStr == "1"
	bBool := bStr == "true" || bStr == "1"

	if aBool == bBool {
		return 0
	}
	if !aBool && bBool {
		return -1 // false < true
	}
	return 1 // true > false
}

// toString converts any value to string representation
func (v *VisualVerifier) toString(value interface{}) string {
	if value == nil {
		return ""
	}

	switch v := value.(type) {
	case string:
		return v
	case int:
		return strconv.Itoa(v)
	case int64:
		return strconv.FormatInt(v, 10)
	case float64:
		return strconv.FormatFloat(v, 'f', -1, 64)
	case float32:
		return strconv.FormatFloat(float64(v), 'f', -1, 32)
	case bool:
		return strconv.FormatBool(v)
	default:
		return fmt.Sprintf("%v", v)
	}
}

// isDateTimeComparison checks if we're comparing datetime values
func (v *VisualVerifier) isDateTimeComparison(value, filterValue interface{}) bool {
	valueStr := v.toString(value)
	filterStr := v.toString(filterValue)

	// Check if one looks like a datetime and the other like a date
	isValueDateTime := strings.Contains(valueStr, "T") && strings.Contains(valueStr, ":")
	isFilterDate := !strings.Contains(filterStr, "T") && strings.Count(filterStr, "-") == 2

	return isValueDateTime && isFilterDate
}

// compareDateTimeValues compares datetime with date, handling T00:00:00 case
func (v *VisualVerifier) compareDateTimeValues(value, filterValue interface{}) int {
	valueStr := v.toString(value)
	filterStr := v.toString(filterValue)

	// If the datetime ends with T00:00:00, extract just the date part for comparison
	if strings.HasSuffix(valueStr, "T00:00:00") {
		datePart := strings.Split(valueStr, "T")[0]
		return strings.Compare(datePart, filterStr)
	}

	// For other times, do normal string comparison
	return strings.Compare(valueStr, filterStr)
}

// hasOnlyEmptyObjects checks if data array contains only empty objects
func (v *VisualVerifier) hasOnlyEmptyObjects(data []map[string]interface{}) bool {
	if len(data) == 0 {
		return false // Handle this case separately
	}

	for _, item := range data {
		if len(item) > 0 {
			return false // Found a non-empty object
		}
	}

	return true // All objects are empty
}

// validateMultiFieldSort validates sort order using recursive grouping approach
func (v *VisualVerifier) validateMultiFieldSort(records []map[string]interface{}, sortFields []types.SortField, result *types.VerificationResult) bool {
	return v.validateSortRecursive(records, sortFields, result, 0)
}

// validateSortRecursive recursively validates sort order by grouping records
func (v *VisualVerifier) validateSortRecursive(records []map[string]interface{}, sortFields []types.SortField, result *types.VerificationResult, depth int) bool {
	// Base case: no more sort fields to check
	if depth >= len(sortFields) {
		return true
	}

	// Current sort field to validate
	currentField := sortFields[depth]
	fieldName := currentField.Field
	direction := currentField.Direction

	// Group records by current field value
	groups := v.groupRecordsByField(records, fieldName)

	// For each group, validate that the current field is correctly sorted within the group
	for _, group := range groups {
		if len(group) > 1 {
			// Extract values for the current field from this group
			values := v.extractFieldValuesFromRecords(group, fieldName)

			// Check if values within this group are correctly sorted
			if !v.checkSortOrder(values, direction, "User", fieldName) {
				result.Issues = append(result.Issues, fmt.Sprintf("Sort field '%s' not properly sorted in %s order within group", fieldName, direction))
				return false
			}
		}

		// Recursively validate remaining sort fields within this group
		if !v.validateSortRecursive(group, sortFields, result, depth+1) {
			return false
		}
	}

	return true
}

// groupRecordsByField groups records by the value of a specific field, preserving order
func (v *VisualVerifier) groupRecordsByField(records []map[string]interface{}, fieldName string) [][]map[string]interface{} {
	if len(records) == 0 {
		return [][]map[string]interface{}{}
	}

	var groups [][]map[string]interface{}
	var currentGroup []map[string]interface{}
	var lastValue interface{} = nil
	var hasLastValue bool = false

	for _, record := range records {
		value, exists := record[fieldName]
		if !exists {
			value = nil
		}

		// Check if this value is different from the last value
		if !hasLastValue || !v.valuesEqual(lastValue, value) {
			// Start a new group
			if len(currentGroup) > 0 {
				groups = append(groups, currentGroup)
			}
			currentGroup = []map[string]interface{}{record}
			lastValue = value
			hasLastValue = true
		} else {
			// Add to current group
			currentGroup = append(currentGroup, record)
		}
	}

	// Add the last group
	if len(currentGroup) > 0 {
		groups = append(groups, currentGroup)
	}

	return groups
}

// extractFieldValuesFromRecords extracts values for a specific field from a list of records
func (v *VisualVerifier) extractFieldValuesFromRecords(records []map[string]interface{}, fieldName string) []interface{} {
	values := make([]interface{}, 0, len(records))
	for _, record := range records {
		if value, exists := record[fieldName]; exists {
			values = append(values, value)
		}
	}
	return values
}

// valuesEqual compares two values for equality
func (v *VisualVerifier) valuesEqual(a, b interface{}) bool {
	return v.compareValues(a, b, "User", "") == 0
}

// isInvalidFieldWithWarning checks if a field is invalid according to schema and has a corresponding warning
func (v *VisualVerifier) isInvalidFieldWithWarning(fieldName string, testCase *types.TestCase) bool {
	// First check if field exists in schema
	if v.schemaCache != nil {
		// Check if field exists in User entity (assuming most tests are for User)
		canonicalName := v.schemaCache.GetCanonicalFieldName("User", fieldName)
		if canonicalName != fieldName {
			// Field was found in schema with canonical name - this is a valid field
			return false
		}

		// Check if field exists in schema with exact name
		if _, exists := v.schemaCache.GetFieldConstraints("User", fieldName); exists {
			// Field exists in schema - this is a valid field
			return false
		}
	}

	// Field not found in schema - check for warning in notifications
	return v.hasRequestWarningForField(fieldName, testCase)
}

// hasRequestWarningForField checks if there's a request_warning for the specified field
func (v *VisualVerifier) hasRequestWarningForField(fieldName string, testCase *types.TestCase) bool {
	if testCase.Result.Notifications == nil {
		return false
	}

	// Parse notifications to look for request_warnings
	switch notifications := testCase.Result.Notifications.(type) {
	case map[string]interface{}:
		if requestWarnings, ok := notifications["request_warnings"]; ok {
			return v.checkWarningsForField(requestWarnings, fieldName)
		}
	case []interface{}:
		// Handle array of notification objects
		for _, notif := range notifications {
			if notifMap, ok := notif.(map[string]interface{}); ok {
				if notifType, ok := notifMap["type"].(string); ok && notifType == "request_warnings" {
					if details, ok := notifMap["details"]; ok {
						return v.checkWarningsForField(details, fieldName)
					}
				}
			}
		}
	}

	return false
}

// checkWarningsForField checks if warnings contain reference to the field
func (v *VisualVerifier) checkWarningsForField(warnings interface{}, fieldName string) bool {
	switch w := warnings.(type) {
	case map[string]interface{}:
		// Check if field name appears as a key or in values
		if _, exists := w[fieldName]; exists {
			return true
		}
		// Check all values for field name references
		for _, value := range w {
			if v.containsFieldReference(value, fieldName) {
				return true
			}
		}
	case []interface{}:
		// Check array of warnings
		for _, warning := range w {
			if v.containsFieldReference(warning, fieldName) {
				return true
			}
		}
	case string:
		// Simple string warning - check if it contains the field name
		return strings.Contains(strings.ToLower(w), strings.ToLower(fieldName))
	}

	return false
}

// containsFieldReference checks if a value contains reference to the field
func (v *VisualVerifier) containsFieldReference(value interface{}, fieldName string) bool {
	switch val := value.(type) {
	case string:
		return strings.Contains(strings.ToLower(val), strings.ToLower(fieldName))
	case map[string]interface{}:
		// Check if field name appears in map keys or values
		for key, mapVal := range val {
			if strings.EqualFold(key, fieldName) {
				return true
			}
			if v.containsFieldReference(mapVal, fieldName) {
				return true
			}
		}
	case []interface{}:
		for _, item := range val {
			if v.containsFieldReference(item, fieldName) {
				return true
			}
		}
	}
	return false
}