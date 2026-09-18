"""Autom8r FastAPI application package.

IMPORTANT: this __init__ must stay side-effect free (no imports of app
modules). The MCP server imports ``backend.app.services.scoring`` from the
repository root, and a heavy __init__ would drag FastAPI into that process.
"""
