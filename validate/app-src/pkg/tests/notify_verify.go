package tests

import (
	"fmt"

	"validate/pkg/types"
)

// NotificationValidator validates notification structure
type NotificationValidator struct{}

// ValidateNotifications validates complete notification structure
// Validates: structure, entity grouping, field context, error types, HTTP status consistency
func ValidateNotifications(result *types.TestResult) {
	if result.Notifications == nil {
		// No notifications to validate - only validate if we expect errors/warnings
		if result.StatusCode >= 400 {
			result.Issues = append(result.Issues, "Expected notifications for error response but got nil")
			result.Passed = false
		}
		return
	}

	nv := &NotificationValidator{}

	// Validate all aspects
	nv.validateBasicStructure(result)
	nv.validateEntityGrouping(result)
	nv.validateFieldContext(result)
	nv.validateErrorTypes(result)
	nv.validateHTTPStatus(result)
}

// validateBasicStructure validates top-level response format: {notifications: {entity_id: {errors: [], warnings: []}}}
func (nv *NotificationValidator) validateBasicStructure(result *types.TestResult) {
	notifMap, ok := result.Notifications.(map[string]interface{})
	if !ok {
		result.Issues = append(result.Issues, "Notifications: Not a valid map structure")
		result.Passed = false
		return
	}

	// Empty notifications is valid for success responses
	if len(notifMap) == 0 {
		return
	}

	// Check structure: notifications should be {entity_id: {errors: [], warnings: []}}
	for entityID, entityData := range notifMap {
		if entityID == "request_warnings" {
			// request_warnings is a special top-level array, not entity-grouped
			if _, ok := entityData.([]interface{}); !ok {
				result.Issues = append(result.Issues, "Notifications: request_warnings is not an array")
				result.Passed = false
			}
			continue
		}

		entityMap, ok := entityData.(map[string]interface{})
		if !ok {
			result.Issues = append(result.Issues, fmt.Sprintf("Notifications: Entity '%s' data is not a map", entityID))
			result.Passed = false
			continue
		}

		// Check for errors or warnings arrays
		hasErrors := false
		hasWarnings := false

		if errors, exists := entityMap["errors"]; exists {
			if _, ok := errors.([]interface{}); ok {
				hasErrors = true
			} else {
				result.Issues = append(result.Issues, fmt.Sprintf("Notifications: Entity '%s' errors is not an array", entityID))
				result.Passed = false
			}
		}

		if warnings, exists := entityMap["warnings"]; exists {
			if _, ok := warnings.([]interface{}); ok {
				hasWarnings = true
			} else {
				result.Issues = append(result.Issues, fmt.Sprintf("Notifications: Entity '%s' warnings is not an array", entityID))
				result.Passed = false
			}
		}

		if !hasErrors && !hasWarnings {
			result.Issues = append(result.Issues, fmt.Sprintf("Notifications: Entity '%s' has neither errors nor warnings", entityID))
			result.Passed = false
		}
	}
}

// validateEntityGrouping validates each entity_id has errors and/or warnings arrays with proper structure
func (nv *NotificationValidator) validateEntityGrouping(result *types.TestResult) {
	notifMap, ok := result.Notifications.(map[string]interface{})
	if !ok {
		return // Already failed in Level 1
	}

	for entityID, entityData := range notifMap {
		if entityID == "request_warnings" {
			// Validate request_warnings array structure
			if reqWarnings, ok := entityData.([]interface{}); ok {
				for i, warning := range reqWarnings {
					warningMap, ok := warning.(map[string]interface{})
					if !ok {
						result.Issues = append(result.Issues, fmt.Sprintf("Notifications: request_warning[%d] is not a map", i))
						result.Passed = false
						continue
					}

					// Check for type and message
					if _, exists := warningMap["type"]; !exists {
						result.Issues = append(result.Issues, fmt.Sprintf("Notifications: request_warning[%d] missing 'type' field", i))
						result.Passed = false
					}
					if _, exists := warningMap["message"]; !exists {
						result.Issues = append(result.Issues, fmt.Sprintf("Notifications: request_warning[%d] missing 'message' field", i))
						result.Passed = false
					}
				}
			}
			continue
		}

		entityMap, ok := entityData.(map[string]interface{})
		if !ok {
			continue // Already failed in Level 1
		}

		// Validate errors array
		if errors, exists := entityMap["errors"]; exists {
			if errorsList, ok := errors.([]interface{}); ok {
				for i, error := range errorsList {
					errorMap, ok := error.(map[string]interface{})
					if !ok {
						result.Issues = append(result.Issues, fmt.Sprintf("Notifications: Entity '%s' error[%d] is not a map", entityID, i))
						result.Passed = false
						continue
					}

					// Check for required fields: type and message
					if _, exists := errorMap["type"]; !exists {
						result.Issues = append(result.Issues, fmt.Sprintf("Notifications: Entity '%s' error[%d] missing 'type' field", entityID, i))
						result.Passed = false
					}
					if _, exists := errorMap["message"]; !exists {
						result.Issues = append(result.Issues, fmt.Sprintf("Notifications: Entity '%s' error[%d] missing 'message' field", entityID, i))
						result.Passed = false
					}
				}
			}
		}

		// Validate warnings array
		if warnings, exists := entityMap["warnings"]; exists {
			if warningsList, ok := warnings.([]interface{}); ok {
				for i, warning := range warningsList {
					warningMap, ok := warning.(map[string]interface{})
					if !ok {
						result.Issues = append(result.Issues, fmt.Sprintf("Notifications: Entity '%s' warning[%d] is not a map", entityID, i))
						result.Passed = false
						continue
					}

					// Check for required fields: type and message
					if _, exists := warningMap["type"]; !exists {
						result.Issues = append(result.Issues, fmt.Sprintf("Notifications: Entity '%s' warning[%d] missing 'type' field", entityID, i))
						result.Passed = false
					}
					if _, exists := warningMap["message"]; !exists {
						result.Issues = append(result.Issues, fmt.Sprintf("Notifications: Entity '%s' warning[%d] missing 'message' field", entityID, i))
						result.Passed = false
					}
				}
			}
		}
	}
}

// validateFieldContext validates field parameter present for field-specific errors, absent for general errors
func (nv *NotificationValidator) validateFieldContext(result *types.TestResult) {
	notifMap, ok := result.Notifications.(map[string]interface{})
	if !ok {
		return // Already failed in Level 1
	}

	// List of error types that MUST have field parameter
	fieldRequiredTypes := map[string]bool{
		"conflict":          true, // Unique violations
		"bad_request":       true, // NOT NULL violations (when from database)
		"validation_failed": true, // FK violations, validation errors
	}

	// List of error types that MUST NOT have field parameter
	fieldForbiddenTypes := map[string]bool{
		"not_found":      true, // Document not found
		"internal_error": true, // Database connection errors
	}

	for entityID, entityData := range notifMap {
		if entityID == "request_warnings" {
			continue // Skip request_warnings
		}

		entityMap, ok := entityData.(map[string]interface{})
		if !ok {
			continue
		}

		// Check errors
		if errors, exists := entityMap["errors"]; exists {
			if errorsList, ok := errors.([]interface{}); ok {
				for i, error := range errorsList {
					errorMap, ok := error.(map[string]interface{})
					if !ok {
						continue
					}

					errorType, hasType := errorMap["type"].(string)
					_, hasField := errorMap["field"]

					if hasType {
						// Check if field is required for this error type
						if fieldRequiredTypes[errorType] && !hasField {
							result.Issues = append(result.Issues,
								fmt.Sprintf("Notifications: Entity '%s' error[%d] type '%s' should have 'field' parameter",
								entityID, i, errorType))
							result.Passed = false
						}

						// Check if field is forbidden for this error type
						if fieldForbiddenTypes[errorType] && hasField {
							result.Issues = append(result.Issues,
								fmt.Sprintf("Notifications: Entity '%s' error[%d] type '%s' should NOT have 'field' parameter",
								entityID, i, errorType))
							result.Passed = false
						}
					}
				}
			}
		}

		// Check warnings
		if warnings, exists := entityMap["warnings"]; exists {
			if warningsList, ok := warnings.([]interface{}); ok {
				for i, warning := range warningsList {
					warningMap, ok := warning.(map[string]interface{})
					if !ok {
						continue
					}

					warningType, hasType := warningMap["type"].(string)
					_, hasField := warningMap["field"]

					if hasType {
						// FK-related warnings should have field
						if warningType == "not_found" || warningType == "missing" || warningType == "unique_violation" {
							if !hasField {
								result.Issues = append(result.Issues,
									fmt.Sprintf("Notifications: Entity '%s' warning[%d] type '%s' should have 'field' parameter",
									entityID, i, warningType))
								result.Passed = false
							}
						}
					}
				}
			}
		}
	}
}

// validateErrorTypes validates constraint violations have correct type and user-friendly messages
func (nv *NotificationValidator) validateErrorTypes(result *types.TestResult) {
	notifMap, ok := result.Notifications.(map[string]interface{})
	if !ok {
		return
	}

	for entityID, entityData := range notifMap {
		if entityID == "request_warnings" {
			continue
		}

		entityMap, ok := entityData.(map[string]interface{})
		if !ok {
			continue
		}

		// Check errors
		if errors, exists := entityMap["errors"]; exists {
			if errorsList, ok := errors.([]interface{}); ok {
				for i, error := range errorsList {
					errorMap, ok := error.(map[string]interface{})
					if !ok {
						continue
					}

					errorType, _ := errorMap["type"].(string)
					message, hasMessage := errorMap["message"].(string)

					// Validate message is user-friendly (< 100 chars, no raw DB errors)
					if hasMessage {
						if len(message) > 100 {
							result.Issues = append(result.Issues,
								fmt.Sprintf("Notifications: Entity '%s' error[%d] message too long (%d chars, max 100)",
								entityID, i, len(message)))
							result.Passed = false
						}

						// Check for raw database error messages
						rawDBKeywords := []string{
							"duplicate key error",
							"DuplicateKeyError",
							"UniqueViolationError",
							"IntegrityError",
							"constraint failed",
							"keyPattern",
							"keyValue",
						}
						for _, keyword := range rawDBKeywords {
							if containsIgnoreCase(message, keyword) {
								result.Issues = append(result.Issues,
									fmt.Sprintf("Notifications: Entity '%s' error[%d] contains raw DB error: '%s'",
									entityID, i, message))
								result.Passed = false
								break
							}
						}
					}

					// Validate field-specific errors have field name in message (for context)
					if field, hasField := errorMap["field"].(string); hasField {
						// For field-specific errors, check that error type is appropriate
						if errorType == "conflict" {
							// Unique violation - message should be friendly
							if !containsIgnoreCase(message, "exists") && !containsIgnoreCase(message, "unique") && !containsIgnoreCase(message, "duplicate") {
								result.Notes = append(result.Notes,
									fmt.Sprintf("Notifications: Entity '%s' error[%d] conflict type should mention 'exists', 'unique', or 'duplicate' (field=%s)",
									entityID, i, field))
							}
						}
					}
				}
			}
		}
	}
}

// validateHTTPStatus validates HTTP status matches error type
func (nv *NotificationValidator) validateHTTPStatus(result *types.TestResult) {
	notifMap, ok := result.Notifications.(map[string]interface{})
	if !ok {
		return
	}

	// Map error types to expected HTTP status codes
	expectedStatus := map[string]int{
		"bad_request":       400,
		"unauthorized":      401,
		"forbidden":         403,
		"not_found":         404,
		"conflict":          409,
		"validation_failed": 422,
		"internal_error":    500,
	}

	for entityID, entityData := range notifMap {
		if entityID == "request_warnings" {
			continue
		}

		entityMap, ok := entityData.(map[string]interface{})
		if !ok {
			continue
		}

		// Check errors
		if errors, exists := entityMap["errors"]; exists {
			if errorsList, ok := errors.([]interface{}); ok {
				for i, error := range errorsList {
					errorMap, ok := error.(map[string]interface{})
					if !ok {
						continue
					}

					errorType, hasType := errorMap["type"].(string)
					if !hasType {
						continue
					}

					// Check if HTTP status matches error type
					if expected, ok := expectedStatus[errorType]; ok {
						if result.StatusCode != expected {
							result.Issues = append(result.Issues,
								fmt.Sprintf("Notifications: Entity '%s' error[%d] type '%s' has HTTP %d but expected %d",
								entityID, i, errorType, result.StatusCode, expected))
							result.Passed = false
						}
					}
				}
			}
		}
	}
}

// Helper function for case-insensitive substring check
func containsIgnoreCase(s, substr string) bool {
	sLower := ""
	substrLower := ""
	for _, r := range s {
		if r >= 'A' && r <= 'Z' {
			sLower += string(r + 32)
		} else {
			sLower += string(r)
		}
	}
	for _, r := range substr {
		if r >= 'A' && r <= 'Z' {
			substrLower += string(r + 32)
		} else {
			substrLower += string(r)
		}
	}

	// Simple substring search
	if len(substrLower) > len(sLower) {
		return false
	}
	for i := 0; i <= len(sLower)-len(substrLower); i++ {
		if sLower[i:i+len(substrLower)] == substrLower {
			return true
		}
	}
	return false
}
