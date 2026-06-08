"""
多模型API统一接入层
OpenAI兼容格式 与 Anthropic格式 两种API协议
自动根据用户填入的 anthropic_base_url 判断使用哪种协议
"""
import json
import time
import asyncio
import httpx
from typing import Optional

from .models import ModelConfig, Message, MessageRole


class ApiClient:
    """
    统一API调用客户端
    自动根据填入的URL类型选择正确的协议格式
    """

    def __init__(self, config: ModelConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=300.0)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    def _has_anthropic_url(self) -> bool:
        url = self.config.anthropic_base_url
        if not url:
            return False
        return bool(url.strip())

    def _ensure_api_key(self) -> str:
        """获取 api_key, 若项目配置中为空则从 config.yaml 全局默认值回填"""
        key = (self.config.api_key or "").strip()
        if key:
            return key
        # 回填: 尝试从 config.yaml 同角色的默认配置取 api_key
        try:
            from ..config.settings import settings
            for rid in ["MX1", "MX2", "MX3", "MX0"]:
                dr = settings.default_roles.get(rid, {})
                dr_url_openai = (dr.get("openai_base_url", "") or "").strip()
                dr_url_anthro = (dr.get("anthropic_base_url", "") or "").strip()
                cfg_url_openai = (self.config.openai_base_url or "").strip()
                cfg_url_anthro = (self.config.anthropic_base_url or "").strip()
                # 通过 URL 匹配找到对应角色的默认 api_key
                if ((dr_url_openai and dr_url_openai == cfg_url_openai)
                    or (dr_url_anthro and dr_url_anthro == cfg_url_anthro)
                    or (dr.get("model", "") == self.config.model)):
                    fallback = (dr.get("api_key", "") or "").strip()
                    if fallback:
                        self.config.api_key = fallback
                        return fallback
        except Exception:
            pass
        return ""

    def _build_openai_request(self, messages: list[Message],
                              system_prompt: str = "") -> tuple:
        """构建OpenAI兼容格式请求（参照接口文档）

        注意：使用 max_tokens 而非 max_completion_tokens，
        因为很多 OpenAI 兼容代理不支持 max_completion_tokens 参数。
        """
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })

        body = {
            "model": self.config.model,
            "temperature": min(self.config.temperature, 2.0),
            "max_tokens": min(self.config.max_output_tokens, 16384),
            "messages": formatted_messages,
            "stream": False,
        }
        if system_prompt:
            body["messages"].insert(0, {"role": "system", "content": system_prompt})

        openai_url = self.config.openai_base_url or ""
        base_url = openai_url.strip() or "https://api.openai.com/v1"
        api_key = self._ensure_api_key()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        return body, endpoint, headers

    def _build_anthropic_request(self, messages: list[Message],
                                 system_prompt: str = "") -> tuple:
        """构建Anthropic格式请求

        关键：Anthropic协议不允许 messages 数组中出现 system 角色，
        所有 system 角色消息必须合并到顶层的 system 字段中。
        此外，Anthropic temperature 范围为 0~1.0，
        max_tokens 上限因模型而异，这里取保守值 16384。
        """
        # 分离 system 消息和非 system 消息
        system_parts = []
        formatted_messages = []
        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_parts.append(msg.content)
            else:
                formatted_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })

        # 合并 system_prompt 和所有 system 消息到顶层 system 字段
        combined_system = system_prompt
        if system_parts:
            extra_system = "\n".join(system_parts)
            combined_system = f"{combined_system}\n{extra_system}" if combined_system else extra_system

        body = {
            "model": self.config.model,
            "max_tokens": min(self.config.max_output_tokens, 16384),
            "temperature": min(self.config.temperature, 1.0),
            "messages": formatted_messages,
            "stream": False,
        }
        if combined_system:
            body["system"] = combined_system

        anthropic_url = self.config.anthropic_base_url or ""
        base_url = anthropic_url.strip() or "https://api.anthropic.com"
        # 确保base_url以/v1结尾（Anthropic API需要/v1/messages）
        if not base_url.rstrip('/').endswith('/v1'):
            base_url = base_url.rstrip('/') + '/v1'

        api_key = self._ensure_api_key()
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        endpoint = f"{base_url.rstrip('/')}/messages"
        return body, endpoint, headers

    def _extract_openai_response(self, data: dict) -> str:
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""

    def _extract_anthropic_response(self, data: dict) -> str:
        content_list = data.get("content", [])
        if content_list:
            return content_list[0].get("text", "")
        return ""

    async def test_connection(self) -> dict:
        """
        测试模型连接状态
        :return: {"ok": bool, "model": 模型名, "latency": 毫秒, "error": 错误信息}
        """
        use_anthropic = self._has_anthropic_url()
        start = time.time()
        test_client = httpx.AsyncClient(timeout=30.0)
        try:
            # 发送前检查 api_key
            api_key = self._ensure_api_key()
            if not api_key:
                return {"ok": False, "model": self.config.model,
                        "latency": 0,
                        "error": "API Key 为空，请先在设置中配置 API Key"}

            body, endpoint, headers = (
                self._build_anthropic_request(
                    [Message(role=MessageRole.USER, content="ping")], ""
                ) if use_anthropic else
                self._build_openai_request(
                    [Message(role=MessageRole.USER, content="ping")], ""
                )
            )
            response = await test_client.post(endpoint, headers=headers, json=body)
            latency = round((time.time() - start) * 1000)
            if response.status_code >= 400:
                error_body = response.text[:500]
                return {"ok": False, "model": self.config.model,
                        "latency": latency,
                        "error": f"HTTP {response.status_code}: {error_body}"}
            return {"ok": True, "model": self.config.model,
                    "latency": latency, "error": ""}
        except Exception as e:
            latency = round((time.time() - start) * 1000)
            return {"ok": False, "model": self.config.model,
                    "latency": latency, "error": str(e)}
        finally:
            await test_client.aclose()

    async def call(self, messages: list[Message],
                   system_prompt: str = "",
                   max_retries: int = 3) -> dict:
        """
        调用模型API
        :return: {"content": 文本, "tokens": Token数, "model": 模型名}
        """
        use_anthropic = self._has_anthropic_url()
        last_error = None

        # 发送前检查 api_key
        api_key = self._ensure_api_key()
        if not api_key:
            return {"content": "[API调用失败] API Key 为空，请先在设置中配置 API Key",
                    "tokens": 0, "model": self.config.model}

        for attempt in range(max_retries):
            try:
                client = await self._get_client()

                if use_anthropic:
                    body, endpoint, headers = self._build_anthropic_request(
                        messages, system_prompt)
                else:
                    body, endpoint, headers = self._build_openai_request(
                        messages, system_prompt)

                response = await client.post(endpoint, headers=headers, json=body)

                if response.status_code >= 400:
                    error_text = response.text[:500]
                    raise Exception(
                        f"HTTP {response.status_code}: {error_text}")

                data = response.json()

                if use_anthropic:
                    content = self._extract_anthropic_response(data)
                else:
                    content = self._extract_openai_response(data)

                usage = data.get("usage", {})
                tokens = usage.get("total_tokens",
                                   usage.get("input_tokens",
                                             usage.get("inputTokenCount", 0)))

                return {
                    "content": content,
                    "tokens": tokens,
                    "model": self.config.model,
                }

            except Exception as e:
                last_error = str(e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

        return {
            "content": f"[API调用失败] {last_error}",
            "tokens": 0,
            "model": self.config.model,
        }
