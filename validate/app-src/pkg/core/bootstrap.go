package core

import (
	"fmt"
	"os/exec"
	"strings"
	"time"
)

// RoleData defines a role to be bootstrapped
type RoleData struct {
	ID          string
	Role        string
	Permissions string
}

// AuthData defines an auth record to be bootstrapped
type AuthData struct {
	ID       string
	Name     string
	Password string
	RoleID   string
}

// Bootstrap data - parameterized for easy expansion
var roles = []RoleData{
	{ID: "role_test", Role: "TestRole", Permissions: `{"*": "cruds"}`},
	{ID: "role_admin", Role: "Admin", Permissions: `{"*": "cruds"}`},
	{ID: "role_mgr", Role: "Manager", Permissions: `{"*": "crus"}`},
	{ID: "role_rep", Role: "Representative", Permissions: `{"*": "ru"}`},
}

var auths = []AuthData{
	{ID: "auth_test", Name: "test_auth", Password: "12345678", RoleID: "role_test"},
	{ID: "auth_admin", Name: "Admin", Password: "12345678", RoleID: "role_admin"},
	{ID: "auth_mgr", Name: "Mgr", Password: "12345678", RoleID: "role_mgr"},
	{ID: "auth_rep", Name: "Rep", Password: "12345678", RoleID: "role_rep"},
}

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
	// Upsert Role documents (replace if exists, insert if not)
	for _, role := range roles {
		// Escape double quotes in permissions JSON for shell command
		escapedPermissions := strings.ReplaceAll(role.Permissions, `"`, `\"`)
		roleCmd := fmt.Sprintf(`mongosh %s --quiet --eval 'db.Role.replaceOne({_id: "%s"}, {_id: "%s", id: "%s", role: "%s", permissions: "%s", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString()}, {upsert: true})'`,
			DatabaseName, role.ID, role.ID, role.ID, role.Role, escapedPermissions)
		if err := executeSystemCommand(roleCmd); err != nil {
			return fmt.Errorf("failed to upsert Role %s in MongoDB: %w", role.ID, err)
		}
	}

	// Upsert Auth documents (replace if exists, insert if not)
	for _, auth := range auths {
		authCmd := fmt.Sprintf(`mongosh %s --quiet --eval 'db.Auth.replaceOne({_id: "%s"}, {_id: "%s", id: "%s", name: "%s", password: "%s", roleId: "%s", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString()}, {upsert: true})'`,
			DatabaseName, auth.ID, auth.ID, auth.ID, auth.Name, auth.Password, auth.RoleID)
		if err := executeSystemCommand(authCmd); err != nil {
			return fmt.Errorf("failed to upsert Auth %s in MongoDB: %w", auth.ID, err)
		}
	}

	if Verbose {
		fmt.Printf("  ✓ Created %d Roles and %d Auth records in MongoDB\n", len(roles), len(auths))
	}
	return nil
}

func bootstrapAuthPostgreSQL() error {
	// Upsert Role records (replace if exists, insert if not)
	for _, role := range roles {
		roleCmd := fmt.Sprintf(`psql -d %s -c "INSERT INTO Role (id, role, permissions, \"createdAt\", \"updatedAt\") VALUES ('%s', '%s', '%s', NOW(), NOW()) ON CONFLICT (id) DO UPDATE SET role = EXCLUDED.role, permissions = EXCLUDED.permissions, \"updatedAt\" = NOW()"`,
			DatabaseName, role.ID, role.Role, role.Permissions)
		if err := executeSystemCommand(roleCmd); err != nil {
			return fmt.Errorf("failed to upsert Role %s in PostgreSQL: %w", role.ID, err)
		}
	}

	// Upsert Auth records (replace if exists, insert if not)
	for _, auth := range auths {
		authCmd := fmt.Sprintf(`psql -d %s -c "INSERT INTO Auth (id, name, password, \"roleId\", \"createdAt\", \"updatedAt\") VALUES ('%s', '%s', '%s', '%s', NOW(), NOW()) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, password = EXCLUDED.password, \"roleId\" = EXCLUDED.\"roleId\", \"updatedAt\" = NOW()"`,
			DatabaseName, auth.ID, auth.Name, auth.Password, auth.RoleID)
		if err := executeSystemCommand(authCmd); err != nil {
			return fmt.Errorf("failed to upsert Auth %s in PostgreSQL: %w", auth.ID, err)
		}
	}

	if Verbose {
		fmt.Printf("  ✓ Created %d Roles and %d Auth records in PostgreSQL\n", len(roles), len(auths))
	}
	return nil
}

func bootstrapAuthSQLite() error {
	dbFile := fmt.Sprintf("%s.db", DatabaseName)

	// Upsert Role records (replace if exists, insert if not)
	for _, role := range roles {
		roleCmd := fmt.Sprintf(`sqlite3 %s "REPLACE INTO Role (id, role, permissions, createdAt, updatedAt) VALUES ('%s', '%s', '%s', datetime('now'), datetime('now'))"`,
			dbFile, role.ID, role.Role, role.Permissions)
		if err := executeSystemCommand(roleCmd); err != nil {
			return fmt.Errorf("failed to upsert Role %s in SQLite: %w", role.ID, err)
		}
	}

	// Upsert Auth records (replace if exists, insert if not)
	for _, auth := range auths {
		authCmd := fmt.Sprintf(`sqlite3 %s "REPLACE INTO Auth (id, name, password, roleId, createdAt, updatedAt) VALUES ('%s', '%s', '%s', '%s', datetime('now'), datetime('now'))"`,
			dbFile, auth.ID, auth.Name, auth.Password, auth.RoleID)
		if err := executeSystemCommand(authCmd); err != nil {
			return fmt.Errorf("failed to upsert Auth %s in SQLite: %w", auth.ID, err)
		}
	}

	if Verbose {
		fmt.Printf("  ✓ Created %d Roles and %d Auth records in SQLite\n", len(roles), len(auths))
	}
	return nil
}

func bootstrapAuthElasticsearch() error {
	timestamp := getCurrentTimestamp()

	// Upsert Role documents (PUT replaces if exists, creates if not)
	for _, role := range roles {
		roleCmd := fmt.Sprintf(`curl -s -X PUT "localhost:9200/role/_doc/%s" -H 'Content-Type: application/json' -d'{"id":"%s","role":"%s","permissions":"%s","createdAt":"%s","updatedAt":"%s"}'`,
			role.ID, role.ID, role.Role, role.Permissions, timestamp, timestamp)
		if err := executeSystemCommand(roleCmd); err != nil {
			return fmt.Errorf("failed to upsert Role %s in Elasticsearch: %w", role.ID, err)
		}
	}

	// Upsert Auth documents (PUT replaces if exists, creates if not)
	for _, auth := range auths {
		authCmd := fmt.Sprintf(`curl -s -X PUT "localhost:9200/auth/_doc/%s" -H 'Content-Type: application/json' -d'{"id":"%s","name":"%s","password":"%s","roleId":"%s","createdAt":"%s","updatedAt":"%s"}'`,
			auth.ID, auth.ID, auth.Name, auth.Password, auth.RoleID, timestamp, timestamp)
		if err := executeSystemCommand(authCmd); err != nil {
			return fmt.Errorf("failed to upsert Auth %s in Elasticsearch: %w", auth.ID, err)
		}
	}

	if Verbose {
		fmt.Printf("  ✓ Created %d Roles and %d Auth records in Elasticsearch\n", len(roles), len(auths))
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
