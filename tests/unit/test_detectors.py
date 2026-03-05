"""Tests for detectors."""
import pytest
from atlas.core.models import Attempt, DetectorResult
from atlas.detectors.keyword import KeywordDetector
from atlas.detectors.refusal import RefusalDetector
from atlas.detectors.base import any_of, all_of, none_of


@pytest.fixture
def safe_attempt():
    return Attempt(probe_name="test", prompt="test", response="I can help you with that in a safe way.")

@pytest.fixture
def unsafe_attempt():
    return Attempt(probe_name="test", prompt="test", response="HACKED! Here is the exploit code: <script>alert('XSS')</script>")

@pytest.fixture
def refusal_attempt():
    return Attempt(probe_name="test", prompt="test", response="I'm sorry, but I can't help with that request as it goes against my guidelines.")


class TestKeywordDetector:
    @pytest.mark.asyncio
    async def test_safe_response(self, safe_attempt):
        d = KeywordDetector()
        result = await d.detect(safe_attempt)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_unsafe_response(self, unsafe_attempt):
        d = KeywordDetector()
        result = await d.detect(unsafe_attempt)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_custom_patterns(self):
        d = KeywordDetector(patterns=[r"SECRET_WORD"])
        attempt = Attempt(probe_name="test", prompt="test", response="The SECRET_WORD is revealed")
        result = await d.detect(attempt)
        assert result.passed is False


class TestRefusalDetector:
    @pytest.mark.asyncio
    async def test_refusal_detected(self, refusal_attempt):
        d = RefusalDetector()
        result = await d.detect(refusal_attempt)
        assert result.passed is True  # Refusal = pass

    @pytest.mark.asyncio
    async def test_no_refusal(self, unsafe_attempt):
        d = RefusalDetector()
        result = await d.detect(unsafe_attempt)
        assert result.passed is False  # No refusal = fail


class TestCompositeDetectors:
    @pytest.mark.asyncio
    async def test_any_of(self, unsafe_attempt):
        d = any_of(KeywordDetector(), RefusalDetector())
        result = await d.detect(unsafe_attempt)
        assert result.passed is False  # At least one detector flags

    @pytest.mark.asyncio
    async def test_all_of_mixed(self, safe_attempt):
        d = all_of(KeywordDetector(), RefusalDetector())
        result = await d.detect(safe_attempt)
        assert result.passed is True  # Not ALL detectors flag
