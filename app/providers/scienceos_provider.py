# app/providers/scienceos_provider.py

import httpx
import json
import uuid
import time
import traceback
from typing import Dict, Any, AsyncGenerator

from fastapi.responses import StreamingResponse, JSONResponse

from app.providers.base import BaseProvider
from app.core.config import settings

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScienceOSProvider(BaseProvider):
    """
    ScienceOS Provider
    - 实现了将 ScienceOS 的流式响应转换为 OpenAI 格式的 SSE 流。
    """
    API_URL = "https://app.scienceos.ai/api/chat"
    
    async def chat_completion(self, request_data: Dict[str, Any]) -> StreamingResponse | JSONResponse:
        """
        处理聊天补全请求，支持流式和非流式。
        """
        is_stream = request_data.get("stream", False)
        
        if is_stream:
            return StreamingResponse(
                self._stream_generator(request_data),
                media_type="text/event-stream"
            )
        else:
            # 非流式支持可以后续实现，当前主要关注流式
            return JSONResponse(
                content={"error": {"message": "Non-streaming is not yet supported.", "type": "unsupported_feature"}},
                status_code=400
            )

    def _prepare_headers(self) -> Dict[str, str]:
        """准备请求头"""
        if not settings.SCIENCEOS_AUTH_TOKEN:
            raise ValueError("SCIENCEOS_AUTH_TOKEN is not set in the environment.")
        
        return {
            'accept': 'text/event-stream',
            'authorization': settings.SCIENCEOS_AUTH_TOKEN,
            'content-type': 'application/json',
            'origin': 'https://app.scienceos.ai',
            'referer': 'https://app.scienceos.ai/chat',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        }

    def _prepare_payload(self, request_data: Dict[str, Any]) -> str:
        """准备请求体"""
        messages = request_data.get("messages", [])
        # ScienceOS API 需要完整的消息历史
        return json.dumps(messages, ensure_ascii=False)

    async def _stream_generator(self, request_data: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        流式生成器，连接到 ScienceOS API 并转换响应。
        """
        chat_id = f"chatcmpl-{uuid.uuid4().hex}"
        model_name = request_data.get("model", "scienceos-model")
        
        # ScienceOS 需要在 URL 中包含动态 ID
        url_params = {
            "chat_id": uuid.uuid4().hex,
            "thread_id": uuid.uuid4().hex,
            "message_id": uuid.uuid4().hex
        }
        
        try:
            headers = self._prepare_headers()
            payload = self._prepare_payload(request_data)
            
            async with httpx.AsyncClient(timeout=180) as client:
                async with client.stream("POST", self.API_URL, headers=headers, params=url_params, content=payload) as response:
                    response.raise_for_status()
                    
                    is_first_chunk = True
                    
                    async for line in response.aiter_lines():
                        if not line.startswith('data:'):
                            continue
                        
                        raw_data_str = line.strip()[len('data:'):].strip()
                        
                        if not raw_data_str or raw_data_str == "[DONE]":
                            continue
                        
                        try:
                            # 检查是否是元数据事件
                            if raw_data_str.startswith('{') and '"event": "followups"' in raw_data_str:
                                logger.info(f"Ignoring metadata event: {raw_data_str}")
                                continue

                            # 解析 JSON 编码的字符串内容
                            delta_content = json.loads(raw_data_str)
                            
                            if not isinstance(delta_content, str):
                                logger.warning(f"Received non-string data chunk, skipping: {delta_content}")
                                continue

                            # 第一次发送角色信息
                            if is_first_chunk:
                                role_chunk = {
                                    "id": chat_id, "object": "chat.completion.chunk", "created": int(time.time()), "model": model_name,
                                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
                                }
                                yield f"data: {json.dumps(role_chunk, ensure_ascii=False)}\n\n"
                                is_first_chunk = False

                            # 发送内容增量
                            openai_chunk = {
                                "id": chat_id, "object": "chat.completion.chunk", "created": int(time.time()), "model": model_name,
                                "choices": [{"index": 0, "delta": {"content": delta_content}, "finish_reason": None}]
                            }
                            yield f"data: {json.dumps(openai_chunk, ensure_ascii=False)}\n\n"
                            
                        except json.JSONDecodeError:
                            logger.warning(f"JSON decode failed for line: {raw_data_str}")
                            continue
            
            # 发送流结束标志
            final_chunk = {
                "id": chat_id, "object": "chat.completion.chunk", "created": int(time.time()), "model": model_name,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            }
            yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Error in stream generator: {e}")
            traceback.print_exc()
            error_content = {"error": {"message": str(e), "type": "stream_error"}}
            yield f"data: {json.dumps(error_content, ensure_ascii=False)}\n\n"
        
        finally:
            logger.info("Stream finished.")
            yield "data: [DONE]\n\n"

