"""HTTP API target for testing remote endpoints."""
from __future__ import annotations

from typing import Any

import httpx

from atlas.core.errors import AtlasConnectionError, AtlasTimeoutError
from atlas.core.models import Attempt, Message
from atlas.logging.setup import get_logger
from atlas.plugins.registry import register
from atlas.targets.base import BaseTarget

logger = get_logger(__name__)


@register("targets", name="http")
class HTTPTarget(BaseTarget):
    """Target that sends prompts to a remote HTTP API endpoint.

    Sends an HTTP POST request with the prompt in a configurable JSON
    body structure and extracts the response from a configurable field
    path in the JSON response.

    Args:
        url: The endpoint URL to send POST requests to.
        headers: Additional HTTP headers (e.g. authorization).
        auth_token: Bearer token added as an ``Authorization`` header.
        request_template: A dictionary template for the request body.
            Use ``{prompt}`` as a placeholder for the actual prompt and
            ``{messages}`` for conversation messages.
            Defaults to ``{"prompt": "{prompt}"}``.
        response_field: Dot-separated path to the response text in the
            JSON response body (e.g. ``"choices.0.message.content"``).
            Defaults to ``"response"``.
        timeout: Request timeout in seconds.
        verify_ssl: Whether to verify SSL certificates.
        name: Human-readable target name.

    Example::

        target = HTTPTarget(
            url="https://api.example.com/v1/chat",
            auth_token="sk-...",
            request_template={
                "model": "my-model",
                "messages": [{"role": "user", "content": "{prompt}"}],
            },
            response_field="choices.0.message.content",
        )
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        auth_token: str | None = None,
        request_template: dict[str, Any] | None = None,
        response_field: str = "response",
        timeout: float = 60.0,
        verify_ssl: bool = True,
        name: str | None = None,
    ) -> None:
        self.url = url
        self.headers = dict(headers) if headers else {}
        self.request_template = request_template or {"prompt": "{prompt}"}
        self.response_field = response_field
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.name = name or f"http:{url}"

        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"

        # Ensure JSON content type
        self.headers.setdefault("Content-Type", "application/json")

        logger.info(
            "http_target_initialized",
            name=self.name,
            url=url,
            response_field=response_field,
            timeout=timeout,
        )

    def _build_request_body(
        self,
        prompt: str,
        messages: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Build the JSON request body by substituting placeholders.

        Recursively walks the request template and replaces ``{prompt}``
        with the actual prompt string and ``{messages}`` with the
        serialised messages list.

        Args:
            prompt: The prompt text to insert.
            messages: Optional list of message dicts for conversation mode.

        Returns:
            The fully populated request body dictionary.
        """
        return self._substitute(self.request_template, prompt, messages)

    def _substitute(
        self,
        obj: Any,
        prompt: str,
        messages: list[dict[str, str]] | None = None,
    ) -> Any:
        """Recursively substitute placeholders in the template."""
        if isinstance(obj, str):
            if obj == "{prompt}":
                return prompt
            if obj == "{messages}":
                return messages or []
            return obj.replace("{prompt}", prompt)
        if isinstance(obj, dict):
            return {k: self._substitute(v, prompt, messages) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._substitute(item, prompt, messages) for item in obj]
        return obj

    def _extract_response(self, data: Any) -> str:
        """Extract the response string from the JSON response body.

        Walks the ``response_field`` dot-path through the response data.
        Numeric path segments are treated as list indices.

        Args:
            data: Parsed JSON response body.

        Returns:
            The extracted response string.

        Raises:
            AtlasConnectionError: If the field path cannot be resolved.
        """
        current = data
        for segment in self.response_field.split("."):
            try:
                if isinstance(current, list):
                    current = current[int(segment)]
                elif isinstance(current, dict):
                    current = current[segment]
                else:
                    raise KeyError(segment)
            except (KeyError, IndexError, ValueError, TypeError) as exc:
                raise AtlasConnectionError(
                    f"Cannot extract response field '{self.response_field}' "
                    f"from response: failed at segment '{segment}'",
                    error_code="TARGET_002",
                    context={
                        "url": self.url,
                        "response_field": self.response_field,
                        "segment": segment,
                        "available_keys": list(current.keys())
                        if isinstance(current, dict)
                        else None,
                    },
                ) from exc

        if not isinstance(current, str):
            current = str(current)
        return current

    async def send(self, attempt: Attempt) -> Attempt:
        """Send a probe attempt via HTTP POST and populate its response.

        Args:
            attempt: The probe attempt to send.

        Returns:
            The attempt with the ``response`` field populated from the API.

        Raises:
            AtlasConnectionError: On HTTP errors or response parsing failures.
            AtlasTimeoutError: If the request exceeds the configured timeout.
        """
        body = self._build_request_body(attempt.prompt)

        logger.debug(
            "http_target_send",
            target=self.name,
            url=self.url,
            probe=attempt.probe_name,
            prompt_len=len(attempt.prompt),
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl,
            ) as client:
                resp = await client.post(
                    self.url,
                    headers=self.headers,
                    json=body,
                )
                resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AtlasTimeoutError(
                f"HTTP request to {self.url} timed out after {self.timeout}s",
                operation="http_target_send",
                timeout_seconds=self.timeout,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise AtlasConnectionError(
                f"HTTP {exc.response.status_code} from {self.url}: "
                f"{exc.response.text[:300]}",
                error_code="TARGET_001",
                context={
                    "url": self.url,
                    "status_code": exc.response.status_code,
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise AtlasConnectionError(
                f"HTTP request to {self.url} failed: {exc}",
                error_code="TARGET_001",
                context={"url": self.url},
            ) from exc

        data = resp.json()
        attempt.response = self._extract_response(data)

        logger.debug(
            "http_target_response",
            target=self.name,
            status_code=resp.status_code,
            response_len=len(attempt.response),
        )
        return attempt

    async def send_messages(self, messages: list[Message]) -> str:
        """Send a conversation via HTTP POST and return the response text.

        Serialises the messages into dicts and injects them into the
        request template via the ``{messages}`` placeholder.  The last
        user message's content is also used for the ``{prompt}``
        placeholder as a fallback.

        Args:
            messages: Ordered list of conversation messages.

        Returns:
            The target's response content as a string.
        """
        msg_dicts = [
            {"role": m.role, "content": m.content, **({"name": m.name} if m.name else {})}
            for m in messages
        ]

        # Use the last user message as the prompt fallback
        prompt = ""
        for m in reversed(messages):
            if m.role == "user":
                prompt = m.content
                break

        body = self._build_request_body(prompt, messages=msg_dicts)

        logger.debug(
            "http_target_send_messages",
            target=self.name,
            url=self.url,
            num_messages=len(messages),
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=self.verify_ssl,
            ) as client:
                resp = await client.post(
                    self.url,
                    headers=self.headers,
                    json=body,
                )
                resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AtlasTimeoutError(
                f"HTTP request to {self.url} timed out after {self.timeout}s",
                operation="http_target_send_messages",
                timeout_seconds=self.timeout,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise AtlasConnectionError(
                f"HTTP {exc.response.status_code} from {self.url}: "
                f"{exc.response.text[:300]}",
                error_code="TARGET_001",
                context={
                    "url": self.url,
                    "status_code": exc.response.status_code,
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise AtlasConnectionError(
                f"HTTP request to {self.url} failed: {exc}",
                error_code="TARGET_001",
                context={"url": self.url},
            ) from exc

        data = resp.json()
        response = self._extract_response(data)

        logger.debug(
            "http_target_messages_response",
            target=self.name,
            status_code=resp.status_code,
            response_len=len(response),
        )
        return response
