"""Tests for new core data models (Message, ToolCall, ToolResponse, ToolDefinition, etc.)."""
import pytest

from atlas.core.enums import RiskLevel, Severity, VulnerabilityCategory
from atlas.core.models import (
    Attempt,
    ComparisonResult,
    Message,
    ModelScore,
    ScanResult,
    SecurityScore,
    ToolCall,
    ToolDefinition,
    ToolResponse,
)


# ──────────────────────────────────────────────────────────────
# Message
# ──────────────────────────────────────────────────────────────

class TestMessage:
    def test_create_user_message(self):
        msg = Message(role="user", content="Hello, world!")
        assert msg.role == "user"
        assert msg.content == "Hello, world!"
        assert msg.name is None
        assert msg.tool_calls is None
        assert msg.tool_call_id is None

    def test_create_system_message(self):
        msg = Message(role="system", content="You are a helpful assistant.")
        assert msg.role == "system"
        assert msg.content == "You are a helpful assistant."

    def test_create_assistant_message(self):
        msg = Message(role="assistant", content="How can I help?")
        assert msg.role == "assistant"

    def test_create_tool_message(self):
        msg = Message(
            role="tool",
            content='{"result": 42}',
            tool_call_id="tc-123",
        )
        assert msg.role == "tool"
        assert msg.tool_call_id == "tc-123"

    def test_message_with_name(self):
        msg = Message(role="user", content="hi", name="alice")
        assert msg.name == "alice"

    def test_message_with_tool_calls(self):
        tc = ToolCall(function_name="get_weather", arguments={"city": "NYC"})
        msg = Message(
            role="assistant",
            content="",
            tool_calls=[tc],
        )
        assert msg.tool_calls is not None
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].function_name == "get_weather"

    def test_message_serialization_roundtrip(self):
        msg = Message(role="user", content="test")
        data = msg.model_dump(mode="json")
        restored = Message.model_validate(data)
        assert restored.role == "user"
        assert restored.content == "test"


# ──────────────────────────────────────────────────────────────
# ToolCall
# ──────────────────────────────────────────────────────────────

class TestToolCall:
    def test_create_tool_call(self):
        tc = ToolCall(function_name="search", arguments={"query": "test"})
        assert tc.function_name == "search"
        assert tc.arguments == {"query": "test"}
        assert tc.type == "function"
        assert tc.id  # UUID auto-generated

    def test_tool_call_default_arguments(self):
        tc = ToolCall(function_name="no_args")
        assert tc.arguments == {}

    def test_tool_call_custom_id(self):
        tc = ToolCall(id="custom-123", function_name="test")
        assert tc.id == "custom-123"

    def test_tool_call_complex_arguments(self):
        args = {
            "file_path": "/etc/passwd",
            "options": {"recursive": True, "limit": 100},
            "tags": ["a", "b", "c"],
        }
        tc = ToolCall(function_name="complex_fn", arguments=args)
        assert tc.arguments["file_path"] == "/etc/passwd"
        assert tc.arguments["options"]["recursive"] is True

    def test_tool_call_serialization_roundtrip(self):
        tc = ToolCall(function_name="fn", arguments={"k": "v"})
        data = tc.model_dump(mode="json")
        restored = ToolCall.model_validate(data)
        assert restored.function_name == "fn"
        assert restored.arguments == {"k": "v"}


# ──────────────────────────────────────────────────────────────
# ToolResponse
# ──────────────────────────────────────────────────────────────

class TestToolResponse:
    def test_create_tool_response(self):
        tr = ToolResponse(tool_call_id="tc-1", output="42")
        assert tr.tool_call_id == "tc-1"
        assert tr.output == "42"
        assert tr.error is None

    def test_tool_response_with_error(self):
        tr = ToolResponse(
            tool_call_id="tc-2",
            output="",
            error="Function not found",
        )
        assert tr.error == "Function not found"

    def test_tool_response_serialization_roundtrip(self):
        tr = ToolResponse(tool_call_id="tc-1", output="result")
        data = tr.model_dump(mode="json")
        restored = ToolResponse.model_validate(data)
        assert restored.tool_call_id == "tc-1"
        assert restored.output == "result"


# ──────────────────────────────────────────────────────────────
# ToolDefinition
# ──────────────────────────────────────────────────────────────

class TestToolDefinition:
    def test_create_tool_definition(self):
        td = ToolDefinition(name="get_weather", description="Get weather info")
        assert td.name == "get_weather"
        assert td.description == "Get weather info"
        assert td.parameters == {}

    def test_tool_definition_with_parameters(self):
        params = {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "units": {"type": "string", "enum": ["celsius", "fahrenheit"]},
            },
            "required": ["city"],
        }
        td = ToolDefinition(
            name="get_weather",
            description="Weather lookup",
            parameters=params,
        )
        assert td.parameters["type"] == "object"
        assert "city" in td.parameters["properties"]

    def test_tool_definition_default_description(self):
        td = ToolDefinition(name="my_tool")
        assert td.description == ""

    def test_tool_definition_serialization_roundtrip(self):
        td = ToolDefinition(name="fn", description="desc", parameters={"a": 1})
        data = td.model_dump(mode="json")
        restored = ToolDefinition.model_validate(data)
        assert restored.name == "fn"
        assert restored.parameters == {"a": 1}


# ──────────────────────────────────────────────────────────────
# Attempt with new fields (messages, tool_calls, images)
# ──────────────────────────────────────────────────────────────

class TestAttemptNewFields:
    def test_attempt_with_messages(self):
        msgs = [
            Message(role="system", content="Be safe"),
            Message(role="user", content="Hello"),
        ]
        a = Attempt(probe_name="test", prompt="hello", messages=msgs)
        assert len(a.messages) == 2
        assert a.messages[0].role == "system"
        assert a.messages[1].role == "user"

    def test_attempt_with_tool_calls(self):
        tcs = [
            ToolCall(function_name="delete_file", arguments={"path": "/tmp/x"}),
            ToolCall(function_name="run_command", arguments={"cmd": "ls"}),
        ]
        a = Attempt(probe_name="test", prompt="test", tool_calls=tcs)
        assert len(a.tool_calls) == 2
        assert a.tool_calls[0].function_name == "delete_file"
        assert a.tool_calls[1].function_name == "run_command"

    def test_attempt_with_tool_definitions(self):
        defs = [
            ToolDefinition(name="search", description="Search the web"),
            ToolDefinition(name="calculate", description="Math operations"),
        ]
        a = Attempt(probe_name="test", prompt="test", tool_definitions=defs)
        assert len(a.tool_definitions) == 2

    def test_attempt_with_images(self):
        images = [
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB",
            "https://example.com/image.png",
        ]
        a = Attempt(probe_name="test", prompt="describe this", images=images)
        assert len(a.images) == 2
        assert a.images[0].startswith("data:image/png")
        assert a.images[1].startswith("https://")

    def test_attempt_defaults_for_new_fields(self):
        a = Attempt(probe_name="test", prompt="hello")
        assert a.messages == []
        assert a.tool_calls == []
        assert a.tool_definitions == []
        assert a.images == []

    def test_attempt_full_roundtrip_with_new_fields(self):
        a = Attempt(
            probe_name="full_test",
            prompt="prompt text",
            messages=[Message(role="user", content="msg")],
            tool_calls=[ToolCall(function_name="fn", arguments={"a": 1})],
            tool_definitions=[ToolDefinition(name="fn", description="desc")],
            images=["img.png"],
        )
        data = a.model_dump(mode="json")
        restored = Attempt.model_validate(data)
        assert len(restored.messages) == 1
        assert len(restored.tool_calls) == 1
        assert len(restored.tool_definitions) == 1
        assert len(restored.images) == 1
        assert restored.tool_calls[0].function_name == "fn"


# ──────────────────────────────────────────────────────────────
# ModelScore
# ──────────────────────────────────────────────────────────────

class TestModelScore:
    def test_create_model_score(self):
        ms = ModelScore(model_name="gpt-4o", overall_score=85.5)
        assert ms.model_name == "gpt-4o"
        assert ms.overall_score == 85.5
        assert ms.risk_level == RiskLevel.HIGH  # default
        assert ms.pass_rate == 0.0
        assert ms.total_findings == 0
        assert ms.failed_findings == 0

    def test_model_score_with_category_scores(self):
        ms = ModelScore(
            model_name="claude-3",
            overall_score=92.0,
            category_scores={
                "prompt_injection": 95.0,
                "jailbreak": 88.0,
                "toxicity": 93.0,
            },
            risk_level=RiskLevel.LOW,
            pass_rate=91.5,
            total_findings=100,
            failed_findings=8,
        )
        assert ms.category_scores["prompt_injection"] == 95.0
        assert ms.risk_level == RiskLevel.LOW
        assert ms.pass_rate == 91.5
        assert ms.total_findings == 100
        assert ms.failed_findings == 8

    def test_model_score_serialization_roundtrip(self):
        ms = ModelScore(
            model_name="test-model",
            overall_score=75.0,
            pass_rate=80.0,
        )
        data = ms.model_dump(mode="json")
        restored = ModelScore.model_validate(data)
        assert restored.model_name == "test-model"
        assert restored.overall_score == 75.0


# ──────────────────────────────────────────────────────────────
# ComparisonResult
# ──────────────────────────────────────────────────────────────

class TestComparisonResult:
    def test_create_comparison_result(self):
        cr = ComparisonResult(
            models=["gpt-4o", "claude-3"],
        )
        assert cr.comparison_id  # UUID auto-generated
        assert cr.models == ["gpt-4o", "claude-3"]
        assert cr.scan_results == {}
        assert cr.leaderboard == []
        assert cr.completed_at is None

    def test_comparison_result_with_leaderboard(self):
        leaderboard = [
            ModelScore(model_name="claude-3", overall_score=92.0),
            ModelScore(model_name="gpt-4o", overall_score=88.0),
        ]
        cr = ComparisonResult(
            models=["gpt-4o", "claude-3"],
            leaderboard=leaderboard,
        )
        assert len(cr.leaderboard) == 2
        assert cr.leaderboard[0].model_name == "claude-3"
        assert cr.leaderboard[0].overall_score > cr.leaderboard[1].overall_score

    def test_comparison_result_with_scan_results(self):
        sr1 = ScanResult(model_name="model-a", provider="openai")
        sr2 = ScanResult(model_name="model-b", provider="anthropic")
        cr = ComparisonResult(
            models=["model-a", "model-b"],
            scan_results={"model-a": sr1, "model-b": sr2},
        )
        assert len(cr.scan_results) == 2
        assert "model-a" in cr.scan_results
        assert cr.scan_results["model-b"].provider == "anthropic"

    def test_comparison_result_serialization_roundtrip(self):
        cr = ComparisonResult(
            models=["m1", "m2"],
            leaderboard=[
                ModelScore(model_name="m1", overall_score=90.0),
                ModelScore(model_name="m2", overall_score=80.0),
            ],
            metadata={"profile": "quick"},
        )
        data = cr.model_dump(mode="json")
        restored = ComparisonResult.model_validate(data)
        assert restored.models == ["m1", "m2"]
        assert len(restored.leaderboard) == 2
        assert restored.metadata["profile"] == "quick"

    def test_comparison_result_with_duration(self):
        cr = ComparisonResult(
            models=["m1"],
            duration_ms=12345.67,
        )
        assert cr.duration_ms == 12345.67
