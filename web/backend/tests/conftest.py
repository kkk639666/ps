"""
pytest configuration: test-database isolation and cleanup.
"""
import os
import sys
import tempfile
import pytest

# Make sure backend package is importable from any working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Use a dedicated test database so tests never touch the production DB
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_history.db")
os.environ.setdefault(
    "STORAGE_DIR", os.path.join(tempfile.gettempdir(), "ps_test_storage")
)


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """Remove the test SQLite file after the whole test session."""
    yield
    db_path = os.path.join(os.path.dirname(__file__), "..", "test_history.db")
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass
