"""Typed application errors.

One exception type per failure category, each carrying the machine-readable
``code`` that ends up in the error envelope. Routes raise these; the global
handlers in main.py convert them to JSON — so no route builds error JSON
by hand and no stack trace ever reaches a client.
"""


class AppError(Exception):
    """Base class: HTTP status + stable error code + safe message."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AuthError(AppError):
    """Missing/invalid credentials -> 401."""

    status_code = 401
    code = "UNAUTHORIZED"


class LeadNotFoundError(AppError):
    """Requested lead id does not exist -> 404."""

    status_code = 404
    code = "LEAD_NOT_FOUND"


class MCPUnavailableError(AppError):
    """The MCP server cannot be reached -> 503."""

    status_code = 503
    code = "MCP_UNAVAILABLE"


class MCPToolError(AppError):
    """The MCP server ran the tool but reported a failure -> 502."""

    status_code = 502
    code = "MCP_TOOL_ERROR"


class SheetsSyncError(AppError):
    """Google Sheets sync failed (lead is still safe in SQLite)."""

    status_code = 502
    code = "SHEETS_SYNC_ERROR"
