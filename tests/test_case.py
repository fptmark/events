#!/usr/bin/env python3
"""
TestCase dataclass for unified test definitions.
"""

from dataclasses import dataclass
from typing import Optional

@dataclass
class TestCase:
    method: str
    url: str
    description: str
    expected_status: int = 200
    expected_data_len: Optional[int] = None
    expected_notification_len: Optional[int] = None
    expected_paging: bool = False
    expected_response: Optional[dict] = None  # For deep validation of fixed records