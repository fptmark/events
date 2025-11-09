package tests

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"validate/pkg/core"
	"validate/pkg/types"
)

type verifier struct {
	entity string // Entity type for metadata lookup (e.g., "User", "Account")
}

// Verify performs verification of data against parameters and populates result fields
func Verify(data []map[string]interface{}, params types.TestParams, entity string, result *types.TestResult) {
	v := &verifier{entity: entity}

	// Extract and verify sort fields
	if len(params.Sort) > 0 {
		v.extractSortFields(data, params.Sort, result)
		v.verifySortData(data, params.Sort, result)
	}

	// Extract and verify filter fields
	if len(params.Filter) > 0 {
		v.extractFilterFields(data, params.Filter, result)
		v.verifyFilterData(data, params.Filter, params.FilterMatch, result)
	}

	// Extract view fields
	if len(params.View) > 0 {
		v.extractViewFields(data, params.View, result)
	}
}

// extractSortFields extracts sort field values for display
func (v *verifier) extractSortFields(data []map[string]interface{}, sortFields []types.SortField, result *types.TestResult) {
	for _, sortField := range sortFields {
		fieldName := sortField.Field
		values := v.extractFieldValues(data, fieldName)
		result.Fields[fmt.Sprintf("sort_%s", fieldName)] = values
	}
}

// extractFilterFields extracts filter field values for display
func (v *verifier) extractFilterFields(data []map[string]interface{}, filters map[string][]types.FilterValue, result *types.TestResult) {
	for fieldName := range filters {
		values := v.extractFieldValues(data, fieldName)
		result.Fields[fmt.Sprintf("filter_%s", fieldName)] = values
	}
}

// extractViewFields extracts view field values for display
func (v *verifier) extractViewFields(data []map[string]interface{}, views map[string][]string, result *types.TestResult) {
	for entity, fields := range views {
		for _, fieldName := range fields {
			values := v.extractNestedFieldValues(data, entity, fieldName)
			result.Fields[fmt.Sprintf("view_%s.%s", entity, fieldName)] = values
		}
	}
}

// extractFieldValues extracts all values for a specific field from the data array
func (v *verifier) extractFieldValues(data []map[string]interface{}, fieldName string) []interface{} {
	var values []interface{}

	for _, item := range data {
		// Try exact match first
		if value, exists := item[fieldName]; exists {
			values = append(values, value)
			continue
		}

		// Fallback: try case-insensitive lookup by iterating through all keys
		for key, value := range item {
			if strings.EqualFold(key, fieldName) {
				values = append(values, value)
				break
			}
		}
	}

	return values
}

// extractNestedFieldValues extracts field values from nested objects (for view parameters)
func (v *verifier) extractNestedFieldValues(data []map[string]interface{}, entity, fieldName string) []interface{} {
	var values []interface{}

	for _, item := range data {
		// Look for the entity as a nested object
		if entityObj, exists := item[entity]; exists {
			if entityMap, ok := entityObj.(map[string]interface{}); ok {
				// Try exact match first
				if value, exists := entityMap[fieldName]; exists {
					values = append(values, value)
					continue
				}

				// Fallback: try case-insensitive lookup
				for key, value := range entityMap {
					if strings.EqualFold(key, fieldName) {
						values = append(values, value)
						break
					}
				}
			}
		}

		// Also check for flattened field names like "entity.field"
		flatFieldName := fmt.Sprintf("%s.%s", entity, fieldName)
		if value, exists := item[flatFieldName]; exists {
			values = append(values, value)
		}
	}

	return values
}

// verifySortData verifies that data is properly sorted according to sort fields
func (v *verifier) verifySortData(data []map[string]interface{}, sortFields []types.SortField, result *types.TestResult) {
	if len(data) <= 1 || len(sortFields) == 0 {
		return
	}

	// Normalize sort fields (handle default direction, unknown fields)
	normalizedSortFields := v.normalizeSortFields(sortFields, result)
	if len(normalizedSortFields) == 0 {
		return // All fields were invalid
	}

	// Validate that adjacent records are in correct order
	v.validateSortOrder(data, normalizedSortFields, result)
}

// verifyFilterData verifies that data matches filter criteria
func (v *verifier) verifyFilterData(data []map[string]interface{}, filters map[string][]types.FilterValue, filterMatch string, result *types.TestResult) {
	if len(data) == 0 {
		return // No data to verify
	}

	for fieldName, filterValues := range filters {
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

		// Check if all records match the active filter criteria
		for i, record := range data {
			if value, exists := record[fieldName]; exists {
				for _, filterValue := range activeFilters {
					if !v.checkFilterMatch(value, filterValue, fieldName, filterMatch) {
						result.Issues = append(result.Issues, fmt.Sprintf("Filter field '%s' value at index %d (%v) doesn't match criteria %s:%v",
							fieldName, i, value, filterValue.Operator, filterValue.Value))
						result.Passed = false
						break // Stop on first failure for this value
					}
				}
			}
		}
	}
}

// checkSortOrder verifies if values are sorted in the specified direction
func (v *verifier) checkSortOrder(values []interface{}, direction, entityType, fieldName string) bool {
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
// Both MongoDB and Elasticsearch use substring matching for non-enum strings, exact matching for enums
func (v *verifier) checkFilterMatch(value interface{}, filter types.FilterValue, fieldName string, filterMatch string) bool {
	// Special handling for datetime comparisons
	if filter.Operator == "eq" && v.isDateTimeComparison(value, filter.Value) {
		return v.compareDateTimeValues(value, filter.Value) == 0
	}

	// For "eq" operator on strings, check if it's an enum field
	if filter.Operator == "eq" {
		valueStr, valueIsString := value.(string)
		filterStr, filterIsString := filter.Value.(string)

		if valueIsString && filterIsString {
			valueLower := strings.ToLower(valueStr)
			filterLower := strings.ToLower(filterStr)

			// Check if this is an enum field - enum fields use exact matching
			isEnumField := core.IsEnumField(v.entity, fieldName)
			if isEnumField {
				// Enum fields: exact match (case-insensitive)
				return strings.EqualFold(valueStr, filterStr)
			}
			// Non-enum strings: use filterMatch setting
			if filterMatch == "full" {
				// Full string matching
				return strings.EqualFold(valueStr, filterStr)
			} else {
				// Substring matching (default)
				return strings.Contains(valueLower, filterLower)
			}
		}
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

// compareValues compares two values using basic field type inference
func (v *verifier) compareValues(a, b interface{}, entityType, fieldName string) int {
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

	// Infer field type from field name and values
	fieldType := v.inferFieldType(fieldName, a, b)

	// Use appropriate comparison based on inferred field type
	switch fieldType {
	case "string":
		return v.compareString(a, b)
	case "number":
		return v.compareNumeric(a, b)
	case "date":
		return v.compareDate(a, b)
	case "boolean":
		return v.compareBoolean(a, b)
	default:
		// Fallback to string comparison for unknown types
		return v.compareString(a, b)
	}
}

// inferFieldType infers field type from field name and values
func (v *verifier) inferFieldType(fieldName string, a, b interface{}) string {
	fieldNameLower := strings.ToLower(fieldName)

	// Check field name patterns
	if strings.Contains(fieldNameLower, "date") || strings.Contains(fieldNameLower, "time") ||
		fieldNameLower == "dob" || fieldNameLower == "createdat" || fieldNameLower == "updatedat" {
		return "date"
	}
	if strings.Contains(fieldNameLower, "worth") || strings.Contains(fieldNameLower, "balance") ||
		strings.Contains(fieldNameLower, "amount") || strings.Contains(fieldNameLower, "price") {
		return "number"
	}
	if strings.Contains(fieldNameLower, "is") || fieldNameLower == "active" || fieldNameLower == "enabled" {
		return "boolean"
	}

	// Check value types
	aStr := v.toString(a)
	bStr := v.toString(b)

	// Try parsing as number
	if _, err := strconv.ParseFloat(aStr, 64); err == nil {
		if _, err := strconv.ParseFloat(bStr, 64); err == nil {
			return "number"
		}
	}

	// Try parsing as date
	if v.looksLikeDate(aStr) && v.looksLikeDate(bStr) {
		return "date"
	}

	// Try parsing as boolean
	if v.looksLikeBool(aStr) && v.looksLikeBool(bStr) {
		return "boolean"
	}

	return "string"
}

// looksLikeDate checks if a string looks like a date
func (v *verifier) looksLikeDate(s string) bool {
	// Check for common date patterns
	if strings.Contains(s, "T") && strings.Contains(s, ":") {
		return true // ISO datetime
	}
	if strings.Count(s, "-") == 2 && len(s) >= 10 {
		return true // YYYY-MM-DD
	}
	return false
}

// looksLikeBool checks if a string looks like a boolean
func (v *verifier) looksLikeBool(s string) bool {
	lower := strings.ToLower(s)
	return lower == "true" || lower == "false" || lower == "1" || lower == "0"
}

// compareString compares two values as strings
func (v *verifier) compareString(a, b interface{}) int {
	aStr := v.toString(a)
	bStr := v.toString(b)

	if core.CaseSensitive {
		return strings.Compare(aStr, bStr)
	}
	// Case-insensitive comparison
	return strings.Compare(strings.ToLower(aStr), strings.ToLower(bStr))
}

// compareNumeric compares two values as numbers
func (v *verifier) compareNumeric(a, b interface{}) int {
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
func (v *verifier) compareDate(a, b interface{}) int {
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
func (v *verifier) compareBoolean(a, b interface{}) int {
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
func (v *verifier) toString(value interface{}) string {
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
func (v *verifier) isDateTimeComparison(value, filterValue interface{}) bool {
	valueStr := v.toString(value)
	filterStr := v.toString(filterValue)

	// Check if one looks like a datetime and the other like a date
	isValueDateTime := strings.Contains(valueStr, "T") && strings.Contains(valueStr, ":")
	isFilterDate := !strings.Contains(filterStr, "T") && strings.Count(filterStr, "-") == 2

	return isValueDateTime && isFilterDate
}

// compareDateTimeValues compares datetime with date, handling T00:00:00 case
func (v *verifier) compareDateTimeValues(value, filterValue interface{}) int {
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
func (v *verifier) hasOnlyEmptyObjects(data []map[string]interface{}) bool {
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

// normalizeSortFields handles unknown fields and default directions
func (v *verifier) normalizeSortFields(sortFields []types.SortField, result *types.TestResult) []types.SortField {
	var normalized []types.SortField

	for _, field := range sortFields {
		// Default direction is "asc" if not specified or empty
		direction := field.Direction
		if direction == "" {
			direction = "asc"
		}

		// Validate direction
		if direction != "asc" && direction != "desc" {
			result.Issues = append(result.Issues, fmt.Sprintf("Invalid sort direction '%s' for field '%s', must be 'asc' or 'desc'", direction, field.Field))
			result.Passed = false
			continue
		}

		normalized = append(normalized, types.SortField{
			Field:     field.Field,
			Direction: direction,
		})
	}

	return normalized
}

// validateSortOrder validates that records are sorted correctly according to sort fields
func (v *verifier) validateSortOrder(records []map[string]interface{}, sortFields []types.SortField, result *types.TestResult) {
	// Compare each adjacent pair of records
	for i := 0; i < len(records)-1; i++ {
		if !v.compareRecords(records[i], records[i+1], sortFields, result) {
			return
		}
	}
}

// compareRecords compares two records according to sort fields, returns true if record1 <= record2
func (v *verifier) compareRecords(record1, record2 map[string]interface{}, sortFields []types.SortField, result *types.TestResult) bool {
	for _, sortField := range sortFields {
		fieldName := sortField.Field
		direction := sortField.Direction

		// Get values from both records
		value1, exists1 := record1[fieldName]
		if !exists1 {
			value1 = nil
		}
		value2, exists2 := record2[fieldName]
		if !exists2 {
			value2 = nil
		}

		// Skip comparison if either value is nil (optional fields with NULL values)
		// NULL handling varies by database, so we only validate sort order for non-NULL values
		if value1 == nil || value2 == nil {
			continue
		}

		// Compare the values
		comparison := v.compareValues(value1, value2, "User", fieldName)

		if comparison != 0 {
			// Values are different - check if they're in correct order
			if direction == "asc" && comparison > 0 {
				result.Issues = append(result.Issues, fmt.Sprintf("Sort violation: field '%s' not in ascending order", fieldName))
				result.Passed = false
				return false
			}
			if direction == "desc" && comparison < 0 {
				result.Issues = append(result.Issues, fmt.Sprintf("Sort violation: field '%s' not in descending order", fieldName))
				result.Passed = false
				return false
			}
			// Values are in correct order for this field, no need to check remaining fields
			return true
		}
		// Values are equal for this field, continue to next field
	}
	// All sort fields are equal between the two records
	return true
}

// valuesEqual compares two values for equality
func (v *verifier) valuesEqual(a, b interface{}) bool {
	return v.compareValues(a, b, "User", "") == 0
}

// compareValues is a standalone comparison function for use by dynamic tests
// Returns negative if a < b, zero if a == b, positive if a > b
func compareValues(a, b interface{}) int {
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

	// Handle numeric values (float64 from JSON)
	aNum, aIsNum := a.(float64)
	bNum, bIsNum := b.(float64)
	if aIsNum && bIsNum {
		if aNum < bNum {
			return -1
		}
		if aNum > bNum {
			return 1
		}
		return 0
	}

	// Handle string values
	aStr := fmt.Sprintf("%v", a)
	bStr := fmt.Sprintf("%v", b)

	if core.CaseSensitive {
		return strings.Compare(aStr, bStr)
	}
	// Case-insensitive comparison
	return strings.Compare(strings.ToLower(aStr), strings.ToLower(bStr))
}
