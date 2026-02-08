#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
评测器/裁判系统
Evaluator/Judge System

负责：
1. 代码计算的指标 (分类准确率、路径正确性、动作正确性)
2. 模型判断的指标 (话术质量、指令遵循能力)
3. 综合评分
4. 评测报告生成
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import json


class MetricType(Enum):
    """指标类型"""
    CODE_COMPUTED = "code_computed"      # 代码计算
    MODEL_JUDGED = "model_judged"        # 模型判断


@dataclass
class MetricScore:
    """指标得分"""
    metric_name: str                     # 指标名称
    metric_type: MetricType              # 指标类型
    score: float                         # 得分 (0-1)
    max_score: float = 1.0               # 最大得分
    weight: float = 1.0                  # 权重
    explanation: str = ""                # 解释
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息


@dataclass
class EvaluationReport:
    """评测报告"""
    simulation_id: str                   # 模拟ID
    scenario_id: str                     # 场景ID
    model_name: str                      # 模型名称
    user_intent: str                     # 用户意图
    adversarial_intensity: str           # 对抗强度
    
    # 指标得分
    metric_scores: List[MetricScore] = field(default_factory=list)
    
    # 综合得分
    overall_score: float = 0.0           # 总体得分
    
    # 评测信息
    evaluation_timestamp: str = ""       # 评测时间戳
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "simulation_id": self.simulation_id,
            "scenario_id": self.scenario_id,
            "model_name": self.model_name,
            "user_intent": self.user_intent,
            "adversarial_intensity": self.adversarial_intensity,
            "metric_scores": [
                {
                    "metric_name": score.metric_name,
                    "metric_type": score.metric_type.value,
                    "score": score.score,
                    "max_score": score.max_score,
                    "weight": score.weight,
                    "explanation": score.explanation,
                    "details": score.details,
                }
                for score in self.metric_scores
            ],
            "overall_score": self.overall_score,
            "evaluation_timestamp": self.evaluation_timestamp,
        }


class CodeComputedEvaluator:
    """代码计算类评测器"""
    
    @staticmethod
    def compute_classification_accuracy(
        agent_classification: Dict[str, Any],
        ground_truth_classification: Dict[str, Any],
        weighted: bool = True
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算分类准确率
        
        Args:
            agent_classification: 模型的分类输出 (可能是dict或ClassificationOutput对象)
            ground_truth_classification: 真实分类
            weighted: 是否使用加权平均
            
        Returns:
            Tuple[float, Dict]: (准确率, 详细信息)
        """
        details = {}
        total_score = 0.0
        field_count = 0
        
        # 【修复】处理agent_classification可能不是字典的情况
        # 如果是ClassificationOutput对象，转换为字典
        if hasattr(agent_classification, 'to_dict'):
            agent_dict = agent_classification.to_dict()
        elif isinstance(agent_classification, dict):
            agent_dict = agent_classification
        else:
            # 未知类型，返回0分
            import logging
            logging.warning(f"Unknown agent_classification type: {type(agent_classification)}, value={agent_classification}")
            return 0.0, {"error": f"Unknown classification type: {type(agent_classification)}"}
        
        for field_name in ground_truth_classification:
            expected_value = ground_truth_classification[field_name]
            actual_value = agent_dict.get(field_name)
            
            # 比较值
            is_correct = expected_value == actual_value
            details[field_name] = {
                "expected": expected_value,
                "actual": actual_value,
                "correct": is_correct,
            }
            
            if is_correct:
                total_score += 1.0
            
            field_count += 1
        
        accuracy = total_score / field_count if field_count > 0 else 0.0
        
        return accuracy, details
    
    @staticmethod
    def normalize_path(path: List[str]) -> List[str]:
        """
        标准化路径 - 去掉start和end节点

        Args:
            path: 原始路径

        Returns:
            标准化后的路径
        """
        return [node for node in path if node not in ['start', 'end']]

    @staticmethod
    def compute_path_correctness(
        path_taken: List[str],
        expected_paths: List[List[str]],
        sop_graph
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算路径正确性

        Args:
            path_taken: 实际走过的路径
            expected_paths: 期望的路径列表
            sop_graph: SOP图

        Returns:
            Tuple[float, Dict]: (正确性得分, 详细信息)
        """
        # 标准化路径 - 去掉start和end
        normalized_taken = CodeComputedEvaluator.normalize_path(path_taken)
        normalized_expected = [CodeComputedEvaluator.normalize_path(p) for p in expected_paths]

        details = {
            "original_path_taken": path_taken,
            "normalized_path_taken": normalized_taken,
            "path_length": len(normalized_taken),
        }

        # 验证标准化后的路径是否有效（只验证相邻节点之间是否有边）
        # 注意：不要求路径必须从start开始到end结束，因为可能只走到中间步骤
        for i in range(len(normalized_taken) - 1):
            current_node = normalized_taken[i]
            next_node = normalized_taken[i + 1]

            # 检查是否存在边（跳过action节点之间的边，因为action节点是终止节点）
            if current_node.startswith("action_") or next_node.startswith("action_"):
                continue

            edge_exists = any(
                edge.source_node_id == current_node and edge.target_node_id == next_node
                for edge in sop_graph.edges
            )

            if not edge_exists:
                details["is_valid"] = False
                details["validation_message"] = f"No edge from {current_node} to {next_node}"
                break
        else:
            # 如果循环正常完成（没有break），说明所有相邻节点之间都有边
            details["is_valid"] = True
            details["validation_message"] = "valid"

        # 检查是否在标准化后的期望路径中
        if normalized_taken in normalized_expected:
            details["is_expected"] = True
            details["exact_match"] = True
            return 1.0, details
        else:
            details["is_expected"] = False

            # 计算与每个期望路径的相似度
            best_match_score = 0.0
            best_match_path = None

            for expected_path in normalized_expected:
                # 计算共同前缀长度
                common_prefix = 0
                for i, (a, b) in enumerate(zip(normalized_taken, expected_path)):
                    if a == b:
                        common_prefix += 1
                    else:
                        break

                # 计算相似度：共同前缀长度 / max(实际路径长度, 期望路径长度)
                max_len = max(len(normalized_taken), len(expected_path))
                similarity = common_prefix / max_len if max_len > 0 else 0.0

                if similarity > best_match_score:
                    best_match_score = similarity
                    best_match_path = expected_path

            details["similarity"] = best_match_score
            details["best_match_path"] = best_match_path
            return best_match_score, details
    
    @staticmethod
    def infer_expected_actions(
        sop_graph,
        path_taken: List[str]
    ) -> List[str]:
        """
        从走过的路径推断期望的动作序列
        
        Args:
            sop_graph: SOP 图
            path_taken: 实际走过的路径
        
        Returns:
            期望的动作列表
        """
        expected_actions = []
        
        # 遍历路径中的所有节点，收集所有 action 节点
        for node_id in path_taken:
            if node_id in sop_graph.nodes:
                node = sop_graph.nodes[node_id]
                # 如果节点有动作名称，添加到期望动作列表
                if hasattr(node, 'action_name') and node.action_name:
                    expected_actions.append(node.action_name)
        
        return expected_actions
    
    @staticmethod
    def compute_action_correctness(
        action_sequence: List[str],
        expected_actions: List[str],
        comparison_mode: str = "final_action"
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算动作正确性
        
        Args:
            action_sequence: 实际动作序列
            expected_actions: 期望的动作序列
            comparison_mode: 比较模式 ("final_action" 或 "sequence")
            
        Returns:
            Tuple[float, Dict]: (正确性得分, 详细信息)
        """
        details = {
            "action_sequence": action_sequence,
            "expected_actions": expected_actions,
            "comparison_mode": comparison_mode,
        }
        
        # 处理空期望动作的情况
        if not expected_actions:
            if action_sequence:
                details["has_action"] = True
                details["warning"] = "No expected actions provided"
                return 0.8, details
            else:
                details["has_action"] = False
                return 0.2, details
        
        if comparison_mode == "final_action":
            # 检查最后一个动作
            if action_sequence:
                last_action = action_sequence[-1]
                expected_last_action = expected_actions[-1]
                
                if last_action == expected_last_action:
                    details["final_action_correct"] = True
                    return 1.0, details
                else:
                    details["final_action_correct"] = False
                    return 0.0, details
            else:
                details["final_action_correct"] = False
                details["error"] = "No actions taken"
                return 0.0, details
        elif comparison_mode == "sequence":
            # 比较完整序列
            if action_sequence == expected_actions:
                details["sequence_match"] = True
                return 1.0, details
            else:
                # 计算相似度
                match_count = sum(1 for a, e in zip(action_sequence, expected_actions) if a == e)
                max_len = max(len(action_sequence), len(expected_actions))
                similarity = match_count / max_len if max_len > 0 else 0.0
                details["sequence_match"] = False
                details["similarity"] = similarity
                return similarity, details
        
        return 0.5, details
    
    @staticmethod
    def compute_finals_correctness(
        agent_finals: Dict[str, Any],
        correct_finals: Dict[str, Any]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算 finals 字段正确性
        
        Args:
            agent_finals: 客服模型输出的 finals
            correct_finals: 正确的 finals（从规则引擎计算）
            
        Returns:
            Tuple[float, Dict]: (正确性得分, 详细信息)
        """
        details = {
            "agent_finals": agent_finals,
            "correct_finals": correct_finals,
        }
        score = 0.0
        
        # 检查 Action 字段
        agent_action = agent_finals.get("Action", "")
        correct_action = correct_finals.get("Action", "")
        action_correct = (agent_action == correct_action)
        details["action_correct"] = action_correct
        details["agent_action"] = agent_action
        details["correct_action"] = correct_action
        
        if action_correct:
            score += 0.7  # Action 占 70%
            
            # 如果 Action 是 PLAN，检查 PLAN 字段
            if correct_action == "PLAN":
                agent_plan = agent_finals.get("PLAN", "")
                correct_plan = correct_finals.get("PLAN", "")
                plan_correct = (agent_plan == correct_plan)
                details["plan_correct"] = plan_correct
                details["agent_plan"] = agent_plan
                details["correct_plan"] = correct_plan
                
                if plan_correct:
                    score += 0.3  # PLAN 占 30%
            else:
                # 非 PLAN 情况，不需要检查 PLAN 字段
                score += 0.3
                details["plan_correct"] = True  # 标记为不需要检查
        
        details["score"] = score
        return score, details


class ModelJudgedEvaluator:
    """模型判断类评测器"""
    
    def __init__(self, judge_model = None):
        """
        初始化模型判断评测器
        
        Args:
            judge_model: 裁判模型 (LLM)
        """
        self.judge_model = judge_model
    
    def evaluate_chat_quality(
        self,
        chat_text: str,
        user_message: str,
        dialogue_context: str,
        evaluation_criteria: Optional[Dict[str, str]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        评估话术质量
        
        Args:
            chat_text: 客服回复文本
            user_message: 用户消息
            dialogue_context: 对话上下文
            evaluation_criteria: 评价标准 (可选)
            
        Returns:
            Tuple[float, Dict]: (评分, 详细信息)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        details = {}
        
        # 基础规则检查
        details["length"] = len(chat_text)
        details["has_content"] = len(chat_text) > 0
        
        # 检查是否是模板回复
        template_phrases = ["感谢您的反馈", "我们正在处理", "尽快给您"]
        details["template_score"] = sum(
            1 for phrase in template_phrases if phrase in chat_text
        ) / len(template_phrases)
        
        # 检查句子完整性
        details["sentence_completeness"] = self._check_sentence_completeness(chat_text)
        
        # 如果有裁判模型，调用LLM评分
        if self.judge_model:
            logger.info(f"Using judge_model for evaluation, model type: {type(self.judge_model).__name__}")
            llm_score, llm_details = self._evaluate_with_llm(
                chat_text, user_message, dialogue_context, evaluation_criteria
            )
            details["llm_score"] = llm_score
            details["llm_details"] = llm_details
            score = llm_score
            logger.info(f"LLM evaluation result: score={llm_score}, has_error={'error' in llm_details}")
        else:
            logger.warning("No judge_model available, using heuristic rules instead")
            # 使用启发式规则
            score = (
                details["has_content"] * 0.3 +
                (1.0 - details["template_score"]) * 0.4 +
                details["sentence_completeness"] * 0.3
            )
        
        return score, details
    
    def _check_sentence_completeness(self, text: str) -> float:
        """检查句子完整性"""
        sentences = text.split("。")
        if not sentences:
            return 0.0
        
        complete_sentences = sum(
            1 for s in sentences if len(s.strip()) > 0
        )
        
        return complete_sentences / len(sentences) if sentences else 0.0
    
    def _evaluate_with_llm(
        self,
        chat_text: str,
        user_message: str,
        dialogue_context: str,
        evaluation_criteria: Optional[Dict[str, str]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        使用LLM评估话术质量
        
        Args:
            chat_text: 客服回复
            user_message: 用户消息
            dialogue_context: 对话上下文
            evaluation_criteria: 评价标准
            
        Returns:
            Tuple[float, Dict]: (评分, 详细信息)
        """
        try:
            # 判断 judge_model 是 LLMJudge 还是其他类型
            if hasattr(self.judge_model, 'evaluate_chat_quality'):
                # 使用 LLMJudge 的 evaluate_chat_quality 方法
                score, details = self.judge_model.evaluate_chat_quality(
                    chat_text=chat_text,
                    user_message=user_message,
                    dialogue_context=dialogue_context,
                    evaluation_criteria=evaluation_criteria,
                )
                return score, details
            else:
                # 如果judge_model不支持evaluate_chat_quality，返回默认值
                import logging
                logger = logging.getLogger(__name__)
                logger.warning("judge_model 不支持 evaluate_chat_quality 方法，返回默认评分")
                return 0.5, {"warning": "Judge model does not support evaluate_chat_quality"}
        except Exception as e:
            import logging
            logging.error(f"Error evaluating with LLM: {e}")
            return 0.5, {"error": str(e)}
    
    def _build_eval_prompt(
        self,
        chat_text: str,
        user_message: str,
        dialogue_context: str,
        evaluation_criteria: Optional[Dict[str, str]] = None
    ) -> str:
        """构建评估提示词"""
        criteria_text = ""
        if evaluation_criteria:
            criteria_text = "评估标准：\n" + "\n".join(
                f"- {k}: {v}" for k, v in evaluation_criteria.items()
            )
        
        prompt = f"""请评估以下客服回复的质量，从0到100分。

用户消息：
{user_message}

客服回复：
{chat_text}

对话上下文：
{dialogue_context}

{criteria_text}

请从以下维度进行评估：
1. 相关性 (是否回答了用户的问题)
2. 自然性 (是否像真人客服的回复)
3. 客户友好度 (是否友好和尊重)
4. 清晰性 (是否清晰易懂)

请返回如下JSON格式：
{{
    "score": <0-100的分数>,
    "reasoning": "<评估理由>",
    "dimension_scores": {{
        "relevance": <0-10>,
        "naturalness": <0-10>,
        "friendliness": <0-10>,
        "clarity": <0-10>
    }}
}}
"""
        return prompt
    
    def _parse_llm_response(self, response: str) -> Tuple[float, str]:
        """解析LLM响应"""
        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                score = data.get("score", 50) / 100.0
                reasoning = data.get("reasoning", "")
                return score, reasoning
        except:
            pass
        
        # 如果无法解析，返回默认值
        return 0.5, "无法解析LLM响应"


class Evaluator:
    """
    综合评测器
    
    整合代码计算评测和模型判断评测
    """
    
    def __init__(
        self,
        scenario_id: str,
        sop_graph,
        judge_model = None
    ):
        """
        初始化评测器
        
        Args:
            scenario_id: 场景ID
            sop_graph: SOP有向图
            judge_model: 裁判模型 (可选)
        """
        self.scenario_id = scenario_id
        self.sop_graph = sop_graph
        self.code_evaluator = CodeComputedEvaluator()
        self.model_evaluator = ModelJudgedEvaluator(judge_model)
    
    def evaluate_simulation(
        self,
        simulation_result,
        expected_path: Optional[List[str]] = None,
        expected_actions: Optional[List[str]] = None,
        expected_classifications: Optional[List[Dict[str, Any]]] = None,
        evaluation_criteria: Optional[Dict[str, str]] = None,
        eval_turns: Optional[List[int]] = None
    ) -> EvaluationReport:
        """
        评估整个模拟 - 新版评测逻辑
        
        评测流程：
        1. 裁判模型生成正确的 classification_output (ground truth)
        2. SOP规则引擎根据 classification_output 计算正确的 now_path 和 finals
        3. 对比客服模型输出，计算各项得分
        4. 综合评分：逻辑能力(80%) + 话术能力(20%)
        
        Args:
            simulation_result: 模拟结果
            expected_path: 期望路径 (已弃用，现由规则引擎计算)
            expected_actions: 期望动作序列 (已弃用，现由规则引擎计算)
            expected_classifications: 期望分类结果列表 (已弃用，现由裁判模型生成)
            evaluation_criteria: 评价标准 (可选)
            eval_turns: 指定评测轮次 (默认使用 [1, 5, 10, 15, last])
            
        Returns:
            EvaluationReport: 评测报告
        """
        from datetime import datetime
        import logging
        from ..sop import get_rule_engine
        
        logger = logging.getLogger(__name__)
        
        report = EvaluationReport(
            simulation_id=simulation_result.simulation_id,
            scenario_id=self.scenario_id,
            model_name=simulation_result.model_name,
            user_intent=simulation_result.user_intent,
            adversarial_intensity=simulation_result.adversarial_intensity,
            evaluation_timestamp=datetime.now().isoformat(),
        )
        
        # 0. 确定评测轮次 (索引从0开始: 0=第1轮, 4=第5轮, 9=第10轮, 14=第15轮, last=最后一轮)
        if eval_turns is None:
            total_turns = len(simulation_result.turns)
            # 评测轮次: 第1、5、10、15轮 + 最后一轮
            # 注意: turn_idx从0开始, 所以第1轮是idx=0, 第5轮是idx=4
            eval_turns = []
            for turn_num in [1, 5, 10, 15]:
                turn_idx = turn_num - 1  # 转换为0-based索引
                if turn_idx < total_turns:
                    eval_turns.append(turn_idx)
            
            # 添加最后一轮(如果不在列表中)
            if total_turns > 0:
                last_idx = total_turns - 1
                if last_idx not in eval_turns:
                    eval_turns.append(last_idx)
        
        # logger.warning(f"【诊断】评测轮次索引: {eval_turns} (总轮数: {len(simulation_result.turns)}, 即第{[i+1 for i in eval_turns]}轮)")
        
        # 1. 获取 SOP 规则引擎
        try:
            rule_engine = get_rule_engine(self.scenario_id)
            logger.info(f"已加载场景 {self.scenario_id} 的规则引擎")
        except Exception as e:
            
            logger.error(f"无法加载规则引擎: {e}")
            rule_engine = None
        
        # 2. 在指定轮次生成 ground truth（裁判模型 + 规则引擎）
        ground_truth_data = {}
        # logger.warning(f"【诊断】开始生成ground truth data，eval_turns={eval_turns}")
        for turn_idx in eval_turns:
            if turn_idx >= len(simulation_result.turns):
                continue
            
            turn = simulation_result.turns[turn_idx]
            dialogue_history = self._build_dialogue_history_list(simulation_result, turn_idx)
            agent_chat = turn.agent_output.chat if hasattr(turn.agent_output, 'chat') else ""
            
            # 2.1 裁判模型综合评估：一次性输出分类 + 话术评分
            gt_classification = {}
            chat_quality_score = 0.5
            chat_quality_dimensions = {}
            
            if self.model_evaluator.judge_model and hasattr(self.model_evaluator.judge_model, 'evaluate_turn_comprehensive'):
                try:
                    # 使用新的综合评估方法
                    context_data = {}
                    if hasattr(simulation_result, 'context_data'):
                        context_data = simulation_result.context_data or {}
                    
                    # 【投票模式】检查是否为 MultiModelVotingJudge，决定是否使用规则验证
                    use_rule_verification = True  # 默认使用规则验证
                    if hasattr(self.model_evaluator.judge_model, 'evaluate_turn_comprehensive'):
                        # 如果是 MultiModelVotingJudge，则不使用规则验证（已用投票代替）
                        judge_class_name = self.model_evaluator.judge_model.__class__.__name__
                        if judge_class_name == 'MultiModelVotingJudge':
                            use_rule_verification = False
                            logger.info(f"检测到投票模式（MultiModelVotingJudge），禁用规则验证")
                    
                    comprehensive_result = self.model_evaluator.judge_model.evaluate_turn_comprehensive(
                        turn_id=turn_idx,
                        user_message=turn.user_message,
                        agent_chat=agent_chat,
                        dialogue_history=dialogue_history,
                        scenario_id=self.scenario_id,
                        context_data=context_data,
                        use_rule_verification=use_rule_verification,
                    )
                    
                    gt_classification = comprehensive_result.get("classification", {})
                    chat_quality_score = comprehensive_result.get("chat_quality_score", 0.5)
                    chat_quality_dimensions = comprehensive_result.get("chat_quality_dimensions", {})
                    logger.info(f"Turn {turn_idx} 裁判综合评估: 分类={gt_classification}, 话术={chat_quality_score:.3f}, 维度={chat_quality_dimensions}")
                    
                    # 【投票模式】把 Judge 的完整结果保存到 turn.judge_evaluation 中
                    # 这样可以在结果文件中看到每个 Judge 的具体输出
                    if judge_class_name == 'MultiModelVotingJudge':
                        # 从 comprehensive_result 中提取投票细节和三个 Judge 的原始结果
                        turn.judge_evaluation = {
                            "mode": "voting",
                            "voting_details": comprehensive_result.get("voting_details", {}),
                            "individual_results": comprehensive_result.get("individual_results", {}),
                            "num_models": comprehensive_result.get("num_models", 0),
                            "final_classification": gt_classification,
                            "final_chat_quality_score": chat_quality_score,
                            "final_chat_quality_dimensions": chat_quality_dimensions,
                        }
                        logger.info(f"Turn {turn_idx} Judge 评测结果已保存到 judge_evaluation")
                    
                    # 【诊断日志】检查classification是否为空
                    if not gt_classification:
                        logger.info(f"Turn {turn_idx}:")
                        logger.warning(f"  - gt_classification: {gt_data.get('classification')}")
                        logger.info(f"  - agent_classification: {agent_output.classification_output if hasattr(agent_output, 'classification_output') else None}")
                        logger.info(f"  - gt_now_path: {gt_data.get('now_path')}")
                        logger.info(f"  - agent_path: {agent_path}")
                        logger.info(f"  - gt_finals: {gt_data.get('finals')}")
                        logger.info(f"  - agent_finals: {agent_finals}")
                        logger.warning(f"⚠️ Turn {turn_idx} 警告: classification为空或为False! comprehensive_result={comprehensive_result}")
                    else:
                        logger.debug(f"Turn {turn_idx} classification字段详情: {list(gt_classification.keys()) if isinstance(gt_classification, dict) else type(gt_classification)}")
                except Exception as e:
                    logger.error(f"Turn {turn_idx} 裁判综合评估失败: {e}")
            
            # 2.2 使用规则引擎计算正确的 now_path 和 finals
            correct_now_path = []
            correct_finals = {}
            reasoning = ""
            if rule_engine and gt_classification:
                try:
                    # 获取额外上下文（如 isRiskUser）
                    context = {}
                    if hasattr(simulation_result, 'context_data'):
                        context = simulation_result.context_data or {}
                    
                    rule_result = rule_engine.compute_correct_path_and_finals(
                        classification_output=gt_classification,
                        context=context
                    )
                    # logger.warning(f"规则引擎计算={rule_result}")
                    correct_now_path = rule_result.now_path
                    correct_finals = rule_result.finals
                    reasoning = rule_result.reasoning
                    # logger.info(f"Turn {turn_idx} 规则引擎计算: path={correct_now_path}, finals={correct_finals}")
                    
                    # 【诊断日志】检查finals是否为空
                    if not correct_finals:
                        logger.warning(f"⚠️ Turn {turn_idx} 警告: finals为空或为False! rule_result.finals={correct_finals}, gt_classification={gt_classification}")
                    else:
                        logger.debug(f"Turn {turn_idx} finals字段详情: {correct_finals}")
                except Exception as e:
                    logger.error(f"Turn {turn_idx} 规则引擎计算失败: {e}")
            
            ground_truth_data[turn_idx] = {
                "classification": gt_classification,
                "now_path": correct_now_path,
                "finals": correct_finals,
                "chat_quality_score": chat_quality_score,  # 新增：话术评分
                "chat_quality_dimensions": chat_quality_dimensions,  # 新增：话术五维度评分
                "reasoning": reasoning
            }
        
        # 3. 对比客服模型输出,计算各项得分
        # 注意:只对JSON解析成功的轮次进行评分
        classification_scores = []
        classification_scores_by_turn = {}
        path_scores = []
        path_scores_by_turn = {}
        finals_scores = []
        finals_scores_by_turn = {}
        chat_scores = []
        chat_scores_by_turn = {}
        json_parse_success_count = 0
        json_parse_failure_count = 0
        
        # logger.warning(f"【诊断】开始第3部分评分计算，ground_truth_data keys={list(ground_truth_data.keys())}")
        
        for turn_idx in eval_turns:
            if turn_idx >= len(simulation_result.turns):
                continue
            
            turn = simulation_result.turns[turn_idx]
            agent_output = turn.agent_output
            gt_data = ground_truth_data.get(turn_idx, {})
            
            # 【诊断】记录每一轮的JSON解析状态
            json_parse_failed = getattr(agent_output, 'json_parse_failed', False)
            logger.debug(f"🔍 Turn {turn_idx} JSON解析状态: json_parse_failed={json_parse_failed}")
            
            # 检查JSON解析状态
            if json_parse_failed:
                json_parse_failure_count += 1
                logger.warning(f"❌ Turn {turn_idx} JSON解析失败,跳过评分 (failure_count={json_parse_failure_count})")
                continue
            else:
                json_parse_success_count += 1
                logger.debug(f"✅ Turn {turn_idx} JSON解析成功,继续评分 (success_count={json_parse_success_count})")
            
            # 3.1 分类准确性 (30%)
            if hasattr(agent_output, 'classification_output') and gt_data.get("classification"):
                c_score, c_details = self.code_evaluator.compute_classification_accuracy(
                    agent_classification=agent_output.classification_output.to_dict() 
                        if hasattr(agent_output.classification_output, 'to_dict')
                        else agent_output.classification_output,
                    ground_truth_classification=gt_data["classification"]
                )
                classification_scores.append(c_score)
                classification_scores_by_turn[turn_idx] = {"score": c_score, "details": c_details}
            else:
                logger.warning(f"Turn {turn_idx} 缺少分类输出或ground truth")
            
            # 3.2 路径正确性 (30%)
            # 客服模型输出可能使用 expected_path 或 now_path 字段
            agent_path = None
            if hasattr(agent_output, 'expected_path'):
                agent_path = agent_output.expected_path if isinstance(agent_output.expected_path, list) else []
            elif hasattr(agent_output, 'now_path'):
                agent_path = agent_output.now_path if isinstance(agent_output.now_path, list) else []
            
            if agent_path is not None and gt_data.get("now_path"):
                p_score, p_details = self.code_evaluator.compute_path_correctness(
                    path_taken=agent_path,
                    expected_paths=[gt_data["now_path"]],
                    sop_graph=self.sop_graph
                )
                path_scores.append(p_score)
                path_scores_by_turn[turn_idx] = {"score": p_score, "details": p_details}
                
                # 添加详细调试日志
                if p_score == 0.0:
                    logger.warning(f"Turn {turn_idx} 路径得分为0! agent_path={agent_path}, gt_path={gt_data['now_path']}, details={p_details}")
            else:
                logger.warning(f"Turn {turn_idx} 缺少路径输出或ground truth (agent_path={agent_path is not None}, gt_path={gt_data.get('now_path') is not None})")
            
            # 3.3 finals 正确性 (20%)
            # 客服模型输出可能使用 final_output 或 finals 字段
            agent_finals = None
            if hasattr(agent_output, 'final_output') and agent_output.final_output:
                agent_finals = agent_output.final_output.to_dict() if hasattr(agent_output.final_output, 'to_dict') else agent_output.final_output
            elif hasattr(agent_output, 'finals'):
                agent_finals = agent_output.finals.to_dict() if hasattr(agent_output.finals, 'to_dict') else agent_output.finals
            
            if agent_finals is not None and gt_data.get("finals"):
                f_score, f_details = self.code_evaluator.compute_finals_correctness(
                    agent_finals=agent_finals,
                    correct_finals=gt_data["finals"]
                )
                finals_scores.append(f_score)
                finals_scores_by_turn[turn_idx] = {"score": f_score, "details": f_details}
            else:
                logger.warning(f"Turn {turn_idx} 缺少finals输出或ground truth (agent_finals={agent_finals is not None}, gt_finals={gt_data.get('finals') is not None})")
            
            # 3.4 话术质量 (20%)
            # 直接使用裁判模型在综合评估中给出的评分
            if gt_data.get("chat_quality_score") is not None:
                chat_score = gt_data["chat_quality_score"]
                chat_dimensions = gt_data.get("chat_quality_dimensions", {})
                chat_details = {
                    "source": "judge_comprehensive_evaluation",
                    "dimensions": chat_dimensions
                }
                chat_scores.append(chat_score)
                chat_scores_by_turn[turn_idx] = {"score": chat_score, "details": chat_details}
            elif hasattr(agent_output, 'chat'):
                # 降级：如果没有综合评估的评分,单独调用评估
                chat_score, chat_details = self.model_evaluator.evaluate_chat_quality(
                    chat_text=agent_output.chat,
                    user_message=turn.user_message,
                    dialogue_context=self._build_dialogue_context(simulation_result, turn_idx),
                    evaluation_criteria=evaluation_criteria,
                )
                chat_scores.append(chat_score)
                chat_scores_by_turn[turn_idx] = {"score": chat_score, "details": chat_details}
            else:
                logger.warning(f"Turn {turn_idx} 缺少chat输出")
        
        # 4. 计算平均分并添加到报告
        # 注意:四个指标的平均分仅基于JSON解析成功的案例
        avg_classification = sum(classification_scores) / len(classification_scores) if classification_scores else 0.0
        avg_path = sum(path_scores) / len(path_scores) if path_scores else 0.0
        avg_finals = sum(finals_scores) / len(finals_scores) if finals_scores else 0.0
        avg_chat = sum(chat_scores) / len(chat_scores) if chat_scores else 0.0
        
        # 计算话术质量五维度平均分
        dimension_names = ["linguistic_quality", "anthropomorphism_emotion", "content_utility", "user_satisfaction", "instruction_compliance"]
        avg_dimensions = {}
        for dim_name in dimension_names:
            dim_values = []
            for turn_idx in eval_turns:
                if turn_idx in chat_scores_by_turn:
                    dimensions = chat_scores_by_turn[turn_idx]["details"].get("dimensions", {})
                    if dim_name in dimensions:
                        dim_values.append(dimensions[dim_name])
            avg_dimensions[dim_name] = sum(dim_values) / len(dim_values) if dim_values else 0.0
        
        # 计算JSON解析错误率
        total_evaluated_turns = json_parse_success_count + json_parse_failure_count
        json_parse_error_rate = json_parse_failure_count / total_evaluated_turns if total_evaluated_turns > 0 else 0.0
        
        logger.info(f"JSON解析统计: 成功={json_parse_success_count}, 失败={json_parse_failure_count}, 错误率={json_parse_error_rate:.2%}")
        logger.info(f"话术质量五维度平均分: {avg_dimensions}")
        
        report.metric_scores = [
            MetricScore(
                metric_name="json_parse_error_rate",
                metric_type=MetricType.CODE_COMPUTED,
                score=json_parse_error_rate,
                weight=0.0,  # 仅作为参考指标,不参与综合评分
                explanation="JSON解析错误率(仅统计,不参与评分)",
                details={
                    "success_count": json_parse_success_count,
                    "failure_count": json_parse_failure_count,
                    "total_count": total_evaluated_turns,
                    "error_rate": json_parse_error_rate,
                    "evaluated_turns": eval_turns,
                }
            ),
            MetricScore(
                metric_name="classification_accuracy",
                metric_type=MetricType.CODE_COMPUTED,
                score=avg_classification,
                weight=0.4,
                explanation="分类字段准确性 (classification_output)",
                details={
                    "individual_scores": classification_scores,
                    "scores_by_turn": classification_scores_by_turn,
                    "average_score": avg_classification,
                    "evaluated_turns": eval_turns,
                }
            ),
            MetricScore(
                metric_name="path_correctness",
                metric_type=MetricType.CODE_COMPUTED,
                score=avg_path,
                weight=0.4,
                explanation="SOP路径正确性 (now_path)",
                details={
                    "individual_scores": path_scores,
                    "scores_by_turn": path_scores_by_turn,
                    "average_score": avg_path,
                    "evaluated_turns": eval_turns,
                }
            ),
            MetricScore(
                metric_name="finals_correctness",
                metric_type=MetricType.CODE_COMPUTED,
                score=avg_finals,
                weight=0.2,
                explanation="最终动作正确性 (finals)",
                details={
                    "individual_scores": finals_scores,
                    "scores_by_turn": finals_scores_by_turn,
                    "average_score": avg_finals,
                    "evaluated_turns": eval_turns,
                }
            ),
            MetricScore(
                metric_name="chat_quality",
                metric_type=MetricType.MODEL_JUDGED,
                score=avg_chat,
                weight=0.2,
                explanation="话术质量 (chat)",
                details={
                    "individual_scores": chat_scores,
                    "scores_by_turn": chat_scores_by_turn,
                    "average_score": avg_chat,
                    "average_dimensions": avg_dimensions,  # 五维度平均分
                    "evaluated_turns": eval_turns,
                }
            )
        ]
        
        # 5. 计算综合得分 - 逻辑能力(80%) + 话术能力(20%)
        logic_ability = (avg_classification * 0.4 + avg_path * 0.4 + avg_finals * 0.2) / 1.0
        chat_ability = avg_chat
        report.overall_score = logic_ability * 0.8 + chat_ability * 0.2
        
        # 添加细分能力得分到 details
        report.details = {
            "logic_ability": {
                "score": logic_ability,
                "weight": 0.8,
                "breakdown": {
                    "classification": {"score": avg_classification, "weight": 0.4},
                    "path": {"score": avg_path, "weight": 0.4},
                    "finals": {"score": avg_finals, "weight": 0.2}
                }
            },
            "chat_ability": {
                "score": chat_ability,
                "weight": 0.2
            },
            "ground_truth_data": ground_truth_data,
            "evaluated_turns": eval_turns
        }
        
        logger.info(f"评测完成 - 逻辑能力: {logic_ability:.3f}, 话术能力: {chat_ability:.3f}, 总分: {report.overall_score:.3f}")
        
        # 7. 存储轮次级评测结果（只在指定轮次评测）
        turn_evaluations = []
        for turn_idx in eval_turns:
            if turn_idx >= len(simulation_result.turns):
                continue
            
            turn = simulation_result.turns[turn_idx]
            # 使用裁判模型生成的ground truth（如果有的话）
            gt_classification = ground_truth_data.get(turn_idx, {}).get("classification", {})
            turn_eval = self.evaluate_turn(
                turn, 
                simulation_result, 
                evaluation_criteria,
                ground_truth_classification=gt_classification
            )
            turn_evaluations.append(turn_eval)
        
        report.metric_scores.append(MetricScore(
            metric_name="turn_level_evaluations",
            metric_type=MetricType.MODEL_JUDGED,
            score=0.0,  # 这是元数据，不参与打分
            weight=0.0,  # 这是元数据，不参与打分
            explanation="轮次级详细评测",
            details={
                "turn_evaluations": turn_evaluations,
                "total_turns": len(turn_evaluations),
                "evaluated_turns": eval_turns,
                "ground_truth_data": ground_truth_data,
            }
        ))
        
        return report
    
    def evaluate_turn(
        self,
        turn,
        simulation_result,
        evaluation_criteria: Optional[Dict[str, str]] = None,
        ground_truth_classification: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        评估单轮对话
        
        Args:
            turn: 单轮对话
            simulation_result: 整体模拟结果
            evaluation_criteria: 评价标准
            ground_truth_classification: 裁判模型生成的正确分类标签 (可选)
            
        Returns:
            Dict: 轮次评测结果
        """
        turn_result = {
            "turn_id": turn.turn_id,
            "user_message": turn.user_message,
            "agent_output": turn.agent_output.to_dict() if hasattr(turn.agent_output, 'to_dict') else turn.agent_output,
        }
        
        # 评估该轮的分类结果
        if hasattr(turn.agent_output, 'classification_output') and turn.agent_output.classification_output:
            try:
                # 如果有裁判模型提供的ground truth，使用它；否则评分为0或跳过
                gt_classification = ground_truth_classification if ground_truth_classification else {}
                
                classification_score, classification_details = self.code_evaluator.compute_classification_accuracy(
                    agent_classification=turn.agent_output.classification_output.to_dict()
                        if hasattr(turn.agent_output.classification_output, 'to_dict')
                        else turn.agent_output.classification_output,
                    ground_truth_classification=gt_classification,
                )
                turn_result["classification_score"] = classification_score
                turn_result["classification_details"] = classification_details
                
                # 如果没有ground truth，标记警告
                if not gt_classification:
                    turn_result["classification_warning"] = "No ground truth provided"
            except Exception as e:
                turn_result["classification_score"] = 0.0
                turn_result["classification_error"] = str(e)
        
        # 评估该轮的话术质量
        # 优先使用 turn.judge_evaluation 中已有的分数（投票模式）
        if hasattr(turn, 'judge_evaluation') and turn.judge_evaluation:
            # 投票模式：从 judge_evaluation 中提取已有的分数
            judge_eval = turn.judge_evaluation
            chat_score = judge_eval.get("final_chat_quality_score", 0.0)
            chat_details = {
                "source": "judge_evaluation",
                "mode": judge_eval.get("mode", "unknown"),
                "dimensions": judge_eval.get("final_chat_quality_dimensions", {})
            }
            turn_result["chat_quality_score"] = chat_score
            turn_result["chat_quality_details"] = chat_details
        elif hasattr(turn.agent_output, 'chat') and turn.agent_output.chat:
            # 非投票模式：调用 evaluate_chat_quality
            try:
                chat_score, chat_details = self.model_evaluator.evaluate_chat_quality(
                    chat_text=turn.agent_output.chat,
                    user_message=turn.user_message,
                    dialogue_context=self._build_dialogue_context(simulation_result, turn.turn_id),
                    evaluation_criteria=evaluation_criteria,
                )
                turn_result["chat_quality_score"] = chat_score
                turn_result["chat_quality_details"] = chat_details
            except Exception as e:
                turn_result["chat_quality_score"] = 0.0
                turn_result["chat_quality_error"] = str(e)
        
        return turn_result
    
    def _build_dialogue_context(self, simulation_result, turn_id: int) -> str:
        """构建对话上下文"""
        context_turns = []
        for turn in simulation_result.turns[:turn_id + 1]:
            context_turns.append(f"用户: {turn.user_message}")
            if turn.agent_output:
                context_turns.append(f"客服: {turn.agent_output.chat}")
        
        return "\n".join(context_turns)
    
    def _build_dialogue_history_list(self, simulation_result, turn_id: int) -> list:
        """构建对话历史列表（供LLMJudge使用）"""
        dialogue_history = []
        for turn in simulation_result.turns[:turn_id + 1]:
            dialogue_history.append({"role": "user", "content": turn.user_message})
            if turn.agent_output:
                dialogue_history.append({"role": "assistant", "content": turn.agent_output.chat})
        
        return dialogue_history
    

    def _check_classification_condition(
        self,
        classification_output,
        field_name: Optional[str],
        label: str
    ) -> bool:
        """
        检查分类条件是否满足
        
        Args:
            classification_output: 分类结果（可以是ClassificationOutput对象或字典）
            field_name: 字段名
            label: 边的标签
            
        Returns:
            条件是否满足
        """
        if not field_name:
            return True
        
        # 获取字段值
        if isinstance(classification_output, dict):
            field_value = classification_output.get(field_name)
        else:
            field_value = getattr(classification_output, field_name, None)
        
        # 比较值和标签
        if isinstance(field_value, bool):
            return str(field_value).lower() == label.lower()
        else:
            return str(field_value) == label
