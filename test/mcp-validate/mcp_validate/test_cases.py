"""
MCP test case definitions.
Similar to test/validate-src/pkg/tests/static.go but for MCP tools.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class TestCase:
    """MCP test case definition"""
    name: str
    description: str
    operation: str  # MCP tool name (e.g., "create_user", "get_account")
    params: Dict[str, Any] = field(default_factory=dict)
    expect_success: bool = True
    expect_error: Optional[str] = None  # Expected error type: "validation", "not_found", etc.
    expected_fields: List[str] = field(default_factory=list)  # Fields that should be in result
    test_class: str = "basic"  # Test classification: basic, create, filter, etc.


def get_all_test_cases() -> List[TestCase]:
    """
    Get all MCP test cases.

    Returns ordered test cases from basic to complex:
    - Basic CRUD (get, create, update, delete)
    - Validation tests (missing fields, invalid values)
    - Filter/sort tests
    - Pagination tests
    """

    test_cases = []

    # =========================================================================
    # PHASE 1: BASIC GET - Individual entity retrieval
    # =========================================================================

    test_cases.extend([
        TestCase(
            name="get_user_valid_001",
            description="Get valid user by ID",
            operation="get_user",
            params={"id": "usr_get_001"},
            expect_success=True,
            expected_fields=["id", "username", "email", "firstName", "lastName"],
            test_class="basic"
        ),
        TestCase(
            name="get_user_valid_002",
            description="Get another valid user by ID",
            operation="get_user",
            params={"id": "usr_get_002"},
            expect_success=True,
            expected_fields=["id", "username", "email"],
            test_class="basic"
        ),
        TestCase(
            name="get_user_not_found",
            description="Get non-existent user",
            operation="get_user",
            params={"id": "usr_nonexist_001"},
            expect_success=False,
            expect_error="not_found",
            test_class="basic"
        ),
        TestCase(
            name="get_account_valid_001",
            description="Get valid account by ID",
            operation="get_account",
            params={"id": "acc_valid_001"},
            expect_success=True,
            expected_fields=["id", "createdAt"],
            test_class="basic"
        ),
        TestCase(
            name="get_account_not_found",
            description="Get non-existent account",
            operation="get_account",
            params={"id": "acc_nonexist_001"},
            expect_success=False,
            expect_error="not_found",
            test_class="basic"
        ),
    ])

    # =========================================================================
    # PHASE 2: CREATE USER - Success cases
    # =========================================================================

    test_cases.extend([
        TestCase(
            name="create_user_all_fields",
            description="Create user with all fields",
            operation="create_user",
            params={
                "firstName": "CreateTest",
                "lastName": "User",
                "email": "createtest@example.com",
                "username": "createtest_user",
                "gender": "male",
                "isAccountOwner": True,
                "netWorth": 50000,
                "dob": "1990-01-01",
                "password": "TestPass123!",
                "accountId": "acc_valid_001"
            },
            expect_success=True,
            expected_fields=["id", "firstName", "lastName", "email", "username", "createdAt"],
            test_class="create"
        ),
        TestCase(
            name="create_user_minimal",
            description="Create user with minimal required fields",
            operation="create_user",
            params={
                "firstName": "Minimal",
                "lastName": "User",
                "email": "minimal@example.com",
                "username": "minimal_user",
                "isAccountOwner": False,
                "password": "TestPass123!",
                "accountId": "acc_valid_001"
            },
            expect_success=True,
            expected_fields=["id", "firstName", "lastName", "email", "username"],
            test_class="create"
        ),
    ])

    # =========================================================================
    # PHASE 3: CREATE USER - Validation failures
    # =========================================================================

    test_cases.extend([
        TestCase(
            name="create_user_missing_firstName",
            description="Create user - missing firstName",
            operation="create_user",
            params={
                "lastName": "User",
                "email": "test@example.com",
                "username": "test_user",
                "password": "TestPass123!",
                "accountId": "acc_valid_001",
                "isAccountOwner": False
            },
            expect_success=False,
            expect_error="validation",
            test_class="create"
        ),
        TestCase(
            name="create_user_missing_lastName",
            description="Create user - missing lastName",
            operation="create_user",
            params={
                "firstName": "Test",
                "email": "test@example.com",
                "username": "test_user",
                "password": "TestPass123!",
                "accountId": "acc_valid_001",
                "isAccountOwner": False
            },
            expect_success=False,
            expect_error="validation",
            test_class="create"
        ),
        TestCase(
            name="create_user_missing_email",
            description="Create user - missing email",
            operation="create_user",
            params={
                "firstName": "Test",
                "lastName": "User",
                "username": "test_user",
                "password": "TestPass123!",
                "accountId": "acc_valid_001",
                "isAccountOwner": False
            },
            expect_success=False,
            expect_error="validation",
            test_class="create"
        ),
        TestCase(
            name="create_user_invalid_gender",
            description="Create user - invalid gender enum",
            operation="create_user",
            params={
                "firstName": "Test",
                "lastName": "User",
                "email": "invalidenum@example.com",
                "username": "invalid_enum_user",
                "gender": "invalid_gender",
                "password": "TestPass123!",
                "accountId": "acc_valid_001",
                "isAccountOwner": False
            },
            expect_success=False,
            expect_error="validation",
            test_class="create"
        ),
        TestCase(
            name="create_user_username_too_short",
            description="Create user - username too short (< 3 chars)",
            operation="create_user",
            params={
                "firstName": "Test",
                "lastName": "User",
                "email": "shortuser@example.com",
                "username": "ab",
                "password": "TestPass123!",
                "accountId": "acc_valid_001",
                "isAccountOwner": False
            },
            expect_success=False,
            expect_error="validation",
            test_class="create"
        ),
    ])

    # =========================================================================
    # PHASE 4: UPDATE USER
    # =========================================================================

    test_cases.extend([
        TestCase(
            name="update_user_single_field",
            description="Update user - single field",
            operation="update_user",
            params={
                "id": "usr_get_001",
                "firstName": "UpdatedName"
            },
            expect_success=True,
            expected_fields=["id", "firstName"],
            test_class="update"
        ),
        TestCase(
            name="update_user_multiple_fields",
            description="Update user - multiple fields",
            operation="update_user",
            params={
                "id": "usr_get_002",
                "firstName": "Updated",
                "lastName": "User",
                "netWorth": 75000
            },
            expect_success=True,
            expected_fields=["id", "firstName", "lastName", "netWorth"],
            test_class="update"
        ),
    ])

    # =========================================================================
    # PHASE 5: LIST / FILTER / SORT
    # =========================================================================

    test_cases.extend([
        TestCase(
            name="list_users_no_params",
            description="List users without parameters",
            operation="list_users",
            params={},
            expect_success=True,
            test_class="list"
        ),
        TestCase(
            name="list_users_with_pagination",
            description="List users with pagination",
            operation="list_users",
            params={"page": 1, "pageSize": 10},
            expect_success=True,
            test_class="list"
        ),
        TestCase(
            name="list_users_with_sort",
            description="List users sorted by creation date",
            operation="list_users",
            params={"sort_by": "-createdAt"},
            expect_success=True,
            test_class="list"
        ),
        TestCase(
            name="list_users_with_filter",
            description="List users filtered by gender",
            operation="list_users",
            params={"filter_field": "gender", "filter_value": "male"},
            expect_success=True,
            test_class="list"
        ),
    ])

    return test_cases


def get_test_cases_by_class(test_class: str) -> List[TestCase]:
    """
    Get test cases filtered by test class.

    Args:
        test_class: Test class (basic, create, update, list, etc.)

    Returns:
        Filtered test cases
    """
    all_cases = get_all_test_cases()
    return [tc for tc in all_cases if tc.test_class == test_class]
