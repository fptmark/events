package core

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
)

// Global config for all packages
var (
	ServerURL   string
	Verbose     bool
	NumUsers    int
	NumAccounts int
)

// SetConfig sets the global configuration
func SetConfig(serverURL string, verbose bool, numUsers int, numAccounts int) {
	ServerURL = serverURL
	Verbose = verbose
	NumUsers = numUsers
	NumAccounts = numAccounts
}

func GetEntityCountsFromReport() (int, int) {
	users := 0
	accounts := 0
	response, err := ExecuteGet("/api/db/report", "report.entities")
	if err == nil {
		// Extract entity count from report.entities.EntityName
		// GetFromResponse navigates: response -> report -> entities -> Users (with default "0")
		if val := GetFromResponse(response, "report", "entities", "Users", "0"); val != "0" {
			if numVal, ok := val.(float64); ok {
				users = int(numVal)
			}
		}
		if val := GetFromResponse(response, "report", "entities", "Accounts", "0"); val != "0" {
			if numVal, ok := val.(float64); ok {
				accounts = int(numVal)
			}
		}
	}
	return users, accounts
}

// ExecuteGet makes a GET request and returns the parsed JSON response
// Prints errors to stderr and returns nil on failure
func ExecuteGet(endpoint string, jsonPath string) (interface{}, error) {
	url := ServerURL + endpoint

	resp, err := http.Get(url)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: failed to GET %s: %v\n", url, err)
		return nil, err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: failed to read response body: %v\n", err)
		return nil, err
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		fmt.Fprintf(os.Stderr, "Error: GET %s returned status %d: %s\n", url, resp.StatusCode, string(body))
		return nil, fmt.Errorf("status %d", resp.StatusCode)
	}

	var responseData interface{}
	if err := json.Unmarshal(body, &responseData); err != nil {
		fmt.Fprintf(os.Stderr, "Error: failed to parse JSON response: %v\n", err)
		return nil, err
	}

	return responseData, nil
}

// GetFromResponse extracts a nested value from a JSON response
// The last argument can be a default value if the path doesn't exist
// Example: GetFromResponse(response, "Users", "0") - returns Users value or "0" if not found
// Example: GetFromResponse(response, "report", "entities", "Users", "0")
func GetFromResponse(response interface{}, keys ...string) interface{} {
	if len(keys) == 0 {
		return response
	}

	// Last key might be a default value - check if we can navigate to second-to-last
	defaultValue := keys[len(keys)-1]
	pathKeys := keys[:len(keys)-1]

	current := response

	// Navigate through the path
	for _, key := range pathKeys {
		if current == nil {
			return defaultValue
		}

		switch v := current.(type) {
		case map[string]interface{}:
			val, exists := v[key]
			if !exists {
				return defaultValue
			}
			current = val
		default:
			return defaultValue
		}
	}

	return current
}

// CreateEntity creates an entity via POST to the API
// Takes a payload and entity type, issues a POST request
// Prints errors to stderr and returns error on failure
func CreateEntity(entityType string, payload map[string]interface{}) error {
	url := ServerURL + "/api/" + entityType

	jsonData, err := json.Marshal(payload)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: failed to marshal %s data: %v\n", entityType, err)
		return err
	}

	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error: failed to create %s: %v\n", entityType, err)
		return err
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)

	// Accept 200, 201, or 409 (already exists)
	if resp.StatusCode == 200 || resp.StatusCode == 201 || resp.StatusCode == 409 {
		return nil
	}

	id := payload["id"]
	fmt.Fprintf(os.Stderr, "Error: failed to create %s %v: status %d - %s\n", entityType, id, resp.StatusCode, string(body))
	return fmt.Errorf("status %d", resp.StatusCode)
}
