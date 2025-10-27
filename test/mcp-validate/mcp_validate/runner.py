"""
MCP test runner.
Orchestrates test execution with three-phase data generation.
"""
import asyncio
import sys
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from .client import MCPClient, MCPConfig
from .fixtures import create_bulk_data, create_fixtures_from_test_cases
from .test_cases import TestCase, get_all_test_cases, get_test_cases_by_class


@dataclass
class TestResult:
    """Test result"""
    test_case: TestCase
    passed: bool
    error: str | None = None
    result: Any = None
    duration_ms: float = 0.0


class MCPTestRunner:
    """MCP test runner"""

    def __init__(
        self,
        mcp_client: MCPClient,
        verbose: bool = False
    ):
        """
        Initialize test runner.

        Args:
            mcp_client: MCP client instance
            verbose: Enable verbose output
        """
        self.client = mcp_client
        self.verbose = verbose
        self.results: List[TestResult] = []

    async def reset_and_populate(
        self,
        num_accounts: int = 10,
        num_users: int = 50
    ) -> None:
        """
        Reset database and populate with test data.

        Three-phase data generation:
        1. Clean database
        2. Create dynamic pre-data (bulk random data)
        3. Create static fixtures (specific test data)

        Args:
            num_accounts: Number of random accounts to create
            num_users: Number of random users to create
        """
        if self.verbose:
            print("\n" + "=" * 60)
            print("RESET AND POPULATE")
            print("=" * 60)

        # Phase 0: Clean database
        await self.client.clean_database()

        # Phase 1: Dynamic pre-data
        if self.verbose:
            print(f"\nPhase 1: Creating {num_accounts} accounts and {num_users} users (dynamic pre-data)")

        await create_bulk_data(
            self.client,
            num_accounts=num_accounts,
            num_users=num_users,
            verbose=self.verbose
        )

        # Phase 2: Static fixtures
        if self.verbose:
            print(f"\nPhase 2: Creating static fixtures from test cases")

        test_cases = get_all_test_cases()
        await create_fixtures_from_test_cases(
            self.client,
            test_cases=[tc.__dict__ for tc in test_cases],
            verbose=self.verbose
        )

        if self.verbose:
            print("\n✅ Reset and populate complete")
            print("=" * 60)

    async def run_test(self, test_case: TestCase) -> TestResult:
        """
        Run a single test case.

        Args:
            test_case: Test case to run

        Returns:
            Test result
        """
        start_time = datetime.now()

        try:
            # Call MCP tool
            result = await self.client.call_tool(
                test_case.operation,
                test_case.params
            )

            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Check if we expected success
            if not test_case.expect_success:
                return TestResult(
                    test_case=test_case,
                    passed=False,
                    error=f"Expected error but got success: {result}",
                    result=result,
                    duration_ms=duration_ms
                )

            # Verify expected fields
            if test_case.expected_fields and isinstance(result, dict):
                missing_fields = [f for f in test_case.expected_fields if f not in result]
                if missing_fields:
                    return TestResult(
                        test_case=test_case,
                        passed=False,
                        error=f"Missing expected fields: {missing_fields}",
                        result=result,
                        duration_ms=duration_ms
                    )

            return TestResult(
                test_case=test_case,
                passed=True,
                result=result,
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Check if we expected an error
            if test_case.expect_error:
                # TODO: Parse error type from exception
                error_str = str(e).lower()

                # Check for expected error types
                if test_case.expect_error == "validation":
                    if "validation" in error_str or "invalid" in error_str or "required" in error_str:
                        return TestResult(
                            test_case=test_case,
                            passed=True,
                            error=str(e),
                            duration_ms=duration_ms
                        )
                elif test_case.expect_error == "not_found":
                    if "not found" in error_str or "404" in error_str:
                        return TestResult(
                            test_case=test_case,
                            passed=True,
                            error=str(e),
                            duration_ms=duration_ms
                        )

            return TestResult(
                test_case=test_case,
                passed=False,
                error=str(e),
                duration_ms=duration_ms
            )

    async def run_all_tests(self, test_filter: str | None = None) -> None:
        """
        Run all test cases.

        Args:
            test_filter: Optional filter by test class (basic, create, etc.)
        """
        if self.verbose:
            print("\n" + "=" * 60)
            print("RUNNING TESTS")
            print("=" * 60)

        # Get test cases
        if test_filter:
            test_cases = get_test_cases_by_class(test_filter)
            if self.verbose:
                print(f"\nFilter: {test_filter}")
        else:
            test_cases = get_all_test_cases()

        if self.verbose:
            print(f"Total tests: {len(test_cases)}\n")

        # Run tests
        for i, test_case in enumerate(test_cases, 1):
            if self.verbose:
                print(f"[{i}/{len(test_cases)}] {test_case.name}: {test_case.description}")

            result = await self.run_test(test_case)
            self.results.append(result)

            # Print result
            status = "✅ PASS" if result.passed else "❌ FAIL"
            if self.verbose:
                print(f"  {status} ({result.duration_ms:.1f}ms)")
                if not result.passed and result.error:
                    print(f"  Error: {result.error}")
                print()

        if self.verbose:
            print("=" * 60)

    def print_summary(self) -> None:
        """Print test summary"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total:  {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")

        if failed > 0:
            print("\nFailed tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  • {result.test_case.name}: {result.error}")

        print("=" * 60)

        # Exit code
        sys.exit(0 if failed == 0 else 1)


async def main():
    """Main entry point for test runner"""
    import argparse

    parser = argparse.ArgumentParser(description="MCP Test Runner")
    parser.add_argument("--server", default="mcp_server.py", help="Path to MCP server script")
    parser.add_argument("--config", default="mongo.json", help="Path to config file (mongo.json, sqlite.json, es.json)")
    parser.add_argument("--accounts", type=int, default=10, help="Number of random accounts to create")
    parser.add_argument("--users", type=int, default=50, help="Number of random users to create")
    parser.add_argument("--test", help="Filter tests by class (basic, create, update, list)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-reset", action="store_true", help="Skip reset and populate")

    args = parser.parse_args()

    # Create MCP client
    config = MCPConfig(
        server_script=args.server,
        config_file=args.config
    )

    client = MCPClient(config, verbose=args.verbose)

    try:
        # Start MCP server
        await client.start()

        # Create test runner
        runner = MCPTestRunner(client, verbose=args.verbose)

        # Reset and populate (unless skipped)
        if not args.no_reset:
            await runner.reset_and_populate(
                num_accounts=args.accounts,
                num_users=args.users
            )

        # Run tests
        await runner.run_all_tests(test_filter=args.test)

        # Print summary
        runner.print_summary()

    finally:
        # Stop MCP server
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())
