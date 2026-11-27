"""pytest configuration and shared fixtures for the AI service test suite."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest

# Make sure the ai-service root is on PYTHONPATH when running tests
_AI_SERVICE_ROOT = Path(__file__).parent.parent
if str(_AI_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_AI_SERVICE_ROOT))

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_CHROMA_DIR = Path(__file__).parent / "_test_chroma"


def pytest_configure(config):
    """Force mock LLM and local embeddings in all tests regardless of .env."""
    os.environ["LLM_PROVIDER"] = "mock"
    os.environ["LLM_API_KEY"] = ""
    os.environ["LLM_MODEL"] = ""
    os.environ["EMBEDDING_PROVIDER"] = "local"
    os.environ["EMBEDDING_MODEL"] = "paraphrase-multilingual-MiniLM-L12-v2"
    os.environ["ENV"] = "development"
    os.environ["AI_SERVICE_API_KEY"] = ""

    from app.core.config import get_settings
    from app.services.llm_service import get_llm_service

    get_settings.cache_clear()
    get_llm_service.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def create_test_fixtures():
    """Generate the tiny TEST fixture PDFs once per test session."""
    # Import here (after path is set)
    from tests.fixtures.create_fixtures import create_all
    create_all()
    yield


@pytest.fixture(scope="session")
def test_chroma_dir():
    """Provide and clean up an isolated Chroma dir for the test session."""
    if TEST_CHROMA_DIR.exists():
        shutil.rmtree(TEST_CHROMA_DIR)
    TEST_CHROMA_DIR.mkdir(parents=True)
    yield str(TEST_CHROMA_DIR)
    shutil.rmtree(TEST_CHROMA_DIR, ignore_errors=True)
