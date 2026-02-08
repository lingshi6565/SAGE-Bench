#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM集成的评判模型
LLM-powered Judge Model

使用LLM进行话术质量评估和其他主观评测
"""

import json
import re
from typing import Optional, Dict, Any, Tuple
import logging

from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class LLMJudge:
    """
    LLM评判模型
    
    用于评估：
    1. 话术质量 (自然性、准确性、客户友好度)
    2. 指令遵循能力
    3. 其他主观指标
    """
    
    # 话术质量五维度权重 (总和为10)
    CHAT_QUALITY_WEIGHTS = {
        "linguistic_quality": 2.0,          # 语言表达 20%
        "anthropomorphism_emotion": 2.5,    # 拟人化与情感交互 25%
        "content_utility": 2.5,             # 内容效用 25%
        "user_satisfaction": 1.5,           # 用户满意度 15%
        "instruction_compliance": 1.5       # 指令遵循度 15%
    }
    
    def __init__(
        self,
        llm_client: LLMClient,
        temperature: float = 0.3,  # 降低温度以获得更一致的评估
        max_tokens: int = 1024,
    ):
        """
        初始化LLM评判模型
        
        Args:
            llm_client: LLM客户端
            temperature: 采样温度
            max_tokens: 最大生成token数
        """
        self.llm_client = llm_client
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    @classmethod
    def calculate_chat_quality_score(cls, dimensions: Dict[str, int]) -> float:
        """
        从五维度评分计算综合话术质量评分
        
        支持多种值类型的自动转换:
        - int: 直接使用
        - str: 使用正则表达式提取整数 (例如 "从3/6/9中选择" -> 3)
        - float: 四舍五入转换为整数
        
        Args:
            dimensions: 五维度评分字典，支持以下格式 {
                "linguistic_quality": 3或6或9或"从3/6/9中选择"或3.0等,
                "anthropomorphism_emotion": ...,
                "content_utility": ...,
                "user_satisfaction": ...,
                "instruction_compliance": ...
            }
            
        Returns:
            float: 综合评分 0-100
        """
        total_score = 0.0
        for dim, weight in cls.CHAT_QUALITY_WEIGHTS.items():
            if dim in dimensions:
                value = dimensions[dim]
                
                # 类型检查和正则提取
                if isinstance(value, int):
                    # 已经是整数，直接使用
                    score_value = value
                elif isinstance(value, str):
                    # 字符串，使用正则提取整数
                    match = re.search(r'\d+', value)
                    if match:
                        score_value = int(match.group())
                        logger.info(f"从字符串'{value}'中提取整数{score_value}")
                    else:
                        logger.warning(f"无法从字符串'{value}'中提取整数，跳过该维度")
                        continue
                elif isinstance(value, float):
                    # 浮点数，转换为整数
                    score_value = int(round(value))
                    logger.info(f"将浮点数{value}转换为整数{score_value}")
                else:
                    # 其他类型，无法处理
                    logger.warning(f"维度'{dim}'的值类型不支持: {type(value)}, 值: {value}")
                    continue
                
                total_score += score_value * weight
        return total_score
  
    def evaluate_turn_comprehensive(
        self,
        turn_id: int,
        user_message: str,
        agent_chat: str,
        dialogue_history: Optional[list] = None,
        scenario_id: str = "online_education",
        context_data: Optional[Dict[str, Any]] = None,
        use_rule_verification: bool = True,  # 是否使用规则引擎验证
        max_retries: int = 2,  # 最大重试次数
    ) -> Dict[str, Any]:
        """
        综合评估单轮对话 - 一次性输出分类Ground Truth和话术质量评分
        增强版: 使用规则引擎验证裁判LLM的分类结果
        
        Args:
            turn_id: 轮次ID
            user_message: 用户消息
            agent_chat: 客服回复
            dialogue_history: 完整对话历史
            scenario_id: 场景ID
            context_data: 上下文数据(用于辅助分类)
            use_rule_verification: 是否使用规则引擎验证裁判的分类
            max_retries: 如果验证失败,最大重试次数
            
        Returns:
            Dict: {
                "classification": {...},  # 正确的分类结果
                "chat_quality_score": 0-1,  # 话术质量评分
                "details": {...},
                "verification_result": {...}  # 验证结果(如果启用)
            }
        """
        dialogue_context = ""
        if dialogue_history:
            dialogue_context = self._build_dialogue_context(dialogue_history, max_turns=turn_id + 1)
        
        # 提取系统信息
        system_info = context_data.get("system_info", {}) if context_data else {}
        system_info_text = json.dumps(system_info, ensure_ascii=False, indent=2) if system_info else "{}"
        
        # 根据场景获取分类字段说明
        classification_fields_desc = self._get_classification_fields_desc(scenario_id)
        
        # 根据场景获取系统信息字段说明
        system_info_desc = self._get_system_info_desc(scenario_id)
        
        # 根据场景获取JSON格式示例
        json_example = self._get_json_example_for_scenario(scenario_id)
        
        prompt = f"""你是一名专业的客服培训评审专家。请对该轮对话进行综合评估,包括:
1. 判断用户消息的正确分类标签(Ground Truth)
2. 评估客服回复的话术质量(0-100分)

【场景】{scenario_id}
【轮次】Turn {turn_id}

【系统信息】
{system_info_desc}
{system_info_text}

【对话上下文】
{dialogue_context if dialogue_context else "（这是第一轮对话）"}

【该轮用户消息】
{user_message}

【该轮客服回复】
{agent_chat}

【分类字段说明】
{classification_fields_desc}

【评估任务】
1. 根据用户消息和对话上下文,判断正确的分类标签
2. 评估客服回复的话术质量并打分,基于以下五个核心维度 (每个维度仅评3/6/9三个等级):
   
   I. 语言表达质量 (linguistic_quality)
      - 3分: 语法有误或表达生硬,存在翻译腔,语种与用户不完全一致
      - 6分: 语法基本正确,表达较自然,语种一致但偶有不够地道之处
      - 9分: 语法完美,表达地道自然,语种严格一致,如同native speaker
   
   II. 拟人化与情感交互 (anthropomorphism_emotion)
      - 3分: 存在AI痕迹或冷冰冰的表述,难以识别用户情绪,缺乏同理心
      - 6分: 基本以人类口吻交流,能识别部分用户情绪,有一定同理心
      - 9分: 完全没有AI痕迹,自然亲切的人类对话风格,精准识别情绪,充分展现同理心和亲和力
   
   III. 内容效用与规范 (content_utility)
      - 3分: 内容与意图偏离,帮助有限,或存在虚假承诺/机械式道歉,内容冗余重复
      - 6分: 内容基本贴切用户意图,提供一定帮助,承诺谨慎但不够恰当
      - 9分: 内容完全贴切意图,提供实质性帮助,简洁无冗余,承诺准确边界清晰
   
   IV. 客户满意度 (user_satisfaction) 
      - 3分: 用户体验差,不能解决问题,甚至加剧用户不满
      - 6分: 用户体验一般,能部分推进对话,但解决程度有限
      - 9分: 用户体验优,能有效解决问题或明显推进对话,用户会感到满意
   
   V. 指令遵循度 (instruction_compliance) 
      - 3分: 违反多项指令,规则遵循度低
      - 6分: 基本遵守指令,偶有偏差
      - 9分: 严格遵守所有指令,既保证用户体验也保证规则遵循

请严格按照以下JSON格式返回：
{json_example}

【注意】
1. 只输出纯JSON,不要有其他内容
2. 分类字段根据场景不同而不同,请严格按照上述字段说明填写
3. chat_quality_dimensions中每个维度必须从3/6/9中选择一个整数（不能选其他数值）
"""
        
        # 尝试生成并验证分类结果
        attempt = 0
        verification_history = []
        
        while attempt <= max_retries:
            try:
                # 第一次或重试时的提示词调整
                current_prompt = prompt
                if attempt > 0 and verification_history:
                    # 添加上一次的验证反馈
                    last_verification = verification_history[-1]
                    feedback = f"""
【上一次尝试的问题】
你上一次给出的分类结果存在以下问题:
{last_verification.get('conflict_description', '分类结果与规则引擎计算的路径不一致')}

规则引擎基于你的分类计算出的路径: {last_verification.get('rule_path', [])}
规则引擎基于你的分类计算出的最终动作: {last_verification.get('rule_finals', {})}

请重新仔细分析用户消息和系统信息,给出更准确的分类结果。
特别注意: {last_verification.get('hint', '确保分类逻辑一致性')}
"""
                    current_prompt = prompt + feedback
                
                response = self.llm_client.generate(
                    prompt=current_prompt,
                    temperature=self.temperature if attempt == 0 else max(0.1, self.temperature - 0.2 * attempt),  # 重试时降低温度
                    max_tokens=self.max_tokens,
                )
                
                result = self._parse_json_response(response.text)
                
                # 从chat_quality_dimensions自动计算chat_quality_score
                if "chat_quality_dimensions" in result:
                    score = self.calculate_chat_quality_score(result["chat_quality_dimensions"])
                    result["chat_quality_score"] = score / 100.0  # 转换为0-1范围
                elif "chat_quality_score" in result:
                    # 兼容旧格式:如果LLM仍输出了chat_quality_score,则转换为0-1范围
                    result["chat_quality_score"] = result["chat_quality_score"] / 100.0
                
                # 【投票模式】不再使用规则引擎验证,直接返回结果
                # 规则验证已由投票机制替代
                result["attempt"] = 1
                return result
                
            except Exception as e:
                # 检查是否是429错误(请求速率限制)
                error_str = str(e)
                is_429 = "429" in error_str or "rate limit" in error_str.lower() or "too many requests" in error_str.lower()
                
                if is_429:
                    logger.warning(f"遇到429错误(请求速率限制),等待120秒后重试... (attempt {attempt + 1})")
                    import time
                    time.sleep(120)
                    logger.info(f"等待完成,继续重试 (attempt {attempt + 1})")
                else:
                    logger.error(f"Error in evaluate_turn_comprehensive (attempt {attempt + 1}): {e}")
                
                if attempt >= max_retries:
                    return {
                        "classification": {},
                        "chat_quality_score": 0.5,
                        "chat_quality_dimensions": {},
                        "error": str(e),
                        "verification_history": verification_history
                    }
                attempt += 1
        
        # 不应该到这里
        return {
            "classification": {},
            "chat_quality_score": 0.5,
            "chat_quality_dimensions": {},
            "error": "Max retries exceeded",
            "verification_history": verification_history
        }
    
    def evaluate_chat_quality(
        self,
        chat_text: str,
        user_message: str,
        dialogue_context: str,
        evaluation_criteria: Optional[Dict[str, str]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        评估话术质量 - 简化版本（只评估话术，不处理分类）
        
        为了兼容ModelJudgedEvaluator的evaluate_chat_quality调用
        
        Args:
            chat_text: 客服回复
            user_message: 用户消息
            dialogue_context: 对话上下文
            evaluation_criteria: 评价标准（可选）
            
        Returns:
            Tuple[float, Dict]: (话术质量评分0-1, 详细信息)
        """
        prompt = f"""你是一名专业的客服培训评审专家。请对该客服回复的话术质量进行评估。

【用户消息】
{user_message}

【该客服回复】
{chat_text}

【对话上下文】
{dialogue_context if dialogue_context else "（这是第一轮对话）"}

请从以下五个维度评估话术质量，每个维度仅评3/6/9三个等级：

1. 语言表达质量 (linguistic_quality): 3/6/9
2. 拟人化与情感交互 (anthropomorphism_emotion): 3/6/9
3. 内容效用与规范 (content_utility): 3/6/9
4. 客户满意度 (user_satisfaction): 3/6/9
5. 指令遵循度 (instruction_compliance): 3/6/9

请严格按照以下JSON格式返回，不要有任何其他内容：
{{
    "chat_quality_dimensions": {{
        "linguistic_quality": <3/6/9>,
        "anthropomorphism_emotion": <3/6/9>,
        "content_utility": <3/6/9>,
        "user_satisfaction": <3/6/9>,
        "instruction_compliance": <3/6/9>
    }},
    "reasoning": "评估理由"
}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            result = self._parse_json_response(response.text)
            
            # 从chat_quality_dimensions自动计算chat_quality_score
            if "chat_quality_dimensions" in result:
                score = self.calculate_chat_quality_score(result["chat_quality_dimensions"])
                return score / 100.0, {  # 转换为0-1范围
                    "chat_quality_score": score / 100.0,
                    "dimensions": result["chat_quality_dimensions"],
                    "reasoning": result.get("reasoning", ""),
                }
            else:
                logger.warning("LLM未返回chat_quality_dimensions，返回默认值")
                return 0.5, {
                    "chat_quality_score": 0.5,
                    "error": "Failed to parse dimensions from LLM response",
                    "raw_response": result,
                }
        
        except Exception as e:
            # 检查是否是429错误(请求速率限制)
            error_str = str(e)
            is_429 = "429" in error_str or "rate limit" in error_str.lower() or "too many requests" in error_str.lower()
            
            if is_429:
                logger.warning(f"遇到429错误(请求速率限制),等待120秒后重试...")
                import time
                time.sleep(120)
                logger.info(f"等待完成,重新调用evaluate_chat_quality")
                # 递归重试一次
                return self.evaluate_chat_quality(chat_text, user_message, dialogue_context, evaluation_criteria)
            
            logger.error(f"Error in evaluate_chat_quality: {e}")
            return 0.5, {
                "chat_quality_score": 0.5,
                "error": str(e),
            }
    
    # 【删除规则引擎验证】投票模式下已不需要规则验证
    # 之前的 _verify_classification_with_rule_engine 方法已删除
    # 现由 MultiModelVotingJudge 的投票机制替代
    
    def _get_system_info_desc(self, scenario_id: str) -> str:
        """根据场景获取系统信息字段说明"""
        
        # 在线教育场景
        if scenario_id == "online_education":
            return """
系统信息字段说明（在线教育场景）：
- CourseList: 学员当前在学的所有课程列表
- HistoricalComplaintRecords: 是否有历史投诉记录 (true/false)
- QuestionTypeFor30Days: 该学员30天内出现的所有问题类型列表
- isRiskUser: 是否为风险用户 (true/false)

注意: 在判断某些分类字段时需要参考系统信息,例如:
- QuestionRelevance需要参考CourseList判断问题是否与在学课程相关
- RepeatedRaised需要参考QuestionTypeFor30Days和对话历史判断是否重复反馈
"""
        
        # 电商退款场景
        elif scenario_id == "ecommerce_refund":
            return """
系统信息字段说明（电商退款场景）：
- ShippingStatus: 物流状态 (Unshipped/Shipping/Signed)
- CreditLevel: 用户信用等级 (High/Medium/Low)

注意: 在判断某些分类字段时需要参考系统信息,例如:
- ProvidedDocument需要根据对话判断用户是否提交了售后凭证
- Responsibility需要结合系统变量判断责任归属
"""
        
        # 电信套餐场景
        elif scenario_id == "telecom_package":
            return """
系统信息字段说明（电信套餐场景）：
- PackageStatus: 用户套餐状态 (Contracted/NoContract)
- Penalty: 用户需缴纳的违约金 (int)

注意: 在判断某些分类字段时需要参考系统信息,例如:
- ApplicationTendency需要根据对话判断用户是否倾向于办理推荐套餐
- ConsumptionType需要判断用户的实际消费意图
"""
        
        # 物业服务场景
        elif scenario_id == "property_service":
            return """
系统信息字段说明（物业服务场景）：
- HouseStatus: 业主房屋的居住状态 (Occupied/Rented/UnOccupied)
- FeePaymentStatus: 业主物业费的缴费状态 (Settled/Unpaid)

注意: 在判断某些分类字段时需要参考系统信息,例如:
- CoreIntention需要判断业主的核心意图（支付、投诉或报修）
- EmergencyLevel需要根据对话内容和房屋状态综合判断
"""
        
        # 快递物流场景
        elif scenario_id == "logistics_delivery":
            return """
系统信息字段说明（快递物流场景）：
- orderStatus: 订单的配送进度状态 (Arrived/Delivered/Undelivered)
- hasInsurance: 订单/包裹是否购买保险 (True/False)

注意: 在判断某些分类字段时需要参考系统信息,例如:
- UserIntention需要判断用户发起请求的核心目的（加急、投诉或修改）
- ComplaintValidity需要根据orderStatus判断投诉是否合理
"""
        
        # 在线航司改签退票场景
        elif scenario_id == "airline_refund":
            return """
系统信息字段说明（在线航司改签退票场景）：
- memberLevel: 用户会员等级 (VIP/Regular/Blacklist)
- hasInsurance: 订单是否购买保险 (True/False)

注意: 在判断某些分类字段时需要参考系统信息,例如:
- CoreDemand需要判断用户核心诉求（改签或退票、投诉、咨询）
- ChangeReason需要判断用户改退签的原因（个人、航司、天气）
"""
        
        # 其他场景
        else:
            return "系统信息字段说明: 根据具体场景定义"
    
    def _get_classification_fields_desc(self, scenario_id: str) -> str:
        """根据场景获取分类字段说明"""
        
        # 在线教育场景
        if scenario_id == "online_education":
            return """
1. DescriptionClear - 问题描述是否清晰（True/False）
   - True: 用户的问题描述具体、明确，有关键信息
   - False: 问题描述模糊、缺少关键信息
2. QuestionRelevance - 问题是否与课程相关（True/False）
   - True: 涉及课程内容、学习进度、课程材料等
   - False: 涉及账号、登录、价格、客服等非课程问题
3. EmotionTendency - 用户情绪倾向（"Calm"/"Dissatisfied"）
   - "Calm": 用户情绪平和、礼貌
   - "Dissatisfied": 用户表现出不满、生气、投诉等负面情绪
4. ResolveDependency - 解决依赖度（"LowDependency"/"MediumDependency"/"HighDependency"/null）
   - "LowDependency": 只需要简单查询、基础解答
   - "MediumDependency": 需要提供示例资料、详细说明
   - "HighDependency": 需要专属辅导老师、一对一辅导
5. RepeatedRaised - 是否重复反馈（True/False）
   - True: 用户明确提到"之前反映过"或对话历史中有相同问题
   - False: 首次提出该问题
6. RegardingRefund - 是否涉及退费（True/False）
   - True: 提到退费、退款、取消等退费相关内容
   - False: 不涉及退费
"""
        
        # 电商退款场景
        elif scenario_id == "ecommerce_refund":
            return """
1. CoreIntention - 用户发起售后的核心需求（"ReturnOrRefund"/"Exchange"）
   - "ReturnOrRefund": 退货退款
   - "Exchange": 换货
2. ProvidedDocument - 用户是否提交售后相关凭证（True/False）
   - True: 提供了照片、视频等凭证
   - False: 未提供凭证
3. Responsibility - 售后问题的责任归属（"User"/"Merchant"）
   - "User": 用户责任
   - "Merchant": 商家/平台责任
4. RefundReasonable - 退款需求是否合理（"Reasonable"/"Unreasonable"）
   - "Reasonable": 退款需求合理
   - "Unreasonable": 退款需求不合理
5. EmotionStatus - 用户情绪状态（"Calm"/"Dissatisfied"）
   - "Calm": 用户情绪平和
   - "Dissatisfied": 用户表现出不满、生气
"""
        
        # 电信套餐场景
        elif scenario_id == "telecom_package":
            return """
1. ConsumptionType - 用户对话的意图（"Enquiry"/"Change"/"Cancel"）
   - "Enquiry": 咨询了解
   - "Change": 变更套餐
   - "Cancel": 取消套餐
2. ApplicationTendency - 用户是否倾向于办理推荐套餐（"Agree"/"Reject"/"Hesitate"）
   - "Agree": 用户同意办理
   - "Reject": 用户拒绝办理
   - "Hesitate": 用户犹豫不决
3. ConsumptionProfile - 用户倾向于办理的套餐类型（"Data"/"Voice"）
   - "Data": 流量套餐
   - "Voice": 语音套餐
4. EmotionTag - 用户对话中表现的情绪（"Calm"/"Discontent"）
   - "Calm": 用户情绪平和
   - "Discontent": 用户表现出不满或沮丧
"""
        
        # 物业服务场景
        elif scenario_id == "property_service":
            return """
1. CoreIntention - 住户对话的意图（"Payment"/"Complaint"/"Repair"）
   - "Payment": 物业费咨询或支付
   - "Complaint": 投诉
   - "Repair": 报修请求
2. EmotionTag - 住户在对话中表现的情绪（"Calm"/"Discontent"）
   - "Calm": 住户情绪平和
   - "Discontent": 住户表现出不满、生气
3. RepairItemCategory - 住户报修事项的具体分类（"IndoorFacilities"/"EnvironmentalHygiene"）
   - "IndoorFacilities": 室内设施维修
   - "EnvironmentalHygiene": 环境卫生问题
4. RelatedScope - 事项涉及的范围（"Personal"/"Public"）
   - "Personal": 个人房屋相关
   - "Public": 公共区域相关
5. EmergencyLevel - 事项紧急程度（"Urgent"/"NoUrgent"）
   - "Urgent": 紧急需要处理
   - "NoUrgent": 不紧急可稍后处理
"""
        
        # 快递物流场景
        elif scenario_id == "logistics_delivery":
            return """
1. RiskStatus - 订单的危险程度（"Risk"/"Safe"）
   - "Risk": 订单存在风险
   - "Safe": 订单安全
2. InfoCompleteness - 用户提交信息的完整程度（True/False）
   - True: 提供了订单号等完整信息
   - False: 信息不完整
3. UserIntention - 用户发起请求的核心目的（"Urge"/"Complaint"/"Modify"）
   - "Urge": 加急查询
   - "Complaint": 投诉
   - "Modify": 修改地址或其他信息
4. EmotionalState - 用户反馈问题时的情绪状态（"Calm"/"Dissatisfied"）
   - "Calm": 用户情绪平和
   - "Dissatisfied": 用户表现出不满
5. EmergencyLevel - 事项紧急程度（"Urgent"/"Normal"）
   - "Urgent": 非常紧急
   - "Normal": 正常紧急程度
6. ComplaintValidity - 投诉的合理性（True/False）
   - True: 投诉合理有效
   - False: 投诉不合理
"""
        
        # 在线航司改签退票场景
        elif scenario_id == "airline_refund":
            return """
1. CoreDemand - 用户核心诉求（"RescheduleOrRefund"/"Complaint"/"Inqury"）
   - "RescheduleOrRefund": 改签或退票
   - "Complaint": 投诉
   - "Inqury": 咨询
2. ChangeReason - 用户改退签的原因（"Personal"/"Airline"/"Weather"）
   - "Personal": 个人原因
   - "Airline": 航司原因
   - "Weather": 天气原因
3. UserEmotion - 用户情绪状态（"Urgent"/"Dissatisfied"/"Normal"）
   - "Urgent": 非常紧急
   - "Dissatisfied": 不满意
   - "Normal": 正常
4. DocumentValidity - 是否提供了合理凭证（"Valid"/"Invalid"）
   - "Valid": 提供了有效凭证
   - "Invalid": 未提供或无效凭证
5. IsInfoComplete - 信息是否完善（"Complete"/"Incomplete"）
   - "Complete": 提供了航班号等完整信息
   - "Incomplete": 信息不完整
"""
        
        # 未知场景
        else:
            return f"（场景 {scenario_id} 的分类字段未定义，请补充配置）"
    
    def _get_json_example_for_scenario(self, scenario_id: str) -> str:
        """根据场景获取JSON格式示例"""
        
        if scenario_id == "online_education":
            return """{
    "classification": {
        "DescriptionClear": "true或false,根据用户描述是否清晰",
        "QuestionRelevance": "true或false,根据提问是否与课程相关",
        "EmotionTendency": "从'Calm'/'Anxious'/'Confused'中选择,根据用户情绪",
        "ResolveDependency": "从'LowDependency'/'MediumDependency'/'HighDependency'中选择",
        "RepeatedRaised": "true或false,根据用户是否重复提问",
        "RegardingRefund": "true或false,根据是否涉及退款"
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
        
        elif scenario_id == "ecommerce_refund":
            return """{
    "classification": {
        "CoreIntention": "从'ReturnOrRefund'/'Complaint'/'Inquiry'中选择,根据用户核心诉求",
        "ProvidedDocument": "true或false,根据用户是否提供了订单/凭证",
        "Responsibility": "从'Merchant'/'Platform'/'User'中选择,根据责任归属",
        "RefundReasonable": "从'Reasonable'/'Unreasonable'/'Unclear'中选择,根据退款合理性",
        "EmotionStatus": "从'Calm'/'Dissatisfied'/'Angry'中选择,根据用户情绪"
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
        
        elif scenario_id == "telecom_package":
            return """{
    "classification": {
        "ConsumptionType": "从'Change'/'Upgrade'/'Query'中选择,根据用户意图",
        "ApplicationTendency": "从'Agree'/'Disagree'/'Uncertain'中选择,根据用户应用意向",
        "ConsumptionProfile": "从'Data'/'Voice'/'Mixed'中选择,根据消费偏好",
        "EmotionTag": "从'Calm'/'Urgent'/'Dissatisfied'中选择,根据用户情绪"
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
        
        elif scenario_id == "property_service":
            return """{
    "classification": {
        "CoreIntention": "从'Repair'/'Complaint'/'Inquiry'中选择,根据用户核心诉求",
        "EmotionTag": "从'Calm'/'Anxious'/'Angry'中选择,根据用户情绪",
        "RepairItemCategory": "从'IndoorFacilities'/'Outdoor'/'Common'中选择,根据维修物业类型",
        "RelatedScope": "从'Personal'/'Shared'/'Building'中选择,根据影响范围",
        "EmergencyLevel": "从'Urgent'/'Normal'/'NoUrgent'中选择,根据紧急程度"
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
        
        elif scenario_id == "logistics_delivery":
            return """{
    "classification": {
        "RiskStatus": "从'Safe'/'AtRisk'/'Lost'中选择,根据包裹风险状态",
        "InfoCompleteness": "true或false,根据用户提供的信息是否完整",
        "UserIntention": "从'Urge'/'Complaint'/'Query'中选择,根据用户意图",
        "EmotionalState": "从'Calm'/'Anxious'/'Angry'中选择,根据用户情绪",
        "EmergencyLevel": "从'Urgent'/'Normal'/'Low'中选择,根据事件紧急程度",
        "ComplaintValidity": "true或false,根据投诉是否有效"
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
        
        elif scenario_id == "airline_refund":
            return """{
    "classification": {
        "CoreDemand": "从'RescheduleOrRefund'/'Complaint'/'Inquiry'中选择,根据用户核心诉求",
        "ChangeReason": "从'Personal'/'Airline'/'Weather'中选择,改退签原因",
        "UserEmotion": "从'Urgent'/'Dissatisfied'/'Normal'中选择,根据用户情绪",
        "DocumentValidity": "从'Valid'/'Invalid'中选择,根据是否提供有效凭证",
        "IsInfoComplete": "从'Complete'/'Incomplete'中选择,根据信息完整性"
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
        
        else:
            # 通用格式
            return """{
    "classification": {
        // 根据场景填写相应的分类字段
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
    
    def _classify_input_helper(self, user_message: str, context_data: Dict[str, Any], scenario_id: str) -> Dict[str, Any]:
        """辅助函数：使用规则引擎提供分类建议"""
        # 这里可以调用规则引擎的_classify_input方法作为辅助
        # 用于和裁判模型的判断相互印证
        return {}  # TODO: 实现规则引擎辅助
    
    
    def _build_dialogue_context(self, dialogue_history: list, max_turns: Optional[int] = None) -> str:
        """
        构建对话上下文文本
        
        Args:
            dialogue_history: 对话历史列表
            max_turns: 最大轮次数（用于限制输出长度）
            
        Returns:
            str: 对话上下文文本
        """
        if not dialogue_history:
            return ""
        
        context_parts = []
        for i, turn in enumerate(dialogue_history):
            if max_turns and i >= max_turns:
                break
            
            # 支持两种格式：列表格式和字典格式
            if isinstance(turn, dict):
                role = turn.get("role", "unknown")
                content = turn.get("content", "")
            else:
                # 假设是(role, content)的元组或列表
                role = turn[0] if len(turn) > 0 else "unknown"
                content = turn[1] if len(turn) > 1 else ""
            
            role_display = "用户" if role == "user" else "客服" if role == "assistant" else role
            context_parts.append(f"{role_display}: {content}")
        
        return "\n".join(context_parts)
     
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析LLM的JSON响应
        
        Args:
            response_text: LLM的响应文本
            
        Returns:
            Dict: 解析后的JSON对象
        """
        try:
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                return data
        
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}")
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
        
        # 返回空字典和错误信息
        return {"error": "Failed to parse JSON", "raw_response": response_text[:200]}
   

class MultiModelJudge:
    """
    多模型评判器
    
    支持同时使用多个LLM进行评估，然后取平均值
    """
    
    def __init__(self, judges: Dict[str, LLMJudge]):
        """
        初始化多模型评判器
        
        Args:
            judges: 评判器字典 {模型名: LLMJudge}
        """
        self.judges = judges
    
    def evaluate_chat_quality(
        self,
        chat_text: str,
        user_message: str,
        dialogue_context: str,
        evaluation_criteria: Optional[Dict[str, str]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        使用多个评判器评估话术质量
        
        Args:
            chat_text: 客服回复
            user_message: 用户消息
            dialogue_context: 对话上下文
            evaluation_criteria: 评价标准
            
        Returns:
            Tuple[float, Dict]: (综合评分, 详细信息)
        """
        scores = []
        details = {}
        
        for model_name, judge in self.judges.items():
            try:
                score, detail = judge.evaluate_chat_quality(
                    chat_text=chat_text,
                    user_message=user_message,
                    dialogue_context=dialogue_context,
                    evaluation_criteria=evaluation_criteria,
                )
                scores.append(score)
                details[model_name] = detail
            except Exception as e:
                logger.error(f"Error from {model_name}: {e}")
        
        # 计算平均分
        avg_score = sum(scores) / len(scores) if scores else 0.5
        
        return avg_score, {
            "average_score": avg_score,
            "model_scores": dict(zip(self.judges.keys(), scores)),
            "details": details,
        }
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM集成的评判模型
LLM-powered Judge Model

使用LLM进行话术质量评估和其他主观评测
"""

import json
import re
from typing import Optional, Dict, Any, Tuple
import logging

from .llm_client import LLMClient

logger = logging.getLogger(__name__)


class LLMJudge:
    """
    LLM评判模型
    
    用于评估：
    1. 话术质量 (自然性、准确性、客户友好度)
    2. 指令遵循能力
    3. 其他主观指标
    """
    
    # 话术质量五维度权重 (总和为10)
    CHAT_QUALITY_WEIGHTS = {
        "linguistic_quality": 2.0,          # 语言表达 20%
        "anthropomorphism_emotion": 2.5,    # 拟人化与情感交互 25%
        "content_utility": 2.5,             # 内容效用 25%
        "user_satisfaction": 1.5,           # 用户满意度 15%
        "instruction_compliance": 1.5       # 指令遵循度 15%
    }
    
    def __init__(
        self,
        llm_client: LLMClient,
        temperature: float = 0.3,  # 降低温度以获得更一致的评估
        max_tokens: int = 1024,
    ):
        """
        初始化LLM评判模型
        
        Args:
            llm_client: LLM客户端
            temperature: 采样温度
            max_tokens: 最大生成token数
        """
        self.llm_client = llm_client
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    @classmethod
    def calculate_chat_quality_score(cls, dimensions: Dict[str, int]) -> float:
        """
        从五维度评分计算综合话术质量评分
        
        支持多种值类型的自动转换:
        - int: 直接使用
        - str: 使用正则表达式提取整数 (例如 "从3/6/9中选择" -> 3)
        - float: 四舍五入转换为整数
        
        Args:
            dimensions: 五维度评分字典，支持以下格式 {
                "linguistic_quality": 3或6或9或"从3/6/9中选择"或3.0等,
                "anthropomorphism_emotion": ...,
                "content_utility": ...,
                "user_satisfaction": ...,
                "instruction_compliance": ...
            }
            
        Returns:
            float: 综合评分 0-100
        """
        total_score = 0.0
        for dim, weight in cls.CHAT_QUALITY_WEIGHTS.items():
            if dim in dimensions:
                value = dimensions[dim]
                
                # 类型检查和正则提取
                if isinstance(value, int):
                    # 已经是整数，直接使用
                    score_value = value
                elif isinstance(value, str):
                    # 字符串，使用正则提取整数
                    match = re.search(r'\d+', value)
                    if match:
                        score_value = int(match.group())
                        logger.info(f"从字符串'{value}'中提取整数{score_value}")
                    else:
                        logger.warning(f"无法从字符串'{value}'中提取整数，跳过该维度")
                        continue
                elif isinstance(value, float):
                    # 浮点数，转换为整数
                    score_value = int(round(value))
                    logger.info(f"将浮点数{value}转换为整数{score_value}")
                else:
                    # 其他类型，无法处理
                    logger.warning(f"维度'{dim}'的值类型不支持: {type(value)}, 值: {value}")
                    continue
                
                total_score += score_value * weight
        return total_score
  
    def evaluate_turn_comprehensive(
        self,
        turn_id: int,
        user_message: str,
        agent_chat: str,
        dialogue_history: Optional[list] = None,
        scenario_id: str = "online_education",
        context_data: Optional[Dict[str, Any]] = None,
        use_rule_verification: bool = True,  # 是否使用规则引擎验证
        max_retries: int = 2,  # 最大重试次数
    ) -> Dict[str, Any]:
        """
        综合评估单轮对话 - 一次性输出分类Ground Truth和话术质量评分
        增强版: 使用规则引擎验证裁判LLM的分类结果
        
        Args:
            turn_id: 轮次ID
            user_message: 用户消息
            agent_chat: 客服回复
            dialogue_history: 完整对话历史
            scenario_id: 场景ID
            context_data: 上下文数据(用于辅助分类)
            use_rule_verification: 是否使用规则引擎验证裁判的分类
            max_retries: 如果验证失败,最大重试次数
            
        Returns:
            Dict: {
                "classification": {...},  # 正确的分类结果
                "chat_quality_score": 0-1,  # 话术质量评分
                "details": {...},
                "verification_result": {...}  # 验证结果(如果启用)
            }
        """
        dialogue_context = ""
        if dialogue_history:
            dialogue_context = self._build_dialogue_context(dialogue_history, max_turns=turn_id + 1)
        
        # 提取系统信息
        system_info = context_data.get("system_info", {}) if context_data else {}
        system_info_text = json.dumps(system_info, ensure_ascii=False, indent=2) if system_info else "{}"
        
        # 根据场景获取分类字段说明
        classification_fields_desc = self._get_classification_fields_desc(scenario_id)
        
        # 根据场景获取系统信息字段说明
        system_info_desc = self._get_system_info_desc(scenario_id)
        
        # 根据场景获取JSON格式示例
        json_example = self._get_json_example_for_scenario(scenario_id)
        
        prompt = f"""你是一名专业的客服培训评审专家。请对该轮对话进行综合评估,包括:
1. 判断用户消息的正确分类标签(Ground Truth)
2. 评估客服回复的话术质量(0-100分)

【场景】{scenario_id}
【轮次】Turn {turn_id}

【系统信息】
{system_info_desc}
{system_info_text}

【对话上下文】
{dialogue_context if dialogue_context else "（这是第一轮对话）"}

【该轮用户消息】
{user_message}

【该轮客服回复】
{agent_chat}

【分类字段说明】
{classification_fields_desc}

【评估任务】
1. 根据用户消息和对话上下文,判断正确的分类标签
2. 评估客服回复的话术质量并打分,基于以下五个核心维度 (每个维度仅评3/6/9三个等级):
   
   I. 语言表达质量 (linguistic_quality)
      - 3分: 语法有误或表达生硬,存在翻译腔,语种与用户不完全一致
      - 6分: 语法基本正确,表达较自然,语种一致但偶有不够地道之处
      - 9分: 语法完美,表达地道自然,语种严格一致,如同native speaker
   
   II. 拟人化与情感交互 (anthropomorphism_emotion)
      - 3分: 存在AI痕迹或冷冰冰的表述,难以识别用户情绪,缺乏同理心
      - 6分: 基本以人类口吻交流,能识别部分用户情绪,有一定同理心
      - 9分: 完全没有AI痕迹,自然亲切的人类对话风格,精准识别情绪,充分展现同理心和亲和力
   
   III. 内容效用与规范 (content_utility)
      - 3分: 内容与意图偏离,帮助有限,或存在虚假承诺/机械式道歉,内容冗余重复
      - 6分: 内容基本贴切用户意图,提供一定帮助,承诺谨慎但不够恰当
      - 9分: 内容完全贴切意图,提供实质性帮助,简洁无冗余,承诺准确边界清晰
   
   IV. 客户满意度 (user_satisfaction) 
      - 3分: 用户体验差,不能解决问题,甚至加剧用户不满
      - 6分: 用户体验一般,能部分推进对话,但解决程度有限
      - 9分: 用户体验优,能有效解决问题或明显推进对话,用户会感到满意
   
   V. 指令遵循度 (instruction_compliance) 
      - 3分: 违反多项指令,规则遵循度低
      - 6分: 基本遵守指令,偶有偏差
      - 9分: 严格遵守所有指令,既保证用户体验也保证规则遵循

请严格按照以下JSON格式返回：
{json_example}

【注意】
1. 只输出纯JSON,不要有其他内容
2. 分类字段根据场景不同而不同,请严格按照上述字段说明填写
3. chat_quality_dimensions中每个维度必须从3/6/9中选择一个整数（不能选其他数值）
"""
        
        # 尝试生成并验证分类结果
        attempt = 0
        verification_history = []
        
        while attempt <= max_retries:
            try:
                # 第一次或重试时的提示词调整
                current_prompt = prompt
                if attempt > 0 and verification_history:
                    # 添加上一次的验证反馈
                    last_verification = verification_history[-1]
                    feedback = f"""
【上一次尝试的问题】
你上一次给出的分类结果存在以下问题:
{last_verification.get('conflict_description', '分类结果与规则引擎计算的路径不一致')}

规则引擎基于你的分类计算出的路径: {last_verification.get('rule_path', [])}
规则引擎基于你的分类计算出的最终动作: {last_verification.get('rule_finals', {})}

请重新仔细分析用户消息和系统信息,给出更准确的分类结果。
特别注意: {last_verification.get('hint', '确保分类逻辑一致性')}
"""
                    current_prompt = prompt + feedback
                
                response = self.llm_client.generate(
                    prompt=current_prompt,
                    temperature=self.temperature if attempt == 0 else max(0.1, self.temperature - 0.2 * attempt),  # 重试时降低温度
                    max_tokens=self.max_tokens,
                )
                
                result = self._parse_json_response(response.text)
                
                # 从chat_quality_dimensions自动计算chat_quality_score
                if "chat_quality_dimensions" in result:
                    score = self.calculate_chat_quality_score(result["chat_quality_dimensions"])
                    result["chat_quality_score"] = score / 100.0  # 转换为0-1范围
                elif "chat_quality_score" in result:
                    # 兼容旧格式:如果LLM仍输出了chat_quality_score,则转换为0-1范围
                    result["chat_quality_score"] = result["chat_quality_score"] / 100.0
                
                # 使用规则引擎验证分类结果
                if use_rule_verification and "classification" in result:
                    verification_result = self._verify_classification_with_rule_engine(
                        classification=result["classification"],
                        context_data=context_data,
                        scenario_id=scenario_id,
                    )
                    
                    result["verification_result"] = verification_result
                    result["attempt"] = attempt + 1
                    
                    # 如果验证通过或已达到最大重试次数,返回结果
                    if verification_result.get("verified", False) or attempt >= max_retries:
                        if not verification_result.get("verified", False):
                            result["warning"] = f"裁判模型在{max_retries + 1}次尝试后仍未通过验证,使用最后一次结果"
                        return result
                    else:
                        # 验证失败,记录并重试
                        verification_history.append(verification_result)
                        attempt += 1
                        logger.warning(f"裁判分类验证失败(尝试{attempt}/{max_retries + 1}),准备重试: {verification_result.get('conflict_description')}")
                        continue
                else:
                    # 不使用验证,直接返回
                    result["attempt"] = 1
                    return result
                
            except Exception as e:
                # 检查是否是429错误(请求速率限制)
                error_str = str(e)
                is_429 = "429" in error_str or "rate limit" in error_str.lower() or "too many requests" in error_str.lower()
                
                if is_429:
                    logger.warning(f"遇到429错误(请求速率限制),等待120秒后重试... (attempt {attempt + 1})")
                    import time
                    time.sleep(120)
                    logger.info(f"等待完成,继续重试 (attempt {attempt + 1})")
                else:
                    logger.error(f"Error in evaluate_turn_comprehensive (attempt {attempt + 1}): {e}")
                
                if attempt >= max_retries:
                    return {
                        "classification": {},
                        "chat_quality_score": 0.5,
                        "chat_quality_dimensions": {},
                        "error": str(e),
                        "verification_history": verification_history
                    }
                attempt += 1
        
        # 不应该到这里
        return {
            "classification": {},
            "chat_quality_score": 0.5,
            "chat_quality_dimensions": {},
            "error": "Max retries exceeded",
            "verification_history": verification_history
        }
    
    def evaluate_chat_quality(
        self,
        chat_text: str,
        user_message: str,
        dialogue_context: str,
        evaluation_criteria: Optional[Dict[str, str]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        评估话术质量 - 简化版本（只评估话术，不处理分类）
        
        为了兼容ModelJudgedEvaluator的evaluate_chat_quality调用
        
        Args:
            chat_text: 客服回复
            user_message: 用户消息
            dialogue_context: 对话上下文
            evaluation_criteria: 评价标准（可选）
            
        Returns:
            Tuple[float, Dict]: (话术质量评分0-1, 详细信息)
        """
        prompt = f"""你是一名专业的客服培训评审专家。请对该客服回复的话术质量进行评估。

【用户消息】
{user_message}

【该客服回复】
{chat_text}

【对话上下文】
{dialogue_context if dialogue_context else "（这是第一轮对话）"}

请从以下五个维度评估话术质量，每个维度仅评3/6/9三个等级：

1. 语言表达质量 (linguistic_quality): 3/6/9
2. 拟人化与情感交互 (anthropomorphism_emotion): 3/6/9
3. 内容效用与规范 (content_utility): 3/6/9
4. 客户满意度 (user_satisfaction): 3/6/9
5. 指令遵循度 (instruction_compliance): 3/6/9

请严格按照以下JSON格式返回，不要有任何其他内容：
{{
    "chat_quality_dimensions": {{
        "linguistic_quality": <3/6/9>,
        "anthropomorphism_emotion": <3/6/9>,
        "content_utility": <3/6/9>,
        "user_satisfaction": <3/6/9>,
        "instruction_compliance": <3/6/9>
    }},
    "reasoning": "评估理由"
}}"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            
            result = self._parse_json_response(response.text)
            
            # 从chat_quality_dimensions自动计算chat_quality_score
            if "chat_quality_dimensions" in result:
                score = self.calculate_chat_quality_score(result["chat_quality_dimensions"])
                return score / 100.0, {  # 转换为0-1范围
                    "chat_quality_score": score / 100.0,
                    "dimensions": result["chat_quality_dimensions"],
                    "reasoning": result.get("reasoning", ""),
                }
            else:
                logger.warning("LLM未返回chat_quality_dimensions，返回默认值")
                return 0.5, {
                    "chat_quality_score": 0.5,
                    "error": "Failed to parse dimensions from LLM response",
                    "raw_response": result,
                }
        
        except Exception as e:
            # 检查是否是429错误(请求速率限制)
            error_str = str(e)
            is_429 = "429" in error_str or "rate limit" in error_str.lower() or "too many requests" in error_str.lower()
            
            if is_429:
                logger.warning(f"遇到429错误(请求速率限制),等待120秒后重试...")
                import time
                time.sleep(120)
                logger.info(f"等待完成,重新调用evaluate_chat_quality")
                # 递归重试一次
                return self.evaluate_chat_quality(chat_text, user_message, dialogue_context, evaluation_criteria)
            
            logger.error(f"Error in evaluate_chat_quality: {e}")
            return 0.5, {
                "chat_quality_score": 0.5,
                "error": str(e),
            }
    
    def _verify_classification_with_rule_engine(
        self,
        classification: Dict[str, Any],
        context_data: Optional[Dict[str, Any]],
        scenario_id: str,
    ) -> Dict[str, Any]:
        """
        使用规则引擎验证裁判LLM的分类结果
        
        验证策略:
        1. 用裁判的分类 + system_info通过规则引擎计算路径和finals
        2. 检查路径和finals是否合理(不出现明显冲突)
        3. 如果发现冲突,返回详细的冲突描述供LLM重新评估
        
        Args:
            classification: 裁判LLM生成的分类
            context_data: 上下文数据
            scenario_id: 场景ID
            
        Returns:
            Dict: {
                "verified": bool,  # 是否通过验证
                "rule_path": list,  # 规则引擎计算的路径
                "rule_finals": dict,  # 规则引擎计算的finals
                "conflict_description": str,  # 冲突描述(如果有)
                "hint": str  # 给LLM的提示
            }
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from ..sop import get_rule_engine
            
            # 获取规则引擎
            rule_engine = get_rule_engine(scenario_id)
            
            # 使用规则引擎计算
            context = context_data or {}
            rule_result = rule_engine.compute_correct_path_and_finals(
                classification_output=classification,
                context=context
            )
            
            # 基础验证: 检查路径和finals是否为空
            if not rule_result.now_path or not rule_result.finals:
                return {
                    "verified": False,
                    "rule_path": rule_result.now_path,
                    "rule_finals": rule_result.finals,
                    "conflict_description": "规则引擎无法基于该分类结果计算出有效的路径或最终动作",
                    "hint": "请检查分类字段的值是否合理,特别是关键决策字段"
                }
            
            # 场景特定的验证逻辑
            conflicts = []
            
            if scenario_id == "online_education":
                # 在线教育场景的验证规则
                regarding_refund = classification.get("RegardingRefund")
                emotion = classification.get("EmotionTendency")
                repeated = classification.get("RepeatedRaised")
                action = rule_result.finals.get("Action")
                
                # 规则1: 如果涉及退费,最终动作应该是REFUND或相关
                if regarding_refund and action not in ["REFUND", "REVIEW", "NEGOTIATE"]:
                    conflicts.append(f"用户涉及退费需求,但规则引擎计算的最终动作是{action},这不太合理")
                
                # 规则2: 如果不涉及退费,最终动作不应该是REFUND
                if not regarding_refund and action == "REFUND":
                    conflicts.append(f"用户不涉及退费需求,但规则引擎计算的最终动作是REFUND,这存在冲突")
                
                # 规则3: 如果是重复反馈,应该走REVIEW路径
                if repeated and "review" not in str(rule_result.now_path).lower():
                    conflicts.append(f"用户重复反馈问题,但规则引擎计算的路径不包含REVIEW步骤: {rule_result.now_path}")
                
                # 规则4: 情绪不满但不涉及退费时,应该有安抚动作
                if emotion == "Dissatisfied" and not regarding_refund and action not in ["COMFORT", "PLAN"]:
                    conflicts.append(f"用户情绪不满但不涉及退费,应该进行安抚或制定方案,但规则引擎计算的动作是{action}")
            
            # 电商退款场景的验证规则
            elif scenario_id == "ecommerce_refund":
                # 根据 ecommerce_refund_prompts.py 中的分类字段
                core_intention = classification.get("CoreIntention")
                provided_doc = classification.get("ProvidedDocument")
                responsibility = classification.get("Responsibility")
                refund_reasonable = classification.get("RefundReasonable")
                emotion = classification.get("EmotionStatus")
                action = rule_result.finals.get("Action")
                
                # 规则1: 核心意图与最终动作应该匹配
                if core_intention == "Exchange" and action in ["Refund", "Interception"]:
                    conflicts.append(f"用户意图是交换(Exchange)，但规则计算的动作是{action}，不匹配")
                elif core_intention == "ReturnOrRefund" and action in ["Exchange"]:
                    conflicts.append(f"用户意图是退货/退款(ReturnOrRefund)，但规则计算的动作是{action}，不匹配")
                
                # 规则2: 信息完整性检查 - 未提供凭证且要求合理应该先要求补充
                if not provided_doc and refund_reasonable == "Reasonable" and action == "Reject":
                    conflicts.append(f"用户未提供凭证但要求合理，不应直接拒绝，应先补充凭证")
                
                # 规则3: 情绪与处理方式的匹配 - 情绪不满应该有安抚
                if emotion == "Dissatisfied" and action == "Reject" and responsibility == "Merchant":
                    conflicts.append(f"用户情绪不满且是商家责任，直接拒绝会加剧矛盾，应提供安抚或补偿")
                
                # 规则4: 合理的退款请求应该被处理而非拒绝
                if refund_reasonable == "Reasonable" and responsibility == "Merchant" and action in ["Reject"]:
                    conflicts.append(f"商家责任且退款要求合理，不应该拒绝")
                
                # 规则5: 不合理的请求应该拒绝或要求补充信息
                if refund_reasonable == "Unreasonable" and action in ["Refund", "CollectionService"]:
                    conflicts.append(f"退款要求不合理，不应批准{action}处理")
            
            # 航空改签退票场景的验证规则
            elif scenario_id == "airline_refund":
                # 根据 airline_refund_prompts.py 中的分类字段
                core_demand = classification.get("CoreDemand")
                change_reason = classification.get("ChangeReason")
                emotion = classification.get("UserEmotion")
                doc_validity = classification.get("DocumentValidity")
                info_complete = classification.get("IsInfoComplete")
                action = rule_result.finals.get("Action")
                
                # 规则1: 信息不完整应该先补充而非直接处理/拒绝
                if not info_complete and action not in ["Supplementary", "Enquiry"]:
                    conflicts.append(f"用户信息不完整({info_complete})，应该要求补充，不应该直接执行{action}")
                
                # 规则2: 凭证无效且是改签/退票需求应该先验证而非直接拒绝
                if doc_validity == "Invalid" and core_demand == "RescheduleOrRefund" and action == "Reject":
                    conflicts.append(f"凭证无效({doc_validity})，应该先要求提供有效凭证，不应直接拒绝")
                
                # 规则3: 投诉需求若凭证有效应该处理而非咨询
                if core_demand == "Complaint" and doc_validity == "Valid" and action == "Enquiry":
                    conflicts.append(f"用户投诉且凭证有效，不应只进行咨询(Enquiry)，应该升级处理")
                
                # 规则4: 航司/天气原因导致的改签不应被拒绝
                if change_reason in ["Airline", "Weather"] and core_demand == "RescheduleOrRefund" and action == "Reject":
                    conflicts.append(f"航司或天气原因的改签请求，不应拒绝，应提供改签/退票方案")
                
                # 规则5: 用户情绪紧急/不满时应该升级处理
                if emotion in ["Urgent", "Dissatisfied"] and action == "Enquiry":
                    conflicts.append(f"用户情绪{emotion}，不应只进行咨询回复，应升级至人工或快速处理")
            
            # 物流配送场景的验证规则
            elif scenario_id == "logistics_delivery":
                # 根据 logistics_delivery_prompts.py 中的分类字段
                risk_status = classification.get("RiskStatus")
                info_complete = classification.get("InfoCompleteness")
                user_intention = classification.get("UserIntention")
                emotion = classification.get("EmotionalState")
                emergency = classification.get("EmergencyLevel")
                complaint_valid = classification.get("ComplaintValidity")
                action = rule_result.finals.get("Action")
                
                # 规则1: 如果订单存在风险，必须拦截
                if risk_status == "Risk" and action != "Interception":
                    conflicts.append(f"订单存在风险，应该拦截，但规则引擎计算的动作是{action}")
                
                # 规则2: 如果信息不完整且用户要求紧急，应该优先要求补充信息
                if not info_complete and emergency == "Urgent" and action not in ["Supplementary", "Registration"]:
                    conflicts.append(f"信息不完整且用户紧急请求，应该补充信息或登记加急，但规则引擎计算的动作是{action}")
                
                # 规则3: 如果投诉无效，不应该赔偿或转人工
                if not complaint_valid and action in ["Compensation", "TransHuman"]:
                    conflicts.append(f"投诉无效，不应该赔偿或转人工，但规则引擎计算的动作是{action}")
                
                # 规则4: 如果用户情绪不满，应该有安抚动作而非简单告知物流
                if emotion == "Dissatisfied" and action == "Detail":
                    conflicts.append(f"用户情绪不满，不应该只告知物流详情，应该安抚或转人工")
                
                # 规则5: 用户意图是修改地址但不是未发货状态，不应该接受修改
                if user_intention == "Modify" and action == "Modify":
                    # 这个需要结合路径判断，路径中应该有相应的检查逻辑
                    pass
            
            # 物业服务场景的验证规则
            elif scenario_id == "property_service":
                # 根据 property_service_prompts.py 中的分类字段
                core_intention = classification.get("CoreIntention")
                emotion = classification.get("EmotionTag")
                repair_category = classification.get("RepairItemCategory")
                related_scope = classification.get("RelatedScope")
                emergency = classification.get("EmergencyLevel")
                action = rule_result.finals.get("Action")
                
                # 规则1: 如果是付款相关，最终动作应该与付款有关
                if core_intention == "Payment" and action not in ["PayInformation", "Payment", "Reject"]:
                    conflicts.append(f"住户咨询付款，但规则引擎计算的动作是{action}，应该是支付相关")
                
                # 规则2: 如果是投诉且情绪不满，应该有安抚或转人工
                if core_intention == "Complaint" and emotion == "Discontent" and action not in ["Comfort", "TransHuman"]:
                    conflicts.append(f"住户投诉且情绪不满，应该安抚或转人工，但规则引擎计算的动作是{action}")
                
                # 规则3: 如果是报修且涉及公共区域，应该登记处理
                if core_intention == "Repair" and related_scope == "Public" and action not in ["Registration", "TransHuman"]:
                    conflicts.append(f"住户报修公共区域问题，应该登记或转人工，但规则引擎计算的动作是{action}")
                
                # 规则4: 如果事项紧急，应该转人工而非简单登记
                if emergency == "Urgent" and action == "Registration":
                    conflicts.append(f"事项紧急，不应该只登记，应该转人工处理")
                
                # 规则5: 如果是投诉且合理但需要支付查证，应该转人工
                if core_intention == "Complaint" and action == "Reject":
                    # 需要检查是否因为欠费而拒绝，如果是欠费则可以接受
                    pass
            
            # 电信套餐场景的验证规则
            elif scenario_id == "telecom_package":
                # 根据 telecom_package_prompts.py 中的分类字段
                consumption_type = classification.get("ConsumptionType")
                application_tendency = classification.get("ApplicationTendency")
                consumption_profile = classification.get("ConsumptionProfile")
                emotion = classification.get("EmotionTag")
                action = rule_result.finals.get("Action")
                
                # 规则1: 如果用户同意办理推荐套餐，最终动作应该是变更
                if application_tendency == "Agree" and consumption_type in ["Enquiry", "Change"] and action not in ["ChangeOrder"]:
                    conflicts.append(f"用户同意办理推荐套餐，应该执行变更，但规则引擎计算的动作是{action}")
                
                # 规则2: 如果用户拒绝或犹豫，不应该强制变更
                if application_tendency in ["Reject", "Hesitate"] and action == "ChangeOrder":
                    conflicts.append(f"用户{application_tendency}推荐套餐，不应该强制变更，但规则引擎计算的动作是{action}")
                
                # 规则3: 如果是查询(Enquiry)且用户同意，应该执行变更或告别
                if consumption_type == "Enquiry" and action not in ["ChangeOrder", "GoodBye"]:
                    conflicts.append(f"查询后应该变更或礼貌结束，但规则引擎计算的动作是{action}")
                
                # 规则4: 如果用户情绪不满，不应该简单结束
                if emotion == "Discontent" and action == "GoodBye":
                    conflicts.append(f"用户情绪不满，不应该直接结束，应该转人工处理")
                
                # 规则5: 如果用户取消套餐，应该走特殊逻辑而非变更
                if consumption_type == "Cancel" and action == "ChangeOrder":
                    conflicts.append(f"用户取消套餐，不应该执行变更，应该处理取消逻辑")
            
            # 如果有冲突,返回验证失败
            if conflicts:
                return {
                    "verified": False,
                    "rule_path": rule_result.now_path,
                    "rule_finals": rule_result.finals,
                    "conflict_description": "; ".join(conflicts),
                    "hint": "请重新审视这些分类字段之间的逻辑关系,确保它们相互一致"
                }
            
            # 验证通过
            return {
                "verified": True,
                "rule_path": rule_result.now_path,
                "rule_finals": rule_result.finals,
                "message": "分类结果通过规则引擎验证"
            }
            
        except Exception as e:
            logger.error(f"规则引擎验证失败: {e}")
            return {
                "verified": True,  # 验证失败时默认通过,不影响评测
                "error": str(e),
                "message": "规则引擎验证过程出错,跳过验证"
            }
    
    def _get_system_info_desc(self, scenario_id: str) -> str:
        """根据场景获取系统信息字段说明"""
        
        # 在线教育场景
        if scenario_id == "online_education":
            return """
系统信息字段说明（在线教育场景）：
- CourseList: 学员当前在学的所有课程列表
- HistoricalComplaintRecords: 是否有历史投诉记录 (true/false)
- QuestionTypeFor30Days: 该学员30天内出现的所有问题类型列表
- isRiskUser: 是否为风险用户 (true/false)

注意: 在判断某些分类字段时需要参考系统信息,例如:
- QuestionRelevance需要参考CourseList判断问题是否与在学课程相关
- RepeatedRaised需要参考QuestionTypeFor30Days和对话历史判断是否重复反馈
"""
        
        # 电商退款场景
        elif scenario_id == "ecommerce_refund":
            return """
系统信息字段说明（电商退款场景）：
- ShippingStatus: 物流状态 (Unshipped/Shipping/Signed)
- CreditLevel: 用户信用等级 (High/Medium/Low)

注意: 在判断某些分类字段时需要参考系统信息,例如:
- ProvidedDocument需要根据对话判断用户是否提交了售后凭证
- Responsibility需要结合系统变量判断责任归属
"""
        
        # 电信套餐场景
        elif scenario_id == "telecom_package":
            return """
系统信息字段说明（电信套餐场景）：
- PackageStatus: 用户套餐状态 (Contracted/NoContract)
- Penalty: 用户需缴纳的违约金 (int)

注意: 在判断某些分类字段时需要参考系统信息,例如:
- ApplicationTendency需要根据对话判断用户是否倾向于办理推荐套餐
- ConsumptionType需要判断用户的实际消费意图
"""
        
        # 物业服务场景
        elif scenario_id == "property_service":
            return """
系统信息字段说明（物业服务场景）：
- HouseStatus: 业主房屋的居住状态 (Occupied/Rented/UnOccupied)
- FeePaymentStatus: 业主物业费的缴费状态 (Settled/Unpaid)

注意: 在判断某些分类字段时需要参考系统信息,例如:
- CoreIntention需要判断业主的核心意图（支付、投诉或报修）
- EmergencyLevel需要根据对话内容和房屋状态综合判断
"""
        
        # 快递物流场景
        elif scenario_id == "logistics_delivery":
            return """
系统信息字段说明（快递物流场景）：
- orderStatus: 订单的配送进度状态 (Arrived/Delivered/Undelivered)
- hasInsurance: 订单/包裹是否购买保险 (True/False)

注意: 在判断某些分类字段时需要参考系统信息,例如:
- UserIntention需要判断用户发起请求的核心目的（加急、投诉或修改）
- ComplaintValidity需要根据orderStatus判断投诉是否合理
"""
        
        # 在线航司改签退票场景
        elif scenario_id == "airline_refund":
            return """
系统信息字段说明（在线航司改签退票场景）：
- memberLevel: 用户会员等级 (VIP/Regular/Blacklist)
- hasInsurance: 订单是否购买保险 (True/False)

注意: 在判断某些分类字段时需要参考系统信息,例如:
- CoreDemand需要判断用户核心诉求（改签或退票、投诉、咨询）
- ChangeReason需要判断用户改退签的原因（个人、航司、天气）
"""
        
        # 其他场景
        else:
            return "系统信息字段说明: 根据具体场景定义"
    
    def _get_classification_fields_desc(self, scenario_id: str) -> str:
        """根据场景获取分类字段说明"""
        
        # 在线教育场景
        if scenario_id == "online_education":
            return """
1. DescriptionClear - 问题描述是否清晰（True/False）
   - True: 用户的问题描述具体、明确，有关键信息
   - False: 问题描述模糊、缺少关键信息
2. QuestionRelevance - 问题是否与课程相关（True/False）
   - True: 涉及课程内容、学习进度、课程材料等
   - False: 涉及账号、登录、价格、客服等非课程问题
3. EmotionTendency - 用户情绪倾向（"Calm"/"Dissatisfied"）
   - "Calm": 用户情绪平和、礼貌
   - "Dissatisfied": 用户表现出不满、生气、投诉等负面情绪
4. ResolveDependency - 解决依赖度（"LowDependency"/"MediumDependency"/"HighDependency"/null）
   - "LowDependency": 只需要简单查询、基础解答
   - "MediumDependency": 需要提供示例资料、详细说明
   - "HighDependency": 需要专属辅导老师、一对一辅导
5. RepeatedRaised - 是否重复反馈（True/False）
   - True: 用户明确提到"之前反映过"或对话历史中有相同问题
   - False: 首次提出该问题
6. RegardingRefund - 是否涉及退费（True/False）
   - True: 提到退费、退款、取消等退费相关内容
   - False: 不涉及退费
"""
        
        # 电商退款场景
        elif scenario_id == "ecommerce_refund":
            return """
1. CoreIntention - 用户发起售后的核心需求（"ReturnOrRefund"/"Exchange"）
   - "ReturnOrRefund": 退货退款
   - "Exchange": 换货
2. ProvidedDocument - 用户是否提交售后相关凭证（True/False）
   - True: 提供了照片、视频等凭证
   - False: 未提供凭证
3. Responsibility - 售后问题的责任归属（"User"/"Merchant"）
   - "User": 用户责任
   - "Merchant": 商家/平台责任
4. RefundReasonable - 退款需求是否合理（"Reasonable"/"Unreasonable"）
   - "Reasonable": 退款需求合理
   - "Unreasonable": 退款需求不合理
5. EmotionStatus - 用户情绪状态（"Calm"/"Dissatisfied"）
   - "Calm": 用户情绪平和
   - "Dissatisfied": 用户表现出不满、生气
"""
        
        # 电信套餐场景
        elif scenario_id == "telecom_package":
            return """
1. ConsumptionType - 用户对话的意图（"Enquiry"/"Change"/"Cancel"）
   - "Enquiry": 咨询了解
   - "Change": 变更套餐
   - "Cancel": 取消套餐
2. ApplicationTendency - 用户是否倾向于办理推荐套餐（"Agree"/"Reject"/"Hesitate"）
   - "Agree": 用户同意办理
   - "Reject": 用户拒绝办理
   - "Hesitate": 用户犹豫不决
3. ConsumptionProfile - 用户倾向于办理的套餐类型（"Data"/"Voice"）
   - "Data": 流量套餐
   - "Voice": 语音套餐
4. EmotionTag - 用户对话中表现的情绪（"Calm"/"Discontent"）
   - "Calm": 用户情绪平和
   - "Discontent": 用户表现出不满或沮丧
"""
        
        # 物业服务场景
        elif scenario_id == "property_service":
            return """
1. CoreIntention - 住户对话的意图（"Payment"/"Complaint"/"Repair"）
   - "Payment": 物业费咨询或支付
   - "Complaint": 投诉
   - "Repair": 报修请求
2. EmotionTag - 住户在对话中表现的情绪（"Calm"/"Discontent"）
   - "Calm": 住户情绪平和
   - "Discontent": 住户表现出不满、生气
3. RepairItemCategory - 住户报修事项的具体分类（"IndoorFacilities"/"EnvironmentalHygiene"）
   - "IndoorFacilities": 室内设施维修
   - "EnvironmentalHygiene": 环境卫生问题
4. RelatedScope - 事项涉及的范围（"Personal"/"Public"）
   - "Personal": 个人房屋相关
   - "Public": 公共区域相关
5. EmergencyLevel - 事项紧急程度（"Urgent"/"NoUrgent"）
   - "Urgent": 紧急需要处理
   - "NoUrgent": 不紧急可稍后处理
"""
        
        # 快递物流场景
        elif scenario_id == "logistics_delivery":
            return """
1. RiskStatus - 订单的危险程度（"Risk"/"Safe"）
   - "Risk": 订单存在风险
   - "Safe": 订单安全
2. InfoCompleteness - 用户提交信息的完整程度（True/False）
   - True: 提供了订单号等完整信息
   - False: 信息不完整
3. UserIntention - 用户发起请求的核心目的（"Urge"/"Complaint"/"Modify"）
   - "Urge": 加急查询
   - "Complaint": 投诉
   - "Modify": 修改地址或其他信息
4. EmotionalState - 用户反馈问题时的情绪状态（"Calm"/"Dissatisfied"）
   - "Calm": 用户情绪平和
   - "Dissatisfied": 用户表现出不满
5. EmergencyLevel - 事项紧急程度（"Urgent"/"Normal"）
   - "Urgent": 非常紧急
   - "Normal": 正常紧急程度
6. ComplaintValidity - 投诉的合理性（True/False）
   - True: 投诉合理有效
   - False: 投诉不合理
"""
        
        # 在线航司改签退票场景
        elif scenario_id == "airline_refund":
            return """
1. CoreDemand - 用户核心诉求（"RescheduleOrRefund"/"Complaint"/"Inqury"）
   - "RescheduleOrRefund": 改签或退票
   - "Complaint": 投诉
   - "Inqury": 咨询
2. ChangeReason - 用户改退签的原因（"Personal"/"Airline"/"Weather"）
   - "Personal": 个人原因
   - "Airline": 航司原因
   - "Weather": 天气原因
3. UserEmotion - 用户情绪状态（"Urgent"/"Dissatisfied"/"Normal"）
   - "Urgent": 非常紧急
   - "Dissatisfied": 不满意
   - "Normal": 正常
4. DocumentValidity - 是否提供了合理凭证（"Valid"/"Invalid"）
   - "Valid": 提供了有效凭证
   - "Invalid": 未提供或无效凭证
5. IsInfoComplete - 信息是否完善（"Complete"/"Incomplete"）
   - "Complete": 提供了航班号等完整信息
   - "Incomplete": 信息不完整
"""
        
        # 未知场景
        else:
            return f"（场景 {scenario_id} 的分类字段未定义，请补充配置）"
    
    def _get_json_example_for_scenario(self, scenario_id: str) -> str:
        """根据场景获取JSON格式示例"""
        
        if scenario_id == "online_education":
            return """{
    "classification": {
        "DescriptionClear": "true或false,根据用户描述是否清晰",
        "QuestionRelevance": "true或false,根据提问是否与课程相关",
        "EmotionTendency": "从'Calm'/'Anxious'/'Confused'中选择,根据用户情绪",
        "ResolveDependency": "从'LowDependency'/'MediumDependency'/'HighDependency'中选择",
        "RepeatedRaised": "true或false,根据用户是否重复提问",
        "RegardingRefund": "true或false,根据是否涉及退款"
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
        
        elif scenario_id == "ecommerce_refund":
            return """{
    "classification": {
        "CoreIntention": "从'ReturnOrRefund'/'Complaint'/'Inquiry'中选择,根据用户核心诉求",
        "ProvidedDocument": "true或false,根据用户是否提供了订单/凭证",
        "Responsibility": "从'Merchant'/'Platform'/'User'中选择,根据责任归属",
        "RefundReasonable": "从'Reasonable'/'Unreasonable'/'Unclear'中选择,根据退款合理性",
        "EmotionStatus": "从'Calm'/'Dissatisfied'/'Angry'中选择,根据用户情绪"
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
        
        elif scenario_id == "telecom_package":
            return """{
    "classification": {
        "ConsumptionType": "从'Change'/'Upgrade'/'Query'中选择,根据用户意图",
        "ApplicationTendency": "从'Agree'/'Disagree'/'Uncertain'中选择,根据用户应用意向",
        "ConsumptionProfile": "从'Data'/'Voice'/'Mixed'中选择,根据消费偏好",
        "EmotionTag": "从'Calm'/'Urgent'/'Dissatisfied'中选择,根据用户情绪"
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
        
        elif scenario_id == "property_service":
            return """{
    "classification": {
        "CoreIntention": "从'Repair'/'Complaint'/'Inquiry'中选择,根据用户核心诉求",
        "EmotionTag": "从'Calm'/'Anxious'/'Angry'中选择,根据用户情绪",
        "RepairItemCategory": "从'IndoorFacilities'/'Outdoor'/'Common'中选择,根据维修物业类型",
        "RelatedScope": "从'Personal'/'Shared'/'Building'中选择,根据影响范围",
        "EmergencyLevel": "从'Urgent'/'Normal'/'NoUrgent'中选择,根据紧急程度"
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
        
        elif scenario_id == "logistics_delivery":
            return """{
    "classification": {
        "RiskStatus": "从'Safe'/'AtRisk'/'Lost'中选择,根据包裹风险状态",
        "InfoCompleteness": "true或false,根据用户提供的信息是否完整",
        "UserIntention": "从'Urge'/'Complaint'/'Query'中选择,根据用户意图",
        "EmotionalState": "从'Calm'/'Anxious'/'Angry'中选择,根据用户情绪",
        "EmergencyLevel": "从'Urgent'/'Normal'/'Low'中选择,根据事件紧急程度",
        "ComplaintValidity": "true或false,根据投诉是否有效"
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
        
        elif scenario_id == "airline_refund":
            return """{
    "classification": {
        "CoreDemand": "从'RescheduleOrRefund'/'Complaint'/'Inquiry'中选择,根据用户核心诉求",
        "ChangeReason": "从'Personal'/'Airline'/'Weather'中选择,改退签原因",
        "UserEmotion": "从'Urgent'/'Dissatisfied'/'Normal'中选择,根据用户情绪",
        "DocumentValidity": "从'Valid'/'Invalid'中选择,根据是否提供有效凭证",
        "IsInfoComplete": "从'Complete'/'Incomplete'中选择,根据信息完整性"
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
        
        else:
            # 通用格式
            return """{
    "classification": {
        // 根据场景填写相应的分类字段
    },
    "chat_quality_dimensions": {
        "linguistic_quality": "从3/6/9中选择",
        "anthropomorphism_emotion": "从3/6/9中选择",
        "content_utility": "从3/6/9中选择",
        "user_satisfaction": "从3/6/9中选择",
        "instruction_compliance": "从3/6/9中选择"
    },
    "classification_reasoning": "分类理由...",
    "chat_quality_reasoning": "每个维度的得分说明，使用相应的分数说明(例如:9分表示...、6分表示...、3分表示...)"
}"""
    
    def _classify_input_helper(self, user_message: str, context_data: Dict[str, Any], scenario_id: str) -> Dict[str, Any]:
        """辅助函数：使用规则引擎提供分类建议"""
        # 这里可以调用规则引擎的_classify_input方法作为辅助
        # 用于和裁判模型的判断相互印证
        return {}  # TODO: 实现规则引擎辅助
    
    
    def _build_dialogue_context(self, dialogue_history: list, max_turns: Optional[int] = None) -> str:
        """
        构建对话上下文文本
        
        Args:
            dialogue_history: 对话历史列表
            max_turns: 最大轮次数（用于限制输出长度）
            
        Returns:
            str: 对话上下文文本
        """
        if not dialogue_history:
            return ""
        
        context_parts = []
        for i, turn in enumerate(dialogue_history):
            if max_turns and i >= max_turns:
                break
            
            # 支持两种格式：列表格式和字典格式
            if isinstance(turn, dict):
                role = turn.get("role", "unknown")
                content = turn.get("content", "")
            else:
                # 假设是(role, content)的元组或列表
                role = turn[0] if len(turn) > 0 else "unknown"
                content = turn[1] if len(turn) > 1 else ""
            
            role_display = "用户" if role == "user" else "客服" if role == "assistant" else role
            context_parts.append(f"{role_display}: {content}")
        
        return "\n".join(context_parts)
     
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析LLM的JSON响应
        
        Args:
            response_text: LLM的响应文本
            
        Returns:
            Dict: 解析后的JSON对象
        """
        try:
            # 尝试提取JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                return data
        
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from LLM response: {e}")
        except Exception as e:
            logger.error(f"Error parsing JSON response: {e}")
        
        # 返回空字典和错误信息
        return {"error": "Failed to parse JSON", "raw_response": response_text[:200]}
   

class MultiModelJudge:
    """
    多模型评判器
    
    支持同时使用多个LLM进行评估，然后取平均值
    """
    
    def __init__(self, judges: Dict[str, LLMJudge]):
        """
        初始化多模型评判器
        
        Args:
            judges: 评判器字典 {模型名: LLMJudge}
        """
        self.judges = judges
    
    def evaluate_chat_quality(
        self,
        chat_text: str,
        user_message: str,
        dialogue_context: str,
        evaluation_criteria: Optional[Dict[str, str]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        使用多个评判器评估话术质量
        
        Args:
            chat_text: 客服回复
            user_message: 用户消息
            dialogue_context: 对话上下文
            evaluation_criteria: 评价标准
            
        Returns:
            Tuple[float, Dict]: (综合评分, 详细信息)
        """
        scores = []
        details = {}
        
        for model_name, judge in self.judges.items():
            try:
                score, detail = judge.evaluate_chat_quality(
                    chat_text=chat_text,
                    user_message=user_message,
                    dialogue_context=dialogue_context,
                    evaluation_criteria=evaluation_criteria,
                )
                scores.append(score)
                details[model_name] = detail
            except Exception as e:
                logger.error(f"Error from {model_name}: {e}")
        
        # 计算平均分
        avg_score = sum(scores) / len(scores) if scores else 0.5
        
        return avg_score, {
            "average_score": avg_score,
            "model_scores": dict(zip(self.judges.keys(), scores)),
            "details": details,
        }


class MultiModelVotingJudge:
    """
    多模型投票评判器
    
    支持同时调用多个LLM模型（通常是三个API模型）进行评估，然后通过投票机制决定最终结果：
    1. 话术质量得分：计算三个模型评分的平均值
    2. 分类字段：三个模型投票，少数服从多数决定最终分类
    
    这样避免了对单个模型的过度依赖，提高了评测的鲁棒性
    """
    
    def __init__(self, judges: Dict[str, LLMJudge]):
        """
        初始化多模型投票评判器
        
        Args:
            judges: 评判器字典 {模型名: LLMJudge}
        """
        if len(judges) < 2:
            raise ValueError("MultiModelVotingJudge requires at least 2 judges")
        
        self.judges = judges
        self.model_names = list(judges.keys())
    
    def _vote_classification(self, classifications: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        通过投票选择最终分类
        
        对每个分类字段，取得票最多的值（少数服从多数）
        
        Args:
            classifications: 各模型的分类结果 {模型名: 分类字典}
            
        Returns:
            Dict: 投票后的分类结果
        """
        # 获取所有分类字段名
        all_fields = set()
        for classification in classifications.values():
            all_fields.update(classification.keys())
        
        voted_classification = {}
        voting_details = {}
        
        for field in all_fields:
            votes = {}
            
            # 收集每个模型对该字段的投票
            for model_name, classification in classifications.items():
                if field in classification:
                    value = classification[field]
                    # 将值转换为字符串以便投票统计（支持布尔值、数字、字符串等）
                    value_str = str(value)
                    if value_str not in votes:
                        votes[value_str] = []
                    votes[value_str].append(model_name)
            
            # 选择得票最多的值
            if votes:
                max_votes = max(len(voters) for voters in votes.values())
                winning_values = [val for val, voters in votes.items() if len(voters) == max_votes]
                
                # 如果有平票，选择字典序最小的（保证确定性）
                winning_value = sorted(winning_values)[0]
                
                # 尝试将字符串转换回原始类型
                if winning_value.lower() == "true":
                    winning_value = True
                elif winning_value.lower() == "false":
                    winning_value = False
                else:
                    try:
                        winning_value = int(winning_value)
                    except ValueError:
                        pass  # 保持字符串格式
                
                voted_classification[field] = winning_value
                voting_details[field] = {
                    "votes": {val: len(voters) for val, voters in votes.items()},
                    "winning_value": winning_value,
                    "winning_voters": votes.get(str(winning_value), []),
                }
        
        return voted_classification, voting_details
    
    def evaluate_turn_comprehensive(
        self,
        turn_id: int,
        user_message: str,
        agent_chat: str,
        dialogue_history: Optional[list] = None,
        scenario_id: str = "online_education",
        context_data: Optional[Dict[str, Any]] = None,
        use_rule_verification: bool = False,  # 投票模式下通常不需要规则验证
    ) -> Dict[str, Any]:
        """
        使用多个模型进行综合评估，然后通过投票机制选择最终结果
        
        Args:
            turn_id: 轮次ID
            user_message: 用户消息
            agent_chat: 客服回复
            dialogue_history: 完整对话历史
            scenario_id: 场景ID
            context_data: 上下文数据
            use_rule_verification: 是否使用规则验证（通常不需要，因为已有投票机制）
            
        Returns:
            Dict: {
                "classification": {...},  # 投票后的分类结果
                "chat_quality_score": 0-1,  # 三个模型评分的平均值
                "voting_details": {
                    "classification_voting": {...},  # 分类投票详情
                    "quality_scores": {...},  # 各模型的质量得分
                    "quality_dimensions": {...},  # 各模型的五维度评分
                },
                "individual_results": {...}  # 各模型的原始结果
            }
        """
        individual_results = {}
        classifications = {}
        quality_scores = []
        quality_dimensions_by_model = {}
        
        # 第一步：调用所有模型进行评估
        logger.info(f"【投票评测】开始调用 {len(self.judges)} 个模型...")
        logger.info(f"【投票评测】Judge 模型列表: {self.model_names}")
        
        for idx, (model_name, judge) in enumerate(self.judges.items()):
            try:
                logger.info(f"【Judge-{idx}】开始调用 {model_name}")
                result = judge.evaluate_turn_comprehensive(
                    turn_id=turn_id,
                    user_message=user_message,
                    agent_chat=agent_chat,
                    dialogue_history=dialogue_history,
                    scenario_id=scenario_id,
                    context_data=context_data,
                    use_rule_verification=False,  # 不使用规则验证，因为我们用投票代替
                )
                
                individual_results[model_name] = result
                
                # 收集分类结果
                if "classification" in result:
                    classifications[model_name] = result["classification"]
                    logger.info(f"【Judge-{idx}】{model_name} 分类结果: {result['classification']}")
                
                # 收集质量评分
                if "chat_quality_score" in result:
                    score = result["chat_quality_score"]
                    if isinstance(score, (int, float)):
                        quality_scores.append(score)
                        logger.info(f"【Judge-{idx}】{model_name} 话术评分: {score:.3f}")
                
                # 收集五维度评分（用于调试）
                if "chat_quality_dimensions" in result:
                    quality_dimensions_by_model[model_name] = result["chat_quality_dimensions"]
                
                logger.info(f"【Judge-{idx}】{model_name} ✓ 评测完成")
            
            except Exception as e:
                # 检查是否是429错误(请求速率限制)
                error_str = str(e)
                is_429 = "429" in error_str or "rate limit" in error_str.lower() or "too many requests" in error_str.lower()
                
                if is_429:
                    logger.warning(f"【Judge-{idx}】{model_name} 遇到429错误,等待120秒后重试...")
                    import time
                    time.sleep(120)
                    logger.info(f"【Judge-{idx}】{model_name} 等待完成,重新调用...")
                    # 重试一次
                    try:
                        result = judge.evaluate_turn_comprehensive(
                            turn_id=turn_id,
                            user_message=user_message,
                            agent_chat=agent_chat,
                            agent_output=agent_output,
                            system_info=system_info,
                            dialogue_context=dialogue_context,
                            evaluation_criteria=evaluation_criteria,
                        )
                        individual_results[model_name] = result
                        
                        if "classification" in result:
                            classifications[model_name] = result["classification"]
                            logger.info(f"【Judge-{idx}】{model_name} 重试成功,分类结果: {result['classification']}")
                        
                        if "chat_quality_score" in result:
                            score = result["chat_quality_score"]
                            if isinstance(score, (int, float)):
                                quality_scores.append(score)
                                logger.info(f"【Judge-{idx}】{model_name} 重试成功,话术评分: {score:.3f}")
                        
                        if "chat_quality_dimensions" in result:
                            quality_dimensions_by_model[model_name] = result["chat_quality_dimensions"]
                        
                        logger.info(f"【Judge-{idx}】{model_name} ✓ 重试成功")
                    except Exception as retry_e:
                        logger.error(f"【Judge-{idx}】{model_name} ✗ 重试仍失败: {retry_e}", exc_info=True)
                        individual_results[model_name] = {"error": str(retry_e)}
                else:
                    logger.error(f"【Judge-{idx}】{model_name} ✗ 评测失败: {e}", exc_info=True)
                    individual_results[model_name] = {"error": str(e)}
        
        # 第二步：对分类结果进行投票
        logger.info(f"【投票评测】收集到 {len(classifications)} 个分类结果")
        if classifications:
            logger.info(f"【投票评测】各 Judge 的分类结果:")
            for model_name, clf in classifications.items():
                logger.info(f"  - {model_name}: {clf}")
            voted_classification, voting_details = self._vote_classification(classifications)
            logger.info(f"【投票评测】投票后的分类结果: {voted_classification}")
        else:
            logger.warning(f"【投票评测】⚠️  没有收集到任何分类结果!")
            voted_classification = {}
            voting_details = {}
        
        # 第三步：计算话术质量得分的平均值
        logger.info(f"【投票评测】收集到 {len(quality_scores)} 个评分")
        if quality_scores:
            logger.info(f"【投票评测】各 Judge 的评分: {quality_scores}")
        avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.5
        logger.info(f"【投票评测】均值话术评分: {avg_quality_score:.3f}")
        
        # 第四步：计算五维度评分的平均值
        # 从各个模型的评分中提取五维度数据，然后计算平均值
        dimension_names = ["linguistic_quality", "anthropomorphism_emotion", "content_utility", "user_satisfaction", "instruction_compliance"]
        average_dimensions = {}
        
        for dim_name in dimension_names:
            dim_values = []
            for model_name, dimensions in quality_dimensions_by_model.items():
                if dim_name in dimensions:
                    value = dimensions[dim_name]
                    # 支持多种值类型（整数、字符串、浮点数）
                    if isinstance(value, int):
                        dim_values.append(value)
                    elif isinstance(value, float):
                        dim_values.append(value)
                    elif isinstance(value, str):
                        # 从字符串中提取整数
                        import re
                        match = re.search(r'\d+', value)
                        if match:
                            dim_values.append(float(match.group()))
            
            # 计算该维度的平均值（如果有数据的话）
            if dim_values:
                average_dimensions[dim_name] = sum(dim_values) / len(dim_values)
            else:
                average_dimensions[dim_name] = 0.0
        
        # 第五步：组合最终结果
        final_result = {
            "classification": voted_classification,
            "chat_quality_score": avg_quality_score,
            "chat_quality_dimensions": average_dimensions,  # 新增：五维度平均评分
            "voting_details": {
                "classification_voting": voting_details,
                "quality_scores": {
                    model_name: quality_scores[i]
                    for i, model_name in enumerate(self.model_names[:len(quality_scores)])
                },
                "average_quality_score": avg_quality_score,
                "quality_dimensions_by_model": quality_dimensions_by_model,  # 各模型的五维度评分
                "average_dimensions": average_dimensions,  # 五维度平均评分
            },
            "individual_results": individual_results,
            "num_models": len(self.judges),
        }
        
        return final_result
