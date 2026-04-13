"""
pytest configuration and fixtures for the auto_clicker_for_cookie_clicker test suite.
"""
import sys
import pytest

# Check for Qt availability
try:
    from PySide6.QtWidgets import QApplication
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "qt: marks tests that require Qt/PySide6 (deselect with '-m \"not qt\"')",
    )
    config.addinivalue_line(
        "markers",
        "e2e: marks end-to-end tests that may be slow or require external resources",
    )


def pytest_collection_modifyitems(config, items):
    """Skip Qt tests if PySide6 is not available."""
    if QT_AVAILABLE:
        return
    
    skip_qt = pytest.mark.skip(reason="PySide6 not installed")
    for item in items:
        if "qt" in item.keywords:
            item.add_marker(skip_qt)


# Optional: Provide a fixture for Qt application
@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for Qt tests."""
    if not QT_AVAILABLE:
        pytest.skip("PySide6 not installed")
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app