package core

import (
	"fmt"
	"io"
	"net/http"
)

// PopulateDataFunc is a function type for creating test data
// Implementation should create bulk test data and fixtures
type PopulateDataFunc func(numAccounts, numUsers int) error

// CleanDatabase cleans all data via the db/init/confirmed endpoint
func CleanDatabase() error {
	if Verbose {
		fmt.Println("🧹 Cleaning database via API...")
	}

	client := &http.Client{}
	req, err := http.NewRequest("POST", ServerURL+"/api/db/init/confirmed", nil)
	if err != nil {
		return fmt.Errorf("failed to create database init request: %w", err)
	}

	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to call database init endpoint: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 && resp.StatusCode != 201 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("database init failed with status %d: %s", resp.StatusCode, string(body))
	}

	if Verbose {
		fmt.Println("✅ Database cleaning completed via /api/db/init/confirmed")
	}

	return nil
}

func GetEntityCountsFromReport() (int, int) {
	users := 0
	accounts := 0
	response, err := ExecuteGet("/api/db/report")
	if err == nil {
		// Extract entity count from report.entities.EntityName
		// GetFromResponse navigates: response -> report -> entities -> Users (with default "0")
		if val := GetFromResponse(response, "report", "entities", "User", "0"); val != "0" {
			if numVal, ok := val.(float64); ok {
				users = int(numVal)
			}
		}
		if val := GetFromResponse(response, "report", "entities", "Account", "0"); val != "0" {
			if numVal, ok := val.(float64); ok {
				accounts = int(numVal)
			}
		}
	}
	return users, accounts
}

// GetDatabaseType returns the database type from /api/db/report
func GetDatabaseType() string {
	response, err := ExecuteGet("/api/db/report")
	if err != nil {
		return "unknown"
	}

	// Extract database type from response.database
	if val := GetFromResponse(response, "database", "unknown"); val != "unknown" {
		if dbType, ok := val.(string); ok {
			return dbType
		}
	}
	return "unknown"
}

// DetectAndSetDatabaseType detects the database type and sets the global DatabaseType variable
func DetectAndSetDatabaseType() {
	DatabaseType = GetDatabaseType()
	if Verbose {
		fmt.Printf("Detected database type: %s\n", DatabaseType)
	}
}
