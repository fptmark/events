package tests

import (
	"fmt"
	"net/url"
	"strconv"
	"strings"

	"validate/pkg/types"
)

// ParseTestURL extracts test parameters from a URL string
func ParseTestURL(urlStr string) (*types.TestParams, error) {
	u, err := url.Parse(urlStr)
	if err != nil {
		return nil, fmt.Errorf("invalid URL: %w", err)
	}

	params := &types.TestParams{
		Sort:        []types.SortField{},
		Filter:      make(map[string][]types.FilterValue),
		FilterMatch: "substring", // default to substring matching
		View:        make(map[string][]string),
		Page:        1,
		PageSize:    25,
	}

	query := u.Query()

	// For duplicate parameters, last value wins
	for key, values := range query {
		lastValue := values[len(values)-1]

		switch strings.ToLower(key) {
		case "page":
			if page, err := strconv.Atoi(lastValue); err == nil {
				params.Page = page
			}
		case "pagesize":
			if pageSize, err := strconv.Atoi(lastValue); err == nil {
				params.PageSize = pageSize
			}
		case "sort":
			params.Sort = ParseSortParam(lastValue)
		case "filter":
			params.Filter = ParseFilterParam(lastValue)
		case "filter_match":
			if lastValue == "" || lastValue == "substring" || lastValue == "full" {
				if lastValue == "" {
					params.FilterMatch = "substring"
				} else {
					params.FilterMatch = lastValue
				}
			}
		case "view":
			params.View = ParseViewParam(lastValue)
		}
	}

	return params, nil
}

// ParseSortParam parses sort parameter like "firstName:desc,lastName:asc"
func ParseSortParam(sortStr string) []types.SortField {
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

// ParseFilterParam parses filter parameter like "lastName:Smith,age:gte:21"
func ParseFilterParam(filterStr string) map[string][]types.FilterValue {
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

// ParseViewParam parses view parameter like "account(id,name),profile(firstName,lastName)"
func ParseViewParam(viewStr string) map[string][]string {
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
