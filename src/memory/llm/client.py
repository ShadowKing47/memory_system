import json
import logging
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from .protocol import LLMClientProtocol, LLMResponse, LLMClientError, AuthenticationError, InsufficientCreditsError

logger = logging.getLogger(__name__)


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ):
        if not api_key:
            raise ValueError("OpenRouter API key is required")
        
        self._api_key = api_key
        self._base_url = base_url
        self._max_retries = max_retries
        
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )
    
    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.HTTPStatusError,
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def complete(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int,
        temperature: float = 0.1,
        enable_reasoning: bool = True,
    ) -> LLMResponse:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "reasoning": {"enabled": enable_reasoning},
        }
        
        response = await self._client.post("/chat/completions", json=payload)
        
        if response.status_code == 401:
            raise AuthenticationError("Invalid OpenRouter API key")
        elif response.status_code == 402:
            raise InsufficientCreditsError("OpenRouter credits exhausted")
        elif response.status_code == 429:
            raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
        elif response.status_code >= 500:
            raise httpx.HTTPStatusError(f"Server error: {response.status_code}", request=response.request, response=response)
        
        response.raise_for_status()
        return LLMResponse.from_openrouter(response.json())
    
    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.HTTPStatusError,
        )),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def complete_stream(
        self,
        messages: list[dict],
        model: str,
        max_tokens: int,
        temperature: float = 0.1,
    ):
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        async with self._client.stream("POST", "/chat/completions", json=payload) as response:
            if response.status_code >= 400:
                raise httpx.HTTPStatusError("Stream error", request=response.request, response=response)
            async for chunk in response.aiter_lines():
                if chunk.startswith("data: "):
                    data = chunk[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue
    
    async def close(self):
        await self._client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()