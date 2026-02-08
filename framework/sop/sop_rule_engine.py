#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SOP规则引擎
SOP Rule Engine

功能：
1. 根据classification_output计算正确的now_path
2. 根据classification_output计算正确的finals
3. 为每个场景实现具体的规则映射逻辑

规则：classification_output → now_path / finals
"""

from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class ScenarioType(Enum):
    """场景类型"""
    ONLINE_EDUCATION = "online_education"
    ECOMMERCE_REFUND = "ecommerce_refund"
    TELECOM_PACKAGE = "telecom_package"
    PROPERTY_SERVICE = "property_service"
    LOGISTICS_DELIVERY = "logistics_delivery"
    AIRLINE_REFUND = "airline_refund"


@dataclass
class SOPRuleResult:
    """SOP规则计算结果"""
    now_path: List[str]  # 正确的路径序列 ["step1", "step2", ...]
    finals: Dict[str, Any]  # 最终输出 {"Action": "...", "PLAN": "...", ...}
    reasoning: str = ""  # 推理过程
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "now_path": self.now_path,
            "finals": self.finals,
            "reasoning": self.reasoning,
        }


class BaseSOPRuleEngine:
    """SOP规则引擎基类"""
    
    def __init__(self, scenario_type: ScenarioType):
        self.scenario_type = scenario_type
    
    def compute_correct_path_and_finals(
        self,
        classification_output: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> SOPRuleResult:
        """
        根据分类输出计算正确的路径和最终动作
        
        Args:
            classification_output: 分类字段结果
            context: 额外上下文信息（如用户风险等级等）
            
        Returns:
            SOPRuleResult: 包含now_path和finals的结果
        """
        raise NotImplementedError("Subclasses must implement this method")


class OnlineEducationSOPRuleEngine(BaseSOPRuleEngine):
    """在线教育场景的SOP规则引擎
    
    SOP流程：
    1. 字段分类 (step1)
    2. 问题确认 (step2): DescriptionClear
    3. 课程关联性确认 (step3): QuestionRelevance  
    4. 重复反馈检查 (step4): RepeatedRaised
    5. 情绪检查 (step5): EmotionTendency
    6. 资源分配 (step6): ResolveDependency + QuestionRelevance
    7. 退费分支 (step7): RegardingRefund
    8. 财务审核 (step8): isRiskUser
    """
    
    def __init__(self):
        super().__init__(ScenarioType.ONLINE_EDUCATION)
    
    def compute_correct_path_and_finals(
        self,
        classification_output: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> SOPRuleResult:
        """
        在线教育场景的规则实现
        
        规则映射：
        - DescriptionClear=false → GUIDE
        - DescriptionClear=true → 继续
        - QuestionRelevance=false → 跳转到资源分配
        - RepeatedRaised=true → REVIEW
        - EmotionTendency=Dissatisfied → COMFORT
        - 资源分配：ResolveDependency + QuestionRelevance → PLAN_A/B/C/D/E/F
        - RegardingRefund=true + isRiskUser=true → NEGOTIATE
        - RegardingRefund=true + isRiskUser=false → REFUND
        """
        context = context or {}
        path = ["step1"]  # 从分类开始
        reasoning_steps = []
        
        # 提取分类字段
        desc_clear = classification_output.get("DescriptionClear")
        question_rel = classification_output.get("QuestionRelevance")
        emotion = classification_output.get("EmotionTendency")
        resolve_dep = classification_output.get("ResolveDependency")
        repeated = classification_output.get("RepeatedRaised")
        refund = classification_output.get("RegardingRefund")
        
        # 从context["system_info"]获取系统信息
        system_info = context.get("system_info", {})
        is_risk_user = system_info.get("isRiskUser", False)
        
        # Step 2: 问题确认
        path.append("step2")
        reasoning_steps.append(f"step2: 问题确认 - DescriptionClear={desc_clear}")
        
        if desc_clear == False:
            # 问题不清楚，执行GUIDE
            finals = {"Action": "GUIDE", "PLAN": "none"}
            reasoning = " → ".join(reasoning_steps) + " → 执行GUIDE"
            return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
        
        # Step 3: 课程关联性确认
        path.append("step3")
        reasoning_steps.append(f"step3: 课程关联性 - QuestionRelevance={question_rel}")
        
        if question_rel == True:
            # 课程相关，检查重复反馈
            path.append("step4")
            reasoning_steps.append(f"step4: 重复检查 - RepeatedRaised={repeated}")
            
            if repeated == True:
                # 重复反馈，执行REVIEW
                finals = {"Action": "REVIEW", "PLAN": "none"}
                reasoning = " → ".join(reasoning_steps) + " → 执行REVIEW"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            
            # Step 5: 情绪检查
            path.append("step5")
            reasoning_steps.append(f"step5: 情绪检查 - EmotionTendency={emotion}")
            
            if emotion == "Dissatisfied":
                # 用户不满，执行COMFORT
                finals = {"Action": "COMFORT", "PLAN": "none"}
                reasoning = " → ".join(reasoning_steps) + " → 执行COMFORT"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
        
        # Step 6: 资源分配
        path.append("step6")
        reasoning_steps.append(f"step6: 资源分配 - ResolveDependency={resolve_dep}, QuestionRelevance={question_rel}")
        
        # 确定PLAN
        plan = self._compute_plan(question_rel, resolve_dep)
        reasoning_steps.append(f"分配方案: {plan}")
        
        # Step 7: 退费分支
        path.append("step7")
        reasoning_steps.append(f"step7: 退费检查 - RegardingRefund={refund}")
        
        if refund == False:
            # 不涉及退费，执行PLAN
            finals = {"Action": "PLAN", "PLAN": plan}
            reasoning = " → ".join(reasoning_steps) + f" → 执行PLAN={plan}"
            return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
        
        # Step 8: 财务审核
        path.append("step8")
        reasoning_steps.append(f"step8: 财务审核 - isRiskUser={is_risk_user}")
        
        if is_risk_user:
            # 风险用户，执行NEGOTIATE
            finals = {"Action": "NEGOTIATE", "PLAN": "none"}
            reasoning = " → ".join(reasoning_steps) + " → 执行NEGOTIATE"
        else:
            # 非风险用户，执行REFUND
            finals = {"Action": "REFUND", "PLAN": "none"}
            reasoning = " → ".join(reasoning_steps) + " → 执行REFUND"
        
        return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
    
    def _compute_plan(self, question_rel: bool, resolve_dep: Optional[str]) -> str:
        """
        计算资源分配方案
        
        规则：
        - 课程相关 + 高依赖 → PLAN_A
        - 课程相关 + 中依赖 → PLAN_B
        - 课程相关 + 低依赖 → PLAN_C
        - 非课程 + 高依赖 → PLAN_D
        - 非课程 + 中依赖 → PLAN_E
        - 非课程 + 低依赖 → PLAN_F
        """
        if question_rel:
            if resolve_dep == "HighDependency":
                return "PLAN_A"
            elif resolve_dep == "MediumDependency":
                return "PLAN_B"
            else:  # LowDependency or None
                return "PLAN_C"
        else:
            if resolve_dep == "HighDependency":
                return "PLAN_D"
            elif resolve_dep == "MediumDependency":
                return "PLAN_E"
            else:  # LowDependency or None
                return "PLAN_F"


class EcommerceRefundSOPRuleEngine(BaseSOPRuleEngine):
    """电商退款场景的SOP规则引擎
    
    SOP流程：
    1. 字段分类 (step1): CoreIntention, ProvidedDocument, Responsibility, RefundReasonable, EmotionStatus
    2. 核心诉求判断 (step2): CoreIntention判断
    3. 物流状态 (step3): ShippingStatus判断
    4. 用户信用等级 (step4): CreditLevel判断
    5. 责任判定 (step5): Responsibility判断
    6. 退款理由是否合理 (step6): RefundReasonable判断
    7. 用户情绪状态 (step7): EmotionStatus判断
    8. 是否提供凭证 (step8): ProvidedDocument判断
    """
    
    def __init__(self):
        super().__init__(ScenarioType.ECOMMERCE_REFUND)
    
    def compute_correct_path_and_finals(
        self,
        classification_output: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> SOPRuleResult:
        """电商退款场景的规则实现"""
        context = context or {}
        path = ["step1"]
        reasoning_steps = []
        
        # 提取分类字段
        core_intent = classification_output.get("CoreIntention")
        provided_doc = classification_output.get("ProvidedDocument")
        responsibility = classification_output.get("Responsibility")
        refund_reasonable = classification_output.get("RefundReasonable")
        emotion_status = classification_output.get("EmotionStatus")
        
        # 从context获取系统变量
        system_info = context.get("system_info", {})
        shipping_status = system_info.get("ShippingStatus")
        credit_level = system_info.get("CreditLevel")
        
        # Step 2: 核心诉求判断
        path.append("step2")
        reasoning_steps.append(f"step2: 核心诉求判断 - CoreIntention={core_intent}")
        
        # Step 3: 物流状态判断
        path.append("step3")
        reasoning_steps.append(f"step3: 物流状态 - ShippingStatus={shipping_status}")
        
        if core_intent == "Exchange":
            # Exchange分支
            if shipping_status == "Unshipped":
                finals = {"Action": "Exchange"}
                reasoning = " → ".join(reasoning_steps) + " → 执行Exchange"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            elif shipping_status == "Shipping":
                finals = {"Action": "Interception"}
                reasoning = " → ".join(reasoning_steps) + " → 执行Interception"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            else:  # Signed
                # Step 4: 用户信用等级
                path.append("step4")
                reasoning_steps.append(f"step4: 用户信用等级 - CreditLevel={credit_level}")
                
                if credit_level in ["High", "Medium"]:
                    finals = {"Action": "Exchange"}
                else:  # Low
                    finals = {"Action": "PayFee"}
                reasoning = " → ".join(reasoning_steps) + f" → 执行{finals['Action']}"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
        
        else:  # ReturnOrRefund
            if shipping_status == "Unshipped":
                finals = {"Action": "Refund"}
                reasoning = " → ".join(reasoning_steps) + " → 执行Refund"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            elif shipping_status == "Shipping":
                finals = {"Action": "Interception"}
                reasoning = " → ".join(reasoning_steps) + " → 执行Interception"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            else:  # Signed
                # Step 5: 责任判定
                path.append("step5")
                reasoning_steps.append(f"step5: 责任判定 - Responsibility={responsibility}")
                
                if responsibility == "User":
                    # User责任分支 → step4
                    path.append("step4")
                    reasoning_steps.append(f"step4: 用户信用等级 - CreditLevel={credit_level}")
                    
                    if credit_level in ["High", "Medium"]:
                        # 高中信用直接揽收
                        finals = {"Action": "CollectionService"}
                    else:  # Low
                        # 低信用需要进入 step6: 退款理由是否合理
                        path.append("step6")
                        reasoning_steps.append(f"step6: 退款理由是否合理 - RefundReasonable={refund_reasonable}")
                        
                        if refund_reasonable == "Reasonable":
                            # Reasonable → step8
                            path.append("step8")
                            reasoning_steps.append(f"step8: 是否提供凭证 - ProvidedDocument={provided_doc}")
                            
                            if provided_doc:
                                finals = {"Action": "CollectionService"}
                            else:  # False
                                finals = {"Action": "Supplementary"}
                        else:  # Unreasonable
                            finals = {"Action": "Reject"}
                
                else:  # Merchant责任
                    # Merchant责任分支 → step4
                    path.append("step4")
                    reasoning_steps.append(f"step4: 用户信用等级 - CreditLevel={credit_level}")
                    
                    if credit_level == "High":
                        finals = {"Action": "Comfort+Compensation"}
                    else:  # Medium or Low
                        # 需要进入 step7: 用户情绪状态
                        path.append("step7")
                        reasoning_steps.append(f"step7: 用户情绪状态 - EmotionStatus={emotion_status}")
                        
                        if emotion_status == "Calm":
                            finals = {"Action": "CollectionService"}
                        else:  # Dissatisfied
                            finals = {"Action": "Comfort"}
                
                reasoning = " → ".join(reasoning_steps) + f" → 执行{finals['Action']}"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)


class TelecomPackageSOPRuleEngine(BaseSOPRuleEngine):
    """电信套餐场景的SOP规则引擎
    
    SOP流程：
    1. 字段分类 (step1): ConsumptionType, ApplicationTendency, ConsumptionProfile, EmotionTag
    2. 消费意图 (step2): ConsumptionType判断 (Enquiry/Change/Cancel)
    3. 消费画像 (step3): ConsumptionProfile判断 (仅Enquiry)
    4. 套餐状态 (step4): PackageStatus判断
    5. 违约金情况 (step5): Penalty判断
    6. 办理倾向 (step6): ApplicationTendency判断 (仅Enquiry)
    7. 情绪判断 (step7): EmotionTag判断
    """
    
    def __init__(self):
        super().__init__(ScenarioType.TELECOM_PACKAGE)
    
    def compute_correct_path_and_finals(
        self,
        classification_output: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> SOPRuleResult:
        """电信套餐场景的规则实现"""
        context = context or {}
        path = ["step1"]
        reasoning_steps = []
        
        # 提取分类字段
        consumption_type = classification_output.get("ConsumptionType")
        app_tendency = classification_output.get("ApplicationTendency")
        consumption_profile = classification_output.get("ConsumptionProfile")
        emotion_tag = classification_output.get("EmotionTag")
        
        # 从context获取系统变量
        system_info = context.get("system_info", {})
        package_status = system_info.get("PackageStatus")
        penalty = system_info.get("Penalty", 0)
        
        # Step 2: 消费意图判断
        path.append("step2")
        reasoning_steps.append(f"step2: 消费意图 - ConsumptionType={consumption_type}")
        
        if consumption_type == "Enquiry":
            # Step 3: 消费画像判断
            path.append("step3")
            reasoning_steps.append(f"step3: 消费画像 - ConsumptionProfile={consumption_profile}")
            
            # Step 6: 办理倾向判断
            path.append("step6")
            reasoning_steps.append(f"step6: 办理倾向 - ApplicationTendency={app_tendency}")
            
            if app_tendency in ["Reject", "Hesitate"]:
                finals = {"Action": "GoodBye"}
                reasoning = " → ".join(reasoning_steps) + " → 执行GoodBye"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            
            # Agree情况，继续step4
            path.append("step4")
            reasoning_steps.append(f"step4: 套餐状态 - PackageStatus={package_status}")
            
            if package_status == "NoContract":
                finals = {"Action": "ChangeOrder"}
                reasoning = " → ".join(reasoning_steps) + " → 执行ChangeOrder"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            
            # Contracted，进入step5
            path.append("step5")
            reasoning_steps.append(f"step5: 违约金情况 - Penalty={penalty}")
            
            if penalty == 0:
                finals = {"Action": "ChangeOrder"}
            else:
                # Step 7: 情绪判断
                path.append("step7")
                reasoning_steps.append(f"step7: 情绪判断 - EmotionTag={emotion_tag}")
                
                if emotion_tag == "Calm":
                    finals = {"Action": "ChangeOrder"}
                else:  # Discontent
                    finals = {"Action": "TransHuman"}
        
        elif consumption_type == "Change":
            # Step 4: 套餐状态判断
            path.append("step4")
            reasoning_steps.append(f"step4: 套餐状态 - PackageStatus={package_status}")
            
            if package_status == "NoContract":
                finals = {"Action": "ChangeOrder"}
                reasoning = " → ".join(reasoning_steps) + " → 执行ChangeOrder"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            
            # Contracted，进入step5
            path.append("step5")
            reasoning_steps.append(f"step5: 违约金情况 - Penalty={penalty}")
            
            if penalty == 0:
                finals = {"Action": "ChangeOrder"}
            else:
                # Step 7: 情绪判断
                path.append("step7")
                reasoning_steps.append(f"step7: 情绪判断 - EmotionTag={emotion_tag}")
                
                if emotion_tag == "Calm":
                    finals = {"Action": "ChangeOrder"}
                else:  # Discontent
                    finals = {"Action": "TransHuman"}
        
        else:  # Cancel
            # Step 5: 违约金情况判断
            path.append("step5")
            reasoning_steps.append(f"step5: 违约金情况 - Penalty={penalty}")
            
            if penalty == 0:
                finals = {"Action": "ChangeOrder"}
                reasoning = " → ".join(reasoning_steps) + " → 执行ChangeOrder"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            
            # 有违约金，进入step7
            path.append("step7")
            reasoning_steps.append(f"step7: 情绪判断 - EmotionTag={emotion_tag}")
            
            if emotion_tag == "Calm":
                finals = {"Action": "ChangeOrder"}
            else:  # Discontent
                finals = {"Action": "TransHuman"}
        
        reasoning = " → ".join(reasoning_steps) + f" → 执行{finals['Action']}"
        return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)


class PropertyServiceSOPRuleEngine(BaseSOPRuleEngine):
    """物业服务场景的SOP规则引擎
    
    SOP流程：
    1. 字段分类 (step1): CoreIntention, EmotionTag, RepairItemCategory, RelatedScope, EmergencyLevel
    2. 业主核心意图判断 (step2): CoreIntention判断 (Payment/Complaint/Repair)
    3. 业主房屋状态判断 (step3): HouseStatus判断 (仅Payment/Complaint)
    4. 报修事项类别判断 (step4): RepairItemCategory判断 (仅Repair)
    5. 事项关联范围判断 (step5): RelatedScope判断 (仅Repair)
    6. 物业费缴纳情况 (step6): FeePaymentStatus判断
    7. 业主情绪状态判断 (step7): EmotionTag判断 (仅Complaint)
    8. 事项紧急程度判断 (step8): EmergencyLevel判断 (Repair时所有路径都需要)
    """
    
    def __init__(self):
        super().__init__(ScenarioType.PROPERTY_SERVICE)
    
    def compute_correct_path_and_finals(
        self,
        classification_output: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> SOPRuleResult:
        """物业服务场景的规则实现"""
        context = context or {}
        path = ["step1"]
        reasoning_steps = []
        
        # 提取分类字段
        core_intent = classification_output.get("CoreIntention")
        emotion_tag = classification_output.get("EmotionTag")
        repair_category = classification_output.get("RepairItemCategory")
        related_scope = classification_output.get("RelatedScope")
        emergency_level = classification_output.get("EmergencyLevel")
        
        # 从context获取系统变量
        system_info = context.get("system_info", {})
        house_status = system_info.get("HouseStatus")
        fee_status = system_info.get("FeePaymentStatus")
        
        # Step 2: 业主核心意图判断
        path.append("step2")
        reasoning_steps.append(f"step2: 业主核心意图判断 - CoreIntention={core_intent}")
        
        if core_intent == "Payment":
            # Payment分支 → step3
            # Step 3: 业主房屋状态判断
            path.append("step3")
            reasoning_steps.append(f"step3: 业主房屋状态判断 - HouseStatus={house_status}")
            
            if house_status == "UnOccupied":
                finals = {"Action": "PayInformation"}
                reasoning = " → ".join(reasoning_steps) + " → 执行PayInformation"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            
            # Occupied/Rented → Step 6
            # Step 6: 物业费缴纳情况
            path.append("step6")
            reasoning_steps.append(f"step6: 物业费缴纳情况 - FeePaymentStatus={fee_status}")
            
            if fee_status == "Settled":
                finals = {"Action": "PayInformation"}
            else:  # Unpaid
                finals = {"Action": "Payment"}
            
            reasoning = " → ".join(reasoning_steps) + f" → 执行{finals['Action']}"
            return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
        
        elif core_intent == "Complaint":
            # Complaint分支 → step3
            # Step 3: 业主房屋状态判断
            path.append("step3")
            reasoning_steps.append(f"step3: 业主房屋状态判断 - HouseStatus={house_status}")
            
            if house_status == "UnOccupied":
                # UnOccupied → step7
                path.append("step7")
                reasoning_steps.append(f"step7: 业主情绪状态判断 - EmotionTag={emotion_tag}")
                
                if emotion_tag == "Calm":
                    finals = {"Action": "Comfort"}
                else:  # Discontent
                    finals = {"Action": "TransHuman"}
                
                reasoning = " → ".join(reasoning_steps) + f" → 执行{finals['Action']}"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            else:  # Occupied or Rented
                # Occupied/Rented → step6
                # Step 6: 物业费缴纳情况
                path.append("step6")
                reasoning_steps.append(f"step6: 物业费缴纳情况 - FeePaymentStatus={fee_status}")
                
                if fee_status == "Unpaid":
                    finals = {"Action": "Payment"}
                    reasoning = " → ".join(reasoning_steps) + " → 执行Payment"
                    return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
                else:  # Settled
                    # Settled → step7
                    # Step 7: 业主情绪状态判断
                    path.append("step7")
                    reasoning_steps.append(f"step7: 业主情绪状态判断 - EmotionTag={emotion_tag}")
                    
                    if emotion_tag == "Calm":
                        finals = {"Action": "Comfort"}
                    else:  # Discontent
                        finals = {"Action": "TransHuman"}
        
        else:  # Repair
            # Repair分支 → step4
            # Step 4: 报修事项类别判断
            path.append("step4")
            reasoning_steps.append(f"step4: 报修事项类别判断 - RepairItemCategory={repair_category}")
            
            # Step 5: 事项关联范围判断
            path.append("step5")
            reasoning_steps.append(f"step5: 事项关联范围判断 - RelatedScope={related_scope}")
            
            if related_scope == "Personal":
                # Personal → step6
                # Step 6: 物业费缴纳情况
                path.append("step6")
                reasoning_steps.append(f"step6: 物业费缴纳情况 - FeePaymentStatus={fee_status}")
                
                if fee_status == "Unpaid":
                    finals = {"Action": "Reject"}
                    reasoning = " → ".join(reasoning_steps) + " → 执行Reject"
                    return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
                # Settled → 继续到step8判断紧急程度
            
            # Personal+Settled 和 Public 都需要判断紧急程度
            # Step 8: 事项紧急程度判断
            path.append("step8")
            reasoning_steps.append(f"step8: 事项紧急程度判断 - EmergencyLevel={emergency_level}")
            
            if emergency_level == "Urgent":
                finals = {"Action": "TransHuman"}
            else:  # NoUrgent
                finals = {"Action": "Registration"}
        
        reasoning = " → ".join(reasoning_steps) + f" → 执行{finals['Action']}"
        return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)


class LogisticsDeliverySOPRuleEngine(BaseSOPRuleEngine):
    """快递物流场景的SOP规则引擎
    
    SOP流程：
    1. 字段分类 (step1): RiskStatus, InfoCompleteness, UserIntention, EmotionalState, EmergencyLevel, ComplaintValidity
    2. 风险控制标签 (step2): RiskStatus判断
    3. 信息完整度判断 (step3): InfoCompleteness判断
    4. 用户意图判断 (step4): UserIntention判断
    5. 订单状态查询 (step5): orderStatus判断
    6. 订单紧急程度判断 (step6): EmergencyLevel判断
    7. 投诉合理性判断 (step7): ComplaintValidity判断
    8. 是否有保险 (step8): hasInsurance判断
    9. 用户情绪状态判断 (step9): EmotionalState判断
    """
    
    def __init__(self):
        super().__init__(ScenarioType.LOGISTICS_DELIVERY)
    
    def compute_correct_path_and_finals(
        self,
        classification_output: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> SOPRuleResult:
        """快递物流场景的规则实现"""
        context = context or {}
        path = ["step1"]
        reasoning_steps = []
        
        # 提取分类字段
        risk_status = classification_output.get("RiskStatus")
        info_complete = classification_output.get("InfoCompleteness")
        user_intention = classification_output.get("UserIntention")
        emotional_state = classification_output.get("EmotionalState")
        emergency_level = classification_output.get("EmergencyLevel")
        complaint_validity = classification_output.get("ComplaintValidity")
        
        # 从context获取系统变量
        system_info = context.get("system_info", {})
        order_status = system_info.get("orderStatus")
        has_insurance = system_info.get("hasInsurance", False)
        
        # Step 2: 风险控制标签
        path.append("step2")
        reasoning_steps.append(f"step2: 风险控制标签 - RiskStatus={risk_status}")
        
        if risk_status == "Risk":
            finals = {"Action": "Interception"}
            reasoning = " → ".join(reasoning_steps) + " → 执行Interception"
            return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
        
        # Step 3: 信息完整度判断
        path.append("step3")
        reasoning_steps.append(f"step3: 信息完整度判断 - InfoCompleteness={info_complete}")
        
        if not info_complete:
            finals = {"Action": "Supplementary"}
            reasoning = " → ".join(reasoning_steps) + " → 执行Supplementary"
            return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
        
        # Step 4: 用户意图判断
        path.append("step4")
        reasoning_steps.append(f"step4: 用户意图判断 - UserIntention={user_intention}")
        
        # Step 5: 订单状态查询
        path.append("step5")
        reasoning_steps.append(f"step5: 订单状态查询 - orderStatus={order_status}")
        
        if user_intention == "Urge":
            # Urge分支
            if order_status == "Arrived":
                finals = {"Action": "Detail"}
                reasoning = " → ".join(reasoning_steps) + " → 执行Detail"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            else:  # Delivered or Undelivered
                # Step 6: 订单紧急程度判断
                path.append("step6")
                reasoning_steps.append(f"step6: 订单紧急程度判断 - EmergencyLevel={emergency_level}")
                
                if emergency_level == "Urgent":
                    finals = {"Action": "Registration"}
                else:  # Normal
                    finals = {"Action": "Detail"}
        
        elif user_intention == "Modify":
            # Modify分支
            if order_status == "Arrived":
                finals = {"Action": "Reject"}
                reasoning = " → ".join(reasoning_steps) + " → 执行Reject"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            elif order_status == "Delivered":
                finals = {"Action": "MakeUpDifference"}
                reasoning = " → ".join(reasoning_steps) + " → 执行MakeUpDifference"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            else:  # Undelivered
                finals = {"Action": "Modify"}
                reasoning = " → ".join(reasoning_steps) + " → 执行Modify"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
        
        else:  # Complaint
            # Complaint分支
            if order_status == "Arrived":
                # Step 7: 投诉合理性判断
                path.append("step7")
                reasoning_steps.append(f"step7: 投诉合理性判断 - ComplaintValidity={complaint_validity}")
                
                if not complaint_validity:
                    finals = {"Action": "Comfort"}
                    reasoning = " → ".join(reasoning_steps) + " → 执行Comfort"
                    return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
                
                # Valid → Step 8: 是否有保险
                path.append("step8")
                reasoning_steps.append(f"step8: 是否有保险 - hasInsurance={has_insurance}")
                
                if has_insurance:
                    finals = {"Action": "Compensation"}
                    reasoning = " → ".join(reasoning_steps) + " → 执行Compensation"
                    return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
                else:  # False
                    # Step 9: 用户情绪状态判断
                    path.append("step9")
                    reasoning_steps.append(f"step9: 用户情绪状态判断 - EmotionalState={emotional_state}")
                    
                    if emotional_state == "Calm":
                        finals = {"Action": "Comfort"}
                    else:  # Dissatisfied
                        finals = {"Action": "TransHuman"}
            else:  # Delivered or Undelivered
                # Step 6: 订单紧急程度判断
                path.append("step6")
                reasoning_steps.append(f"step6: 订单紧急程度判断 - EmergencyLevel={emergency_level}")
                
                if emergency_level == "Urgent":
                    finals = {"Action": "Registration"}
                else:  # Normal
                    finals = {"Action": "Detail"}
        
        reasoning = " → ".join(reasoning_steps) + f" → 执行{finals['Action']}"
        return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)


class AirlineRefundSOPRuleEngine(BaseSOPRuleEngine):
    """在线旅游/航司改签退票场景的SOP规则引擎
    
    SOP流程：
    1. 字段分类 (step1): CoreDemand, ChangeReason, UserEmotion, DocumentValidity, IsInfoComplete
    2. 核心诉求判断 (step2): CoreDemand判断
    3. 变更原因 (step3): ChangeReason判断 (仅RescheduleOrRefund)
    4. 会员等级 (step4): memberLevel判断
    5. 信息是否完善 (step5): IsInfoComplete判断
    6. 用户情绪状态判断 (step6): UserEmotion判断
    7. 是否购买保险 (step7): hasInsurance判断 (仅Personal+Regular)
    8. 凭证是否合理 (step8): DocumentValidity判断
    """
    
    def __init__(self):
        super().__init__(ScenarioType.AIRLINE_REFUND)
    
    def compute_correct_path_and_finals(
        self,
        classification_output: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> SOPRuleResult:
        """政企服务场景的规则实现"""
        context = context or {}
        path = ["step1"]
        reasoning_steps = []
        
        # 提取分类字段
        core_demand = classification_output.get("CoreDemand")
        change_reason = classification_output.get("ChangeReason")
        user_emotion = classification_output.get("UserEmotion")
        doc_validity = classification_output.get("DocumentValidity")
        info_complete = classification_output.get("IsInfoComplete")
        
        # 从context获取系统变量
        system_info = context.get("system_info", {})
        member_level = system_info.get("memberLevel")
        has_insurance = system_info.get("hasInsurance", False)
        
        # Step 2: 核心诉求判断
        path.append("step2")
        reasoning_steps.append(f"step2: 核心诉求判断 - CoreDemand={core_demand}")
        
        if core_demand == "Inqury":
            # Inqury分支 → step5
            path.append("step5")
            reasoning_steps.append(f"step5: 信息是否完善 - IsInfoComplete={info_complete}")
            
            if info_complete == "Incomplete":
                finals = {"Action": "Supplementary"}
            else:  # Complete
                finals = {"Action": "Enquiry"}
            
            reasoning = " → ".join(reasoning_steps) + f" → 执行{finals['Action']}"
            return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
        
        elif core_demand == "RescheduleOrRefund":
            # RescheduleOrRefund分支 → step3
            path.append("step3")
            reasoning_steps.append(f"step3: 变更原因 - ChangeReason={change_reason}")
            
            if change_reason == "Personal":
                # Personal → step5
                path.append("step5")
                reasoning_steps.append(f"step5: 信息是否完善 - IsInfoComplete={info_complete}")
                
                if info_complete == "Incomplete":
                    finals = {"Action": "Supplementary"}
                    reasoning = " → ".join(reasoning_steps) + " → 执行Supplementary"
                    return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
                
                # Complete → step8
                path.append("step8")
                reasoning_steps.append(f"step8: 凭证是否合理 - DocumentValidity={doc_validity}")
                
                if doc_validity == "Invalid":
                    finals = {"Action": "Supplementary"}
                    reasoning = " → ".join(reasoning_steps) + " → 执行Supplementary"
                    return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
                
                # Valid → step4
                path.append("step4")
                reasoning_steps.append(f"step4: 会员等级 - memberLevel={member_level}")
                
                if member_level == "VIP":
                    finals = {"Action": "RescheduleOrRefund"}
                elif member_level == "Blacklist":
                    finals = {"Action": "Reject"}
                else:  # Regular
                    # Step 7: 是否购买保险
                    path.append("step7")
                    reasoning_steps.append(f"step7: 是否购买保险 - hasInsurance={has_insurance}")
                    
                    if has_insurance:
                        finals = {"Action": "RescheduleOrRefund"}
                    else:  # False
                        finals = {"Action": "RescheduleOrRefund+HandlingFee"}
            
            else:  # Airline or Weather
                # Airline/Weather → step4
                path.append("step4")
                reasoning_steps.append(f"step4: 会员等级 - memberLevel={member_level}")
                
                if member_level == "VIP":
                    finals = {"Action": "RescheduleOrRefund+Compensation"}
                else:  # Regular or Blacklist
                    finals = {"Action": "RescheduleOrRefund"}
        
        else:  # Complaint
            # Complaint分支 → step4
            path.append("step4")
            reasoning_steps.append(f"step4: 会员等级 - memberLevel={member_level}")
            
            if member_level == "VIP":
                finals = {"Action": "TransHuman"}
                reasoning = " → ".join(reasoning_steps) + " → 执行TransHuman"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            elif member_level == "Blacklist":
                finals = {"Action": "Reject"}
                reasoning = " → ".join(reasoning_steps) + " → 执行Reject"
                return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
            else:  # Regular
                # Step 6: 用户情绪状态判断
                path.append("step6")
                reasoning_steps.append(f"step6: 用户情绪状态判断 - UserEmotion={user_emotion}")
                
                if user_emotion == "Normal":
                    finals = {"Action": "Comfort"}
                    reasoning = " → ".join(reasoning_steps) + " → 执行Comfort"
                    return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)
                else:  # Urgent or Dissatisfied
                    # Step 8: 凭证是否合理
                    path.append("step8")
                    reasoning_steps.append(f"step8: 凭证是否合理 - DocumentValidity={doc_validity}")
                    
                    if doc_validity == "Invalid":
                        finals = {"Action": "Comfort"}
                    else:  # Valid
                        finals = {"Action": "Compensation"}
        
        reasoning = " → ".join(reasoning_steps) + f" → 执行{finals['Action']}"
        return SOPRuleResult(now_path=path, finals=finals, reasoning=reasoning)


def get_rule_engine(scenario_id: str) -> BaseSOPRuleEngine:
    """
    根据场景ID获取对应的规则引擎
    
    Args:
        scenario_id: 场景ID
        
    Returns:
        BaseSOPRuleEngine: 对应场景的规则引擎实例
        
    Raises:
        ValueError: 未知的场景ID
    """
    engines = {
        "online_education": OnlineEducationSOPRuleEngine(),
        "ecommerce_refund": EcommerceRefundSOPRuleEngine(),
        "telecom_package": TelecomPackageSOPRuleEngine(),
        "property_service": PropertyServiceSOPRuleEngine(),
        "logistics_delivery": LogisticsDeliverySOPRuleEngine(),
        "airline_refund": AirlineRefundSOPRuleEngine(),
    }
    
    if scenario_id not in engines:
        raise ValueError(f"Unknown scenario_id: {scenario_id}. Supported: {list(engines.keys())}")
    
    return engines[scenario_id]
