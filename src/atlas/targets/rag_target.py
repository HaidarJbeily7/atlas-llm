"""RAG (Retrieval-Augmented Generation) pipeline target."""
from __future__ import annotations

from typing import Any

import httpx

from atlas.core.errors import AtlasConnectionError, AtlasTimeoutError
from atlas.core.models import Attempt, Message
from atlas.generators.litellm import LiteLLMGenerator
from atlas.logging.setup import get_logger
from atlas.plugins.registry import register
from atlas.targets.base import BaseTarget

logger = get_logger(__name__)

_DEFAULT_RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant. Use the following retrieved context to "
    "answer the user's question. If the context does not contain enough "
    "information, say so clearly.\n\n"
    "--- Retrieved Context ---\n{context}\n--- End Context ---"
)


@register("targets", name="rag")
class RAGTarget(BaseTarget):
    """Target that simulates a full Retrieval-Augmented Generation pipeline.

    The pipeline works in two stages:

    1. **Retrieval** -- The user's prompt is sent to an external retriever
       endpoint (HTTP POST) which returns relevant context chunks.
    2. **Generation** -- The retrieved context is injected into a system
       prompt and the augmented conversation is sent to a generator LLM
       for the final answer.

    This allows ATLAS to probe the entire RAG pipeline end-to-end,
    testing both retrieval poisoning and generation-side vulnerabilities.

    Args:
        retriever_url: URL of the retriever API endpoint.
        generator: A configured :class:`LiteLLMGenerator` for the generation stage.
        retriever_headers: Additional HTTP headers for the retriever endpoint.
        retriever_auth_token: Bearer token for the retriever endpoint.
        retriever_request_template: JSON body template for the retriever request.
            Use ``{prompt}`` as a placeholder. Defaults to ``{"query": "{prompt}"}``.
        retriever_response_field: Dot-path to the context text in the
            retriever's JSON response. Defaults to ``"context"``.
        context_system_prompt: Template for the system prompt injected into
            the generator. Use ``{context}`` as a placeholder for the
            retrieved content.
        retriever_timeout: Timeout in seconds for retriever requests.
        top_k: Number of context chunks to request (sent as ``top_k`` in the request body).
        name: Human-readable target name.
    """

    def __init__(
        self,
        retriever_url: str,
        generator: LiteLLMGenerator,
        retriever_headers: dict[str, str] | None = None,
        retriever_auth_token: str | None = None,
        retriever_request_template: dict[str, Any] | None = None,
        retriever_response_field: str = "context",
        context_system_prompt: str = _DEFAULT_RAG_SYSTEM_PROMPT,
        retriever_timeout: float = 30.0,
        top_k: int = 5,
        name: str | None = None,
    ) -> None:
        self.retriever_url = retriever_url
        self.generator = generator
        self.retriever_headers = dict(retriever_headers) if retriever_headers else {}
        self.retriever_request_template = retriever_request_template or {
            "query": "{prompt}",
            "top_k": top_k,
        }
        self.retriever_response_field = retriever_response_field
        self.context_system_prompt = context_system_prompt
        self.retriever_timeout = retriever_timeout
        self.top_k = top_k
        self.name = name or f"rag:{retriever_url}+{generator.model_name}"

        if retriever_auth_token:
            self.retriever_headers["Authorization"] = f"Bearer {retriever_auth_token}"
        self.retriever_headers.setdefault("Content-Type", "application/json")

        logger.info(
            "rag_target_initialized",
            name=self.name,
            retriever_url=retriever_url,
            generator_model=generator.model_name,
            top_k=top_k,
        )

    @classmethod
    def from_config(
        cls,
        retriever_url: str,
        generator_model: str,
        generator_api_key: str | None = None,
        generator_api_base: str | None = None,
        generator_timeout: int = 30,
        generator_max_retries: int = 3,
        generator_temperature: float = 0.0,
        generator_max_tokens: int | None = None,
        generator_extra: dict[str, Any] | None = None,
        retriever_headers: dict[str, str] | None = None,
        retriever_auth_token: str | None = None,
        retriever_request_template: dict[str, Any] | None = None,
        retriever_response_field: str = "context",
        context_system_prompt: str = _DEFAULT_RAG_SYSTEM_PROMPT,
        retriever_timeout: float = 30.0,
        top_k: int = 5,
        name: str | None = None,
    ) -> RAGTarget:
        """Create a RAGTarget from explicit configuration values.

        Builds the underlying :class:`LiteLLMGenerator` automatically.

        Returns:
            A fully configured :class:`RAGTarget`.
        """
        generator = LiteLLMGenerator(
            model_name=generator_model,
            api_key=generator_api_key,
            api_base=generator_api_base,
            timeout=generator_timeout,
            max_retries=generator_max_retries,
            temperature=generator_temperature,
            max_tokens=generator_max_tokens,
            extra=generator_extra,
        )
        return cls(
            retriever_url=retriever_url,
            generator=generator,
            retriever_headers=retriever_headers,
            retriever_auth_token=retriever_auth_token,
            retriever_request_template=retriever_request_template,
            retriever_response_field=retriever_response_field,
            context_system_prompt=context_system_prompt,
            retriever_timeout=retriever_timeout,
            top_k=top_k,
            name=name,
        )

    # ------------------------------------------------------------------
    # Retrieval helpers
    # ------------------------------------------------------------------

    def _build_retriever_body(self, prompt: str) -> dict[str, Any]:
        """Build the retriever request body from the template."""
        return self._substitute(self.retriever_request_template, prompt)

    @staticmethod
    def _substitute(obj: Any, prompt: str) -> Any:
        """Recursively substitute ``{prompt}`` in the template."""
        if isinstance(obj, str):
            if obj == "{prompt}":
                return prompt
            return obj.replace("{prompt}", prompt)
        if isinstance(obj, dict):
            return {k: RAGTarget._substitute(v, prompt) for k, v in obj.items()}
        if isinstance(obj, list):
            return [RAGTarget._substitute(item, prompt) for item in obj]
        return obj

    def _extract_context(self, data: Any) -> str:
        """Extract retrieved context from the retriever's JSON response.

        Walks the ``retriever_response_field`` dot-path.  If the resolved
        value is a list, the items are joined with double newlines.
        """
        current = data
        for segment in self.retriever_response_field.split("."):
            try:
                if isinstance(current, list):
                    current = current[int(segment)]
                elif isinstance(current, dict):
                    current = current[segment]
                else:
                    raise KeyError(segment)
            except (KeyError, IndexError, ValueError, TypeError) as exc:
                raise AtlasConnectionError(
                    f"Cannot extract context field '{self.retriever_response_field}' "
                    f"from retriever response: failed at segment '{segment}'",
                    error_code="TARGET_003",
                    context={
                        "retriever_url": self.retriever_url,
                        "response_field": self.retriever_response_field,
                        "segment": segment,
                    },
                ) from exc

        # If the context is a list of chunks, join them
        if isinstance(current, list):
            return "\n\n".join(str(chunk) for chunk in current)
        return str(current)

    async def _retrieve(self, prompt: str) -> str:
        """Send the prompt to the retriever and return the context string.

        Args:
            prompt: The user's query to send to the retriever.

        Returns:
            The retrieved context as a string.

        Raises:
            AtlasConnectionError: On HTTP errors or response parsing failures.
            AtlasTimeoutError: If the request times out.
        """
        body = self._build_retriever_body(prompt)

        logger.debug(
            "rag_retriever_request",
            target=self.name,
            url=self.retriever_url,
            prompt_len=len(prompt),
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.retriever_timeout,
            ) as client:
                resp = await client.post(
                    self.retriever_url,
                    headers=self.retriever_headers,
                    json=body,
                )
                resp.raise_for_status()
        except httpx.TimeoutException as exc:
            raise AtlasTimeoutError(
                f"Retriever request to {self.retriever_url} timed out "
                f"after {self.retriever_timeout}s",
                operation="rag_retrieve",
                timeout_seconds=self.retriever_timeout,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise AtlasConnectionError(
                f"Retriever HTTP {exc.response.status_code} from "
                f"{self.retriever_url}: {exc.response.text[:300]}",
                error_code="TARGET_003",
                context={
                    "retriever_url": self.retriever_url,
                    "status_code": exc.response.status_code,
                },
            ) from exc
        except httpx.HTTPError as exc:
            raise AtlasConnectionError(
                f"Retriever request to {self.retriever_url} failed: {exc}",
                error_code="TARGET_003",
                context={"retriever_url": self.retriever_url},
            ) from exc

        data = resp.json()
        context = self._extract_context(data)

        logger.debug(
            "rag_retriever_response",
            target=self.name,
            context_len=len(context),
        )
        return context

    def _build_system_prompt(self, context: str) -> str:
        """Build the generation system prompt with the retrieved context."""
        return self.context_system_prompt.replace("{context}", context)

    # ------------------------------------------------------------------
    # Target interface
    # ------------------------------------------------------------------

    async def send(self, attempt: Attempt) -> Attempt:
        """Execute the full RAG pipeline for a probe attempt.

        1. Retrieve context for ``attempt.prompt``.
        2. Build a system prompt with the context.
        3. Generate a response via the LLM generator.
        4. Store retrieval metadata on the attempt.

        Args:
            attempt: The probe attempt to process.

        Returns:
            The attempt with ``response`` populated and retrieval metadata
            stored under ``attempt.metadata["rag"]``.
        """
        logger.debug(
            "rag_target_send",
            target=self.name,
            probe=attempt.probe_name,
            prompt_len=len(attempt.prompt),
        )

        # Stage 1: Retrieval
        context = await self._retrieve(attempt.prompt)

        # Stage 2: Generation
        system_prompt = self._build_system_prompt(context)
        response = await self.generator.generate(
            prompt=attempt.prompt,
            system_prompt=system_prompt,
        )

        attempt.response = response
        attempt.metadata["rag"] = {
            "retriever_url": self.retriever_url,
            "context": context,
            "context_length": len(context),
            "generator_model": self.generator.model_name,
        }

        logger.debug(
            "rag_target_response",
            target=self.name,
            context_len=len(context),
            response_len=len(response),
        )
        return attempt

    async def send_messages(self, messages: list[Message]) -> str:
        """Execute the RAG pipeline for a conversation.

        Uses the last user message as the retrieval query, injects the
        retrieved context as a system message, and generates via the LLM.

        Args:
            messages: Ordered list of conversation messages.

        Returns:
            The generator's response text.
        """
        # Find the last user message to use as the retrieval query
        query = ""
        for m in reversed(messages):
            if m.role == "user":
                query = m.content
                break

        if not query:
            logger.warning(
                "rag_target_no_user_message",
                target=self.name,
                num_messages=len(messages),
            )
            # Fall back to generating without retrieval
            return await self.generator.generate_conversation(messages)

        logger.debug(
            "rag_target_send_messages",
            target=self.name,
            num_messages=len(messages),
            query_len=len(query),
        )

        # Stage 1: Retrieval
        context = await self._retrieve(query)

        # Stage 2: Augment the conversation with retrieved context
        system_prompt = self._build_system_prompt(context)
        augmented_messages = [
            Message(role="system", content=system_prompt),
            *[m for m in messages if m.role != "system"],
        ]

        # Stage 3: Generation
        response = await self.generator.generate_conversation(augmented_messages)

        logger.debug(
            "rag_target_messages_response",
            target=self.name,
            context_len=len(context),
            response_len=len(response),
        )
        return response
