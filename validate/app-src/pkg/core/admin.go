package core

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

var reportData interface{} = nil

func LoadReportDataFunc() {
	response, err := ExecuteGet("/api/db/report")
	if err == nil {
		reportData = response
	}
	if val := GetFromResponse(reportData, "database", "unknown"); val != "unknown" {
		if dbType, ok := val.(string); ok {
			DatabaseType = dbType
		} else {
			DatabaseType = "unknown"
		}
	}
	if val := GetFromResponse(reportData, "report", "config", "db_name", "unknown"); val != "unknown" {
		if dbName, ok := val.(string); ok {
			DatabaseName = dbName
		} else {
			DatabaseName = ""
		}
	}
	if val := GetFromResponse(reportData, "report", "config", "case_sensitive", "unknown"); val != "unknown" {
		if case_sensitive, ok := val.(bool); ok {
			CaseSensitive = case_sensitive
		} else {
			CaseSensitive = false
		}
	}
}

// PopulateDataFunc is a function type for creating test data
// Implementation should create bulk test data and fixtures
type PopulateDataFunc func(numAccounts, numUsers int) error

// CleanDatabase cleans all data via the db/init endpoint with confirmed: true payload
func CleanDatabase() error {
	if Verbose {
		fmt.Println("🧹 Cleaning database via API...")
	}

	// Prepare JSON payload {confirmed: true}
	payload := map[string]bool{"confirmed": true}
	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal payload: %w", err)
	}

	client := &http.Client{}
	req, err := http.NewRequest("POST", ServerURL+"/api/db/init", bytes.NewBuffer(payloadBytes))
	if err != nil {
		return fmt.Errorf("failed to create database init request: %w", err)
	}

	// Set Content-Type header for JSON
	req.Header.Set("Content-Type", "application/json")

	// Add session cookie if authenticated
	if SessionID != "" {
		req.Header.Set("Cookie", "sessionId="+SessionID)
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
		fmt.Println("✅ Database cleaning completed via /api/db/init")
	}

	return nil
}

func GetEntityCountsFromReport() (int, int) {
	users := 0
	accounts := 0

	// Fetch fresh data instead of using cached reportData
	response, err := ExecuteGet("/api/db/report")
	if err != nil {
		return 0, 0
	}

	// Extract entity count from report.entities.EntityName
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

	return users, accounts
}

// // GetDatabaseType returns the database type from /api/db/report
// func GetDatabaseType() string {
// 	if reportData != nil {}
// 	// Extract database type from response.database
// 	if val := GetFromResponse(reportData, "database", "unknown"); val != "unknown" {
// 		if dbType, ok := val.(string); ok {
// 			return dbType
// 		}
// 	}
// 	return "unknown"
// }

// // DetectAndSetDatabaseType detects the database type and sets the global DatabaseType variable
// func DetectAndSetDatabaseType() {
// 	DatabaseType = GetDatabaseType()
// 	if Verbose {
// 		fmt.Printf("Detected database type: %s\n", DatabaseType)
// 	}
// }
