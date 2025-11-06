package types

// Entity models matching Python Pydantic models
// Single source of truth for entity structure across all tests

// User represents the User entity model
type User struct {
	ID             string  `json:"id,omitempty"`
	Username       string  `json:"username"`
	Email          string  `json:"email"`
	Password       string  `json:"password"`
	FirstName      string  `json:"firstName"`
	LastName       string  `json:"lastName"`
	Gender         string  `json:"gender,omitempty"`
	DOB            string  `json:"dob,omitempty"`
	Address        string  `json:"address,omitempty"`
	City           string  `json:"city,omitempty"`
	State          string  `json:"state,omitempty"`
	Zip            string  `json:"zip,omitempty"`
	IsAccountOwner bool    `json:"isAccountOwner"`
	NetWorth       float64 `json:"netWorth,omitempty"`
	AccountID      string  `json:"accountId"`
	CreatedAt      string  `json:"createdAt,omitempty"`
	UpdatedAt      string  `json:"updatedAt,omitempty"`
}

// Account represents the Account entity model
type Account struct {
	ID         string  `json:"id,omitempty"`
	Name       string  `json:"name"`
	Credit     float64 `json:"credit,omitempty"`
	ExpireDate string  `json:"expireDate,omitempty"`
	Enabled    bool    `json:"enabled,omitempty"`
	CreatedAt  string  `json:"createdAt,omitempty"`
	UpdatedAt  string  `json:"updatedAt,omitempty"`
}

// Role represents the Role entity model
type Role struct {
	ID          string `json:"id,omitempty"`
	Role        string `json:"role"`
	Permissions string `json:"permissions"`
}

// Auth represents the Auth entity model (authentication users)
type Auth struct {
	ID       string `json:"id,omitempty"`
	Name     string `json:"name"`     // Maps to "login" in API (authn service input)
	Password string `json:"password"`
	RoleID   string `json:"roleId"`
}
