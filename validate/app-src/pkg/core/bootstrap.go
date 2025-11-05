package core

import (
	"fmt"
	"os/exec"
	"time"
)

// BootstrapAuthData creates Role and Auth entities using database-specific CLI tools
// This bypasses the application layer to avoid chicken-egg authentication problem
func BootstrapAuthData() error {
	if Verbose {
		fmt.Println("🔐 Bootstrapping authentication data using DB CLI tools...")
	}

	switch DatabaseType {
	case "mongodb":
		return bootstrapAuthMongoDB()
	case "postgresql":
		return bootstrapAuthPostgreSQL()
	case "sqlite":
		return bootstrapAuthSQLite()
	case "elasticsearch":
		return bootstrapAuthElasticsearch()
	default:
		return fmt.Errorf("unsupported database type for bootstrap: %s", DatabaseType)
	}
}

func bootstrapAuthMongoDB() error {
	// Create Role document
	roleCmd := fmt.Sprintf(`mongosh %s --quiet --eval 'db.Role.insertOne({_id: "role_admin", id: "role_admin", role: "Admin", permissions: "{\"*\": \"crud\"}", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString()})'`, DatabaseName)
	if err := executeSystemCommand(roleCmd); err != nil {
		return fmt.Errorf("failed to create Role in MongoDB: %w", err)
	}

	// Create Auth document
	authCmd := fmt.Sprintf(`mongosh %s --quiet --eval 'db.Auth.insertOne({_id: "auth_mark", id: "auth_mark", name: "mark", password: "12345678", roleId: "role_admin", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString()})'`, DatabaseName)
	if err := executeSystemCommand(authCmd); err != nil {
		return fmt.Errorf("failed to create Auth in MongoDB: %w", err)
	}

	if Verbose {
		fmt.Println("  ✓ Created Role and Auth in MongoDB")
	}
	return nil
}

func bootstrapAuthPostgreSQL() error {
	// Create Role record
	roleCmd := fmt.Sprintf(`psql -d %s -c "INSERT INTO Role (id, role, permissions, \"createdAt\", \"updatedAt\") VALUES ('role_admin', 'Admin', '{\"*\": \"crud\"}', NOW(), NOW())"`, DatabaseName)
	if err := executeSystemCommand(roleCmd); err != nil {
		return fmt.Errorf("failed to create Role in PostgreSQL: %w", err)
	}

	// Create Auth record
	authCmd := fmt.Sprintf(`psql -d %s -c "INSERT INTO Auth (id, name, password, \"roleId\", \"createdAt\", \"updatedAt\") VALUES ('auth_mark', 'mark', '12345678', 'role_admin', NOW(), NOW())"`, DatabaseName)
	if err := executeSystemCommand(authCmd); err != nil {
		return fmt.Errorf("failed to create Auth in PostgreSQL: %w", err)
	}

	if Verbose {
		fmt.Println("  ✓ Created Role and Auth in PostgreSQL")
	}
	return nil
}

func bootstrapAuthSQLite() error {
	dbFile := fmt.Sprintf("%s.db", DatabaseName)

	// Create Role record
	roleCmd := fmt.Sprintf(`sqlite3 %s "INSERT INTO Role (id, role, permissions, createdAt, updatedAt) VALUES ('role_admin', 'Admin', '{\"*\": \"crud\"}', datetime('now'), datetime('now'))"`, dbFile)
	if err := executeSystemCommand(roleCmd); err != nil {
		return fmt.Errorf("failed to create Role in SQLite: %w", err)
	}

	// Create Auth record
	authCmd := fmt.Sprintf(`sqlite3 %s "INSERT INTO Auth (id, name, password, roleId, createdAt, updatedAt) VALUES ('auth_mark', 'mark', '12345678', 'role_admin', datetime('now'), datetime('now'))"`, dbFile)
	if err := executeSystemCommand(authCmd); err != nil {
		return fmt.Errorf("failed to create Auth in SQLite: %w", err)
	}

	if Verbose {
		fmt.Println("  ✓ Created Role and Auth in SQLite")
	}
	return nil
}

func bootstrapAuthElasticsearch() error {
	// Create Role document
	roleCmd := `curl -s -X POST "localhost:9200/role/_doc/role_admin" -H 'Content-Type: application/json' -d'{"id":"role_admin","role":"Admin","permissions":"{\"*\": \"crud\"}","createdAt":"` + getCurrentTimestamp() + `","updatedAt":"` + getCurrentTimestamp() + `"}'`
	if err := executeSystemCommand(roleCmd); err != nil {
		return fmt.Errorf("failed to create Role in Elasticsearch: %w", err)
	}

	// Create Auth document
	authCmd := `curl -s -X POST "localhost:9200/auth/_doc/auth_mark" -H 'Content-Type: application/json' -d'{"id":"auth_mark","name":"mark","password":"12345678","roleId":"role_admin","createdAt":"` + getCurrentTimestamp() + `","updatedAt":"` + getCurrentTimestamp() + `"}'`
	if err := executeSystemCommand(authCmd); err != nil {
		return fmt.Errorf("failed to create Auth in Elasticsearch: %w", err)
	}

	if Verbose {
		fmt.Println("  ✓ Created Role and Auth in Elasticsearch")
	}
	return nil
}

func executeSystemCommand(cmd string) error {
	// Use bash -c to execute the command
	execCmd := exec.Command("bash", "-c", cmd)
	output, err := execCmd.CombinedOutput()
	if err != nil {
		if Verbose {
			fmt.Printf("Command failed: %s\nOutput: %s\n", cmd, string(output))
		}
		return err
	}
	return nil
}

func getCurrentTimestamp() string {
	return time.Now().UTC().Format(time.RFC3339)
}
