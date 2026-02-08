#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
客服模型系统
Agent Model System

负责：
1. 根据用户输入和SOP流程生成客服响应
2. 执行分类、决策、路由等逻辑
3. 输出结构化的决策信息和自然语言回复
4. 跟踪对话流程的正确性
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json
from datetime import datetime


@dataclass
class ClassificationOutput:
    """分类输出 - online_education场景"""
    DescriptionClear: Optional[bool] = None
    QuestionRelevance: Optional[bool] = None
    EmotionTendency: Optional[str] = None
    ResolveDependency: Optional[str] = None
    RepeatedRaised: Optional[bool] = None
    RegardingRefund: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "DescriptionClear": self.DescriptionClear,
            "QuestionRelevance": self.QuestionRelevance,
            "EmotionTendency": self.EmotionTendency,
            "ResolveDependency": self.ResolveDependency,
            "RepeatedRaised": self.RepeatedRaised,
            "RegardingRefund": self.RegardingRefund,
        }


@dataclass
class EcommerceRefundClassification:
    """分类输出 - ecommerce_refund场景"""
    CoreIntention: Optional[str] = None
    ProvidedDocument: Optional[bool] = None
    Responsibility: Optional[str] = None
    RefundReasonable: Optional[str] = None
    EmotionStatus: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "CoreIntention": self.CoreIntention,
            "ProvidedDocument": self.ProvidedDocument,
            "Responsibility": self.Responsibility,
            "RefundReasonable": self.RefundReasonable,
            "EmotionStatus": self.EmotionStatus,
        }


@dataclass
class TelecomPackageClassification:
    """分类输出 - telecom_package场景"""
    ConsumptionType: Optional[str] = None
    ApplicationTendency: Optional[str] = None
    ConsumptionProfile: Optional[str] = None
    EmotionTag: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "ConsumptionType": self.ConsumptionType,
            "ApplicationTendency": self.ApplicationTendency,
            "ConsumptionProfile": self.ConsumptionProfile,
            "EmotionTag": self.EmotionTag,
        }


@dataclass
class PropertyServiceClassification:
    """分类输出 - property_service场景"""
    CoreIntention: Optional[str] = None
    EmotionTag: Optional[str] = None
    RepairItemCategory: Optional[str] = None
    RelatedScope: Optional[str] = None
    EmergencyLevel: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "CoreIntention": self.CoreIntention,
            "EmotionTag": self.EmotionTag,
            "RepairItemCategory": self.RepairItemCategory,
            "RelatedScope": self.RelatedScope,
            "EmergencyLevel": self.EmergencyLevel,
        }


@dataclass
class LogisticsDeliveryClassification:
    """分类输出 - logistics_delivery场景"""
    RiskStatus: Optional[str] = None
    InfoCompleteness: Optional[bool] = None
    UserIntention: Optional[str] = None
    EmotionalState: Optional[str] = None
    EmergencyLevel: Optional[str] = None
    ComplaintValidity: Optional[bool] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "RiskStatus": self.RiskStatus,
            "InfoCompleteness": self.InfoCompleteness,
            "UserIntention": self.UserIntention,
            "EmotionalState": self.EmotionalState,
            "EmergencyLevel": self.EmergencyLevel,
            "ComplaintValidity": self.ComplaintValidity,
        }


@dataclass
class AirlineRefundClassification:
    """分类输出 - airline_refund场景"""
    CoreDemand: Optional[str] = None
    ChangeReason: Optional[str] = None
    UserEmotion: Optional[str] = None
    DocumentValidity: Optional[str] = None
    IsInfoComplete: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "CoreDemand": self.CoreDemand,
            "ChangeReason": self.ChangeReason,
            "UserEmotion": self.UserEmotion,
            "DocumentValidity": self.DocumentValidity,
            "IsInfoComplete": self.IsInfoComplete,
        }


@dataclass
class FinalOutput:
    """最终动作输出
    
    支持通用框架，包含固定字段和场景特定字段。
    固定字段：Action, PLAN, chat
    场景特定字段：在online_education中包含PLAN；在其他场景中可扩展
    
    示例（在线教育场景）：
    {
        "Action": "PLAN",
        "PLAN": "PLAN_A",
        "chat": "根据您的需求，我们为您制定了相应的支持方案。"
    }
    """
    Action: str = ""               # 动作类型: PLAN/REFUND/NEGOTIATE/REVIEW/COMFORT/GUIDE
    PLAN: str = ""                 # PLAN类型的具体方案: PLAN_A/PLAN_B/PLAN_C/PLAN_D/PLAN_E/PLAN_F (当Action非PLAN时为"none")
    
    # 支持场景特定字段（通过extra_fields存储）
    extra_fields: Dict[str, Any] = field(default_factory=dict)  # 场景特定字段存储
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "Action": self.Action,
            "PLAN": self.PLAN,
        }
        # 添加场景特定字段
        result.update(self.extra_fields)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FinalOutput":
        """从字典创建FinalOutput
        
        Args:
            data: 包含Action、PLAN等字段的字典，可能包含场景特定字段
            
        Returns:
            FinalOutput: 实例对象
        """
        action = data.get("Action", "")
        plan = data.get("PLAN", "")
        
        # 提取场景特定字段（除了固定字段之外的所有字段）
        fixed_fields = {"Action", "PLAN"}
        extra_fields = {k: v for k, v in data.items() if k not in fixed_fields}
        
        return cls(
            Action=action,
            PLAN=plan,
            extra_fields=extra_fields,
        )
    
    def set_scenario_field(self, field_name: str, value: Any) -> None:
        """设置场景特定字段
        
        Args:
            field_name: 字段名（如"PLAN"在在线教育场景，其他字段在其他场景）
            value: 字段值
        """
        self.extra_fields[field_name] = value
    
    def get_scenario_field(self, field_name: str, default: Any = None) -> Any:
        """获取场景特定字段
        
        Args:
            field_name: 字段名
            default: 默认值
            
        Returns:
            字段值或默认值
        """
        return self.extra_fields.get(field_name, default)


@dataclass
class AgentTurnOutput:
    """客服单轮输出"""
    turn_id: int                   # 轮次ID
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # 结构化输出
    classification_output: Optional[ClassificationOutput] = None  # 分类结果
    cot: str = ""                  # Chain of Thought - 推理过程
    current_step: str = ""         # 当前SOP步骤
    next_step: Optional[str] = None  # 下一步骤
    
    # 期望路径和最终动作(按新格式要求)
    expected_path: List[str] = field(default_factory=list)  # 按实际流程顺序填写的期望路径
    final_output: Optional[FinalOutput] = None  # 最终动作输出
    
    # 兼容旧格式的字段
    action: str = ""               # 最终动作 (兼容字段)
    action_parameters: Dict[str, Any] = field(default_factory=dict)  # 动作参数 (兼容字段)
    plan: str = ""                 # 资源分配计划 (兼容字段)
    
    # 自然语言输出
    chat: str = ""                 # 客服回复文本
    
    # 路径追踪
    path_taken: List[str] = field(default_factory=list)  # 走过的步骤
    
    # JSON解析状态
    json_parse_failed: bool = False  # 是否JSON解析失败
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典 - 按新格式输出"""
        return {
            "turn_id": self.turn_id,
            "timestamp": self.timestamp,
            "classification_output": self.classification_output.to_dict() if self.classification_output else None,
            "cot": self.cot,
            "expected_path": self.expected_path,  # 新格式：期望路径
            "final_output": self.final_output.to_dict() if self.final_output else None,  # 新格式：最终动作
            "chat": self.chat,
            "path_taken": self.path_taken,
            "json_parse_failed": self.json_parse_failed,  # JSON解析失败标记
        }
    
    def to_dict_legacy(self) -> Dict[str, Any]:
        """转换为字典 - 兼容旧格式"""
        return {
            "turn_id": self.turn_id,
            "timestamp": self.timestamp,
            "classification_output": self.classification_output.to_dict() if self.classification_output else None,
            "cot": self.cot,
            "current_step": self.current_step,
            "next_step": self.next_step,
            "action": self.action,
            "action_parameters": self.action_parameters,
            "plan": self.plan,
            "chat": self.chat,
            "path_taken": self.path_taken,
        }


class AgentModel:
    """
    客服模型 - 基于SOP的多轮对话生成
    
    核心功能：
    1. 维护对话状态和当前SOP步骤
    2. 根据输入进行分类和决策
    3. 遵循SOP流程进行路由
    4. 生成结构化输出和自然语言回复
    """
    
    def __init__(self, scenario_id: str, sop_graph, system_prompt: str = "", 
                 use_llm_for_classification: bool = False, llm_client=None,
                 use_llm_for_full_output: bool = True):
        """
        初始化客服模型
        
        Args:
            scenario_id: 场景ID
            sop_graph: SOP有向图
            system_prompt: 系统提示词
            use_llm_for_classification: 是否使用LLM进行分类(已废弃,使用use_llm_for_full_output)
            llm_client: LLM客户端 (可选，用于生成完整JSON输出)
            use_llm_for_full_output: 是否使用LLM生成完整JSON输出(classification+path+finals+chat)
        """
        self.scenario_id = scenario_id
        self.sop_graph = sop_graph
        self.system_prompt = system_prompt
        self.use_llm_for_classification = use_llm_for_classification  # 保留兼容性
        self.use_llm_for_full_output = use_llm_for_full_output
        self.llm_client = llm_client
        
        # 状态管理
        self.current_step = sop_graph.start_node_id
        self.path_taken: List[str] = []  # 标准化路径，不包含start节点
        
        # 对话历史
        self.dialogue_history: List[Dict[str, str]] = []
        self.turn_history: List[AgentTurnOutput] = []
        self.current_turn = 0
        
        # 内部状态
        self.last_classification: Optional[ClassificationOutput] = None
        self.context_data: Dict[str, Any] = {}
    
    def add_user_message(self, message: str) -> None:
        """添加用户消息到对话历史"""
        self.dialogue_history.append({
            "role": "user",
            "content": message
        })
    
    def add_agent_message(self, message: str) -> None:
        """添加客服消息到对话历史"""
        self.dialogue_history.append({
            "role": "assistant",
            "content": message
        })
    
    def get_dialogue_context(self) -> Dict[str, Any]:
        """获取对话上下文"""
        return {
            "scenario_id": self.scenario_id,
            "current_step": self.current_step,
            "path_taken": self.path_taken,
            "dialogue_history": self.dialogue_history,
            "turn_count": self.current_turn,
            "context_data": self.context_data,
        }
    
    def process_turn(
        self,
        user_message: str,
        context_data: Optional[Dict[str, Any]] = None,
        classification_output: Optional[ClassificationOutput] = None
    ) -> AgentTurnOutput:
        """
        处理一轮对话

        Args:
            user_message: 用户消息
            context_data: 上下文数据 (如学员信息、系统信息等)
            classification_output: 分类输出 (可选，如果为None则需要进行分类)

        Returns:
            AgentTurnOutput: 客服单轮输出
        """
        import logging
        
        # 调试日志 - 使用print确保能看到
        # print(f"[DEBUG] === process_turn 开始 ===")
        # print(f"[DEBUG] use_llm_for_full_output: {self.use_llm_for_full_output}")
        # print(f"[DEBUG] llm_client is not None: {self.llm_client is not None}")
        # print(f"[DEBUG] llm_client类型: {type(self.llm_client) if self.llm_client else 'None'}")
        
        # 记录用户消息
        self.add_user_message(user_message)

        # 更新上下文
        if context_data:
            self.context_data.update(context_data)

        # 创建本轮输出
        turn_output = AgentTurnOutput(turn_id=self.current_turn)

        # 如果使用LLM生成完整输出
        # print(f"[DEBUG] 检查条件: use_llm={self.use_llm_for_full_output} and llm_client={self.llm_client is not None}")
        if self.use_llm_for_full_output and self.llm_client:
            # print("[DEBUG] 条件满足,调用_process_turn_with_llm")
            return self._process_turn_with_llm(user_message, context_data, turn_output)
        # else:
        #     print(f"[DEBUG] ❌ 条件不满足! use_llm={self.use_llm_for_full_output}, has_client={self.llm_client is not None}")
        #     print(f"[DEBUG] 将使用规则引擎而不是LLM")

        # 输出为空，就是空
        # 分类处理
        if classification_output is None:
            classification_output = {}
            # self._classify_input(user_message, context_data) # 规则引擎(旧逻辑)

        turn_output.classification_output = classification_output
        self.last_classification = classification_output

        # 获取当前步骤节点
        current_node = self.sop_graph.nodes[self.current_step]
        turn_output.current_step = current_node.step_name

        # 记录当前节点到路径（只记录决策节点和步骤节点，不记录action节点）
        node_type = current_node.node_type
        if node_type.value in ['decision', 'action']:
            # 只记录有实际意义的节点（step1, step2... 或 action_review, action_plan 等）
            if current_node.node_id != 'start' and current_node.node_id not in self.path_taken:
                self.path_taken.append(current_node.node_id)

        # 处理决策 (下一步骤)
        next_steps = self.sop_graph.get_next_nodes(self.current_step)

        if len(next_steps) > 1:
            # 多个后继节点 - 需要根据条件选择
            next_node_id, decision = self._make_decision(next_steps, classification_output)
        elif len(next_steps) == 1:
            # 单个后继节点 - 直接跳转
            next_node_id, transition_label = next_steps[0]
            decision = "auto"
        else:
            # 没有后继节点 - 流程结束
            next_node_id = None
            decision = "end"

        # 更新步骤
        if next_node_id:
            self.current_step = next_node_id
            next_node = self.sop_graph.nodes[next_node_id]
            turn_output.next_step = next_node.step_name

            # 生成动作和回复
            if next_node.action_name:
                turn_output.action = next_node.action_name
                turn_output.action_parameters = next_node.parameters
                
                # 生成新格式的最终动作输出
                plan_value = "none"
                action_value = next_node.action_name
                
                # 如果是PLAN动作，从参数中获取PLAN类型
                if next_node.action_name == "PLAN" and next_node.parameters:
                    plan_value = next_node.parameters.get("plan_type", "PLAN_A")
                
                turn_output.final_output = FinalOutput(
                    Action=action_value,
                    PLAN=plan_value
                )
        
        # 如果当前节点没有动作(还在中间步骤),根据分类结果预测最终动作
        # 注意:这里不能使用规则引擎,因为要评测模型自己的决策能力
        if turn_output.final_output is None:
            turn_output.final_output = self._predict_final_output_from_classification(
                classification_output,
                context_data
            )

        # 记录最终路径和期望路径
        turn_output.path_taken = self.path_taken.copy()
        
        # 生成期望路径（从step1开始的完整路径,而不是从当前节点开始）
        turn_output.expected_path = self._generate_expected_path(
            classification_output,
            self.sop_graph.start_node_id  # 从start节点开始,确保生成完整路径
        )

        # 生成Chain of Thought
        turn_output.cot = self._generate_cot(
            current_node, classification_output, decision, next_node_id
        )

        # 生成自然语言回复
        turn_output.chat = self._generate_response(
            user_message, classification_output, turn_output.action, context_data
        )

        # 记录回复
        self.add_agent_message(turn_output.chat)

        # 保存到历史
        self.turn_history.append(turn_output)
        self.current_turn += 1

        return turn_output
    
    # def _classify_input(
    #     self,
    #     user_message: str,
    #     context_data: Optional[Dict[str, Any]] = None
    # ) -> ClassificationOutput:
    #     """
    #     分类输入 - 根据用户消息和上下文进行分类

    #     分类字段说明:
    #     1. DescriptionClear: 问题描述清晰度 (True/False)
    #     2. QuestionRelevance: 问题与课程关联性 (True/False)
    #     3. EmotionTendency: 学员情绪倾向 ("Calm"/"Dissatisfied")
    #     4. ResolveDependency: 问题解决依赖度 ("LowDependency"/"MediumDependency"/"HighDependency")
    #     5. RepeatedRaised: 问题是否重复反馈 (True/False)
    #     6. RegardingRefund: 是否涉及退费需求 (True/False)

    #     Args:
    #         user_message: 用户消息
    #         context_data: 上下文数据 (包含学员信息等)

    #     Returns:
    #         ClassificationOutput: 分类结果
    #     """
    #     classification = ClassificationOutput()
    #     user_msg = user_message.lower()

    #     # ========== 1. DescriptionClear (问题描述清晰度) ==========
    #     # 清晰：问题描述具体，有明确的信息
    #     # 不清晰：问题模糊、缺少关键信息
    #     unclear_keywords = ["怎么回事", "什么原因", "不知道", "问一下", "有个问题",
    #                       "我想问一下", "帮我看看", "怎么处理", "怎么办"]
    #     # 只要用户提出了一个具体的问题（即使没有详细描述），也认为问题清晰
    #     # 只有纯模糊的询问才认为不清晰
    #     very_unclear_patterns = ["有个问题", "我想问一下", "请问一下"]

    #     if any(kw in user_msg for kw in very_unclear_patterns) and len(user_msg) < 20:
    #         # 纯模糊询问，问题不清晰
    #         classification.DescriptionClear = False
    #     else:
    #         # 其他情况都认为问题清晰（用户至少表达了一个具体需求）
    #         classification.DescriptionClear = True

    #     # ========== 2. QuestionRelevance (问题与课程关联性) ==========
    #     # 课程相关词汇
    #     course_keywords = ["课程", "学习", "视频", "课时", "讲义", "作业", "考试",
    #                       "证书", "毕业", "学习进度", "课程内容", "上课"]
    #     # 非课程相关词汇
    #     non_course_keywords = ["客服", "电话", "账号", "登录", "密码", "费用",
    #                           "价格", "优惠", "活动", "发票", "退款到账"]

    #     if any(kw in user_msg for kw in course_keywords):
    #         classification.QuestionRelevance = True
    #     elif any(kw in user_msg for kw in non_course_keywords):
    #         classification.QuestionRelevance = False
    #     else:
    #         # 默认认为是课程相关的（在线教育场景）
    #         classification.QuestionRelevance = True

    #     # ========== 3. EmotionTendency (学员情绪倾向) ==========
    #     negative_emotions = ["不满", "生气", "愤怒", "太差", "太差了", "非常不满",
    #                         "投诉", "太差劲", "不满意", "怎么还没", "怎么一直",
    #                         "非常生气", "无语", "坑", "骗子", "虚假"]
    #     calm_indicators = ["请问", "想问一下", "咨询", "了解一下", "帮忙", "谢谢",
    #                       "你好", "在吗", "请教"]

    #     if any(kw in user_msg for kw in negative_emotions):
    #         classification.EmotionTendency = "Dissatisfied"
    #     else:
    #         classification.EmotionTendency = "Calm"

    #     # ========== 4. ResolveDependency (问题解决依赖度) ==========
    #     # HighDependency: 需要专属辅导老师和教学支持组骨干
    #     high_keywords = ["不会", "听不懂", "太难", "跟不上", "需要辅导", "一对一",
    #                     "专门辅导", "深入讲解", "详细解答"]
    #     # MediumDependency: 需要教学支持专员和示例资料
    #     medium_keywords = ["例子", "示例", "资料", "文档", "说明", "讲解",
    #                       "想看看", "有没有"]
    #     # LowDependency: 只需要教学支持专员
    #     low_keywords = ["查一下", "看看", "多少钱", "时间", "进度", "状态"]

    #     if any(kw in user_msg for kw in high_keywords):
    #         classification.ResolveDependency = "HighDependency"
    #     elif any(kw in user_msg for kw in medium_keywords):
    #         classification.ResolveDependency = "MediumDependency"
    #     elif any(kw in user_msg for kw in low_keywords):
    #         classification.ResolveDependency = "LowDependency"
    #     else:
    #         # 默认中等依赖度
    #         classification.ResolveDependency = "MediumDependency"

    #     # ========== 5. RepeatedRaised (问题是否重复反馈) ==========
    #     # 检查上下文中的历史投诉记录
    #     repeated_keywords = ["之前", "上次", "以前", "反映过", "问过", "说过",
    #                         "上次问过", "上次反映"]

    #     if any(kw in user_msg for kw in repeated_keywords):
    #         classification.RepeatedRaised = True
    #     elif context_data and context_data.get("HistoricalComplaintRecords"):
    #         # 如果有历史投诉记录，认为是重复反馈
    #         classification.RepeatedRaised = True
    #     else:
    #         classification.RepeatedRaised = False

    #     # ========== 6. RegardingRefund (是否涉及退费需求) ==========
    #     refund_keywords = ["退费", "退款", "取消", "不学了", "不上了", "钱",
    #                       "费用", "全额退款", "部分退款", "退学费", "要退款",
    #                       "能退吗", "可以退吗", "能不能退", "退多少钱"]

    #     if any(kw in user_msg for kw in refund_keywords):
    #         classification.RegardingRefund = True
    #     else:
    #         classification.RegardingRefund = False

    #     return classification
    
    def _make_decision(
        self,
        next_steps: List[Tuple[str, str]],
        classification_output: ClassificationOutput
    ) -> Tuple[str, str]:
        """
        根据分类结果进行决策
        
        Args:
            next_steps: 可能的后继步骤
            classification_output: 分类结果
            
        Returns:
            Tuple[str, str]: (选择的下一步骤ID, 决策原因)
        """
        # 获取当前步骤的决策字段
        current_node = self.sop_graph.nodes[self.current_step]
        decision_field = current_node.parameters.get("decision_field")
        
        # 根据分类字段值进行决策
        for next_node_id, label in next_steps:
            if self._check_condition(classification_output, decision_field, label):
                return next_node_id, label
        
        # 默认选择第一条边
        return next_steps[0][0], "default"
    
    def _check_condition(
        self,
        classification_output: ClassificationOutput,
        field_name: Optional[str],
        label: str
    ) -> bool:
        """
        检查条件是否满足
        
        Args:
            classification_output: 分类结果
            field_name: 字段名
            label: 边的标签 (如 "true", "false", "Calm", "Dissatisfied")
            
        Returns:
            bool: 条件是否满足
        """
        if not field_name:
            return True
        
        # 获取分类结果中对应字段的值
        field_value = getattr(classification_output, field_name, None)
        
        # 比较值和标签
        if isinstance(field_value, bool):
            return str(field_value).lower() == label.lower()
        else:
            return str(field_value) == label
    
    def _generate_expected_path(
        self,
        classification_output: ClassificationOutput,
        current_node_id: str
    ) -> List[str]:
        """
        根据分类结果和当前步骤生成期望路径
        
        Args:
            classification_output: 分类结果
            current_node_id: 当前节点ID
            
        Returns:
            List[str]: 期望的步骤路径
        """
        # 收集从当前节点开始的所有可能的路径
        expected_path = []
        
        # 模拟前向遍历，根据分类结果选择路径
        node_id = current_node_id
        visited = set()
        max_steps = 20  # 防止无限循环
        step_count = 0
        
        while node_id and step_count < max_steps:
            if node_id in visited:
                break
            visited.add(node_id)
            
            node = self.sop_graph.nodes[node_id]
            
            # 添加到期望路径
            if node_id != 'start':
                expected_path.append(node_id)
            
            # 如果是end节点，停止
            if node_id == 'end':
                break
            
            # 获取下一个节点
            next_steps = self.sop_graph.get_next_nodes(node_id)
            
            if len(next_steps) == 0:
                break
            elif len(next_steps) == 1:
                node_id = next_steps[0][0]
            else:
                # 多个选择，根据分类结果选择
                decision_field = node.parameters.get("decision_field") if hasattr(node, 'parameters') else None
                node_id = None
                for next_node_id, label in next_steps:
                    if self._check_condition(classification_output, 
                                            decision_field,
                                            label):
                        node_id = next_node_id
                        break
                
                # 如果没有匹配的条件，选择第一个
                if node_id is None and next_steps:
                    node_id = next_steps[0][0]
            
            step_count += 1
        
        return expected_path
    
    def _generate_cot(
        self,
        current_node,
        classification_output: ClassificationOutput,
        decision: str,
        next_node_id: Optional[str]
    ) -> str:
        """
        生成Chain of Thought
        
        Args:
            current_node: 当前节点
            classification_output: 分类结果
            decision: 决策
            next_node_id: 下一步骤ID
            
        Returns:
            str: CoT文本
        """
        cot_parts = [
            f"当前步骤: {current_node.step_name}",
            f"分类结果: {classification_output.to_dict()}",
            f"决策: {decision}",
        ]
        
        if next_node_id:
            next_node = self.sop_graph.nodes[next_node_id]
            cot_parts.append(f"下一步骤: {next_node.step_name}")
        
        return " -> ".join(cot_parts)
    
    def _generate_response(
        self,
        user_message: str,
        classification_output: ClassificationOutput,
        action: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成自然语言回复
        
        Args:
            user_message: 用户消息
            classification_output: 分类结果
            action: 动作
            context_data: 上下文数据
            
        Returns:
            str: 回复文本
        """
        # 模板回复 (作为默认降级方案)
        templates = {
            "GUIDE": f"我已收到您的问题。为了更好地帮助您，能否提供更详细的信息？具体是关于哪个课程章节的问题？",
            "COMFORT": f"我非常理解您的感受。我们会认真对待您的问题，并尽快为您解决。",
            "REVIEW": f"感谢您的反馈。我们发现您之前反映过类似问题，我们的专业团队正在进行审核，将尽快给您答复。",
            "PLAN": f"根据您的需求，我们为您制定了相应的支持方案。",
            "REFUND": f"经过审核，您的退款请求已批准。我们将在3个工作日内处理。",
            "NEGOTIATE": f"感谢您的耐心。让我们坐下来讨论最佳的解决方案。",
        }
        
        # 如果配置了LLM客户端，使用LLM生成回复
        if self.llm_client:
            try:
                prompt = self._build_response_prompt(
                    user_message=user_message,
                    classification_output=classification_output,
                    action=action,
                    context_data=context_data
                )
                response = self.llm_client.generate(
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=256,
                )
                return response.text.strip()
            except Exception as e:
                # LLM生成失败，降级到模板
                import logging
                # logging.warning(f"LLM生成客服回复失败: {e}，使用模板回复")
                return templates.get(action, "感谢您的反馈，我们正在处理您的问题。")
        
        # 默认使用模板回复
        return templates.get(action, "感谢您的反馈，我们正在处理您的问题。")
    
    def _build_response_prompt(
        self,
        user_message: str,
        classification_output: ClassificationOutput,
        action: str,
        context_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建客服回复生成提示词（从框架的prompts中获取）"""
        
        from ..prompts import get_agent_response_prompt
        
        # 构建对话上下文
        dialogue_context = "\n".join([
            f"{'用户' if msg['role'] == 'user' else '客服'}: {msg['content']}"
            for msg in self.dialogue_history[-6:]  # 最近6条消息
        ])
        
        # 从框架的prompts中获取对应场景和动作的提示词
        prompt_template = get_agent_response_prompt(
            scenario_id=self.scenario_id,
            action=action or "PLAN"  # 默认使用PLAN动作
        )
        
        # 格式化提示词
        try:
            prompt = prompt_template.format(
                user_message=user_message,
                dialogue_context=dialogue_context,
            )
        except KeyError:
            # 如果格式化失败，使用简单的提示词
            prompt = f"""你是一名专业的客服代表，需要根据用户的问题生成一条自然、友好的回复。

用户最后的消息：{user_message}

对话历史：
{dialogue_context}

要求：
1. 回复应该自然、友好、专业
2. 简洁自然，5-30字范围内
3. 只返回回复内容"""
        
        return prompt
    
    def _clean_json_string(self, json_str: str) -> str:
        """
        清理JSON字符串中的无效控制字符和特殊字符
        Qwen3输出可能包含BOM、零宽字符等，导致JSON解析失败
        
        注意：JSON 结构中的换行符和空格是合法的（用于格式化），不应该被移除
        只需要移除不可见的特殊字符即可
        
        Args:
            json_str: 原始JSON字符串
            
        Returns:
            str: 清理后的JSON字符串
        """
        import re
        
        # 1. 移除 BOM (Byte Order Mark)
        if json_str.startswith('\ufeff'):
            json_str = json_str[1:]
        
        # 2. 移除零宽字符（Zero-Width characters）
        # U+200B: Zero Width Space
        # U+200C: Zero Width Non-Joiner
        # U+200D: Zero Width Joiner
        # U+FEFF: Zero Width No-Break Space (BOM)
        # U+2060: Word Joiner
        zero_width_chars = ['\u200b', '\u200c', '\u200d', '\ufeff', '\u2060']
        for char in zero_width_chars:
            json_str = json_str.replace(char, '')
        
        # 3. 修复JSON字符串中未转义的单引号和双引号
        # 处理chat字段中的Python代码示例导致的JSON解析失败
        # 例如: "chat": "... f"{greeting}, {name}" ..." 
        # 策略：在JSON字符串值内部，将未转义的单引号替换为转义的单引号
        # 但要注意：不要破坏JSON的结构（键值对的双引号）
        
        # 使用正则替换JSON字符串值中的问题字符
        # 这是一个简化的方案，可能无法处理所有edge case
        # 更健壮的方案是使用专门的JSON修复库
        
        # 注意：不要转义JSON结构中的\n, \r, \t等
        # 这些是合法的JSON格式化字符
        # json.loads()会正确处理它们
        
        return json_str
    
    def _process_turn_with_llm(
        self,
        user_message: str,
        context_data: Optional[Dict[str, Any]],
        turn_output: AgentTurnOutput
    ) -> AgentTurnOutput:
        """
        使用LLM生成完整的JSON输出
        
        Args:
            user_message: 用户消息
            context_data: 上下文数据
            turn_output: 轮次输出对象
            
        Returns:
            AgentTurnOutput: 填充完整的轮次输出
        """
        import json
        import re
        import logging
        
        # 方法入口日志
        # print(f"[DEBUG] === 进入 _process_turn_with_llm ===")
        # print(f"[DEBUG] user_message: {user_message[:100] if user_message else 'None'}...")
        # print(f"[DEBUG] llm_client存在: {self.llm_client is not None}")
        # print(f"[DEBUG] llm_client类型: {type(self.llm_client)}")
        
        # 构建对话历史
        dialogue_context = "\n".join([
            f"{'用户' if msg['role'] == 'user' else '客服'}: {msg['content']}"
            for msg in self.dialogue_history[-10:]  # 最近10条消息
        ])
        
        # 构建消息列表
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"【对话历史】\n{dialogue_context}\n\n【当前用户消息】\n{user_message}"}
        ]
        
        # 调试日志:记录发送给LLM的消息
        # logging.debug(f"=== LLM Input ===")
        # logging.debug(f"System: {self.system_prompt[:200]}...")
        # logging.debug(f"User: {messages[1]['content'][:200]}...")
        
        try:
            # 调用LLM
            # print(f"[DEBUG] === 开始调用LLM ===")
            # print(f"[DEBUG] LLM Client类型: {type(self.llm_client)}")
            # print(f"[DEBUG] Messages数量: {len(messages)}")
            
            response = self.llm_client.generate(
                prompt="",  # 使用messages参数
                messages=messages,
                temperature=0.1,  # 较低温度保证输出格式稳定
                max_tokens=8192  # 增加到8192以确保即使think很长也不会被截断
                # repetition_penalty= 1.2
            )
            
            # print(f"[DEBUG] === LLM调用成功 ===")
            # print(f"[DEBUG] Response type: {type(response)}")
            # print(f"[DEBUG] Response is None: {response is None}")
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # 检查 finish_reason（如果有的话）
            finish_reason = None
            try:
                finish_reason = getattr(response, 'finish_reason', None) or \
                            (response.metadata.get('finish_reason') if hasattr(response, 'metadata') else None)
            except (AttributeError, TypeError):
                # 如果任何访问失败，finish_reason 保持为 None
                pass

            # finish_reason = getattr(response, 'finish_reason', None) or \
            #                (response.metadata.get('finish_reason') if hasattr(response, 'metadata') else None)
            
            # 调试日志：记录响应长度（改为WARNING级别以便看到）
            # logging.warning(f"LLM response length: {len(response_text)} chars (max_tokens=8192, finish_reason={finish_reason})")
            # logging.debug(f"LLM response (first 500 chars): {response_text[:500]}")
            # logging.debug(f"LLM response (last 200 chars): {response_text[-200:]}")
            
            # if finish_reason == 'length':
            #     logging.error(f"⚠️  Response was truncated due to max_tokens limit! Consider increasing max_tokens beyond 8192.")
            
            # if len(response_text) > 7800:
            #     logging.warning(f"⚠️  Response is very long ({len(response_text)} chars), may be approaching max_tokens limit!")
            
            # 解析JSON - 优先尝试直接解析,失败后再用正则提取
            # print(f"[DEBUG] 开始解析JSON,response_text长度: {len(response_text)}")
            # print(f"[DEBUG] response_text前500字符: {response_text[:500]}")
            
            json_str = None
            data = None
            response_text = response_text.replace('```json', '').replace('```', '').replace('True', 'true').replace('False', 'false')
            # 策略1: 先尝试直接解析response_text(去除首尾空白)
            try:
                # print(f"[DEBUG] 策略1: 尝试直接解析response_text...")
                data = json.loads(response_text.strip())
                # print(f"[DEBUG] ✅ 策略1成功! 直接解析成功")
                json_str = response_text.strip()
            except json.JSONDecodeError as e:
                print(f"[DEBUG] 策略1失败: {e}, 尝试策略2...")
                
                # 预处理: 如果是Qwen3模型,先移除<think>标签及其内容
                cleaned_response_text = response_text
                # print('qwen3' in self.llm_client.model_name.lower())
                if self.llm_client and hasattr(self.llm_client, 'model_name'):
                    model_name = self.llm_client.model_name.lower()
                    if 'qwen3' in model_name or 'qwen-3' in model_name:
                        # 移除<think>...</think>标签及其内容
                        cleaned_response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
                        # print(f"[DEBUG] Qwen3模型检测到,已移除think标签,清理后长度: {len(cleaned_response_text)}")

                # 计算需要的右括号数量
                open_braces = cleaned_response_text.count('{')
                close_braces = cleaned_response_text.count('}')
                
                if open_braces > close_braces:
                    # 缺少右括号,添加
                    missing = open_braces - close_braces
                    fixed_text = cleaned_response_text + "}" * missing
                    try:
                        data= json.loads(fixed_text)
                    except json.JSONDecodeError:
                        pass
                
                elif close_braces > open_braces:
                    # 多余右括号,删除
                    extra = close_braces - open_braces
                    fixed_text = cleaned_response_text.rstrip('}')
                    fixed_text = fixed_text + "}" * (close_braces - open_braces - extra)
                    try:
                        data= json.loads(fixed_text)
                    except json.JSONDecodeError:
                        pass


                
                json_match = re.search(r'\{.*\}', cleaned_response_text, re.DOTALL)
                if not json_match:
                    # 策略2: 使用正则提取JSON对象
                    logging.error(f"cleaned_response_text string: {cleaned_response_text}")
                    error_msg = f"LLM response does not contain JSON (length={len(cleaned_response_text)}): {cleaned_response_text[:]}"
                    logging.error(error_msg)
                    raise ValueError(error_msg)
                
                json_str = json_match.group(0)
                # print(f"[DEBUG] 策略2: 正则提取JSON,长度: {len(json_str)}")
                
                # 清理JSON字符串中的无效控制字符
                json_str = self._clean_json_string(json_str)
                
                # 检查JSON是否完整
                json_str_stripped = json_str.rstrip()
                if not json_str_stripped.endswith('}'):
                    pass  # print(f"[DEBUG] ⚠️ JSON可能被截断")
            
            # 如果策略1失败,尝试解析策略2提取的JSON
            if data is None:
                # print(f"[DEBUG] 尝试解析提取的JSON,长度: {len(json_str)}")
                try:
                    data = json.loads(json_str)
                    # print(f"[DEBUG] ✅ JSON解析成功!")
                except json.JSONDecodeError as e:
                    # print(f"[DEBUG] ❌ JSON解析失败: {e}")
                    logging.error(f"JSON decode error: {e}")
                    # logging.error(f"JSON string: {json_str[:]}")
                    # logging.error(f"JSON string (last 200 chars): {json_str[-200:]}")
                    # # 打印前10个字符的Unicode码点，帮助诊断隐藏字符
                    # logging.error(f"First 10 chars as unicode: {[hex(ord(c)) for c in json_str[:10]]}")
                # 检查是否因为截断导致的错误
                if not json_str_stripped.endswith('}'):
                    logging.error("⚠️  JSON is INCOMPLETE (truncated)! This is likely due to max_tokens being too small.")
                
                # 尝试使用宽松的JSON解析策略
                try:
                    import ast
                    # 尝试将单引号替换为双引号
                    fixed_json_str = json_str.replace("'", '"')
                    data = json.loads(fixed_json_str)
                    # logging.warning("JSON parse succeeded after replacing single quotes with double quotes")
                except:
                    # 如果还是失败，尝试使用ast.literal_eval (Python字面量解析)
                    try:
                        data = ast.literal_eval(json_str)
                        # logging.warning("JSON parse succeeded using ast.literal_eval")
                    except:
                        # 所有尝试都失败，抛出原始错误
                        # print(f"[DEBUG] ❌ 所有JSON解析策略都失败!")
                        logging.error("All JSON parsing strategies failed, falling back to rule engine")
                        raise
            
            # 提取分类输出
            if "classification_output" in data:
                # 【重要】根据scenario_id从scenario_config中读取正确的分类字段
                # 为所有6个场景都提供特殊处理，而不是通用的字典处理
                from ..config import get_scenario_config
                
                classification_dict = data["classification_output"]
                
                # 确保classification_dict是字典格式
                if isinstance(classification_dict, dict):
                    classification_data = classification_dict
                else:
                    classification_data = {}
                
                # 从scenario_config中获取当前场景的分类字段列表
                scenario_config = get_scenario_config(self.scenario_id)
                expected_fields = set(scenario_config.classification_fields.keys()) if scenario_config and scenario_config.classification_fields else set()
                
                # 【为所有6个场景都提供特殊处理】
                if self.scenario_id == "online_education":
                    turn_output.classification_output = ClassificationOutput(
                        DescriptionClear=classification_data.get("DescriptionClear"),
                        QuestionRelevance=classification_data.get("QuestionRelevance"),
                        EmotionTendency=classification_data.get("EmotionTendency"),
                        ResolveDependency=classification_data.get("ResolveDependency"),
                        RepeatedRaised=classification_data.get("RepeatedRaised"),
                        RegardingRefund=classification_data.get("RegardingRefund"),
                    )
                elif self.scenario_id == "ecommerce_refund":
                    turn_output.classification_output = EcommerceRefundClassification(
                        CoreIntention=classification_data.get("CoreIntention"),
                        ProvidedDocument=classification_data.get("ProvidedDocument"),
                        Responsibility=classification_data.get("Responsibility"),
                        RefundReasonable=classification_data.get("RefundReasonable"),
                        EmotionStatus=classification_data.get("EmotionStatus"),
                    )
                elif self.scenario_id == "telecom_package":
                    turn_output.classification_output = TelecomPackageClassification(
                        ConsumptionType=classification_data.get("ConsumptionType"),
                        ApplicationTendency=classification_data.get("ApplicationTendency"),
                        ConsumptionProfile=classification_data.get("ConsumptionProfile"),
                        EmotionTag=classification_data.get("EmotionTag"),
                    )
                elif self.scenario_id == "property_service":
                    turn_output.classification_output = PropertyServiceClassification(
                        CoreIntention=classification_data.get("CoreIntention"),
                        EmotionTag=classification_data.get("EmotionTag"),
                        RepairItemCategory=classification_data.get("RepairItemCategory"),
                        RelatedScope=classification_data.get("RelatedScope"),
                        EmergencyLevel=classification_data.get("EmergencyLevel"),
                    )
                elif self.scenario_id == "logistics_delivery":
                    turn_output.classification_output = LogisticsDeliveryClassification(
                        RiskStatus=classification_data.get("RiskStatus"),
                        InfoCompleteness=classification_data.get("InfoCompleteness"),
                        UserIntention=classification_data.get("UserIntention"),
                        EmotionalState=classification_data.get("EmotionalState"),
                        EmergencyLevel=classification_data.get("EmergencyLevel"),
                        ComplaintValidity=classification_data.get("ComplaintValidity"),
                    )
                elif self.scenario_id == "airline_refund":
                    turn_output.classification_output = AirlineRefundClassification(
                        CoreDemand=classification_data.get("CoreDemand"),
                        ChangeReason=classification_data.get("ChangeReason"),
                        UserEmotion=classification_data.get("UserEmotion"),
                        DocumentValidity=classification_data.get("DocumentValidity"),
                        IsInfoComplete=classification_data.get("IsInfoComplete"),
                    )
                else:
                    # 未知场景，直接使用字典
                    turn_output.classification_output = classification_data
                    logging.warning(f"Turn : Unknown scenario_id={self.scenario_id}, using raw classification dict")
            
            # 提取路径
            if "now_path" in data:
                turn_output.expected_path = data["now_path"]
            
            # 提取finals
            if "finals" in data:
                finals_dict = data["finals"]
                turn_output.final_output = FinalOutput(
                    Action=finals_dict.get("Action", ""),
                    PLAN=finals_dict.get("PLAN", "none"),
                    extra_fields={k: v for k, v in finals_dict.items() if k not in ["Action", "PLAN"]}
                )
            
            # 提取chat
            if "chat" in data:
                turn_output.chat = data["chat"]
            
            # 提取cot (可选)
            if "cot" in data:
                turn_output.cot = data["cot"]
            
            # 设置next_step: 从now_path的最后一个节点推断下一步
            # 如果finals的Action不是END,说明对话应该继续
            if turn_output.final_output and turn_output.final_output.Action not in ["END", "end"]:
                # 从now_path获取当前位置,推断下一步
                if turn_output.expected_path and len(turn_output.expected_path) > 0:
                    last_node_id = turn_output.expected_path[-1]
                    # 检查该节点是否有后继
                    next_steps = self.sop_graph.get_next_nodes(last_node_id)
                    if next_steps:
                        next_node_id, _ = next_steps[0]
                        next_node = self.sop_graph.nodes.get(next_node_id)
                        if next_node:
                            turn_output.next_step = next_node.step_name
                        else:
                            turn_output.next_step = next_node_id
                    else:
                        turn_output.next_step = None  # 流程结束
                else:
                    # 如果没有path信息,默认继续对话
                    turn_output.next_step = "continue"
            else:
                # Action是END,对话终止
                turn_output.next_step = None
            
            # 记录回复
            self.add_agent_message(turn_output.chat)
            
            # 保存到历史
            self.turn_history.append(turn_output)
            self.current_turn += 1
            
            # print(f"[DEBUG] ✅ 准备返回turn_output, chat={turn_output.chat[:50] if turn_output.chat else 'None'}...")
            return turn_output
            
        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            
            # 记录详细错误信息
            logger.error(f"JSON解析失败 Turn {turn_output.turn_id}: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            
            # 标记JSON解析失败
            turn_output.json_parse_failed = True
            
            # ⚠️ 关键修复: 返回带有失败标记的turn_output,而不是抛出异常
            # 这样评估器可以统计JSON解析错误率
            turn_output.chat = "[JSON解析失败,无法生成回复]"
            
            # 记录回复到历史
            self.add_agent_message(turn_output.chat)
            self.turn_history.append(turn_output)
            self.current_turn += 1
            
            return turn_output
    
    def _fallback_to_rule_engine(
        self,
        user_message: str,
        context_data: Optional[Dict[str, Any]],
        turn_output: AgentTurnOutput
    ) -> AgentTurnOutput:
        """LLM失败时降级到规则引擎"""
        import logging
        # logging.warning("Falling back to rule engine due to LLM failure")
        
        # 使用规则引擎分类
        classification_output = self._classify_input(user_message, context_data)
        turn_output.classification_output = classification_output
        
        # 生成路径和finals
        turn_output.expected_path = self._generate_expected_path(
            classification_output,
            self.sop_graph.start_node_id
        )
        turn_output.final_output = self._predict_final_output_from_classification(
            classification_output,
            context_data
        )
        
        # 生成chat
        turn_output.chat = self._generate_response(
            user_message, classification_output, "", context_data
        )
        
        # 记录
        self.add_agent_message(turn_output.chat)
        self.turn_history.append(turn_output)
        self.current_turn += 1
        
        return turn_output
    
    def _predict_final_output_from_classification(
        self,
        classification_output: ClassificationOutput,
        context_data: Optional[Dict[str, Any]] = None
    ) -> FinalOutput:
        """
        根据客服模型自己的分类结果预测最终动作
        注意:这里使用客服模型自己的决策逻辑,而不是规则引擎
        
        Args:
            classification_output: 分类结果
            context_data: 上下文数据
            
        Returns:
            FinalOutput: 预测的最终动作
        """
        # 使用 _generate_expected_path 遍历到最后,找到最终的动作节点
        expected_path = self._generate_expected_path(
            classification_output,
            self.sop_graph.start_node_id
        )
        
        # 从路径中找到最后一个 action 节点
        action_value = ""
        plan_value = "none"
        
        for node_id in reversed(expected_path):
            if node_id in self.sop_graph.nodes:
                node = self.sop_graph.nodes[node_id]
                if node.action_name:
                    action_value = node.action_name
                    # 如果是PLAN动作,从参数中获取PLAN类型
                    if node.action_name == "PLAN" and node.parameters:
                        plan_value = node.parameters.get("plan_type", "PLAN_A")
                    break
        
        return FinalOutput(
            Action=action_value,
            PLAN=plan_value
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "scenario_id": self.scenario_id,
            "current_step": self.current_step,
            "path_taken": self.path_taken,
            "dialogue_history": self.dialogue_history,
            "turn_count": self.current_turn,
            "context_data": self.context_data,
        }
