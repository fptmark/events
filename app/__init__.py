"""
Events application package.

This package contains the server-side code for the Events application.
It includes models, routes, and utilities for managing events and related data.
"""

__version__ = "1.0.0"

from . import models
from . import routers
from . import utils
from . import db

__all__ = ["models", "routers", "utils", "db"] 