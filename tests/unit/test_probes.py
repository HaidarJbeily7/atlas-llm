"""Tests for probes."""
from atlas.probes.prompt_injection import PromptInjectionProbe
from atlas.probes.jailbreak import JailbreakProbe
from atlas.probes.encoding import EncodingProbe
from atlas.probes.extraction import ExtractionProbe
from atlas.probes.toxicity import ToxicityProbe
from atlas.probes.hallucination import HallucinationProbe
from atlas.probes.web_injection import WebInjectionProbe
from atlas.probes.malware import MalwareProbe


class TestPromptInjectionProbe:
    def test_generates_prompts(self):
        probe = PromptInjectionProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 0
        assert all(a.probe_name == "prompt_injection" for a in prompts)


class TestJailbreakProbe:
    def test_generates_prompts(self):
        probe = JailbreakProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 0


class TestEncodingProbe:
    def test_generates_prompts(self):
        probe = EncodingProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 0
        # Should have base64, hex, rot13, morse variants
        encodings = {a.metadata.get("encoding") for a in prompts}
        assert "base64" in encodings
        assert "rot13" in encodings


class TestExtractionProbe:
    def test_generates_prompts(self):
        probe = ExtractionProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) == 30


class TestToxicityProbe:
    def test_generates_prompts(self):
        probe = ToxicityProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 0


class TestHallucinationProbe:
    def test_generates_prompts(self):
        probe = HallucinationProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) >= 25  # 10 factual + 10 package + 5 reasoning


class TestWebInjectionProbe:
    def test_generates_prompts(self):
        probe = WebInjectionProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) > 0


class TestMalwareProbe:
    def test_generates_prompts(self):
        probe = MalwareProbe()
        prompts = probe.generate_prompts()
        assert len(prompts) == 20
