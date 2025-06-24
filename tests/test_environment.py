"""Test environment setup and basic imports."""

import pytest
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_python_version():
    """Test that Python version is 3.11+"""
    assert sys.version_info >= (3, 11), "Python 3.11+ is required"


def test_package_imports():
    """Test that all main packages can be imported"""
    try:
        import dfautotrans
        assert dfautotrans.__version__ == "0.1.0"
        assert dfautotrans.__author__ == "LF\\Tommy.Yeung"
    except ImportError as e:
        pytest.fail(f"Failed to import dfautotrans: {e}")


def test_dependencies():
    """Test that all required dependencies are available"""
    dependencies = [
        "playwright",
        "pydantic", 
        "sqlalchemy",
        "alembic",
        "loguru",
    ]
    
    for dep in dependencies:
        try:
            __import__(dep)
        except ImportError as e:
            pytest.fail(f"Required dependency '{dep}' not available: {e}")
    
    # Test python-dotenv separately
    try:
        from dotenv import load_dotenv
    except ImportError as e:
        pytest.fail(f"Required dependency 'python-dotenv' not available: {e}")


@pytest.mark.asyncio
async def test_playwright_basic():
    """Test basic Playwright functionality"""
    try:
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Simple test - navigate to a basic page
        await page.goto("about:blank")
        assert page.url == "about:blank"
        
        await browser.close()
        await playwright.stop()
        
    except Exception as e:
        pytest.fail(f"Playwright basic test failed: {e}")


if __name__ == "__main__":
    # Run basic tests
    test_python_version()
    test_package_imports() 
    test_dependencies()
    print("✅ Environment setup successful!")
    print("✅ All dependencies installed correctly!")
    print("✅ Ready for development!") 