"""Base target class for ATLAS scan targets."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from atlas.core.models import Attempt, Message
from atlas.logging.setup import get_logger

logger = get_logger(__name__)


class BaseTarget(ABC):
    """Abstract base class for all scan targets.

    A target represents the system under test -- an LLM endpoint,
    an HTTP API, a RAG pipeline, or any other system that accepts
    prompts and returns responses.

    Subclasses must implement :meth:`send` and :meth:`send_messages`.
    """

    name: str = ""

    @abstractmethod
    async def send(self, attempt: Attempt) -> Attempt:
        """Send a probe attempt to the target and return it with the response filled.

        Args:
            attempt: The probe attempt containing the prompt to send.

        Returns:
            The same attempt with the ``response`` field populated.
        """
        ...

    @abstractmethod
    async def send_messages(self, messages: list[Message]) -> str:
        """Send a conversation (list of messages) and return the response text.

        Args:
            messages: Ordered list of conversation messages.

        Returns:
            The target's response content as a string.
        """
        ...

    def __repr__(self) -> str:
        return f"<{type(self).__name__} name={self.name!r}>"
