package database

import (
	"context"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"

	"data-generator/pkg/models"
)

// DatabaseClient interface for database operations
type DatabaseClient interface {
	Connect(ctx context.Context) error
	Disconnect(ctx context.Context) error
	SaveUsers(ctx context.Context, users []models.User) error
	SaveAccounts(ctx context.Context, accounts []models.Account) error
	ValidateConnections(ctx context.Context) error
	CountUsers(ctx context.Context) (int64, error)
	CountAccounts(ctx context.Context) (int64, error)
}

// MongoClient implements DatabaseClient for MongoDB
type MongoClient struct {
	client   *mongo.Client
	database *mongo.Database
	dbURI    string
	dbName   string
}

// NewMongoClient creates a new MongoDB client
func NewMongoClient(dbURI, dbName string) *MongoClient {
	return &MongoClient{
		dbURI:  dbURI,
		dbName: dbName,
	}
}

// Connect establishes connection to MongoDB
func (mc *MongoClient) Connect(ctx context.Context) error {
	clientOptions := options.Client().ApplyURI(mc.dbURI)

	client, err := mongo.Connect(ctx, clientOptions)
	if err != nil {
		return fmt.Errorf("failed to connect to MongoDB: %w", err)
	}

	// Ping the database to verify connection
	if err := client.Ping(ctx, nil); err != nil {
		return fmt.Errorf("failed to ping MongoDB: %w", err)
	}

	mc.client = client
	mc.database = client.Database(mc.dbName)

	return nil
}

// Disconnect closes the MongoDB connection
func (mc *MongoClient) Disconnect(ctx context.Context) error {
	if mc.client != nil {
		return mc.client.Disconnect(ctx)
	}
	return nil
}

// SaveUsers saves user documents to MongoDB
func (mc *MongoClient) SaveUsers(ctx context.Context, users []models.User) error {
	if len(users) == 0 {
		return nil
	}

	collection := mc.database.Collection("users")

	// Drop existing collection to start fresh
	if err := collection.Drop(ctx); err != nil {
		// Ignore error if collection doesn't exist
	}

	// Convert users to interface slice for batch insert
	docs := make([]interface{}, len(users))
	for i, user := range users {
		docs[i] = user
	}

	// Insert all users
	_, err := collection.InsertMany(ctx, docs)
	if err != nil {
		return fmt.Errorf("failed to insert users: %w", err)
	}

	return nil
}

// SaveAccounts saves account documents to MongoDB
func (mc *MongoClient) SaveAccounts(ctx context.Context, accounts []models.Account) error {
	if len(accounts) == 0 {
		return nil
	}

	collection := mc.database.Collection("accounts")

	// Drop existing collection to start fresh
	if err := collection.Drop(ctx); err != nil {
		// Ignore error if collection doesn't exist
	}

	// Convert accounts to interface slice for batch insert
	docs := make([]interface{}, len(accounts))
	for i, account := range accounts {
		docs[i] = account
	}

	// Insert all accounts
	_, err := collection.InsertMany(ctx, docs)
	if err != nil {
		return fmt.Errorf("failed to insert accounts: %w", err)
	}

	return nil
}

// ValidateConnections validates FK relationships
func (mc *MongoClient) ValidateConnections(ctx context.Context) error {
	// TODO: Implement FK validation logic
	return nil
}

// ElasticsearchClient implements DatabaseClient for Elasticsearch
type ElasticsearchClient struct {
	endpoint string
	dbName   string
}

// NewElasticsearchClient creates a new Elasticsearch client
func NewElasticsearchClient(endpoint, dbName string) *ElasticsearchClient {
	return &ElasticsearchClient{
		endpoint: endpoint,
		dbName:   dbName,
	}
}

// Connect establishes connection to Elasticsearch
func (ec *ElasticsearchClient) Connect(ctx context.Context) error {
	// TODO: Implement Elasticsearch connection
	return fmt.Errorf("Elasticsearch support not yet implemented")
}

// Disconnect closes the Elasticsearch connection
func (ec *ElasticsearchClient) Disconnect(ctx context.Context) error {
	// TODO: Implement Elasticsearch disconnect
	return nil
}

// SaveUsers saves user documents to Elasticsearch
func (ec *ElasticsearchClient) SaveUsers(ctx context.Context, users []models.User) error {
	// TODO: Implement Elasticsearch user saving
	return fmt.Errorf("Elasticsearch support not yet implemented")
}

// SaveAccounts saves account documents to Elasticsearch
func (ec *ElasticsearchClient) SaveAccounts(ctx context.Context, accounts []models.Account) error {
	// TODO: Implement Elasticsearch account saving
	return fmt.Errorf("Elasticsearch support not yet implemented")
}

// ValidateConnections validates FK relationships in Elasticsearch
func (ec *ElasticsearchClient) ValidateConnections(ctx context.Context) error {
	// TODO: Implement Elasticsearch FK validation
	return nil
}

// NewDatabaseClient creates appropriate database client based on type
func NewDatabaseClient(dbType, dbURI, dbName string) (DatabaseClient, error) {
	switch dbType {
	case "mongodb":
		return NewMongoClient(dbURI, dbName), nil
	case "elasticsearch":
		return NewElasticsearchClient(dbURI, dbName), nil
	default:
		return nil, fmt.Errorf("unsupported database type: %s", dbType)
	}
}

// CleanAllData cleans all test data from the database
func CleanAllData(ctx context.Context, dbType, dbURI, dbName string, verbose bool) error {
	client, err := NewDatabaseClient(dbType, dbURI, dbName)
	if err != nil {
		return fmt.Errorf("failed to create database client: %w", err)
	}

	// Set timeout for database operations
	ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	// Connect to database
	if err := client.Connect(ctx); err != nil {
		return fmt.Errorf("failed to connect to database: %w", err)
	}
	defer client.Disconnect(ctx)

	if verbose {
		fmt.Printf("📊 Connected to %s database: %s\n", dbType, dbName)
	}

	// Clean collections by saving empty arrays
	if err := client.SaveUsers(ctx, []models.User{}); err != nil {
		return fmt.Errorf("failed to clean users: %w", err)
	}

	if err := client.SaveAccounts(ctx, []models.Account{}); err != nil {
		return fmt.Errorf("failed to clean accounts: %w", err)
	}

	if verbose {
		fmt.Println("✅ Database collections cleaned")
	}

	return nil
}

// SaveAllData saves all generated data to the database
func SaveAllData(ctx context.Context, dbType, dbURI, dbName string, users []models.User, accounts []models.Account, verbose bool) error {
	client, err := NewDatabaseClient(dbType, dbURI, dbName)
	if err != nil {
		return fmt.Errorf("failed to create database client: %w", err)
	}

	// Set timeout for database operations
	ctx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	// Connect to database
	if err := client.Connect(ctx); err != nil {
		return fmt.Errorf("failed to connect to database: %w", err)
	}
	defer client.Disconnect(ctx)

	if verbose {
		fmt.Printf("📊 Connected to %s database: %s\n", dbType, dbName)
	}

	// Save accounts first (users reference them)
	if err := client.SaveAccounts(ctx, accounts); err != nil {
		return fmt.Errorf("failed to save accounts: %w", err)
	}

	if verbose {
		fmt.Printf("✅ Saved %d accounts\n", len(accounts))
	}

	// Save users
	if err := client.SaveUsers(ctx, users); err != nil {
		return fmt.Errorf("failed to save users: %w", err)
	}

	if verbose {
		fmt.Printf("✅ Saved %d users\n", len(users))
	}

	return nil
}