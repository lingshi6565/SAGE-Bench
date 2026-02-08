#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM集成的用户模型
LLM-powered User Model

使用LLM生成更自然的用户消息
"""

from typing import Optional, Dict, Any
import json
import logging

from ..models import UserModel, UserProfile
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class LLMUserModel(UserModel):
    """
    LLM驱动的用户模型
    
    使用LLM生成用户的下一条消息，而不是使用固定的模板
    """
    
    def __init__(
        self,
        profile: UserProfile,
        system_prompt: str = "",
        llm_client: Optional[LLMClient] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ):
        """
        初始化LLM用户模型
        
        Args:
            profile: 用户画像
            system_prompt: 系统提示词
            llm_client: LLM客户端
            temperature: 采样温度
            max_tokens: 最大生成token数
        """
        super().__init__(profile, system_prompt)
        self.llm_client = llm_client
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # 新增: 追踪问题是否已解决
        self.problem_status = "unsolved"  # unsolved, partially_solved, solved
        self.last_courtesy_turn = -1  # 记录上次礼貌性结束的轮次
        
        if llm_client is None:
            logger.warning("No LLM client provided. User message generation may be limited.")
    
    def generate_initial_message(self) -> str:
        """
        生成对话的第一条消息
        
        Returns:
            str: 生成的初始消息
        """
        if not self.llm_client:
            # 没有LLM客户端，返回默认消息
            return "您好，我有个问题想咨询一下。"
        
        # 构建初始消息生成提示词
        prompt = self._build_initial_message_prompt()
        
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            message = response.text.strip()
            
            # 清理生成的消息
            message = self._clean_generated_message(message)
            
            return message
        
        except Exception as e:
            logger.error(f"Error generating initial user message: {e}")
            return "您好，我有个问题想咨询一下。"
    
    def generate_next_message(
        self,
        agent_last_message: str,
        turn_count: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        使用LLM生成用户的下一条消息
        
        Args:
            agent_last_message: 客服最后的消息
            turn_count: 当前轮次
            context: 额外的上下文信息
            
        Returns:
            str: 生成的用户消息
        """
        if not self.llm_client:
            # 没有LLM客户端，返回默认消息
            return self._default_next_message(agent_last_message, turn_count)
        
        # 构建生成提示词
        prompt = self._build_generation_prompt(
            agent_last_message=agent_last_message,
            turn_count=turn_count,
            context=context,
        )
        
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            message = response.text.strip()
            
            # 清理生成的消息
            message = self._clean_generated_message(message)
            
            return message
        
        except Exception as e:
            logger.error(f"Error generating user message: {e}")
            return self._default_next_message(agent_last_message, turn_count)
    
    def _get_role_description(self) -> str:
        """
        根据场景获取人物身份描述
        
        Returns:
            str: 人物身份描述
        """
        scenario_id = self.profile.scenario_id
        role_descriptions = {
            "online_education": "一名在线教育学员",
            "ecommerce_refund": "一名电商平台的买家",
            "telecom_package": "一名电信运营商的客户",
            "property_service": "一名物业管理区域的住户",
            "logistics_delivery": "一名期待收货的寄件人或收件人",
            "airline_refund": "一名航空公司的乘客",
        }
        return role_descriptions.get(scenario_id, "一名客户")
    
    def _build_initial_message_prompt(self) -> str:
        """
        构建初始消息生成的提示词
        支持多个场景: online_education, ecommerce_refund, telecom_package, 
                   property_service, logistics_delivery, airline_refund
        
        Returns:
            str: 初始消息生成提示词
        """
        # 根据对抗强度确定语气引导
        intensity_guidance = {
            "zero_conflict": "友好礼貌，但简洁直接",
            "weak_conflict": "礼貌但带有一些疑虑或急切",
            "strong_conflict": "不满或急躁，语气较强硬"
        }
        intensity_desc = intensity_guidance.get(self.profile.adversarial_intensity, "正常交互")
        
        # 根据场景选择人物身份
        scenario_id = self.profile.scenario_id
        role_desc = self._get_role_description()
        
        prompt = f"""你正在扮演{role_desc}，准备向客服发起对话。

【你的身份】
- 意图: {self.profile.user_intent}
- 对抗强度: {intensity_desc}
- 情感状态: {self.emotion_state.value}
- 场景: {scenario_id}

【你的背景和问题】
{self.system_prompt}

【要求】
1. 根据你的身份和背景,生成第一条开场消息
2. 消息应该自然、简洁(30-60字),直接表达你的问题或诉求
3. 根据对抗强度调整语气: {intensity_desc}
4. 不要一次性说出所有细节,留待后续对话展开
5. 只返回你要说的话,不要有额外的说明或格式

【你的第一条消息】
"""
        return prompt
    
    def _build_generation_prompt(
        self,
        agent_last_message: str,
        turn_count: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """构建用户消息生成提示词"""
        
        # 构建对话上下文
        dialogue_context = "\n".join([
            f"{'用户' if msg['role'] == 'user' else '客服'}: {msg['content']}"
            for msg in self.dialogue_history[-4:]  # 最近4条消息
        ])
        
        # 根据对抗强度调整指导
        intensity = self.profile.adversarial_intensity
        intensity_guidance = {
            "zero_conflict": "友好配合，表现出信任和耐心",
            "weak_conflict": "有些疑虑但愿意配合，提出合理的问题",
            "strong_conflict": "对立态度，需要证据支撑，可能有些挑剔",
        }
        
        intensity_desc = intensity_guidance.get(intensity, "正常交互")
        
        # 判断问题是否已解决
        self._update_problem_status(agent_last_message)
        
        # 根据问题状态调整prompt
        if self.problem_status == "solved" and turn_count >= 3:
            # 问题已解决且对话至少3轮,应该礼貌结束
            ending_guidance = """
【重要】你的问题已经得到解决！请简短地表示感谢并礼貌地结束对话。
不要再提出新的问题或继续讨论,避免无意义的重复感谢。
可以说："谢谢您的帮助，问题解决了，再见！"或类似的话。
"""
        elif turn_count - self.last_courtesy_turn <= 1 and self.last_courtesy_turn > 0:
            # 如果上一轮已经表示过感谢,这一轮应该结束对话
            ending_guidance = """
【重要】你上一轮已经表示过感谢了，现在应该直接说"再见"结束对话，不要继续重复感谢！
"""
        else:
            ending_guidance = """
【对话策略】
- 如果你的问题已经得到满意的解答,简短感谢后说"再见"结束对话
- 如果还有疑问,继续追问,但要聚焦在核心问题上
- 避免空泛的感谢和祝福,要么提问要么结束
"""
        
        # 根据场景选择人物身份
        scenario_id = self.profile.scenario_id
        role_desc = self._get_role_description()
        
        prompt = f"""你正在扮演{role_desc},继续与客服的对话。

【用户身份】
- 意图: {self.profile.user_intent}
- 对抗强度: {intensity_desc}
- 情感状态: {self.emotion_state.value}
- 满意度: {self.satisfaction_score:.1f}/1.0
- 当前轮次: {turn_count}
- 场景: {scenario_id}

【对话上下文】
{dialogue_context}

【客服最后的消息】
{agent_last_message}

{ending_guidance}

【要求】
1. 根据对话上下文和客服消息生成你的下一条回复
2. 保持角色一致性,但避免过度礼貌导致对话无法结束
3. 回复应该自然、简洁(20-50字),不要过度感谢
4. 根据满意度和情感状态调整态度
5. 只返回你的消息,不要有额外的说明

【你的下一条消息】
"""
        return prompt
    
    def _update_problem_status(self, agent_message: str) -> None:
        """
        根据客服的回复更新问题解决状态
        
        Args:
            agent_message: 客服的回复消息
        """
        agent_msg_lower = agent_message.lower()
        
        # 检测表示问题已解决的关键词
        solved_keywords = [
            '已经解决', '问题解决', '已处理', '已完成', '成功提交',
            '退款已', '已批准', '已通过', '方案已', '资源已分配',
            '祝您学习愉快', '祝您学习顺利', '期待您', '欢迎随时',
            '如果还有其他问题', '如有其他问题', '随时联系我们'
        ]
        
        # 检测表示部分解决的关键词
        partial_keywords = [
            '正在处理', '会尽快', '稍后', '我们会', '预计',
            '建议您', '可以尝试', '先复习', '请您'
        ]
        
        # 检测表示需要更多信息的关键词
        need_info_keywords = [
            '能否', '请问', '可以提供', '具体', '详细',
            '哪个', '什么时候', '如何', '怎么'
        ]
        
        # 判断状态
        if any(keyword in agent_message for keyword in solved_keywords):
            # 客服使用了"祝您学习愉快"等结束语,说明认为问题已处理
            self.problem_status = "solved"
        elif any(keyword in agent_msg_lower for keyword in need_info_keywords):
            # 客服还在询问信息,问题未解决
            self.problem_status = "unsolved"
        elif any(keyword in agent_message for keyword in partial_keywords):
            # 客服说"正在处理",部分解决
            self.problem_status = "partially_solved"
        
        # 如果客服连续2次没有提问,也认为问题基本解决
        if len(self.dialogue_history) >= 4:
            last_two_agent = [
                msg['content'] for msg in self.dialogue_history[-4:]
                if msg['role'] == 'assistant'
            ]
            if len(last_two_agent) >= 2:
                has_questions = any(
                    any(q in msg for q in ['?', '?', '能否', '请问', '可以'])
                    for msg in last_two_agent[-2:]
                )
                if not has_questions and self.problem_status != "unsolved":
                    self.problem_status = "solved"
    
    def _clean_generated_message(self, message: str) -> str:
        """清理生成的消息"""
        # 移除可能的引号
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]
        
        # 移除可能的前缀
        for prefix in ["我:", "用户:", "学员:", "我说:", "我的回复:"]:
            if message.startswith(prefix):
                message = message[len(prefix):].strip()
        
        # 限制长度
        if len(message) > 500:
            message = message[:500]
        
        # 检测是否是礼貌性结束消息
        thank_keywords = ['谢谢', '感谢', 'thank']
        blessing_keywords = ['祝', '顺利', '愉快', '加油', '进步']
        if (any(keyword in message for keyword in thank_keywords) or
            any(keyword in message for keyword in blessing_keywords)):
            # 记录这是一次礼貌性回复
            self.last_courtesy_turn = self.current_turn
        
        return message.strip()
    
    def _default_next_message(self, agent_last_message: str, turn_count: int) -> str:
        """
        默认消息生成（无LLM时）
        支持多个场景: online_education, ecommerce_refund, telecom_package, 
                   property_service, logistics_delivery, airline_refund
        """
        scenario_id = self.profile.scenario_id
        
        # 通用逻辑：根据对话历史和情感推断下一步
        if "能否" in agent_last_message or "可否" in agent_last_message or "?" in agent_last_message:
            # 客服在询问信息
            if scenario_id == "online_education":
                return "我是在学第三章第二节的时候，对函数参数默认值不理解。"
            elif scenario_id == "ecommerce_refund":
                return "这是订单号XXXX，商品已收到但有质量问题。"
            elif scenario_id == "telecom_package":
                return "我当前用的是88元套餐，想了解一下升级到128元套餐的费用。"
            elif scenario_id == "property_service":
                return "我家的厕所漏水问题已经很严重了，能否尽快派人来维修？"
            elif scenario_id == "logistics_delivery":
                return "订单号是12345，寄件地址是北京朝阳区XXX。"
            elif scenario_id == "airline_refund":
                return "我的航班号是CA1234，由于个人原因需要改签。"
            else:
                return "您能详细说明一下具体情况吗？"
        
        if "退费" in agent_last_message or "赔偿" in agent_last_message or "退款" in agent_last_message:
            if self.emotion_state.value == "angry":
                return "我必须要求退款，这是我的权利！"
            else:
                return "能否给我一个合理的解决方案？"
        
        if "安抚" in agent_last_message or "理解" in agent_last_message or "歉意" in agent_last_message:
            self.update_satisfaction(0.1)
            return "谢谢你的耐心帮助。"
        
        if "祝您" in agent_last_message or "再见" in agent_last_message or "有需要" in agent_last_message:
            # 结束话语
            return "谢谢，再见！"
        
        # 默认消息
        return "好的，谢谢你的帮助。"


class LLMUserMessageGenerator:
    """LLM用户消息生成器"""
    
    def __init__(self, llm_client: LLMClient):
        """
        初始化生成器
        
        Args:
            llm_client: LLM客户端
        """
        self.llm_client = llm_client
    
    def __call__(
        self,
        user_model: UserModel,
        agent_last_message: str,
        turn_count: int,
        **kwargs
    ) -> str:
        """
        使该对象可调用，直接调用generate方法
        """
        return self.generate(
            user_model=user_model,
            agent_last_message=agent_last_message,
            turn_count=turn_count,
            **kwargs
        )
    
    def generate(
        self,
        user_model: UserModel,
        agent_last_message: str,
        turn_count: int,
        **kwargs
    ) -> str:
        """
        生成用户的下一条消息
        
        Args:
            user_model: 用户模型
            agent_last_message: 客服最后的消息
            turn_count: 当前轮次
            
        Returns:
            str: 生成的用户消息
        """
        if not isinstance(user_model, LLMUserModel):
            # 如果不是LLMUserModel，创建临时的生成提示词
            prompt = self._build_simple_prompt(
                user_intent=user_model.profile.user_intent,
                dialogue_history=user_model.dialogue_history,
                agent_message=agent_last_message,
                turn_count=turn_count,
            )
        else:
            # 使用LLMUserModel的生成逻辑
            return user_model.generate_next_message(
                agent_last_message=agent_last_message,
                turn_count=turn_count,
            )
        
        try:
            response = self.llm_client.generate(prompt=prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating message: {type(e).__name__}: {e}")
            # 当LLM生成失败时，返回简单但有效的回复
            if turn_count > 2:
                return "好的，我理解了。"
            else:
                return "好的，谢谢。"
    
    def _build_simple_prompt(
        self,
        user_intent: str,
        dialogue_history: list,
        agent_message: str,
        turn_count: int,
    ) -> str:
        """构建简单的生成提示词"""
        dialogue_context = "\n".join([
            f"{'用户' if msg['role'] == 'user' else '客服'}: {msg['content']}"
            for msg in dialogue_history[-4:]
        ])
        
        prompt = f"""继续这个对话。用户意图是"{user_intent}"，生成用户的下一条消息。

【对话历史】
{dialogue_context}

【客服最后的消息】
{agent_message}

只返回用户的下一条消息，不要有任何额外说明。
"""
        return prompt
