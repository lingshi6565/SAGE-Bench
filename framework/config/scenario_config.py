#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
场景配置管理系统
Scenario Configuration Management System

定义不同任务场景的配置：
1. 在线教育平台客服 (Online Education Customer Service)
2. 外呼客服 (Outbound Call Center)
3. 外卖平台智能客服 (Food Delivery Platform Customer Service)

每个场景包括：
- 对抗强度等级 (Adversarial Intensity Levels)
- 用户意图分类 (User Intents)
- SOP流程 (Standard Operating Procedures)
- 评价标准 (Evaluation Criteria)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set
from enum import Enum


class AdversarialIntensity(Enum):
    """对抗强度等级"""
    ZERO = "zero_conflict"          # 零对抗 - 协作型意图 (Collaborative intent)
    WEAK = "weak_conflict"          # 弱对抗 - 查询型意图 (Query intent)
    STRONG = "strong_conflict"      # 强对抗 - 博弈型意图 (Negotiation intent)


@dataclass
class UserIntentConfig:
    """用户意图配置"""
    intent_name: str                # 意图名称
    intensity_level: AdversarialIntensity  # 对抗强度
    description: str                # 意图描述
    keywords: List[str]             # 关键词
    examples: List[str] = field(default_factory=list)  # 示例


@dataclass
class ClassificationFieldConfig:
    """分类字段配置"""
    field_name: str                 # 字段名
    data_type: str                  # 数据类型 (bool, string, etc.)
    options: List[str]              # 可选值列表
    description: str                # 字段描述


@dataclass
class ActionConfig:
    """动作配置"""
    action_name: str                # 动作名称
    description: str                # 动作描述
    parameters: Dict[str, str] = field(default_factory=dict)  # 参数


@dataclass
class EvaluationMetricConfig:
    """评价指标配置"""
    metric_name: str                # 指标名称
    metric_type: str                # 指标类型 (code_computed, model_judged)
    description: str                # 指标描述
    weight: float = 1.0             # 权重


@dataclass
class ScenarioConfig:
    """场景完整配置"""
    scenario_id: str                # 场景ID
    scenario_name: str              # 场景名称
    description: str                # 场景描述
    
    # 用户意图配置
    user_intents: Dict[str, UserIntentConfig] = field(default_factory=dict)
    
    # 分类字段配置
    classification_fields: Dict[str, ClassificationFieldConfig] = field(default_factory=dict)
    
    # 动作配置
    actions: Dict[str, ActionConfig] = field(default_factory=dict)
    
    # 评价标准
    evaluation_metrics: Dict[str, EvaluationMetricConfig] = field(default_factory=dict)
    
    # SOP步骤名称列表
    sop_steps: List[str] = field(default_factory=list)
    
    # 初始状态模板
    initial_state_template: Dict = field(default_factory=dict)


# ==================== 在线教育平台客服配置 ====================

ONLINE_EDUCATION_INTENTS = {
    "seek_answer": UserIntentConfig(
        intent_name="seek_answer",
        intensity_level=AdversarialIntensity.WEAK,
        description="寻求问题答案 - 学生询问课程内容、作业、考试等问题",
        keywords=["答案", "怎么做", "什么是", "如何", "解释"],
        examples=[
            "第三章第二节公式推导看不懂",
            "能给我第三章习题答案吗",
            "请问这个公式怎么用"
        ]
    ),
    "technical_issue": UserIntentConfig(
        intent_name="technical_issue",
        intensity_level=AdversarialIntensity.WEAK,
        description="技术问题 - 课程平台操作、视频加载等问题",
        keywords=["不了", "卡", "加载", "操作", "问题", "提交失败"],
        examples=[
            "作业提交失败",
            "视频加载缓慢",
            "如何下载课件"
        ]
    ),
    "complaint": UserIntentConfig(
        intent_name="complaint",
        intensity_level=AdversarialIntensity.STRONG,
        description="投诉处理 - 学生对课程质量、服务不满意",
        keywords=["投诉", "差", "不满意", "浪费", "退款", "赔偿"],
        examples=[
            "多次反馈都没解决，浪费我的时间",
            "课程质量太差，要求退款",
            "老师讲得不清楚，影响学习"
        ]
    ),
    "refund_request": UserIntentConfig(
        intent_name="refund_request",
        intensity_level=AdversarialIntensity.STRONG,
        description="退款谈判 - 学生要求退费或赔偿",
        keywords=["退费", "退款", "赔偿", "补偿", "返还"],
        examples=[
            "我要求退费",
            "这个课程不值这个价格，要求退款",
            "必须给我赔偿"
        ]
    ),
    "consultation": UserIntentConfig(
        intent_name="consultation",
        intensity_level=AdversarialIntensity.ZERO,
        description="咨询确认 - 学生咨询课程信息、确认学习进度",
        keywords=["咨询", "询问", "确认", "了解", "多少", "有吗"],
        examples=[
            "请确认我的课程信息",
            "询问学习进度",
            "这个课程有什么要求"
        ]
    )
}

ONLINE_EDUCATION_CLASSIFICATION_FIELDS = {
    "DescriptionClear": ClassificationFieldConfig(
        field_name="DescriptionClear",
        data_type="bool",
        options=[True, False],
        description="问题描述清晰度 - 是否包含具体课程章节、明确问题类型"
    ),
    "QuestionRelevance": ClassificationFieldConfig(
        field_name="QuestionRelevance",
        data_type="bool",
        options=[True, False],
        description="问题与课程关联性 - 是否与当前在学课程直接相关"
    ),
    "EmotionTendency": ClassificationFieldConfig(
        field_name="EmotionTendency",
        data_type="str",
        options=["Calm", "Dissatisfied"],
        description="学员情绪倾向 - 是否存在不满情绪表现"
    ),
    "ResolveDependency": ClassificationFieldConfig(
        field_name="ResolveDependency",
        data_type="str",
        options=["LowDependency", "MediumDependency", "HighDependency", "null"],
        description="问题解决依赖度 - 需要多少外部资源支持"
    ),
    "RepeatedRaised": ClassificationFieldConfig(
        field_name="RepeatedRaised",
        data_type="bool",
        options=[True, False],
        description="是否重复反馈 - 过去7天内是否反馈过相同问题"
    ),
    "RegardingRefund": ClassificationFieldConfig(
        field_name="RegardingRefund",
        data_type="bool",
        options=[True, False],
        description="是否涉及退费 - 用户是否明确提出退费请求"
    )
}

ONLINE_EDUCATION_ACTIONS = {
    "GUIDE": ActionConfig(
        action_name="GUIDE",
        description="引导用户补充信息以明确问题",
        parameters={"type": "clarification", "priority": "high"}
    ),
    "REVIEW": ActionConfig(
        action_name="REVIEW",
        description="审核处理 - 对重复反馈问题进行专项审核",
        parameters={"type": "review", "priority": "medium"}
    ),
    "COMFORT": ActionConfig(
        action_name="COMFORT",
        description="安抚用户 - 对不满情绪用户进行安抚处理",
        parameters={"type": "appeasement", "priority": "high"}
    ),
    "PLAN": ActionConfig(
        action_name="PLAN",
        description="分配资源计划",
        parameters={"type": "resource_allocation", "priority": "medium"}
    ),
    "REFUND": ActionConfig(
        action_name="REFUND",
        description="退款处理 - 审核通过，执行退款",
        parameters={"type": "refund", "priority": "high"}
    ),
    "NEGOTIATE": ActionConfig(
        action_name="NEGOTIATE",
        description="协商处理 - 与风险用户进行协商",
        parameters={"type": "negotiation", "priority": "high"}
    )
}

ONLINE_EDUCATION_EVALUATION_METRICS = {
    "classification_accuracy": EvaluationMetricConfig(
        metric_name="classification_accuracy",
        metric_type="code_computed",
        description="分类字段正确率 - 所有6个分类字段的准确度",
        weight=0.3
    ),
    "path_correctness": EvaluationMetricConfig(
        metric_name="path_correctness",
        metric_type="code_computed",
        description="SOP路径正确性 - 是否遵循正确的SOP流程路径",
        weight=0.3
    ),
    "action_correctness": EvaluationMetricConfig(
        metric_name="action_correctness",
        metric_type="code_computed",
        description="动作正确性 - 最终输出的动作是否正确",
        weight=0.2
    ),
    "chat_quality": EvaluationMetricConfig(
        metric_name="chat_quality",
        metric_type="model_judged",
        description="话术质量 - 模型回复的自然性、准确性和客户友好度",
        weight=0.2
    )
}

# SOP步骤
ONLINE_EDUCATION_SOP_STEPS = [
    "step1_classification",
    "step2_description_check",
    "step3_relevance_check",
    "step4_repeated_check",
    "step5_emotion_check",
    "step6_resource_allocation",
    "step7_refund_branch",
    "step8_financial_review",
    "step_final_action"
]

# 在线教育平台完整配置
ONLINE_EDUCATION_CONFIG = ScenarioConfig(
    scenario_id="online_education",
    scenario_name="在线教育平台客服",
    description="学员问题处理、投诉处理、退费谈判等多场景",
    user_intents=ONLINE_EDUCATION_INTENTS,
    classification_fields=ONLINE_EDUCATION_CLASSIFICATION_FIELDS,
    actions=ONLINE_EDUCATION_ACTIONS,
    evaluation_metrics=ONLINE_EDUCATION_EVALUATION_METRICS,
    sop_steps=ONLINE_EDUCATION_SOP_STEPS,
    initial_state_template={
        "CourseList": [],
        "HistoricalComplaintRecords": False,
        "QuestionTypeFor30Days": [],
        "isRiskUser": False,
        "user_profile": {},
        "dialogue_history": []
    }
)


# ==================== 电商退款场景配置 ====================

ECOMMERCE_REFUND_INTENTS = {
    "exchange_product": UserIntentConfig(
        intent_name="exchange_product",
        intensity_level=AdversarialIntensity.WEAK,
        description="换货需求 - 商品信息错误或不合适要求换货",
        keywords=["换货", "尺码", "颜色", "不合适", "能换"],
        examples=[
            "我买的鞋子尺码不太合适",
            "我想换一双大一码的，可以吗？",
            "如果已签收，我保证鞋子没穿过，包装都完好的"
        ]
    ),
    "refund_before_shipping": UserIntentConfig(
        intent_name="refund_before_shipping",
        intensity_level=AdversarialIntensity.ZERO,
        description="未发货退款 - 订单未发货时取消订单退款",
        keywords=["取消", "退款", "未发货", "还没发"],
        examples=[
            "你好，我昨天下的订单还没发货吧？",
            "我想取消订单，可以退款吗？",
            "不好意思给你们添麻烦了"
        ]
    ),
    "refund_on_the_way": UserIntentConfig(
        intent_name="refund_on_the_way",
        intensity_level=AdversarialIntensity.WEAK,
        description="运输中退款 - 物流途中要求拦截并退款",
        keywords=["拦截", "在路上", "配送中", "物流"],
        examples=[
            "客服，我买的东西现在正在配送，我不想要了",
            "能帮我拦截一下吗？我想退款",
            "我看物流显示还在路上，应该来得及吧？"
        ]
    ),
    "merchant_compensation_high_credit": UserIntentConfig(
        intent_name="merchant_compensation_high_credit",
        intensity_level=AdversarialIntensity.STRONG,
        description="商家责任赔偿（高信用） - 商家责任且用户高信用获得赔偿",
        keywords=["投诉", "虚假宣传", "欺骗", "赔偿", "不符"],
        examples=[
            "我要投诉！你们这个商品和描述完全不一样！",
            "这是虚假宣传，我要退货退款！",
            "我是老客户了，你们必须给出合理的赔偿！"
        ]
    ),
    "merchant_compensation_low_credit": UserIntentConfig(
        intent_name="merchant_compensation_low_credit",
        intensity_level=AdversarialIntensity.STRONG,
        description="商家责任赔偿（低/中信用） - 商家责任且用户低或中信用",
        keywords=["投诉", "虚假宣传", "欺骗", "赔偿", "不符"],
        examples=[
            "这个商品和描述不一样，我要投诉！",
            "这是欺骗消费者，我要退货！",
            "你们必须处理这个问题！"
        ]
    ),
    "user_return_high_credit": UserIntentConfig(
        intent_name="user_return_high_credit",
        intensity_level=AdversarialIntensity.ZERO,
        description="用户发起退货（高信用） - 用户责任且高信用可直接揽收",
        keywords=["退货", "申请", "取件", "配合"],
        examples=[
            "你好，我想申请退货",
            "麻烦帮我安排一下上门取件",
            "谢谢你们的配合"
        ]
    ),
    "user_return_medium_credit": UserIntentConfig(
        intent_name="user_return_medium_credit",
        intensity_level=AdversarialIntensity.WEAK,
        description="用户发起退货（中信用） - 用户责任且中信用可直接揽收",
        keywords=["退货", "申请", "取件", "配合"],
        examples=[
            "客服你好，我想申请退货",
            "可以安排上门取件吗？",
            "谢谢"
        ]
    ),
    "user_return_low_credit_with_doc": UserIntentConfig(
        intent_name="user_return_low_credit_with_doc",
        intensity_level=AdversarialIntensity.WEAK,
        description="用户发起退货（低信用+有凭证） - 低信用用户提交凭证可揽收",
        keywords=["退货", "凭证", "照片", "证明"],
        examples=[
            "客服你好，我想退货",
            "我已经拍了照片作为证明",
            "麻烦安排上门取件好吗？"
        ]
    ),
    "user_return_low_credit_no_doc": UserIntentConfig(
        intent_name="user_return_low_credit_no_doc",
        intensity_level=AdversarialIntensity.WEAK,
        description="用户发起退货（低信用+无凭证） - 低信用用户缺少凭证需补充",
        keywords=["退货", "申请", "凭证", "证明"],
        examples=[
            "客服，我想申请退货",
            "理由是商品不符合预期",
            "需要我提供什么证明吗？"
        ]
    ),
    "unreasonable_refund": UserIntentConfig(
        intent_name="unreasonable_refund",
        intensity_level=AdversarialIntensity.STRONG,
        description="无理由退款 - 用户自身原因要求退款，理由不充分直接拒绝",
        keywords=["退货", "退款", "使用痕迹", "不讲理"],
        examples=[
            "这个东西我不想要了，要退货！",
            "我用了几天就不喜欢了，你们必须给我退款！",
            "不然我要投诉你们！"
        ]
    )
}

ECOMMERCE_REFUND_CLASSIFICATION_FIELDS = {
    "CoreIntention": ClassificationFieldConfig(
        field_name="CoreIntention",
        data_type="str",
        options=["ReturnOrRefund", "Exchange"],
        description="用户发起售后的核心需求 - 退货退款还是换货"
    ),
    "ProvidedDocument": ClassificationFieldConfig(
        field_name="ProvidedDocument",
        data_type="bool",
        options=[True, False],
        description="用户是否提交售后相关凭证 - 如照片、视频等证明材料"
    ),
    "Responsibility": ClassificationFieldConfig(
        field_name="Responsibility",
        data_type="str",
        options=["User", "Merchant"],
        description="售后问题的责任归属 - 是用户责任还是商家责任"
    ),
    "RefundReasonable": ClassificationFieldConfig(
        field_name="RefundReasonable",
        data_type="str",
        options=["Reasonable", "Unreasonable"],
        description="退款需求是否合理 - 是否符合平台退款规则"
    ),
    "EmotionStatus": ClassificationFieldConfig(
        field_name="EmotionStatus",
        data_type="str",
        options=["Calm", "Dissatisfied"],
        description="用户情绪状态 - 是否存在不满、生气等负面情绪"
    )
}

ECOMMERCE_REFUND_ACTIONS = {
    "Supplementary": ActionConfig(
        action_name="Supplementary",
        description="补充凭证 - 要求用户提交退换货所需的凭证和材料",
        parameters={"type": "information_collection", "priority": "medium"}
    ),
    "Interception": ActionConfig(
        action_name="Interception",
        description="拦截物流 - 在物流运输过程中拦截商品",
        parameters={"type": "logistics", "priority": "high"}
    ),
    "Exchange": ActionConfig(
        action_name="Exchange",
        description="换货 - 为用户安排换货处理",
        parameters={"type": "exchange", "priority": "high"}
    ),
    "Refund": ActionConfig(
        action_name="Refund",
        description="退款 - 为用户办理退款",
        parameters={"type": "refund", "priority": "high"}
    ),
    "PayFee": ActionConfig(
        action_name="PayFee",
        description="支付运费 - 要求用户支付运费或手续费",
        parameters={"type": "payment", "priority": "medium"}
    ),
    "CollectionService": ActionConfig(
        action_name="CollectionService",
        description="上门取件 - 安排上门取件服务",
        parameters={"type": "logistics", "priority": "medium"}
    ),
    "Comfort": ActionConfig(
        action_name="Comfort",
        description="安抚用户 - 对不满情绪用户进行安抚处理",
        parameters={"type": "emotion_management", "priority": "high"}
    ),
    "Reject": ActionConfig(
        action_name="Reject",
        description="拒绝 - 委婉拒绝用户的不合理请求",
        parameters={"type": "rejection", "priority": "medium"}
    ),
    "Comfort+Compensation": ActionConfig(
        action_name="Comfort+Compensation",
        description="安抚并补偿 - 由商家原因导致，进行安抚并提供补偿",
        parameters={"type": "compensation", "priority": "high"}
    )
}

ECOMMERCE_REFUND_EVALUATION_METRICS = {
    "classification_accuracy": EvaluationMetricConfig(
        metric_name="classification_accuracy",
        metric_type="code_computed",
        description="分类字段正确率 - 所有5个分类字段的准确度",
        weight=0.3
    ),
    "path_correctness": EvaluationMetricConfig(
        metric_name="path_correctness",
        metric_type="code_computed",
        description="SOP路径正确性 - 是否遵循正确的SOP流程路径",
        weight=0.3
    ),
    "action_correctness": EvaluationMetricConfig(
        metric_name="action_correctness",
        metric_type="code_computed",
        description="动作正确性 - 最终输出的动作是否正确",
        weight=0.2
    ),
    "chat_quality": EvaluationMetricConfig(
        metric_name="chat_quality",
        metric_type="model_judged",
        description="话术质量 - 模型回复的自然性、准确性和客户友好度",
        weight=0.2
    )
}

ECOMMERCE_REFUND_SOP_STEPS = [
    "step1_classification",
    "step2_core_intention",
    "step3_shipping_status",
    "step4_credit_level",
    "step5_responsibility",
    "step6_refund_reasonable",
    "step7_emotion_status",
    "step8_provided_document",
    "step_final_action"
]

ECOMMERCE_REFUND_CONFIG = ScenarioConfig(
    scenario_id="ecommerce_refund",
    scenario_name="电商退款",
    description="电商平台退款处理、订单问题处理、物流异常等多场景",
    user_intents=ECOMMERCE_REFUND_INTENTS,
    classification_fields=ECOMMERCE_REFUND_CLASSIFICATION_FIELDS,
    actions=ECOMMERCE_REFUND_ACTIONS,
    evaluation_metrics=ECOMMERCE_REFUND_EVALUATION_METRICS,
    sop_steps=ECOMMERCE_REFUND_SOP_STEPS,
    initial_state_template={
        "ShippingStatus": "",
        "CreditLevel": "",
        "user_profile": {},
        "dialogue_history": []
    }
)


# ==================== 电信套餐办理场景配置 ====================

TELECOM_PACKAGE_INTENTS = {
    "enquiry_data_agree": UserIntentConfig(
        intent_name="enquiry_data_agree",
        intensity_level=AdversarialIntensity.ZERO,
        description="咨询流量套餐（倾向办理）",
        keywords=["流量", "套餐", "更新", "足够"],
        examples=[
            "你好，我想咨询一下流量套餐。",
            "我现在的流量经常不够用。",
            "有什么合适的套餐推荐吗？"
        ]
    ),
    "enquiry_voice_agree": UserIntentConfig(
        intent_name="enquiry_voice_agree",
        intensity_level=AdversarialIntensity.ZERO,
        description="咨询通话套餐（倾向办理）",
        keywords=["通话", "时长", "套餐", "打电话"],
        examples=[
            "你好，我想问一下通话套餐的事情。",
            "我工作经常要打电话，通话时长不太够。",
            "有什么通话多的套餐吗？"
        ]
    ),
    "enquiry_hesitate": UserIntentConfig(
        intent_name="enquiry_hesitate",
        intensity_level=AdversarialIntensity.WEAK,
        description="咨询但犹豫不决",
        keywords=["比较", "考虑", "仔细", "怎么样"],
        examples=[
            "我想了解一下你们现在的套餐。",
            "我现在用的套餐有点贵，想看看有没有更划算的。",
            "但我需要仔细比较一下。"
        ]
    ),
    "enquiry_reject": UserIntentConfig(
        intent_name="enquiry_reject",
        intensity_level=AdversarialIntensity.WEAK,
        description="咨询但拒绝办理",
        keywords=["了解", "介绍", "不换", "暂时"],
        examples=[
            "我想问一下现在都有什么套餐。",
            "我就是了解一下，暂时不打算换。",
            "你给我介绍一下就行。"
        ]
    ),
    "change_no_contract": UserIntentConfig(
        intent_name="change_no_contract",
        intensity_level=AdversarialIntensity.ZERO,
        description="更换套餐（无合约）",
        keywords=["换", "更换", "改", "办理"],
        examples=[
            "你好，我想换个套餐。",
            "现在的套餐不太适合我了。",
            "能帮我办理一下吗？"
        ]
    ),
    "change_with_contract_no_penalty": UserIntentConfig(
        intent_name="change_with_contract_no_penalty",
        intensity_level=AdversarialIntensity.ZERO,
        description="更换套餐（有合约无违约金）",
        keywords=["合约", "到期", "换", "新套餐"],
        examples=[
            "我的套餐合约应该到期了吧？",
            "我想换个新套餐。",
            "应该不用交违约金了吧？"
        ]
    ),
    "change_with_penalty_calm": UserIntentConfig(
        intent_name="change_with_penalty_calm",
        intensity_level=AdversarialIntensity.WEAK,
        description="更换套餐（有违约金且情绪平静）",
        keywords=["违约金", "合约", "怎么办", "协商"],
        examples=[
            "我想换套餐，但我还在合约期内。",
            "需要交违约金吗？多少钱？",
            "能不能商量一下？"
        ]
    ),
    "change_with_penalty_discontent": UserIntentConfig(
        intent_name="change_with_penalty_discontent",
        intensity_level=AdversarialIntensity.STRONG,
        description="更换套餐（有违约金且情绪不满）",
        keywords=["为什么", "不合理", "投诉", "说清楚"],
        examples=[
            "我要换套餐，为什么还要交违约金？",
            "当初办理的时候你们也没说清楚！",
            "这个违约金太不合理了！"
        ]
    ),
    "cancel_no_penalty": UserIntentConfig(
        intent_name="cancel_no_penalty",
        intensity_level=AdversarialIntensity.WEAK,
        description="取消套餐（无违约金）",
        keywords=["取消", "到期", "不用", "办理"],
        examples=[
            "你好，我想取消现在的套餐。",
            "合约应该到期了吧？",
            "能帮我办理取消吗？"
        ]
    ),
    "cancel_with_penalty_calm": UserIntentConfig(
        intent_name="cancel_with_penalty_calm",
        intensity_level=AdversarialIntensity.WEAK,
        description="取消套餐（有违约金且情绪平静）",
        keywords=["取消", "违约金", "多少", "怎么操作"],
        examples=[
            "我需要取消套餐。",
            "我知道可能要交违约金。",
            "具体多少钱？怎么办理？"
        ]
    ),
    "cancel_with_penalty_discontent": UserIntentConfig(
        intent_name="cancel_with_penalty_discontent",
        intensity_level=AdversarialIntensity.STRONG,
        description="取消套餐（有违约金且情绪不满）",
        keywords=["投诉", "取消", "凭什么", "不满"],
        examples=[
            "你们的服务这么差，我要取消套餐！",
            "还要我交违约金？凭什么？",
            "这不是我的问题，是你们服务不行！"
        ]
    )
}

TELECOM_PACKAGE_CLASSIFICATION_FIELDS = {
    "ConsumptionType": ClassificationFieldConfig(
        field_name="ConsumptionType",
        data_type="str",
        options=["Enquiry", "Change", "Cancel"],
        description="用户对话的意图 - 咨询、变更、取消"
    ),
    "ApplicationTendency": ClassificationFieldConfig(
        field_name="ApplicationTendency",
        data_type="str",
        options=["Agree", "Reject", "Hesitate"],
        description="用户是否倾向于办理推荐套餐 - 同意、拒绝、犹豫"
    ),
    "ConsumptionProfile": ClassificationFieldConfig(
        field_name="ConsumptionProfile",
        data_type="str",
        options=["Data", "Voice"],
        description="用户倾向于办理的套餐类型 - 流量型或通话型"
    ),
    "EmotionTag": ClassificationFieldConfig(
        field_name="EmotionTag",
        data_type="str",
        options=["Calm", "Discontent"],
        description="用户对话中表现的情绪 - 平静或不满"
    )
}

TELECOM_PACKAGE_ACTIONS = {
    "ChangeOrder": ActionConfig(
        action_name="ChangeOrder",
        description="变更套餐 - 为用户办理套餐变更",
        parameters={"type": "package_change", "priority": "high"}
    ),
    "GoodBye": ActionConfig(
        action_name="GoodBye",
        description="委婉结束 - 委婉的结束对话",
        parameters={"type": "conversation_end", "priority": "medium"}
    ),
    "TransHuman": ActionConfig(
        action_name="TransHuman",
        description="转人工处理 - 转人工处理",
        parameters={"type": "escalation", "priority": "high"}
    )
}

TELECOM_PACKAGE_EVALUATION_METRICS = {
    "classification_accuracy": EvaluationMetricConfig(
        metric_name="classification_accuracy",
        metric_type="code_computed",
        description="分类字段正确率 - 所有4个分类字段的准确度",
        weight=0.3
    ),
    "path_correctness": EvaluationMetricConfig(
        metric_name="path_correctness",
        metric_type="code_computed",
        description="SOP路径正确性 - 是否遵循正确的SOP流程路径",
        weight=0.3
    ),
    "action_correctness": EvaluationMetricConfig(
        metric_name="action_correctness",
        metric_type="code_computed",
        description="动作正确性 - 最终输出的动作是否正确",
        weight=0.2
    ),
    "chat_quality": EvaluationMetricConfig(
        metric_name="chat_quality",
        metric_type="model_judged",
        description="话术质量 - 模型回复的自然性、准确性和客户友好度",
        weight=0.2
    )
}

TELECOM_PACKAGE_SOP_STEPS = [
    "step1_classification",
    "step2_consumption_type",
    "step3_consumption_profile",
    "step4_package_status",
    "step5_penalty_check",
    "step6_application_tendency",
    "step7_emotion_assessment",
    "step_final_action"
]

TELECOM_PACKAGE_CONFIG = ScenarioConfig(
    scenario_id="telecom_package",
    scenario_name="电信套餐办理",
    description="电信客服套餐办理、套餐变更、费用咨询、投诉处理等多场景",
    user_intents=TELECOM_PACKAGE_INTENTS,
    classification_fields=TELECOM_PACKAGE_CLASSIFICATION_FIELDS,
    actions=TELECOM_PACKAGE_ACTIONS,
    evaluation_metrics=TELECOM_PACKAGE_EVALUATION_METRICS,
    sop_steps=TELECOM_PACKAGE_SOP_STEPS,
    initial_state_template={
        "PackageStatus": "NoContract",
        "Penalty": 0,
        "user_profile": {},
        "dialogue_history": []
    }
)


# ==================== 物业服务场景配置 ====================

PROPERTY_SERVICE_INTENTS = {
    "payment_inquiry": UserIntentConfig(
        intent_name="payment_inquiry",
        intensity_level=AdversarialIntensity.ZERO,
        description="缴费咨询 - 业主咨询物业费缴费情况",
        keywords=["缴费", "物业费", "咨询", "确认"],
        examples=[
            "你好，我想查一下我家的物业费缴纳情况。",
            "想了解一下物业费都包括哪些服务。",
            "顺便问问缴费方式有哪些。"
        ]
    ),
    "payment_occupied": UserIntentConfig(
        intent_name="payment_occupied",
        intensity_level=AdversarialIntensity.ZERO,
        description="自住房缴费 - 自住房业主的缴费处理",
        keywords=["缴费", "自住", "物业费"],
        examples=[
            "你好，我想了解一下我家的物业费情况。",
            "我是业主，自己住在这里。",
            "想问一下缴费状态。"
        ]
    ),
    "payment_rented": UserIntentConfig(
        intent_name="payment_rented",
        intensity_level=AdversarialIntensity.ZERO,
        description="租赁房缴费 - 租赁房业主的缴费处理",
        keywords=["缴费", "出租", "物业费"],
        examples=[
            "你好，我想问一下租赁房的物业费问题。",
            "我的房子是出租的。",
            "想确认一下缴费情况。"
        ]
    ),
    "payment_unoccupied": UserIntentConfig(
        intent_name="payment_unoccupied",
        intensity_level=AdversarialIntensity.WEAK,
        description="空置房缴费 - 空置房业主的缴费处理",
        keywords=["空置", "物业费", "收费标准"],
        examples=[
            "你好，我想问一下空置房的物业费问题。",
            "我的房子一直没住人，还要交全额物业费吗？",
            "有没有什么优惠政策？"
        ]
    ),
    "payment_unpaid": UserIntentConfig(
        intent_name="payment_unpaid",
        intensity_level=AdversarialIntensity.WEAK,
        description="欠费缴纳 - 业主补交欠费",
        keywords=["欠费", "忘记", "补缴"],
        examples=[
            "不好意思，我最近太忙忘记交物业费了。",
            "现在能补交吗？需要怎么操作？",
            "会不会有滞纳金？"
        ]
    ),
    "complaint_occupied_settled_calm": UserIntentConfig(
        intent_name="complaint_occupied_settled_calm",
        intensity_level=AdversarialIntensity.WEAK,
        description="自住房投诉平静已缴费 - 自住房已缴费投诉且平静",
        keywords=["投诉", "反映", "卫生", "管理"],
        examples=[
            "你好，我想反映一下小区卫生的问题。",
            "最近楼道里经常有垃圾没人清理。",
            "我们都按时交物业费了，希望能改进。"
        ]
    ),
    "complaint_occupied_settled_discontent": UserIntentConfig(
        intent_name="complaint_occupied_settled_discontent",
        intensity_level=AdversarialIntensity.STRONG,
        description="自住房投诉不满已缴费 - 自住房已缴费投诉且不满",
        keywords=["投诉", "生气", "不满"],
        examples=[
            "我要投诉！昨晚楼上装修到半夜，物业根本不管！",
            "我们按时交钱，你们就这么管理小区的？",
            "这个问题必须给我一个说法！"
        ]
    ),
    "complaint_occupied_unpaid": UserIntentConfig(
        intent_name="complaint_occupied_unpaid",
        intensity_level=AdversarialIntensity.WEAK,
        description="自住房投诉欠费 - 自住房欠费的投诉处理",
        keywords=["投诉", "欠费"],
        examples=[
            "我有点不满意小区的管理。",
            "但我知道自己可能还欠费了。",
            "能先帮我处理一下问题吗？"
        ]
    ),
    "complaint_rented_settled_calm": UserIntentConfig(
        intent_name="complaint_rented_settled_calm",
        intensity_level=AdversarialIntensity.WEAK,
        description="租赁房投诉平静已缴费 - 租赁房已缴费投诉且平静",
        keywords=["投诉", "反映", "管理"],
        examples=[
            "你好，我想反映一下小区的问题。",
            "作为业主，我觉得这方面有改进空间。",
            "希望能得到重视。"
        ]
    ),
    "complaint_rented_settled_discontent": UserIntentConfig(
        intent_name="complaint_rented_settled_discontent",
        intensity_level=AdversarialIntensity.STRONG,
        description="租赁房投诉不满已缴费 - 租赁房已缴费投诉且不满",
        keywords=["投诉", "生气", "不满"],
        examples=[
            "我要投诉！小区管理太差了！",
            "我已经按时交费了，你们应该做得更好！",
            "必须给我一个满意的解释！"
        ]
    ),
    "complaint_rented_unpaid": UserIntentConfig(
        intent_name="complaint_rented_unpaid",
        intensity_level=AdversarialIntensity.WEAK,
        description="租赁房投诉欠费 - 租赁房欠费的投诉处理",
        keywords=["投诉", "欠费"],
        examples=[
            "我对小区管理有意见。",
            "但我知道自己可能还欠物业费。",
            "希望能先处理一下问题。"
        ]
    ),
    "complaint_unoccupied_calm": UserIntentConfig(
        intent_name="complaint_unoccupied_calm",
        intensity_level=AdversarialIntensity.WEAK,
        description="空置房投诉平静 - 空置房业主平静的投诉",
        keywords=["投诉", "空置", "收费"],
        examples=[
            "你好，我想反映一些问题。",
            "我的房子虽然空置，但我也关心小区状况。",
            "希望能了解相关政策。"
        ]
    ),
    "complaint_unoccupied_discontent": UserIntentConfig(
        intent_name="complaint_unoccupied_discontent",
        intensity_level=AdversarialIntensity.STRONG,
        description="空置房投诉不满 - 空置房业主不满的投诉",
        keywords=["投诉", "空置", "不合理"],
        examples=[
            "我要投诉，我房子根本没住人。",
            "为什么还要收全额物业费？这不合理！",
            "给我一个合理的解释！"
        ]
    ),
    "repair_indoor_personal_unpaid": UserIntentConfig(
        intent_name="repair_indoor_personal_unpaid",
        intensity_level=AdversarialIntensity.WEAK,
        description="室内报修欠费 - 室内设施个户报修但欠费",
        keywords=["报修", "电路", "欠费"],
        examples=[
            "你好，我家电路出问题了，能帮我报修吗？",
            "我知道物业费还没交，但这个真的挺急的。",
            "能不能先帮我修，我马上补交费用？"
        ]
    ),
    "repair_environmental_personal_unpaid": UserIntentConfig(
        intent_name="repair_environmental_personal_unpaid",
        intensity_level=AdversarialIntensity.WEAK,
        description="卫生报修欠费 - 环卫设施个户报修但欠费",
        keywords=["报修", "卫生", "欠费"],
        examples=[
            "你好，我家附近的卫生有问题，想报修。",
            "不过我知道自己物业费还欠着。",
            "能先处理问题吗？我会补交。"
        ]
    ),
    "repair_indoor_personal_settled_urgent": UserIntentConfig(
        intent_name="repair_indoor_personal_settled_urgent",
        intensity_level=AdversarialIntensity.STRONG,
        description="室内个户报修已缴费紧急 - 室内设施个户报修且已缴费且紧急",
        keywords=["紧急", "漏水", "爆裂"],
        examples=[
            "你好，我家里有紧急情况需要维修！",
            "水管突然爆裂了，赶紧派人来！",
            "这太紧急了，请立即派维修工！"
        ]
    ),
    "repair_indoor_personal_settled_normal": UserIntentConfig(
        intent_name="repair_indoor_personal_settled_normal",
        intensity_level=AdversarialIntensity.ZERO,
        description="室内个户报修已缴费非紧急 - 室内设施个户报修且已缴费且非紧急",
        keywords=["报修", "灯坏", "维修"],
        examples=[
            "你好，我家里的灯坏了，需要报修。",
            "能不能尽快安排师傅过来看看？",
            "我家的照明有问题。"
        ]
    ),
    "repair_environmental_personal_settled_urgent": UserIntentConfig(
        intent_name="repair_environmental_personal_settled_urgent",
        intensity_level=AdversarialIntensity.STRONG,
        description="卫生个户报修已缴费紧急 - 环卫设施个户报修且已缴费且紧急",
        keywords=["紧急", "堵塞"],
        examples=[
            "你好，楼道堵塞了，太紧急了！",
            "影响我们出入，请立即派人处理！",
            "这是紧急情况！"
        ]
    ),
    "repair_environmental_personal_settled_normal": UserIntentConfig(
        intent_name="repair_environmental_personal_settled_normal",
        intensity_level=AdversarialIntensity.WEAK,
        description="卫生个户报修已缴费非紧急 - 环卫设施个户报修且已缴费且非紧急",
        keywords=["报修", "卫生"],
        examples=[
            "你好，我想报修一下卫生设施。",
            "楼道的清洁效果不太理想。",
            "能帮忙处理一下吗？"
        ]
    ),
    "repair_indoor_public_urgent": UserIntentConfig(
        intent_name="repair_indoor_public_urgent",
        intensity_level=AdversarialIntensity.STRONG,
        description="室内公共紧急报修 - 室内公共设施紧急维修",
        keywords=["紧急", "被困", "电梯"],
        examples=[
            "喂！电梯坏了！我被困在里面了！",
            "快点派人来！这是紧急情况！",
            "赶紧处理！"
        ]
    ),
    "repair_indoor_public_normal": UserIntentConfig(
        intent_name="repair_indoor_public_normal",
        intensity_level=AdversarialIntensity.ZERO,
        description="室内公共普通报修 - 室内公共设施非紧急维修",
        keywords=["报修", "一楼", "灯"],
        examples=[
            "你好，我发现一楼的灯坏了。",
            "是公共区域，需要修一下。",
            "麻烦帮忙安排维修。"
        ]
    ),
    "repair_environmental_public_urgent": UserIntentConfig(
        intent_name="repair_environmental_public_urgent",
        intensity_level=AdversarialIntensity.STRONG,
        description="卫生公共紧急报修 - 卫生公共设施紧急维修",
        keywords=["紧急", "下水道", "堵"],
        examples=[
            "你好，小区下水道堵了！",
            "这是紧急情况，赶紧派人来！",
            "影响了很多住户！"
        ]
    ),
    "repair_environmental_public_normal": UserIntentConfig(
        intent_name="repair_environmental_public_normal",
        intensity_level=AdversarialIntensity.ZERO,
        description="卫生公共普通报修 - 卫生公共设施非紧急维修",
        keywords=["报修", "路灯", "安全"],
        examples=[
            "你好，我发现小区花园有几盏路灯不亮了。",
            "晚上走路不太安全，能帮忙修一下吗？",
            "麻烦你们了。"
        ]
    )
}

PROPERTY_SERVICE_CLASSIFICATION_FIELDS = {
    "CoreIntention": ClassificationFieldConfig(
        field_name="CoreIntention",
        data_type="str",
        options=["Payment", "Complaint", "Repair"],
        description="住户对话的意图 - 缴费、投诉、报修"
    ),
    "EmotionTag": ClassificationFieldConfig(
        field_name="EmotionTag",
        data_type="str",
        options=["Calm", "Discontent"],
        description="住户在对话中表现的情绪 - 平静或不满"
    ),
    "RepairItemCategory": ClassificationFieldConfig(
        field_name="RepairItemCategory",
        data_type="str",
        options=["IndoorFacilities", "EnvironmentalHygiene"],
        description="住户报修事项的具体分类 - 室内设施或环境卫生"
    ),
    "RelatedScope": ClassificationFieldConfig(
        field_name="RelatedScope",
        data_type="str",
        options=["Personal", "Public"],
        description="事项涉及的范围 - 个人房屋或公共区域"
    ),
    "EmergencyLevel": ClassificationFieldConfig(
        field_name="EmergencyLevel",
        data_type="str",
        options=["Urgent", "NoUrgent"],
        description="事项紧急程度 - 紧急或不紧急"
    )
}

PROPERTY_SERVICE_ACTIONS = {
    "PayInformation": ActionConfig(
        action_name="PayInformation",
        description="对物业费以及物业服务进行相关说明",
        parameters={"type": "information_provision", "priority": "medium"}
    ),
    "Payment": ActionConfig(
        action_name="Payment",
        description="开启支付通道",
        parameters={"type": "payment", "priority": "high"}
    ),
    "TransHuman": ActionConfig(
        action_name="TransHuman",
        description="转人工处理",
        parameters={"type": "escalation", "priority": "high"}
    ),
    "Reject": ActionConfig(
        action_name="Reject",
        description="拒绝住户的请求，并委婉提醒住户补交物业费",
        parameters={"type": "rejection", "priority": "medium"}
    ),
    "Registration": ActionConfig(
        action_name="Registration",
        description="登记住户反映的问题",
        parameters={"type": "registration", "priority": "medium"}
    ),
    "Comfort": ActionConfig(
        action_name="Comfort",
        description="安抚住户情绪",
        parameters={"type": "emotion_management", "priority": "medium"}
    )
}

PROPERTY_SERVICE_EVALUATION_METRICS = {
    "classification_accuracy": EvaluationMetricConfig(
        metric_name="classification_accuracy",
        metric_type="code_computed",
        description="分类字段正确率 - 所有5个分类字段的准确度",
        weight=0.3
    ),
    "path_correctness": EvaluationMetricConfig(
        metric_name="path_correctness",
        metric_type="code_computed",
        description="SOP路径正确性 - 是否遵循正确的SOP流程路径",
        weight=0.3
    ),
    "action_correctness": EvaluationMetricConfig(
        metric_name="action_correctness",
        metric_type="code_computed",
        description="动作正确性 - 最终输出的动作是否正确",
        weight=0.2
    ),
    "chat_quality": EvaluationMetricConfig(
        metric_name="chat_quality",
        metric_type="model_judged",
        description="话术质量 - 模型回复的自然性、准确性和客户友好度",
        weight=0.2
    )
}

PROPERTY_SERVICE_SOP_STEPS = [
    "step1_classification",
    "step2_core_intention",
    "step3_house_status",
    "step4_repair_category",
    "step5_related_scope",
    "step6_fee_payment_status",
    "step7_emotion_status",
    "step8_emergency_level",
    "step_final_action"
]

PROPERTY_SERVICE_CONFIG = ScenarioConfig(
    scenario_id="property_service",
    scenario_name="物业服务",
    description="物业客服缴费咨询、投诉处理、报修服务等多场景",
    user_intents=PROPERTY_SERVICE_INTENTS,
    classification_fields=PROPERTY_SERVICE_CLASSIFICATION_FIELDS,
    actions=PROPERTY_SERVICE_ACTIONS,
    evaluation_metrics=PROPERTY_SERVICE_EVALUATION_METRICS,
    sop_steps=PROPERTY_SERVICE_SOP_STEPS,
    initial_state_template={
        "HouseStatus": "Occupied",
        "FeePaymentStatus": "Settled",
        "user_profile": {},
        "dialogue_history": []
    }
)


# ==================== 快递物流场景配置 ====================

LOGISTICS_DELIVERY_INTENTS = {
    "risk_package_interception": UserIntentConfig(
        intent_name="risk_package_interception",
        intensity_level=AdversarialIntensity.WEAK,
        description="风险包裹拦截 - 系统标记风险包裹需要拦截",
        keywords=["拦截", "风险", "为什么"],
        examples=[
            "客服你好，为什么我的包裹被拦截了？",
            "我寄的只是普通商品啊。",
            "需要我提供什么信息吗？"
        ]
    ),
    "info_incomplete_supplementary": UserIntentConfig(
        intent_name="info_incomplete_supplementary",
        intensity_level=AdversarialIntensity.ZERO,
        description="信息不完整补充 - 用户信息不完整需补充",
        keywords=["查询", "订单号找不到", "什么时候下的单"],
        examples=[
            "你好，我想查一下快递到哪了。",
            "但是我订单号找不到了，能帮我查吗？",
            "我记得是上周三下的单，寄到北京的。"
        ]
    ),
    "urge_arrived_detail": UserIntentConfig(
        intent_name="urge_arrived_detail",
        intensity_level=AdversarialIntensity.WEAK,
        description="催促已到达详情 - 已到达包裹用户催促",
        keywords=["什么时候", "到了吗", "配送站"],
        examples=[
            "你好，我想问一下我的快递什么时候能送到？",
            "物流显示已经到配送站两天了。",
            "订单号是XXX123。"
        ]
    ),
    "urge_undelivered_urgent": UserIntentConfig(
        intent_name="urge_undelivered_urgent",
        intensity_level=AdversarialIntensity.STRONG,
        description="催促未送达紧急 - 未送达包裹用户催促且紧急",
        keywords=["非常急", "加急", "必须"],
        examples=[
            "客服你好，我的快递非常急！明天上午必须要用！",
            "现在物流还显示在路上，能不能帮我加急？",
            "这是工作需要的重要文件，真的很急！"
        ]
    ),
    "urge_undelivered_normal": UserIntentConfig(
        intent_name="urge_undelivered_normal",
        intensity_level=AdversarialIntensity.WEAK,
        description="催促未送达正常 - 未送达包裹用户催促但不紧急",
        keywords=["什么时候", "派送"],
        examples=[
            "你好，想问一下我的快递什么时候能送到？",
            "物流显示还在配送中。",
            "麻烦帮我查一下。"
        ]
    ),
    "urge_delivered_urgent": UserIntentConfig(
        intent_name="urge_delivered_urgent",
        intensity_level=AdversarialIntensity.STRONG,
        description="催促已送达紧急 - 已送达包裹用户催促且紧急",
        keywords=["已签收", "非常紧急"],
        examples=[
            "我的快递显示已签收，但我没收到！",
            "非常紧急，请马上帮我查一下！",
            "这个包裹我急用！"
        ]
    ),
    "urge_delivered_normal": UserIntentConfig(
        intent_name="urge_delivered_normal",
        intensity_level=AdversarialIntensity.WEAK,
        description="催促已送达正常 - 已送达包裹用户催促但不紧急",
        keywords=["派送", "没收到"],
        examples=[
            "你好，我的快递显示派送了，但还没收到。",
            "能帮我查一下吗？",
            "不是特别急，就是想确认一下。"
        ]
    ),
    "modify_arrived_reject": UserIntentConfig(
        intent_name="modify_arrived_reject",
        intensity_level=AdversarialIntensity.WEAK,
        description="修改已到达拒绝 - 已到达包裹无法修改",
        keywords=["地址填错", "改地址"],
        examples=[
            "客服，我的包裹到配送站了，但地址填错了。",
            "现在还能改地址吗？",
            "这个包裹对我很重要。"
        ]
    ),
    "modify_delivered_makeup": UserIntentConfig(
        intent_name="modify_delivered_makeup",
        intensity_level=AdversarialIntensity.WEAK,
        description="修改已送达补差 - 已送达包裹修改需补差",
        keywords=["派送地址", "补差价"],
        examples=[
            "你好，我的快递派送地址有问题。",
            "能修改吗？补差价也可以。",
            "订单号是XXX。"
        ]
    ),
    "modify_undelivered_ok": UserIntentConfig(
        intent_name="modify_undelivered_ok",
        intensity_level=AdversarialIntensity.WEAK,
        description="修改未送达通过 - 未送达包裹可修改",
        keywords=["填错地址", "改一下", "还没派送"],
        examples=[
            "你好，我填错收货地址了，能改一下吗？",
            "包裹还没派送，应该来得及吧？",
            "订单号是XXX789。"
        ]
    ),
    "complaint_arrived_invalid": UserIntentConfig(
        intent_name="complaint_arrived_invalid",
        intensity_level=AdversarialIntensity.STRONG,
        description="投诉到达无效 - 到达包裹投诉不合理",
        keywords=["投诉", "必须赔"],
        examples=[
            "你们的快递有问题！我要投诉！",
            "必须给我赔偿，不然我就投诉到总部！",
            "反正就是你们的问题！"
        ]
    ),
    "complaint_arrived_valid_insured": UserIntentConfig(
        intent_name="complaint_arrived_valid_insured",
        intensity_level=AdversarialIntensity.STRONG,
        description="投诉到达有保险 - 到达包裹投诉合理且有保险",
        keywords=["破损", "赔偿", "保险"],
        examples=[
            "我要投诉！包裹送到时已经破损了！",
            "里面的东西都摔坏了，你们必须赔偿！",
            "我买了保险的，有照片为证！"
        ]
    ),
    "complaint_arrived_valid_uninsured_calm": UserIntentConfig(
        intent_name="complaint_arrived_valid_uninsured_calm",
        intensity_level=AdversarialIntensity.WEAK,
        description="投诉到达无保险平静 - 到达包裹投诉合理无保险且平静",
        keywords=["受损", "没买保险"],
        examples=[
            "你好，我收到的包裹有些受损。",
            "我没买保险，但希望能得到处理。",
            "能帮我看看吗？"
        ]
    ),
    "complaint_arrived_valid_uninsured_dissatisfied": UserIntentConfig(
        intent_name="complaint_arrived_valid_uninsured_dissatisfied",
        intensity_level=AdversarialIntensity.STRONG,
        description="投诉到达无保险不满 - 到达包裹投诉合理无保险且不满",
        keywords=["损坏", "不满"],
        examples=[
            "我的包裹送到就已经坏了！",
            "你们的快递太不专业了！",
            "我要投诉，必须给我一个说法！"
        ]
    ),
    "complaint_undelivered_urgent": UserIntentConfig(
        intent_name="complaint_undelivered_urgent",
        intensity_level=AdversarialIntensity.STRONG,
        description="投诉未送达紧急 - 未送达包裹投诉用户紧急",
        keywords=["已签收", "没收到", "着急"],
        examples=[
            "我的快递显示已签收，但我根本没收到！",
            "快递员电话也打不通，这是怎么回事？",
            "我非常着急，赶紧帮我查一下！"
        ]
    ),
    "complaint_undelivered_normal": UserIntentConfig(
        intent_name="complaint_undelivered_normal",
        intensity_level=AdversarialIntensity.WEAK,
        description="投诉未送达正常 - 未送达包裹投诉用户不紧急",
        keywords=["没更新", "查一下"],
        examples=[
            "你好，我的快递好几天没更新了。",
            "想问一下发生了什么。",
            "能帮我查一下吗？"
        ]
    ),
    "complaint_delivered_urgent": UserIntentConfig(
        intent_name="complaint_delivered_urgent",
        intensity_level=AdversarialIntensity.STRONG,
        description="投诉已送达紧急 - 已送达包裹投诉用户紧急",
        keywords=["派送", "没收到", "冒领"],
        examples=[
            "我的快递显示派送了，但我真的没收到！",
            "是不是被冒领了？这太过分了！",
            "必须给我立即查处，我很着急！"
        ]
    ),
    "complaint_delivered_normal": UserIntentConfig(
        intent_name="complaint_delivered_normal",
        intensity_level=AdversarialIntensity.WEAK,
        description="投诉已送达正常 - 已送达包裹投诉用户不紧急",
        keywords=["派送", "没收到"],
        examples=[
            "你好，我的快递显示派送了，但我还没收到。",
            "能帮我查一下吗？",
            "可能是还在楼下，但想先问问。"
        ]
    )
}

LOGISTICS_DELIVERY_CLASSIFICATION_FIELDS = {
    "RiskStatus": ClassificationFieldConfig(
        field_name="RiskStatus",
        data_type="str",
        options=["Risk", "Safe"],
        description="订单的危险程度 - 是否存在风险因素"
    ),
    "InfoCompleteness": ClassificationFieldConfig(
        field_name="InfoCompleteness",
        data_type="bool",
        options=[True, False],
        description="用户提交信息的完整程度 - 是否包含订单号等必要信息"
    ),
    "UserIntention": ClassificationFieldConfig(
        field_name="UserIntention",
        data_type="str",
        options=["Urge", "Complaint", "Modify"],
        description="用户发起请求的核心目的 - 催促、投诉还是修改"
    ),
    "EmotionalState": ClassificationFieldConfig(
        field_name="EmotionalState",
        data_type="str",
        options=["Calm", "Dissatisfied"],
        description="用户反馈问题时的情绪状态 - 是否存在不满情绪"
    ),
    "EmergencyLevel": ClassificationFieldConfig(
        field_name="EmergencyLevel",
        data_type="str",
        options=["Urgent", "Normal"],
        description="事项紧急程度 - 是否需要加急处理"
    ),
    "ComplaintValidity": ClassificationFieldConfig(
        field_name="ComplaintValidity",
        data_type="bool",
        options=[True, False],
        description="投诉的合理性 - 投诉理由是否充分合理"
    )
}

LOGISTICS_DELIVERY_ACTIONS = {
    "Interception": ActionConfig(
        action_name="Interception",
        description="拦截 - 对有风险的包裹进行拦截",
        parameters={"type": "risk_management", "priority": "high"}
    ),
    "Supplementary": ActionConfig(
        action_name="Supplementary",
        description="补充信息 - 要求用户提供订单号等必要信息",
        parameters={"type": "information_collection", "priority": "medium"}
    ),
    "TransHuman": ActionConfig(
        action_name="TransHuman",
        description="转人工 - 将问题转接人工客服处理",
        parameters={"type": "escalation", "priority": "high"}
    ),
    "Reject": ActionConfig(
        action_name="Reject",
        description="拒绝 - 委婉拒绝用户修改地址的请求",
        parameters={"type": "rejection", "priority": "medium"}
    ),
    "Registration": ActionConfig(
        action_name="Registration",
        description="登记加急 - 登记加急包裹物流",
        parameters={"type": "priority_handling", "priority": "high"}
    ),
    "Comfort": ActionConfig(
        action_name="Comfort",
        description="安抚 - 安抚用户情绪",
        parameters={"type": "emotion_management", "priority": "medium"}
    ),
    "Detail": ActionConfig(
        action_name="Detail",
        description="告知详情 - 告知包裹的物流详情",
        parameters={"type": "information_provision", "priority": "medium"}
    ),
    "MakeUpDifference": ActionConfig(
        action_name="MakeUpDifference",
        description="补差价 - 启动补差价流程",
        parameters={"type": "payment", "priority": "medium"}
    ),
    "Modify": ActionConfig(
        action_name="Modify",
        description="修改地址 - 修改收货地址",
        parameters={"type": "logistics", "priority": "high"}
    ),
    "Compensation": ActionConfig(
        action_name="Compensation",
        description="赔偿 - 提供赔偿方案",
        parameters={"type": "compensation", "priority": "high"}
    )
}

LOGISTICS_DELIVERY_EVALUATION_METRICS = {
    "classification_accuracy": EvaluationMetricConfig(
        metric_name="classification_accuracy",
        metric_type="code_computed",
        description="分类字段正确率 - 所有6个分类字段的准确度",
        weight=0.3
    ),
    "path_correctness": EvaluationMetricConfig(
        metric_name="path_correctness",
        metric_type="code_computed",
        description="SOP路径正确性 - 是否遵循正确的SOP流程路径",
        weight=0.3
    ),
    "action_correctness": EvaluationMetricConfig(
        metric_name="action_correctness",
        metric_type="code_computed",
        description="动作正确性 - 最终输出的动作是否正确",
        weight=0.2
    ),
    "chat_quality": EvaluationMetricConfig(
        metric_name="chat_quality",
        metric_type="model_judged",
        description="话术质量 - 模型回复的自然性、准确性和客户友好度",
        weight=0.2
    )
}

LOGISTICS_DELIVERY_SOP_STEPS = [
    "step1_classification",
    "step2_risk_control",
    "step3_info_completeness",
    "step4_user_intention",
    "step5_order_status",
    "step6_emergency_level",
    "step7_complaint_validity",
    "step8_insurance_check",
    "step9_emotion_status",
    "step_final_action"
]

LOGISTICS_DELIVERY_CONFIG = ScenarioConfig(
    scenario_id="logistics_delivery",
    scenario_name="快递物流",
    description="快递客服物流查询、派送问题、丢失赔偿、退货处理等多场景",
    user_intents=LOGISTICS_DELIVERY_INTENTS,
    classification_fields=LOGISTICS_DELIVERY_CLASSIFICATION_FIELDS,
    actions=LOGISTICS_DELIVERY_ACTIONS,
    evaluation_metrics=LOGISTICS_DELIVERY_EVALUATION_METRICS,
    sop_steps=LOGISTICS_DELIVERY_SOP_STEPS,
    initial_state_template={
        "orderStatus": "",
        "hasInsurance": False,
        "user_profile": {},
        "dialogue_history": []
    }
)


# ==================== 政企服务场景配置（在线航司改签退票） ====================

AIRLINE_REFUND_INTENTS = {
    # ==================== 咨询分支 ====================
    "inquiry_incomplete": UserIntentConfig(
        intent_name="inquiry_incomplete",
        intensity_level=AdversarialIntensity.ZERO,
        description="信息不完整的咨询 - 用户信息不完整需补充",
        keywords=["查询", "订单号找不到", "什么时候"],
        examples=[
            "你好，我想查一下我的航班。",
            "但是我订单号找不到了，能帮我查吗？",
            "我记得是去上海的，大概是本月15号左右。"
        ]
    ),
    "inquiry_complete": UserIntentConfig(
        intent_name="inquiry_complete",
        intensity_level=AdversarialIntensity.ZERO,
        description="完整的咨询 - 用户提供完整信息的咨询",
        keywords=["确认", "起飞时间", "登机口"],
        examples=[
            "你好，我想确认一下我的航班信息。",
            "能帮我查一下具体的起飞时间和登机口吗？",
            "订单号是CA123456，出发日期是明天。"
        ]
    ),

    # ==================== 个人原因改签分支 ====================
    "personal_reason_incomplete": UserIntentConfig(
        intent_name="personal_reason_incomplete",
        intensity_level=AdversarialIntensity.WEAK,
        description="个人原因改签（信息不完整）",
        keywords=["改签", "会议时间", "需要"],
        examples=[
            "你好，我想改签航班，因为会议时间改了。",
            "我买的是下周的航班，能改签吗？",
            "我需要提供什么信息吗？"
        ]
    ),
    "personal_reason_invalid_doc": UserIntentConfig(
        intent_name="personal_reason_invalid_doc",
        intensity_level=AdversarialIntensity.WEAK,
        description="个人原因改签（信息完整+凭证无效）",
        keywords=["改签", "凭证"],
        examples=[
            "我想改签航班CA123456。",
            "我已经提供了订单号和出行日期。",
            "为什么说我的凭证无效？"
        ]
    ),
    "personal_reason_regular_with_insurance": UserIntentConfig(
        intent_name="personal_reason_regular_with_insurance",
        intensity_level=AdversarialIntensity.WEAK,
        description="个人原因改签（普通会员+有保险）",
        keywords=["改签", "保险"],
        examples=[
            "你好，我想改签航班，因为会议时间改了。",
            "我买的是下周三的航班，能改到下周五吗？",
            "我记得我买了保险的。"
        ]
    ),
    "personal_reason_regular_no_insurance": UserIntentConfig(
        intent_name="personal_reason_regular_no_insurance",
        intensity_level=AdversarialIntensity.WEAK,
        description="个人原因改签（普通会员+无保险）",
        keywords=["改签", "扣费"],
        examples=[
            "客服你好，我有事需要改签航班。",
            "请问改签要扣多少钱？",
            "我当时没买保险，会不会损失很大？"
        ]
    ),
    "personal_reason_vip": UserIntentConfig(
        intent_name="personal_reason_vip",
        intensity_level=AdversarialIntensity.WEAK,
        description="VIP个人原因改签",
        keywords=["紧急", "VIP", "优先"],
        examples=[
            "你好，我需要紧急改签航班！",
            "我家人突发疾病，我必须马上回去。",
            "我是VIP会员，能不能优先帮我处理？"
        ]
    ),
    "personal_reason_blacklist": UserIntentConfig(
        intent_name="personal_reason_blacklist",
        intensity_level=AdversarialIntensity.STRONG,
        description="黑名单个人原因改签",
        keywords=["改签", "强硬"],
        examples=[
            "我要改签！马上给我办理！",
            "别跟我说什么规则，我就要改！",
            "你们不办我就投诉你们平台！"
        ]
    ),

    # ==================== 航司/天气原因改签分支 ====================
    "airline_reason_regular": UserIntentConfig(
        intent_name="airline_reason_regular",
        intensity_level=AdversarialIntensity.WEAK,
        description="航司原因改签（普通会员）",
        keywords=["取消", "改签"],
        examples=[
            "你好，我的航班被取消了。",
            "航司说要给我改签，麻烦你帮我处理一下。",
            "我需要尽快出发，什么时候能改签好？"
        ]
    ),
    "airline_reason_vip": UserIntentConfig(
        intent_name="airline_reason_vip",
        intensity_level=AdversarialIntensity.WEAK,
        description="航司原因改签（VIP）",
        keywords=["取消", "VIP"],
        examples=[
            "我的航班被航司取消了。",
            "作为VIP会员，我期望能得到及时处理和补偿。",
            "能为我安排最近的航班吗？"
        ]
    ),
    "airline_reason_blacklist": UserIntentConfig(
        intent_name="airline_reason_blacklist",
        intensity_level=AdversarialIntensity.WEAK,
        description="航司原因改签（黑名单）",
        keywords=["取消", "责任"],
        examples=[
            "我的航班被取消了，这不是我的问题。",
            "航司有责任给我改签吧？",
            "我什么时候能改签？"
        ]
    ),
    "weather_reason_regular": UserIntentConfig(
        intent_name="weather_reason_regular",
        intensity_level=AdversarialIntensity.WEAK,
        description="天气原因改签（普通会员）",
        keywords=["天气", "改签"],
        examples=[
            "你好，我看天气预报说目的地有暴雨。",
            "我的航班还能正常起飞吗？能不能改签？",
            "因为是天气原因，应该不用我承担费用吧？"
        ]
    ),
    "weather_reason_vip": UserIntentConfig(
        intent_name="weather_reason_vip",
        intensity_level=AdversarialIntensity.WEAK,
        description="天气原因改签（VIP）",
        keywords=["天气", "VIP"],
        examples=[
            "你好，目的地有严重天气，我的航班受影响。",
            "作为VIP会员，我期望能有更优的解决方案。",
            "能为我安排到更便利的航班吗？"
        ]
    ),
    "weather_reason_blacklist": UserIntentConfig(
        intent_name="weather_reason_blacklist",
        intensity_level=AdversarialIntensity.WEAK,
        description="天气原因改签（黑名单）",
        keywords=["天气", "改签"],
        examples=[
            "我的航班因为天气原因可能取消。",
            "我能改签吗？什么时候可以改？",
            "我急着出发，能尽快处理吗？"
        ]
    ),

    # ==================== 投诉分支 ====================
    "complaint_regular_normal_emotion": UserIntentConfig(
        intent_name="complaint_regular_normal_emotion",
        intensity_level=AdversarialIntensity.WEAK,
        description="投诉-普通会员情绪正常",
        keywords=["投诉", "理性"],
        examples=[
            "你好，我想投诉一下服务。",
            "最近我遭遇了一些问题，想了解怎么处理。",
            "能帮我看一下吗？"
        ]
    ),
    "complaint_regular_urgent_invalid_doc": UserIntentConfig(
        intent_name="complaint_regular_urgent_invalid_doc",
        intensity_level=AdversarialIntensity.STRONG,
        description="投诉-普通会员紧急情绪无凭证",
        keywords=["投诉", "生气"],
        examples=[
            "我非常生气！我的航班出问题了！",
            "你们必须给我一个说法！",
            "我早就应该投诉你们了！"
        ]
    ),
    "complaint_regular_dissatisfied_valid_doc": UserIntentConfig(
        intent_name="complaint_regular_dissatisfied_valid_doc",
        intensity_level=AdversarialIntensity.STRONG,
        description="投诉-普通会员不满情绪有凭证",
        keywords=["投诉", "延误", "赔偿"],
        examples=[
            "我要投诉！航班延误3小时，我的会议都错过了！",
            "这是你们航司的责任，必须给我一个说法！",
            "我有延误证明，你们必须赔偿！"
        ]
    ),
    "vip_complaint": UserIntentConfig(
        intent_name="vip_complaint",
        intensity_level=AdversarialIntensity.STRONG,
        description="VIP投诉转人工",
        keywords=["VIP", "投诉", "主管"],
        examples=[
            "我是VIP会员，我遭遇了严重问题！",
            "这种服务质量无法接受！",
            "我需要和主管或人工客服谈话！"
        ]
    ),
    "blacklist_complaint": UserIntentConfig(
        intent_name="blacklist_complaint",
        intensity_level=AdversarialIntensity.STRONG,
        description="黑名单投诉拒绝",
        keywords=["投诉", "黑名单"],
        examples=[
            "我要投诉！我要投诉！",
            "你们的服务太差了！",
            "我必须得到赔偿！"
        ]
    )
}

AIRLINE_REFUND_CLASSIFICATION_FIELDS = {
    "CoreDemand": ClassificationFieldConfig(
        field_name="CoreDemand",
        data_type="str",
        options=["RescheduleOrRefund", "Complaint", "Inqury"],
        description="用户核心诉求 - 改签退票、投诉还是查询"
    ),
    "ChangeReason": ClassificationFieldConfig(
        field_name="ChangeReason",
        data_type="str",
        options=["Personal", "Airline", "Weather"],
        description="改退签原因 - 个人原因、航司原因还是天气原因"
    ),
    "UserEmotion": ClassificationFieldConfig(
        field_name="UserEmotion",
        data_type="str",
        options=["Urgent", "Dissatisfied", "Normal"],
        description="用户情绪状态 - 紧急、不满还是正常"
    ),
    "DocumentValidity": ClassificationFieldConfig(
        field_name="DocumentValidity",
        data_type="str",
        options=["Valid", "Invalid"],
        description="是否提供合理凭证 - 投诉凭证是否充分有效"
    ),
    "IsInfoComplete": ClassificationFieldConfig(
        field_name="IsInfoComplete",
        data_type="str",
        options=["Complete", "Incomplete"],
        description="信息是否完善 - 是否提供了航班号等必要信息"
    )
}

AIRLINE_REFUND_ACTIONS = {
    "RescheduleOrRefund": ActionConfig(
        action_name="RescheduleOrRefund",
        description="办理改签或退票 - 为用户办理改签或退票",
        parameters={"type": "booking_change", "priority": "high"}
    ),
    "Supplementary": ActionConfig(
        action_name="Supplementary",
        description="补充信息 - 要求用户提供订单号、航班号等信息",
        parameters={"type": "information_collection", "priority": "medium"}
    ),
    "TransHuman": ActionConfig(
        action_name="TransHuman",
        description="转人工处理 - 将复杂问题转接人工客服",
        parameters={"type": "escalation", "priority": "high"}
    ),
    "Reject": ActionConfig(
        action_name="Reject",
        description="拒绝 - 委婉拒绝不符合规则的请求",
        parameters={"type": "rejection", "priority": "medium"}
    ),
    "RescheduleOrRefund+Compensation": ActionConfig(
        action_name="RescheduleOrRefund+Compensation",
        description="办理改签或退票并赔偿 - 由航司或天气原因导致，提供赔偿",
        parameters={"type": "compensation", "priority": "high"}
    ),
    "Comfort": ActionConfig(
        action_name="Comfort",
        description="安抚用户 - 对不满或焦虑用户进行安抚",
        parameters={"type": "emotion_management", "priority": "medium"}
    ),
    "Enquiry": ActionConfig(
        action_name="Enquiry",
        description="告知航班详情 - 提供航班信息查询服务",
        parameters={"type": "information_provision", "priority": "medium"}
    ),
    "RescheduleOrRefund+HandlingFee": ActionConfig(
        action_name="RescheduleOrRefund+HandlingFee",
        description="办理改签或退票并收费 - 需要支付手续费",
        parameters={"type": "payment", "priority": "medium"}
    ),
    "Compensation": ActionConfig(
        action_name="Compensation",
        description="赔偿 - 提供赔偿方案",
        parameters={"type": "compensation", "priority": "high"}
    )
}

AIRLINE_REFUND_EVALUATION_METRICS = {
    "classification_accuracy": EvaluationMetricConfig(
        metric_name="classification_accuracy",
        metric_type="code_computed",
        description="分类字段正确率 - 所有5个分类字段的准确度",
        weight=0.3
    ),
    "path_correctness": EvaluationMetricConfig(
        metric_name="path_correctness",
        metric_type="code_computed",
        description="SOP路径正确性 - 是否遵循正确的SOP流程路径",
        weight=0.3
    ),
    "action_correctness": EvaluationMetricConfig(
        metric_name="action_correctness",
        metric_type="code_computed",
        description="动作正确性 - 最终输出的动作是否正确",
        weight=0.2
    ),
    "chat_quality": EvaluationMetricConfig(
        metric_name="chat_quality",
        metric_type="model_judged",
        description="话术质量 - 模型回复的自然性、准确性和客户友好度",
        weight=0.2
    )
}

AIRLINE_REFUND_SOP_STEPS = [
    "step1_classification",
    "step2_core_demand",
    "step3_change_reason",
    "step4_member_level",
    "step5_info_completeness",
    "step6_emotion_status",
    "step7_insurance_check",
    "step8_document_validity",
    "step_final_action"
]

AIRLINE_REFUND_CONFIG = ScenarioConfig(
scenario_id="airline_refund",
scenario_name="在线航司改签退票",
description="在线航司改签退票、航班投诉、航班信息查询等多场景",
    user_intents=AIRLINE_REFUND_INTENTS,
    classification_fields=AIRLINE_REFUND_CLASSIFICATION_FIELDS,
    actions=AIRLINE_REFUND_ACTIONS,
    evaluation_metrics=AIRLINE_REFUND_EVALUATION_METRICS,
    sop_steps=AIRLINE_REFUND_SOP_STEPS,
    initial_state_template={
        "memberLevel": "",
        "hasInsurance": False,
        "user_profile": {},
        "dialogue_history": []
    }
)


def get_scenario_config(scenario_id: str) -> ScenarioConfig:
    """
    根据场景ID获取场景配置
    
    Args:
        scenario_id: 场景ID
        
    Returns:
        ScenarioConfig: 场景配置对象
        
    Raises:
        ValueError: 未知的场景ID
    
    支持的场景:
        - online_education: 在线教育平台客服
        - ecommerce_refund: 电商退款 (待完成)
        - telecom_package: 电信套餐办理 (待完成)
- property_service: 物业服务 (待完成)
- logistics_delivery: 快递物流 (待完成)
- airline_refund: 在线航司改签退票 (待完成)
    """
    configs = {
    "online_education": ONLINE_EDUCATION_CONFIG,
    "ecommerce_refund": ECOMMERCE_REFUND_CONFIG,
    "telecom_package": TELECOM_PACKAGE_CONFIG,
    "property_service": PROPERTY_SERVICE_CONFIG,
    "logistics_delivery": LOGISTICS_DELIVERY_CONFIG,
    "airline_refund": AIRLINE_REFUND_CONFIG,
}
    
    if scenario_id not in configs:
        raise ValueError(f"Unknown scenario_id: {scenario_id}. Available: {list(configs.keys())}")
    
    return configs[scenario_id]


def list_available_scenarios() -> List[str]:
    """获取所有可用的场景ID列表"""
    return [
        "online_education",
        "ecommerce_refund",
        "telecom_package",
        "property_service",
        "logistics_delivery",
        "airline_refund",
    ]
