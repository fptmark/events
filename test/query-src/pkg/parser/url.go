package parser

import (
	"fmt"
	"net/url"
	"strconv"
	"strings"

	"events-shared/schema"
	"query-verify/pkg/types"
)

// ParseTestURL extracts test parameters from a URL string and normalizes field names
func ParseTestURL(urlStr string) (*types.TestParams, error) {
	u, err := url.Parse(urlStr)
	if err != nil {
		return nil, fmt.Errorf("invalid URL: %w", err)
	}

	params := &types.TestParams{
		Sort:     []types.SortField{},
		Filter:   make(map[string][]types.FilterValue),
		View:     make(map[string][]string),
		Page:     1,
		PageSize: 25,
	}

	// Load schema for field name normalization
	var schemaCache *schema.SchemaCache
	if schemaPath, err := schema.FindSchemaFile(); err == nil {
		if cache, err := schema.NewSchemaCache(schemaPath); err == nil {
			schemaCache = cache
		}
	}

	query := u.Query()

	// Parse page
	if pageStr := query.Get("page"); pageStr != "" {
		if page, err := strconv.Atoi(pageStr); err == nil && page > 0 {
			params.Page = page
		}
	}

	// Parse pageSize
	if pageSizeStr := query.Get("pageSize"); pageSizeStr != "" {
		if pageSize, err := strconv.Atoi(pageSizeStr); err == nil && pageSize > 0 {
			params.PageSize = pageSize
		}
	}

	// Parse sort parameter
	if sortStr := query.Get("sort"); sortStr != "" {
		params.Sort = parseSortParamWithNormalization(sortStr, schemaCache)
	}

	// Parse filter parameter
	if filterStr := query.Get("filter"); filterStr != "" {
		params.Filter = parseFilterParamWithNormalization(filterStr, schemaCache)
	}

	// Parse view parameter
	if viewStr := query.Get("view"); viewStr != "" {
		params.View = parseViewParamWithNormalization(viewStr, schemaCache)
	}

	return params, nil
}

// parseSortParamWithNormalization parses sort parameter and normalizes field names
func parseSortParamWithNormalization(sortStr string, schemaCache *schema.SchemaCache) []types.SortField {
	var sortFields []types.SortField

	for _, fieldSpec := range strings.Split(sortStr, ",") {
		fieldSpec = strings.TrimSpace(fieldSpec)
		if fieldSpec == "" {
			continue
		}

		// Check for field:direction format
		parts := strings.Split(fieldSpec, ":")
		field := strings.TrimSpace(parts[0])
		direction := "asc" // default

		if len(parts) > 1 {
			dir := strings.ToLower(strings.TrimSpace(parts[1]))
			if dir == "desc" || dir == "asc" {
				direction = dir
			}
		}

		if field != "" {
			// Normalize field name using schema
			canonicalField := field
			if schemaCache != nil {
				canonicalField = schemaCache.GetCanonicalFieldName("User", field)
			}

			sortFields = append(sortFields, types.SortField{
				Field:     canonicalField,
				Direction: direction,
			})
		}
	}

	return sortFields
}

// parseSortParam parses sort parameter like "firstName:desc,lastName:asc" (legacy)
func parseSortParam(sortStr string) []types.SortField {
	var sortFields []types.SortField

	for _, fieldSpec := range strings.Split(sortStr, ",") {
		fieldSpec = strings.TrimSpace(fieldSpec)
		if fieldSpec == "" {
			continue
		}

		// Check for field:direction format
		parts := strings.Split(fieldSpec, ":")
		field := strings.TrimSpace(parts[0])
		direction := "asc" // default

		if len(parts) > 1 {
			dir := strings.ToLower(strings.TrimSpace(parts[1]))
			if dir == "desc" || dir == "asc" {
				direction = dir
			}
		}

		if field != "" {
			sortFields = append(sortFields, types.SortField{
				Field:     field,
				Direction: direction,
			})
		}
	}

	return sortFields
}

// parseFilterParamWithNormalization parses filter parameter and normalizes field names
func parseFilterParamWithNormalization(filterStr string, schemaCache *schema.SchemaCache) map[string][]types.FilterValue {
	filters := make(map[string][]types.FilterValue)

	for _, filterPart := range strings.Split(filterStr, ",") {
		filterPart = strings.TrimSpace(filterPart)
		if filterPart == "" {
			continue
		}

		// Split by colon - minimum 2 parts (field:value)
		parts := strings.SplitN(filterPart, ":", 3)
		if len(parts) < 2 {
			continue
		}

		field := strings.TrimSpace(parts[0])
		if field == "" {
			continue
		}

		// Normalize field name using schema
		canonicalField := field
		if schemaCache != nil {
			canonicalField = schemaCache.GetCanonicalFieldName("User", field)
		}

		var operator string
		var value string

		if len(parts) == 2 {
			// Simple format: field:value
			operator = "eq"
			value = strings.TrimSpace(parts[1])
		} else {
			// Extended format: field:operator:value
			operator = strings.ToLower(strings.TrimSpace(parts[1]))
			value = strings.TrimSpace(parts[2])
		}

		// Convert value to appropriate type
		var typedValue interface{} = value
		if intVal, err := strconv.Atoi(value); err == nil {
			typedValue = intVal
		} else if floatVal, err := strconv.ParseFloat(value, 64); err == nil {
			typedValue = floatVal
		} else if boolVal, err := strconv.ParseBool(value); err == nil {
			typedValue = boolVal
		}

		filters[canonicalField] = append(filters[canonicalField], types.FilterValue{
			Operator: operator,
			Value:    typedValue,
		})
	}

	return filters
}

// parseFilterParam parses filter parameter like "lastName:Smith,age:gte:21" (legacy)
func parseFilterParam(filterStr string) map[string][]types.FilterValue {
	filters := make(map[string][]types.FilterValue)

	for _, filterPart := range strings.Split(filterStr, ",") {
		filterPart = strings.TrimSpace(filterPart)
		if filterPart == "" {
			continue
		}

		// Split by colon - minimum 2 parts (field:value)
		parts := strings.SplitN(filterPart, ":", 3)
		if len(parts) < 2 {
			continue
		}

		field := strings.TrimSpace(parts[0])
		if field == "" {
			continue
		}

		var operator string
		var value string

		if len(parts) == 2 {
			// Simple format: field:value
			operator = "eq"
			value = strings.TrimSpace(parts[1])
		} else {
			// Extended format: field:operator:value
			operator = strings.ToLower(strings.TrimSpace(parts[1]))
			value = strings.TrimSpace(parts[2])
		}

		// Convert value to appropriate type
		var typedValue interface{} = value
		if intVal, err := strconv.Atoi(value); err == nil {
			typedValue = intVal
		} else if floatVal, err := strconv.ParseFloat(value, 64); err == nil {
			typedValue = floatVal
		} else if boolVal, err := strconv.ParseBool(value); err == nil {
			typedValue = boolVal
		}

		filters[field] = append(filters[field], types.FilterValue{
			Operator: operator,
			Value:    typedValue,
		})
	}

	return filters
}

// parseViewParamWithNormalization parses view parameter and normalizes field names
func parseViewParamWithNormalization(viewStr string, schemaCache *schema.SchemaCache) map[string][]string {
	viewSpec := make(map[string][]string)

	// Find all entity(field1,field2) patterns
	parts := strings.Split(viewStr, ")")
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}

		// Find the opening parenthesis
		parenIndex := strings.Index(part, "(")
		if parenIndex == -1 {
			continue
		}

		entity := strings.TrimSpace(part[:parenIndex])
		fieldsStr := strings.TrimSpace(part[parenIndex+1:])

		if entity == "" || fieldsStr == "" {
			continue
		}

		// Parse and normalize fields
		var fields []string
		for _, field := range strings.Split(fieldsStr, ",") {
			field = strings.TrimSpace(field)
			if field != "" {
				// Normalize field name using schema for the specific entity
				canonicalField := field
				if schemaCache != nil {
					canonicalField = schemaCache.GetCanonicalFieldName(entity, field)
				}
				fields = append(fields, canonicalField)
			}
		}

		if len(fields) > 0 {
			viewSpec[entity] = fields
		}
	}

	return viewSpec
}

// parseViewParam parses view parameter like "account(id,name),profile(firstName,lastName)" (legacy)
func parseViewParam(viewStr string) map[string][]string {
	viewSpec := make(map[string][]string)

	// Find all entity(field1,field2) patterns
	parts := strings.Split(viewStr, ")")
	for _, part := range parts {
		part = strings.TrimSpace(part)
		if part == "" {
			continue
		}

		// Find the opening parenthesis
		parenIndex := strings.Index(part, "(")
		if parenIndex == -1 {
			continue
		}

		entity := strings.TrimSpace(part[:parenIndex])
		fieldsStr := strings.TrimSpace(part[parenIndex+1:])

		if entity == "" || fieldsStr == "" {
			continue
		}

		// Parse fields
		var fields []string
		for _, field := range strings.Split(fieldsStr, ",") {
			field = strings.TrimSpace(field)
			if field != "" {
				fields = append(fields, field)
			}
		}

		if len(fields) > 0 {
			viewSpec[entity] = fields
		}
	}

	return viewSpec
}