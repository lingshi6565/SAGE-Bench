#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM客户端集成
LLM Client Integration

支持两种方式调用LLM：
1. vLLM本地部署
2. API接口调用 (OpenAI兼容或其他API)
"""

import json
import requests
import time
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM响应"""
    text: str                           # 生成的文本
    model: str                          # 使用的模型
    tokens: int = 0                     # token数
    metadata: Dict[str, Any] = None     # 额外元数据


class LLMClient(ABC):
    """LLM客户端抽象基类"""
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> LLMResponse:
        """生成文本"""
        pass


class VLLMLocalClient(LLMClient):
    """
    vLLM本地客户端
    
    使用方式：
    1. 启动vLLM服务：
       python -m vllm.entrypoints.openai.api_server \
           --model /path/to/model \
           --port 8000 \
           --tensor-parallel-size 4
    
    2. 创建客户端：
       client = VLLMLocalClient(
           base_url="http://localhost:8000",
           model_name="your-model"
       )
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        model_name: str = "default",
        api_key: str = "EMPTY",
        timeout: int = 300,
        max_retries: int = 3,
    ):
        """
        初始化vLLM本地客户端
        
        Args:
            base_url: vLLM服务器URL
            model_name: 模型名称
            api_key: API密钥 (vLLM通常为EMPTY)
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
    
    def _filter_think_tags(self, text: str) -> str:
        """
        过滤 Qwen3 think 模式的 <think> 标签内容
        仅保留实际输出，移除思考过程
        
        Args:
            text: 原始文本
            
        Returns:
            str: 过滤后的文本
        """
        import re
        
        # 移除 <think>...</think> 标签及其内容
        # 同时移除标签前后可能的空白字符，避免留下多余的换行
        filtered_text = re.sub(r'\s*<think[^>]*>.*?</think>\s*', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除其他常见的思考标签（如果有）
        filtered_text = re.sub(r'\s*<user_think[^>]*>.*?</user_think>\s*', '', filtered_text, flags=re.DOTALL | re.IGNORECASE)
        
        # 清理开头和结尾的空白字符
        filtered_text = filtered_text.strip()
        
        return filtered_text
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.95,
        **kwargs
    ) -> LLMResponse:
        """
        生成文本
        
        Args:
            prompt: 输入提示词
            temperature: 采样温度
            max_tokens: 最大生成token数
            top_p: nucleus采样参数
            **kwargs: 其他参数
            
        Returns:
            LLMResponse: 生成的响应
        """
        url = f"{self.base_url}/v1/completions"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stop": kwargs.get("stop", None),
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # 重试逻辑
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                
                data = response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    text = data["choices"][0]["text"]
                    tokens = data.get("usage", {}).get("completion_tokens", 0)
                    
                    # 过滤 Qwen3 think 模式的 <think> 标签内容（仅保留实际输出）
                    text = self._filter_think_tags(text)
                    
                    return LLMResponse(
                        text=text,
                        model=self.model_name,
                        tokens=tokens,
                        metadata={
                            "finish_reason": data["choices"][0].get("finish_reason"),
                        }
                    )
                else:
                    raise ValueError("No choices in response")
            
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
            
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error on attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
            
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
        
        raise RuntimeError(f"Failed to generate after {self.max_retries} attempts")


class VLLMChatClient(LLMClient):
    """vLLM聊天格式客户端"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        model_name: str = "default",
        api_key: str = "EMPTY",
        timeout: int = 300,
        max_retries: int = 3,
    ):
        """初始化vLLM聊天客户端"""
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
    
    def _filter_think_tags(self, text: str) -> str:
        """
        过滤 Qwen3 think 模式的 <think> 标签内容
        仅保留实际输出，移除思考过程
        
        Args:
            text: 原始文本
            
        Returns:
            str: 过滤后的文本
        """
        import re
        
        # 移除 <think>...</think> 标签及其内容
        # 同时移除标签前后可能的空白字符，避免留下多余的换行
        filtered_text = re.sub(r'\s*<think[^>]*>.*?</think>\s*', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除其他常见的思考标签（如果有）
        filtered_text = re.sub(r'\s*<user_think[^>]*>.*?</user_think>\s*', '', filtered_text, flags=re.DOTALL | re.IGNORECASE)
        
        # 清理开头和结尾的空白字符
        filtered_text = filtered_text.strip()
        
        return filtered_text
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.95,
        messages: Optional[list] = None,
        **kwargs
    ) -> LLMResponse:
        """
        生成文本 (聊天格式)
        
        Args:
            prompt: 输入提示词 (如果messages为None则使用)
            temperature: 采样温度
            max_tokens: 最大生成token数
            top_p: nucleus采样参数
            messages: 消息列表 [{role, content}, ...]
            **kwargs: 其他参数
            
        Returns:
            LLMResponse: 生成的响应
        """
        url = f"{self.base_url}/v1/chat/completions"
        
        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }
        
        # Qwen3模型:thinking模式应该在vLLM服务器启动时通过--chat-template-kwargs参数禁用
        # API调用时通过extra_body传递该参数无效,vLLM不支持运行时动态修改chat_template_kwargs
        # 参考: run.sh中的start_server_single函数会在启动时自动为Qwen3添加--chat-template-kwargs参数
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        for attempt in range(self.max_retries):
            try:
                # 调试信息：第一次尝试时打印请求详情
                # if attempt == 0:
                #     logger.debug(f"vLLM请求: URL={url}, Model={self.model_name}, Message数={len(messages)}")
                
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                
                data = response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    text = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get("completion_tokens", 0)
                    
                    # 过滤 Qwen3 think 模式的 <think> 标签内容（仅保留实际输出）
                    text = self._filter_think_tags(text)
                    
                    return LLMResponse(
                        text=text,
                        model=self.model_name,
                        tokens=tokens,
                        metadata={
                            "finish_reason": data["choices"][0].get("finish_reason"),
                        }
                    )
                else:
                    raise ValueError("No choices in response")
            
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"Error on attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning(f"Rate limit exceeded (429) on attempt {attempt + 1}/{self.max_retries}. Waiting 120 seconds...")
                    if attempt < self.max_retries - 1:
                        time.sleep(120)
                        continue
                    else:
                        raise
                
                logger.error(f"HTTP error on attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
            
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}/{self.max_retries}: URL={url}, Model={self.model_name}, Error={e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
        
        raise RuntimeError(f"Failed to generate after {self.max_retries} attempts")


class OpenAIAPIClient(LLMClient):
    """
    OpenAI兼容API客户端
    
    支持：
    - OpenAI官方API
    - 任何OpenAI兼容的API (如LM Studio, Ollama等)
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model_name: str = "gpt-3.5-turbo",
        timeout: int = 300,
        max_retries: int = 3,
    ):
        """
        初始化OpenAI兼容API客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model_name: 模型名称
            timeout: 请求超时时间
            max_retries: 最大重试次数
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.max_retries = max_retries
    
    def _filter_think_tags(self, text: str) -> str:
        """
        过滤 Qwen3 think 模式的 <think> 标签内容
        仅保留实际输出，移除思考过程
        
        Args:
            text: 原始文本
            
        Returns:
            str: 过滤后的文本
        """
        import re
        
        # 移除 <think>...</think> 标签及其内容
        # 同时移除标签前后可能的空白字符，避免留下多余的换行
        filtered_text = re.sub(r'\s*<think[^>]*>.*?</think>\s*', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除其他常见的思考标签（如果有）
        filtered_text = re.sub(r'\s*<user_think[^>]*>.*?</user_think>\s*', '', filtered_text, flags=re.DOTALL | re.IGNORECASE)
        
        # 清理开头和结尾的空白字符
        filtered_text = filtered_text.strip()
        
        return filtered_text
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        top_p: float = 0.95,
        messages: Optional[list] = None,
        **kwargs
    ) -> LLMResponse:
        """生成文本 (聊天格式)"""
        url = f"{self.base_url}/chat/completions"
        
        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        
        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                
                data = response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    text = data["choices"][0]["message"]["content"]
                    tokens = data.get("usage", {}).get("completion_tokens", 0)
                    
                    # 过滤 Qwen3 think 模式的 <think> 标签内容（仅保留实际输出）
                    text = self._filter_think_tags(text)
                    
                    return LLMResponse(
                        text=text,
                        model=self.model_name,
                        tokens=tokens,
                    )
                else:
                    raise ValueError("No choices in response")
            
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.warning(f"Rate limit exceeded (429) on attempt {attempt + 1}/{self.max_retries}. Waiting 120 seconds...")
                    if attempt < self.max_retries - 1:
                        time.sleep(120)
                        continue
                    else:
                        raise
                
                logger.error(f"HTTP error on attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
            
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1}/{self.max_retries}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise
        
        raise RuntimeError(f"Failed to generate after {self.max_retries} attempts")


def get_llm_client(
    client_type: str,
    **config
) -> LLMClient:
    """
    工厂函数 - 根据类型创建LLM客户端
    
    Args:
        client_type: 客户端类型
            - "vllm_local": vLLM本地 (completions格式)
            - "vllm_chat": vLLM本地 (chat格式)
            - "openai_api": OpenAI兼容API
            - "openai": OpenAI官方API
        **config: 客户端配置参数
        
    Returns:
        LLMClient: LLM客户端实例
    """
    if client_type == "vllm_local":
        return VLLMLocalClient(**config)
    elif client_type == "vllm_chat":
        return VLLMChatClient(**config)
    elif client_type in ["openai_api", "openai"]:
        return OpenAIAPIClient(**config)
    else:
        raise ValueError(f"Unknown client type: {client_type}")


# 示例配置
EXAMPLE_CONFIG = {
    # vLLM本地配置示例
    "vllm_local": {
        "base_url": "http://localhost:8000",
        "model_name": "Qwen/Qwen2.5-14B-Instruct",
        "timeout": 300,
    },
    # OpenAI API配置示例
    "openai_api": {
        "api_key": "sk-xxx",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-3.5-turbo",
        "timeout": 300,
    },
}
