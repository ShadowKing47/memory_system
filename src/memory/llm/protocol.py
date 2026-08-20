from typing import Protocol, AsyncIterator
from pydantic import BaseModel


class LLMResponse(BaseModel):
    content: str
    reasoning_details: list[dict] | None = None
    model: str
    usage: dict
    
    @classmethod
    def from_openrouter(cls, data: dict) -> "LLMResponse":
        msg = data["choices"][0]["message"]
        return cls(
            content=msg.get("content", ""),
            reasoning_details=msg.get("reasoning_details"),
            model=data.get("model", ""),
            usage=data.get("usage", {}),
        )


class LLMClientProtocol(Protocol):
    async def complete(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int,
        temperature: float = 0.1,
        enable_reasoning: bool = True,
    ) -> LLMResponse: ...
    
    async def complete_stream(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int,
        temperature: float = 0.1,
    ) -> AsyncIterator[dict]: ...
    
    async def close(self) -> None: ...


class LLMClientError(Exception):
    pass


class AuthenticationError(LLMClientError):
    pass


class InsufficientCreditsError(LLMClientError):
    pass


class MockLLMClient:
    def __init__(self, responses: list[LLMResponse] | None = None):
        self._responses = responses or []
        self._call_count = 0
    
    async def complete(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int,
        temperature: float = 0.1,
        enable_reasoning: bool = True,
    ) -> LLMResponse:
        if self._responses:
            response = self._responses[self._call_count % len(self._responses)]
        else:
            response = LLMResponse(
                content='[{"entity": "test", "fact": "Mock fact", "is_update": false}]',
                reasoning_details=None,
                model="mock",
                usage={},
            )
        self._call_count += 1
        return response
    
    async def complete_stream(self, *args, **kwargs):
        yield {}
    
    async def close(self) -> None:
        pass