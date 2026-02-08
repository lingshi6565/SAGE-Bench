"""
LLM集成模块
LLM Integration Module

支持：
- vLLM本地部署
- OpenAI API
- 其他兼容API

提供：
- LLM客户端
- LLM驱动的用户模型
- LLM评判模型
"""

from .llm_client import (
    LLMClient,
    VLLMLocalClient,
    VLLMChatClient,
    OpenAIAPIClient,
    LLMResponse,
    get_llm_client,
    EXAMPLE_CONFIG,
)

from .llm_user_model import (
    LLMUserModel,
    LLMUserMessageGenerator,
)

from .llm_judge import (
    LLMJudge,
    MultiModelJudge,
    MultiModelVotingJudge,
)

__all__ = [
    "LLMClient",
    "VLLMLocalClient",
    "VLLMChatClient",
    "OpenAIAPIClient",
    "LLMResponse",
    "get_llm_client",
    "EXAMPLE_CONFIG",
    "LLMUserModel",
    "LLMUserMessageGenerator",
    "LLMJudge",
    "MultiModelJudge",
    "MultiModelVotingJudge",
]
