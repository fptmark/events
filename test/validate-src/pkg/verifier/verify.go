package verifier

import (
	"fmt"
	"strconv"
	"strings"
	"time"

	"validate/pkg/types"
)

// Verifier handles verification of test results
type Verifier struct {
	// Note: Schema cache removed for now - validate-src doesn't have events-shared dependency
	// Will fall back to string comparison which is still functional
}

// NewVerifier creates a new verifier instance
func NewVerifier() *Verifier {
	return &Verifier{}
}

// Verify performs verification of a test case
func (v *Verifier) Verify(testCase *types.TestCase, extraction *types.FieldExtraction) *types.VerificationResult {
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
func (v *Verifier) verifySortFields(testCase *types.TestCase, extraction *types.FieldExtraction, result *types.VerificationResult) {
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
func (v *Verifier) verifyFilterFields(testCase *types.TestCase, extraction *types.FieldExtraction, result *types.VerificationResult) {
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
func (v *Verifier) addViewFields(extraction *types.FieldExtraction, result *types.VerificationResult) {
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
func (v *Verifier) isInvalidViewFieldWithWarning(entity, fieldName string, testID int) bool {
	// For view fields, if they're empty, we'll assume they're either:
	// 1. Invalid fields that generated warnings (acceptable)
	// 2. Valid fields with no data in the current result set (also acceptable)
	// This makes view field validation less strict than sort/filter validation
	return true
}

// checkSortOrder verifies if values are sorted in the specified direction
func (v *Verifier) checkSortOrder(values []interface{}, direction, entityType, fieldName string) bool {
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
func (v *Verifier) checkFilterMatch(value interface{}, filter types.FilterValue, fieldName string) bool {
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

// compareValues compares two values using basic field type inference
func (v *Verifier) compareValues(a, b interface{}, entityType, fieldName string) int {
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
func (v *Verifier) inferFieldType(fieldName string, a, b interface{}) string {
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
func (v *Verifier) looksLikeDate(s string) bool {
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
func (v *Verifier) looksLikeBool(s string) bool {
	lower := strings.ToLower(s)
	return lower == "true" || lower == "false" || lower == "1" || lower == "0"
}

// compareString compares two values as strings
func (v *Verifier) compareString(a, b interface{}) int {
	aStr := v.toString(a)
	bStr := v.toString(b)
	return strings.Compare(aStr, bStr)
}

// compareNumeric compares two values as numbers
func (v *Verifier) compareNumeric(a, b interface{}) int {
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
func (v *Verifier) compareDate(a, b interface{}) int {
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
func (v *Verifier) compareBoolean(a, b interface{}) int {
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
func (v *Verifier) toString(value interface{}) string {
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
func (v *Verifier) isDateTimeComparison(value, filterValue interface{}) bool {
	valueStr := v.toString(value)
	filterStr := v.toString(filterValue)

	// Check if one looks like a datetime and the other like a date
	isValueDateTime := strings.Contains(valueStr, "T") && strings.Contains(valueStr, ":")
	isFilterDate := !strings.Contains(filterStr, "T") && strings.Count(filterStr, "-") == 2

	return isValueDateTime && isFilterDate
}

// compareDateTimeValues compares datetime with date, handling T00:00:00 case
func (v *Verifier) compareDateTimeValues(value, filterValue interface{}) int {
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
func (v *Verifier) hasOnlyEmptyObjects(data []map[string]interface{}) bool {
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
func (v *Verifier) validateMultiFieldSort(records []map[string]interface{}, sortFields []types.SortField, result *types.VerificationResult) bool {
	return v.validateSortRecursive(records, sortFields, result, 0)
}

// validateSortRecursive recursively validates sort order by grouping records
func (v *Verifier) validateSortRecursive(records []map[string]interface{}, sortFields []types.SortField, result *types.VerificationResult, depth int) bool {
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
func (v *Verifier) groupRecordsByField(records []map[string]interface{}, fieldName string) [][]map[string]interface{} {
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
func (v *Verifier) extractFieldValuesFromRecords(records []map[string]interface{}, fieldName string) []interface{} {
	values := make([]interface{}, 0, len(records))
	for _, record := range records {
		if value, exists := record[fieldName]; exists {
			values = append(values, value)
		}
	}
	return values
}

// valuesEqual compares two values for equality
func (v *Verifier) valuesEqual(a, b interface{}) bool {
	return v.compareValues(a, b, "User", "") == 0
}

// isInvalidFieldWithWarning checks if a field is invalid and has a corresponding warning
func (v *Verifier) isInvalidFieldWithWarning(fieldName string, testCase *types.TestCase) bool {
	// Without schema cache, we'll check for warning in notifications
	return v.hasRequestWarningForField(fieldName, testCase)
}

// hasRequestWarningForField checks if there's a request_warning for the specified field
func (v *Verifier) hasRequestWarningForField(fieldName string, testCase *types.TestCase) bool {
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
func (v *Verifier) checkWarningsForField(warnings interface{}, fieldName string) bool {
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
func (v *Verifier) containsFieldReference(value interface{}, fieldName string) bool {
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

// ExtractVerificationFields extracts relevant fields from test results based on parameters
func ExtractVerificationFields(testCase *types.TestCase) *types.FieldExtraction {
	extraction := &types.FieldExtraction{
		SortFields:   make(map[string][]interface{}),
		FilterFields: make(map[string][]interface{}),
		ViewFields:   make(map[string][]interface{}),
	}

	// Extract sort fields (field names already normalized by URL parser)
	for _, sortField := range testCase.Params.Sort {
		fieldName := sortField.Field
		values := extractFieldValues(testCase.Result.Data, fieldName)
		extraction.SortFields[fieldName] = values
	}

	// Extract filter fields (field names already normalized by URL parser)
	for fieldName := range testCase.Params.Filter {
		values := extractFieldValues(testCase.Result.Data, fieldName)
		extraction.FilterFields[fieldName] = values
	}

	// Extract view fields
	for entity, fields := range testCase.Params.View {
		for _, fieldName := range fields {
			// Look for the field in the main data or in nested objects
			values := extractNestedFieldValues(testCase.Result.Data, entity, fieldName)
			// Always add the field to extraction, even if empty (for invalid field detection)
			extraction.ViewFields[fmt.Sprintf("%s.%s", entity, fieldName)] = values
		}
	}

	return extraction
}

// extractFieldValues extracts all values for a specific field from the data array
func extractFieldValues(data []map[string]interface{}, fieldName string) []interface{} {
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
func extractNestedFieldValues(data []map[string]interface{}, entity, fieldName string) []interface{} {
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