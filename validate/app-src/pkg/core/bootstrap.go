package core

import (
	"fmt"
	"os/exec"
	"strings"
	"time"
)

// Bootstrap data - parameterized for easy expansion
// Uses map[string]interface{} for dynamic entity creation
// Exported so tests can reference bootstrap permissions
var Roles = []map[string]interface{}{
	{"id": "role_test", "role": "TestRole", "permissions": `{"*": "cruds"}`},
	{"id": "role_admin", "role": "Admin", "permissions": `{"*": "cruds"}`},
	{"id": "role_mgr", "role": "Manager", "permissions": `{"*": "cru", "Role": "r", "Auth": "", "Account": "r", "Crawl": ""}`},
	{"id": "role_rep", "role": "Representative", "permissions": `{"*": "ru", "Role": "r", "Auth": "", "Account": "r", "Crawl": ""}`},
}

var Auths = []map[string]interface{}{
	{"id": "auth_test", "name": "test_auth", "password": "12345678", "roleId": "role_test"},
	{"id": "auth_admin", "name": "Admin", "password": "12345678", "roleId": "role_admin"},
	{"id": "auth_mgr", "name": "Mgr", "password": "12345678", "roleId": "role_mgr"},
	{"id": "auth_rep", "name": "Rep", "password": "12345678", "roleId": "role_rep"},
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
	for _, role := range Roles {
		// Escape double quotes in permissions JSON for shell command
		roleID := role["id"].(string)
		roleName := role["role"].(string)
		permissions := role["permissions"].(string)
		escapedPermissions := strings.ReplaceAll(permissions, `"`, `\"`)
		roleCmd := fmt.Sprintf(`mongosh %s --quiet --eval 'db.Role.replaceOne({_id: "%s"}, {_id: "%s", id: "%s", role: "%s", permissions: "%s", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString()}, {upsert: true})'`,
			DatabaseName, roleID, roleID, roleID, roleName, escapedPermissions)
		if err := executeSystemCommand(roleCmd); err != nil {
			return fmt.Errorf("failed to upsert Role %s in MongoDB: %w", roleID, err)
		}
	}

	// Upsert Auth documents (replace if exists, insert if not)
	for _, auth := range Auths {
		authID := auth["id"].(string)
		name := auth["name"].(string)
		password := auth["password"].(string)
		roleID := auth["roleId"].(string)
		authCmd := fmt.Sprintf(`mongosh %s --quiet --eval 'db.Auth.replaceOne({_id: "%s"}, {_id: "%s", id: "%s", name: "%s", password: "%s", roleId: "%s", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString()}, {upsert: true})'`,
			DatabaseName, authID, authID, authID, name, password, roleID)
		if err := executeSystemCommand(authCmd); err != nil {
			return fmt.Errorf("failed to upsert Auth %s in MongoDB: %w", authID, err)
		}
	}

	if Verbose {
		fmt.Printf("  ✓ Created %d Roles and %d Auth records in MongoDB\n", len(Roles), len(Auths))
	}
	return nil
}

func bootstrapAuthPostgreSQL() error {
	// Upsert Role records (replace if exists, insert if not)
	// Note: Role table only has: id, role, permissions (no timestamps)
	for _, role := range Roles {
		// Escape double quotes in permissions JSON for shell command
		roleID := role["id"].(string)
		roleName := role["role"].(string)
		permissions := role["permissions"].(string)
		escapedPermissions := strings.ReplaceAll(permissions, `"`, `\"`)
		roleCmd := fmt.Sprintf(`psql -d %s -c "INSERT INTO \"Role\" (id, role, permissions) VALUES ('%s', '%s', '%s') ON CONFLICT (id) DO UPDATE SET role = EXCLUDED.role, permissions = EXCLUDED.permissions"`,
			DatabaseName, roleID, roleName, escapedPermissions)
		if err := executeSystemCommand(roleCmd); err != nil {
			return fmt.Errorf("failed to upsert Role %s in PostgreSQL: %w", roleID, err)
		}
	}

	// Upsert Auth records (replace if exists, insert if not)
	// Note: Auth table only has: id, name, password, roleId (no timestamps)
	for _, auth := range Auths {
		authID := auth["id"].(string)
		name := auth["name"].(string)
		password := auth["password"].(string)
		roleID := auth["roleId"].(string)
		authCmd := fmt.Sprintf(`psql -d %s -c "INSERT INTO \"Auth\" (id, name, password, \"roleId\") VALUES ('%s', '%s', '%s', '%s') ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, password = EXCLUDED.password, \"roleId\" = EXCLUDED.\"roleId\""`,
			DatabaseName, authID, name, password, roleID)
		if err := executeSystemCommand(authCmd); err != nil {
			return fmt.Errorf("failed to upsert Auth %s in PostgreSQL: %w", authID, err)
		}
	}

	if Verbose {
		fmt.Printf("  ✓ Created %d Roles and %d Auth records in PostgreSQL\n", len(Roles), len(Auths))
	}
	return nil
}

func bootstrapAuthSQLite() error {
	dbFile := fmt.Sprintf("%s.db", DatabaseName)

	// Upsert Role records (replace if exists, insert if not)
	// Note: Role table only has: id, role, permissions (no timestamps)
	for _, role := range Roles {
		// Escape double quotes in permissions JSON for shell command
		roleID := role["id"].(string)
		roleName := role["role"].(string)
		permissions := role["permissions"].(string)
		escapedPermissions := strings.ReplaceAll(permissions, `"`, `\"`)
		roleCmd := fmt.Sprintf(`sqlite3 %s "REPLACE INTO Role (id, role, permissions) VALUES ('%s', '%s', '%s')"`,
			dbFile, roleID, roleName, escapedPermissions)
		if err := executeSystemCommand(roleCmd); err != nil {
			return fmt.Errorf("failed to upsert Role %s in SQLite: %w", roleID, err)
		}
	}

	// Upsert Auth records (replace if exists, insert if not)
	// Note: Auth table only has: id, name, password, roleId (no timestamps)
	for _, auth := range Auths {
		authID := auth["id"].(string)
		name := auth["name"].(string)
		password := auth["password"].(string)
		roleID := auth["roleId"].(string)
		authCmd := fmt.Sprintf(`sqlite3 %s "REPLACE INTO Auth (id, name, password, roleId) VALUES ('%s', '%s', '%s', '%s')"`,
			dbFile, authID, name, password, roleID)
		if err := executeSystemCommand(authCmd); err != nil {
			return fmt.Errorf("failed to upsert Auth %s in SQLite: %w", authID, err)
		}
	}

	if Verbose {
		fmt.Printf("  ✓ Created %d Roles and %d Auth records in SQLite\n", len(Roles), len(Auths))
	}
	return nil
}

func bootstrapAuthElasticsearch() error {
	timestamp := getCurrentTimestamp()

	// Upsert Role documents (PUT replaces if exists, creates if not)
	// Use refresh=wait_for to ensure documents are searchable immediately
	for _, role := range Roles {
		// Escape double quotes in permissions JSON for curl -d'...' syntax
		roleID := role["id"].(string)
		roleName := role["role"].(string)
		permissions := role["permissions"].(string)
		escapedPermissions := strings.ReplaceAll(permissions, `"`, `\"`)
		roleCmd := fmt.Sprintf(`curl -s -X PUT "localhost:9200/role/_doc/%s?refresh=wait_for" -H 'Content-Type: application/json' -d'{"id":"%s","role":"%s","permissions":"%s","createdAt":"%s","updatedAt":"%s"}'`,
			roleID, roleID, roleName, escapedPermissions, timestamp, timestamp)
		if err := executeSystemCommand(roleCmd); err != nil {
			return fmt.Errorf("failed to upsert Role %s in Elasticsearch: %w", roleID, err)
		}
	}

	// Upsert Auth documents (PUT replaces if exists, creates if not)
	// Use refresh=wait_for to ensure documents are searchable immediately
	for _, auth := range Auths {
		authID := auth["id"].(string)
		name := auth["name"].(string)
		password := auth["password"].(string)
		roleID := auth["roleId"].(string)
		authCmd := fmt.Sprintf(`curl -s -X PUT "localhost:9200/auth/_doc/%s?refresh=wait_for" -H 'Content-Type: application/json' -d'{"id":"%s","name":"%s","password":"%s","roleId":"%s","createdAt":"%s","updatedAt":"%s"}'`,
			authID, authID, name, password, roleID, timestamp, timestamp)
		if err := executeSystemCommand(authCmd); err != nil {
			return fmt.Errorf("failed to upsert Auth %s in Elasticsearch: %w", authID, err)
		}
	}

	if Verbose {
		fmt.Printf("  ✓ Created %d Roles and %d Auth records in Elasticsearch\n", len(Roles), len(Auths))
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
