#!/bin/bash

# testall.sh - Run validation tests against all database backends
# Usage: ./testall.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Config files for each database
CONFIGS=("mongo.json" "es.json" "sqlite.json" "postgres.json")

# Results tracking
RESULTS=()

echo "Starting full test suite across all databases..."
echo "=============================================="
echo

for CONFIG in "${CONFIGS[@]}"; do
    DB_NAME=$(basename "$CONFIG" .json)
    echo -e "${YELLOW}Testing with $DB_NAME...${NC}"

    # Start server with config
    echo "  Starting server with $CONFIG..."
    PYTHONPATH=. python3 app/main.py "$CONFIG" > "server_${DB_NAME}.log" 2>&1 &
    SERVER_PID=$!

    # Check if server is responding (try up to 10 times, 1 sec between attempts)
    READY=false
    for i in {1..10}; do
        sleep 1
        # Check if process died
        if ! kill -0 $SERVER_PID 2>/dev/null; then
            echo -e "  ${RED}ERROR: Server process died (see server_${DB_NAME}.log)${NC}"
            RESULTS+=("$DB_NAME: FAILED (server crashed)")
            READY="crashed"
            break
        fi
        # Check if server is responding
        if curl -s -f http://localhost:5500/api/User > /dev/null 2>&1; then
            READY=true
            echo "  Server ready after ${i} seconds"
            break
        fi
    done

    if [ "$READY" = "crashed" ]; then
        continue
    elif [ "$READY" = false ]; then
        echo -e "  ${RED}ERROR: Server not responding after 10 seconds (see server_${DB_NAME}.log)${NC}"
        kill $SERVER_PID 2>/dev/null
        wait $SERVER_PID 2>/dev/null
        RESULTS+=("$DB_NAME: FAILED (server not responding)")
        continue
    fi

    # Run tests
    echo "  Running validation tests..."
    ./validate/app -f > "test_${DB_NAME}.log" 2>&1
    TEST_RESULT=$?

    # Stop server
    echo "  Stopping server..."
    kill $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null

    # Parse summary line to check for failures
    # Format: "Summary: 258/1/259 tests passed/failed/total (99.6%)"
    SUMMARY_LINE=$(grep "Summary:" "test_${DB_NAME}.log" | tail -1)
    FAILED_COUNT=$(echo "$SUMMARY_LINE" | grep -oE "[0-9]+/[0-9]+/[0-9]+" | cut -d'/' -f2)

    # Record result based on failure count
    if [ -z "$FAILED_COUNT" ]; then
        echo -e "  ${RED}FAILED - Could not parse test results${NC} (see test_${DB_NAME}.log)"
        RESULTS+=("$DB_NAME: FAILED - Could not parse test results")
    elif [ "$FAILED_COUNT" -eq 0 ]; then
        echo -e "  ${GREEN}PASSED${NC}"
        RESULTS+=("$DB_NAME: PASSED")
    else
        echo -e "  ${RED}FAILED - $FAILED_COUNT test(s) failed${NC} (see test_${DB_NAME}.log)"
        RESULTS+=("$DB_NAME: FAILED - $FAILED_COUNT test(s) failed")
    fi

    echo
done

# Summary
echo "=============================================="
echo "Test Results Summary:"
echo "=============================================="
for RESULT in "${RESULTS[@]}"; do
    if [[ $RESULT == *"PASSED"* ]]; then
        echo -e "${GREEN}✓ $RESULT${NC}"
    else
        echo -e "${RED}✗ $RESULT${NC}"
    fi
done
echo
