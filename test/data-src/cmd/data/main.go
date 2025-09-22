package main

import (
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/spf13/cobra"

	"data-generator/pkg/generator"
)

var (
	hostURL string
	verbose bool
)

func main() {
	var rootCmd = &cobra.Command{
		Use:   "data [clean] [list] [records[=users,accounts]] [curl]",
		Short: "Generate test data and curl.sh script",
		Long: `Generate comprehensive test data for all entities and create curl.sh test script.

Commands (processed in order):
  clean                        # Clean database
  list                         # Show available test categories
  records                      # Show current record counts
  records=users,accounts       # Ensure minimum record counts
  curl                         # Generate curl.sh (ensures 25,10 records minimum)

Examples:
  data curl                    # Generate curl.sh with minimum test data
  data clean curl              # Clean database, then generate curl.sh
  data list records            # Show categories and current counts
  data records=100,20 curl     # Ensure 100 users, 20 accounts, then generate curl.sh
  data clean records=50,15 curl # Clean, ensure records, generate curl.sh`,
		Run: runCommands,
	}


	// Global flags
	rootCmd.PersistentFlags().StringVar(&hostURL, "host", "http://localhost:5500", "API server URL")
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "Enable verbose output")

	// Disable completion command
	rootCmd.CompletionOptions.DisableDefaultCmd = true

	if err := rootCmd.Execute(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %v\n", err)
		os.Exit(1)
	}
}

func runCommands(cmd *cobra.Command, args []string) {
	config := generator.Config{
		ServerURL: hostURL,
		Verbose:   verbose,
	}

	// Track maximum record requirements for curl command
	maxUsers, maxAccounts := 25, 10 // curl defaults

	// Process commands in order - each command is independent
	for _, arg := range args {
		switch {
		case arg == "clean":
			// Show before counts
			beforeUsers, beforeAccounts, err := generator.GetRecordCounts(config)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Failed to get record counts before clean: %v\n", err)
				os.Exit(1)
			}
			fmt.Printf("Before clean: %d users, %d accounts\n", beforeUsers, beforeAccounts)

			if err := generator.CleanDatabase(config); err != nil {
				fmt.Fprintf(os.Stderr, "Failed to clean database: %v\n", err)
				os.Exit(1)
			}

			// Show after counts
			afterUsers, afterAccounts, err := generator.GetRecordCounts(config)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Failed to get record counts after clean: %v\n", err)
				os.Exit(1)
			}
			fmt.Printf("After clean: %d users, %d accounts\n", afterUsers, afterAccounts)

		case arg == "list":
			categories := generator.GetAvailableCategories()
			fmt.Println("Available test categories:")
			for _, category := range categories {
				fmt.Printf("  %s - %s\n", category.Name, category.Description)
			}

		case arg == "records":
			// Just report current counts
			users, accounts, err := generator.GetRecordCounts(config)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Failed to get record counts: %v\n", err)
				os.Exit(1)
			}
			fmt.Printf("Current records: %d users, %d accounts\n", users, accounts)

		case len(arg) > 8 && arg[:8] == "records=":
			// Parse records=x,y format and ensure minimum records
			recordSpec := arg[8:]

			// Show before counts
			beforeUsers, beforeAccounts, err := generator.GetRecordCounts(config)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Failed to get record counts before ensure: %v\n", err)
				os.Exit(1)
			}
			fmt.Printf("Before ensure: %d users, %d accounts\n", beforeUsers, beforeAccounts)

			// Parse target counts for during message
			targetUsers, targetAccounts, err := parseRecordSpec(recordSpec)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Invalid record specification: %v\n", err)
				os.Exit(1)
			}

			if verbose {
				fmt.Printf("Ensuring minimum: %d users, %d accounts\n", targetUsers, targetAccounts)
			}

			if err := generator.EnsureMinRecords(config, recordSpec); err != nil {
				fmt.Fprintf(os.Stderr, "Failed to ensure minimum records: %v\n", err)
				os.Exit(1)
			}

			// Show after counts
			afterUsers, afterAccounts, err := generator.GetRecordCounts(config)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Failed to get record counts after ensure: %v\n", err)
				os.Exit(1)
			}
			fmt.Printf("After ensure: %d users, %d accounts\n", afterUsers, afterAccounts)

			// Track highest requirements for curl
			if targetUsers > maxUsers { maxUsers = targetUsers }
			if targetAccounts > maxAccounts { maxAccounts = targetAccounts }

		case arg == "curl":
			// Ensure adequate records for meaningful curl.sh, then generate
			curlSpec := fmt.Sprintf("%d,%d", maxUsers, maxAccounts)
			if err := generator.EnsureMinRecords(config, curlSpec); err != nil {
				fmt.Fprintf(os.Stderr, "Failed to ensure minimum records for curl: %v\n", err)
				os.Exit(1)
			}
			if err := generator.GenerateAll(config); err != nil {
				fmt.Fprintf(os.Stderr, "Failed to generate curl.sh: %v\n", err)
				os.Exit(1)
			}
			if verbose {
				fmt.Println("✅ curl.sh generation completed successfully")
			}

		default:
			fmt.Fprintf(os.Stderr, "Unknown command: %s\n", arg)
			fmt.Fprintf(os.Stderr, "Valid commands: clean, list, records, records=users,accounts, curl\n")
			os.Exit(1)
		}
	}
}

// parseRecordSpec parses "users,accounts" format and returns the values
func parseRecordSpec(spec string) (int, int, error) {
	parts := strings.Split(spec, ",")
	if len(parts) != 2 {
		return 0, 0, fmt.Errorf("invalid format")
	}

	users, err1 := strconv.Atoi(strings.TrimSpace(parts[0]))
	accounts, err2 := strconv.Atoi(strings.TrimSpace(parts[1]))

	if err1 != nil || err2 != nil {
		return 0, 0, fmt.Errorf("invalid numbers")
	}

	return users, accounts, nil
}