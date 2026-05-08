import json
import threading
import time
from collections import defaultdict
from collections.abc import AsyncIterator

import httpx
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.api_call import ApiCall
from app.models.model import Model, ModelInstance
from app.models.user import User
from app.utils.exceptions import APIError


class AIService:
    _rr_counters: dict[str, int] = defaultdict(int)
    _rr_lock = threading.Lock()

    def __init__(self, db: Session):
        self.db = db

    def list_public_models(self) -> dict:
        models = list(
            self.db.scalars(
                select(Model).where(Model.status == "online").order_by(Model.name.asc())
            )
        )
        return {
            "object": "list",
            "data": [
                {
                    "id": model.name,
                    "object": "model",
                    "created": int(model.created_at.timestamp()),
                    "owned_by": "suit-api",
                }
                for model in models
            ],
        }

    async def proxy_chat_completion(self, payload: dict, user: User, api_key: str):
        return await self._proxy_openai_request("/v1/chat/completions", payload, user, api_key)

    async def proxy_completion(self, payload: dict, user: User, api_key: str):
        return await self._proxy_openai_request("/v1/completions", payload, user, api_key)

    async def proxy_embeddings(self, payload: dict, user: User, api_key: str):
        return await self._proxy_openai_request("/v1/embeddings", payload, user, api_key)

    async def _proxy_openai_request(self, endpoint: str, payload: dict, user: User, api_key: str):
        model_name = payload.get("model")
        if not model_name:
            raise APIError("Field 'model' is required")
        model = self.db.scalar(select(Model).where(Model.name == model_name))
        if model is None:
            raise APIError("Model not found", status_code=404, code=40401)
        instance = self._select_running_instance(model.id)
        stream = bool(payload.get("stream"))
        start = time.perf_counter()

        if stream:
            iterator = self._stream_proxy(instance, endpoint, payload, user, api_key, start)
            return StreamingResponse(iterator, media_type="text/event-stream")

        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(f"{instance.api_endpoint}{endpoint}", json=payload)
        latency_ms = int((time.perf_counter() - start) * 1000)
        body = self._parse_response_body(response)
        usage = body.get("usage", {}) if isinstance(body, dict) else {}
        self._record_api_call(
            user_id=user.id,
            api_key=api_key,
            model_name=model_name,
            endpoint=endpoint,
            tokens_input=int(usage.get("prompt_tokens", 0) or 0),
            tokens_output=int(usage.get("completion_tokens", 0) or 0),
            latency_ms=latency_ms,
            status_code=response.status_code,
        )
        return JSONResponse(status_code=response.status_code, content=body)

    def _select_running_instance(self, model_id: str) -> ModelInstance:
        instances = list(
            self.db.scalars(
                select(ModelInstance)
                .where(ModelInstance.model_id == model_id, ModelInstance.status == "running")
                .order_by(ModelInstance.started_at.asc())
            )
        )
        if not instances:
            raise APIError("Model is not deployed", status_code=409, code=40906)
        with AIService._rr_lock:
            index = AIService._rr_counters[model_id] % len(instances)
            AIService._rr_counters[model_id] += 1
        return instances[index]

    async def _stream_proxy(
        self,
        instance: ModelInstance,
        endpoint: str,
        payload: dict,
        user: User,
        api_key: str,
        start: float,
    ) -> AsyncIterator[bytes]:
        status_code = 200
        prompt_tokens = 0
        completion_tokens = 0
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("POST", f"{instance.api_endpoint}{endpoint}", json=payload) as response:
                    status_code = response.status_code
                    if response.status_code >= 400:
                        error_body = await response.aread()
                        raise APIError(
                            f"Upstream model error: {error_body.decode('utf-8', errors='ignore')}",
                            status_code=response.status_code,
                            code=50204,
                        )
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            usage = self._extract_usage_from_chunk(chunk)
                            if usage:
                                prompt_tokens = int(usage.get("prompt_tokens", prompt_tokens) or prompt_tokens)
                                completion_tokens = int(
                                    usage.get("completion_tokens", completion_tokens) or completion_tokens
                                )
                            yield chunk
        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)
            self._record_api_call(
                user_id=user.id,
                api_key=api_key,
                model_name=payload.get("model"),
                endpoint=endpoint,
                tokens_input=prompt_tokens,
                tokens_output=completion_tokens,
                latency_ms=latency_ms,
                status_code=status_code,
            )

    def _record_api_call(
        self,
        user_id: str,
        api_key: str,
        model_name: str | None,
        endpoint: str,
        tokens_input: int,
        tokens_output: int,
        latency_ms: int,
        status_code: int,
    ) -> None:
        api_call = ApiCall(
            user_id=user_id,
            api_key=api_key,
            model_name=model_name,
            endpoint=endpoint,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
            status_code=status_code,
        )
        self.db.add(api_call)
        self.db.commit()

    @staticmethod
    def _parse_response_body(response: httpx.Response):
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type.lower():
            return response.json()
        text = response.text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}

    @staticmethod
    def _extract_usage_from_chunk(chunk: bytes) -> dict | None:
        text = chunk.decode("utf-8", errors="ignore")
        for line in text.splitlines():
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                continue
            usage = data.get("usage")
            if isinstance(usage, dict):
                return usage
        return None
