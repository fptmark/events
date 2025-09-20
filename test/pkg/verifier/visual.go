package verifier

import (
	"fmt"
	"strconv"
	"strings"

	"query-verify/pkg/types"
)

// VisualVerifier handles visual verification of test results
type VisualVerifier struct{}

// NewVisualVerifier creates a new visual verifier instance
func NewVisualVerifier() *VisualVerifier {
	return &VisualVerifier{}
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

// verifySortFields verifies that sort fields are properly ordered
func (v *VisualVerifier) verifySortFields(testCase *types.TestCase, extraction *types.FieldExtraction, result *types.VerificationResult) {
	for _, sortField := range testCase.Params.Sort {
		fieldName := sortField.Field
		values, exists := extraction.SortFields[fieldName]

		if !exists || len(values) == 0 {
			result.Issues = append(result.Issues, fmt.Sprintf("Sort field '%s' not found in results", fieldName))
			result.Passed = false
			continue
		}

		// Add to fields for display
		result.Fields[fmt.Sprintf("sort_%s", fieldName)] = values

		// Check if values are properly sorted
		if len(values) > 1 {
			sortedCorrectly := v.checkSortOrder(values, sortField.Direction)
			if !sortedCorrectly {
				result.Issues = append(result.Issues, fmt.Sprintf("Sort field '%s' not properly sorted in %s order", fieldName, sortField.Direction))
				result.Passed = false
			}
		}
	}
}

// verifyFilterFields verifies that filter fields match the expected criteria
func (v *VisualVerifier) verifyFilterFields(testCase *types.TestCase, extraction *types.FieldExtraction, result *types.VerificationResult) {
	// If there are no results (empty data), then filter verification passes
	// because the filter correctly returned zero matches
	if len(testCase.Result.Data) == 0 {
		for fieldName := range testCase.Params.Filter {
			result.Fields[fmt.Sprintf("filter_%s", fieldName)] = []interface{}{}
		}
		return
	}

	for fieldName, filterValue := range testCase.Params.Filter {
		values, exists := extraction.FilterFields[fieldName]

		if !exists || len(values) == 0 {
			result.Issues = append(result.Issues, fmt.Sprintf("Filter field '%s' not found in results", fieldName))
			result.Passed = false
			continue
		}

		// Add to fields for display
		result.Fields[fmt.Sprintf("filter_%s", fieldName)] = values

		// Check if all values match the filter criteria
		for i, value := range values {
			if !v.checkFilterMatch(value, filterValue) {
				result.Issues = append(result.Issues, fmt.Sprintf("Filter field '%s' value at index %d (%v) doesn't match criteria %s:%v",
					fieldName, i, value, filterValue.Operator, filterValue.Value))
				result.Passed = false
			}
		}
	}
}

// addViewFields adds view fields to the result for display
func (v *VisualVerifier) addViewFields(extraction *types.FieldExtraction, result *types.VerificationResult) {
	for fieldName, values := range extraction.ViewFields {
		result.Fields[fmt.Sprintf("view_%s", fieldName)] = values
	}
}

// checkSortOrder verifies if values are sorted in the specified direction
func (v *VisualVerifier) checkSortOrder(values []interface{}, direction string) bool {
	if len(values) <= 1 {
		return true
	}

	for i := 0; i < len(values)-1; i++ {
		comparison := v.compareValues(values[i], values[i+1])

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
func (v *VisualVerifier) checkFilterMatch(value interface{}, filter types.FilterValue) bool {
	// Special handling for datetime comparisons
	if filter.Operator == "eq" && v.isDateTimeComparison(value, filter.Value) {
		return v.compareDateTimeValues(value, filter.Value) == 0
	}

	comparison := v.compareValues(value, filter.Value)

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

// compareValues compares two values and returns -1, 0, or 1
func (v *VisualVerifier) compareValues(a, b interface{}) int {
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

	// Convert to strings for comparison if types don't match
	aStr := v.toString(a)
	bStr := v.toString(b)

	// Try numeric comparison first
	if aNum, aErr := strconv.ParseFloat(aStr, 64); aErr == nil {
		if bNum, bErr := strconv.ParseFloat(bStr, 64); bErr == nil {
			if aNum < bNum {
				return -1
			}
			if aNum > bNum {
				return 1
			}
			return 0
		}
	}

	// Fall back to string comparison
	return strings.Compare(strings.ToLower(aStr), strings.ToLower(bStr))
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