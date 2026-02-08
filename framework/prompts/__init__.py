"""
提示词模块
Prompts Module

支持的场景 (Supported Scenarios):
  ✓ online_education         - 在线教育平台客服
  ✓ ecommerce_refund        - 电商退款
  ✓ telecom_package         - 电信套餐办理
  ✓ property_service        - 物业服务
  ✓ logistics_delivery      - 快递物流
  ✓ airline_refund         - 在线航司改签退票

结构说明:
- 每个场景的提示词定义在对应的 {scenario_id}_prompts.py 中
"""

from .online_education_prompts import (
    AGENT_SYSTEM_PROMPT,
    USER_SYSTEM_PROMPT_TEMPLATE,
    USER_INTENT_PROMPTS,
    AGENT_RESPONSE_PROMPTS,
    EVALUATION_CRITERIA,
    INITIAL_STATE_EXAMPLES,
    get_user_prompt_for_intent,
    get_initial_state_for_intent,
    get_initial_messages_for_intent,
    get_agent_response_prompt,
)

from . import ecommerce_refund_prompts
from . import telecom_package_prompts
from . import property_service_prompts
from . import logistics_delivery_prompts
from . import airline_refund_prompts

__all__ = [
    "AGENT_SYSTEM_PROMPT",
    "USER_SYSTEM_PROMPT_TEMPLATE",
    "USER_INTENT_PROMPTS",
    "AGENT_RESPONSE_PROMPTS",
    "EVALUATION_CRITERIA",
    "INITIAL_STATE_EXAMPLES",
    "get_user_prompt_for_intent",
    "get_initial_state_for_intent",
    "get_initial_messages_for_intent",
    "get_agent_response_prompt",
]
