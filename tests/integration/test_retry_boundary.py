"""Actual SDK HTTP retry behavior with an in-memory HTTP transport."""

import httpx2 as httpx
import pytest
from fast_agent import Prompt
from fast_agent.constants import FAST_AGENT_ERROR_CHANNEL
from fast_agent.llm.provider.openai.llm_generic import GenericLLM
from fast_agent.llm.provider_types import Provider
from fast_agent.types import PromptMessageExtended, RequestParams
from openai import AsyncOpenAI, BadRequestError

from housing.agents.fast_agent import disable_sdk_retries


@pytest.mark.parametrize(
    ("status", "recover", "expected"), [(500, True, 2), (500, False, 2), (400, False, 1)]
)
async def test_one_framework_retry_without_compounded_sdk_retries(
    status: int, recover: bool, expected: int
) -> None:
    calls = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if not recover or calls == 1:
            return httpx.Response(
                status, json={"error": {"message": "injected transport control", "type": "server_error"}}
            )
        return httpx.Response(
            200,
            json={
                "id": "controlled",
                "object": "chat.completion",
                "created": 0,
                "model": "controlled",
                "choices": [
                    {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "ok"}}
                ],
            },
        )

    # Avoid provider setup; exercise the real inherited retry loop and actual SDK transport.
    llm = object.__new__(GenericLLM)
    llm._stream_call_sequence = 0
    llm._stream_listeners = set()
    llm._resolved_model_spec = None
    llm.default_request_params = RequestParams(model="controlled")
    llm._provider = Provider.GENERIC

    def client() -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key="test",
            base_url="http://controlled.invalid/v1",
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
        )

    llm._openai_client = client  # type: ignore[method-assign]
    disable_sdk_retries(llm)
    llm.retry_backoff_seconds = 0

    async def operation() -> PromptMessageExtended:
        async with llm._openai_client() as sdk:
            assert sdk.max_retries == 0
            response = await sdk.chat.completions.create(
                model="controlled", messages=[{"role": "user", "content": "test"}]
            )
        return Prompt.assistant(response.choices[0].message.content or "")

    if recover:
        result = await llm._execute_with_retry(operation)
        assert result.first_text() == "ok"
    elif status == 400:
        with pytest.raises(BadRequestError):
            await llm._execute_with_retry(operation)
    else:
        result = await llm._execute_with_retry(operation)
        assert result.channels and FAST_AGENT_ERROR_CHANNEL in result.channels
    assert calls == expected
