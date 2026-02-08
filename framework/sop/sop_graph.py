#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SOP图结构系统
SOP Graph Structure System

将标准操作流程 (SOP) 转化为有向图，用于：
1. 动态多轮对话生成
2. 测试用例覆盖
3. 对话轨迹正确性评测

有向图节点 = SOP步骤
有向图边 = 条件转移
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple, Callable
from enum import Enum
import json


class NodeType(Enum):
    """节点类型"""
    START = "start"                # 起始节点
    DECISION = "decision"          # 决策节点 (条件分支)
    ACTION = "action"              # 动作节点
    END = "end"                    # 终止节点


@dataclass
class SOPNode:
    """SOP图节点"""
    node_id: str                   # 节点ID
    node_type: NodeType            # 节点类型
    step_name: str                 # SOP步骤名
    description: str               # 节点描述
    action_name: Optional[str] = None  # 关联的动作名称 (仅限ACTION节点)
    parameters: Dict = field(default_factory=dict)  # 节点参数


@dataclass
class TransitionCondition:
    """转移条件"""
    condition_name: str            # 条件名称
    condition_func: Optional[Callable] = None  # 条件函数 (可选，用于后续动态评估)
    description: str = ""          # 条件描述


@dataclass
class SOPEdge:
    """SOP图边 - 表示条件转移"""
    source_node_id: str            # 源节点ID
    target_node_id: str            # 目标节点ID
    transition_condition: TransitionCondition  # 转移条件
    transition_label: str = ""     # 转移标签 (如 "true", "false", "yes", "no")


class SOPGraph:
    """
    SOP有向图
    
    用于表示完整的业务流程，包括：
    - 线性流程 (step1 -> step2 -> ...)
    - 条件分支 (step2根据条件跳转到step3或step5)
    - 多条合并 (多条路径汇聚到同一步骤)
    - 循环 (某些步骤可能返回到前面的步骤)
    """
    
    def __init__(self, scenario_id: str):
        self.scenario_id = scenario_id
        self.nodes: Dict[str, SOPNode] = {}
        self.edges: List[SOPEdge] = []
        self.start_node_id: Optional[str] = None
        self.end_node_ids: Set[str] = set()
    
    def add_node(self, node: SOPNode) -> None:
        """添加节点"""
        self.nodes[node.node_id] = node
        
        if node.node_type == NodeType.START:
            self.start_node_id = node.node_id
        elif node.node_type == NodeType.END:
            self.end_node_ids.add(node.node_id)
    
    def add_edge(self, edge: SOPEdge) -> None:
        """添加边"""
        if edge.source_node_id not in self.nodes:
            raise ValueError(f"Source node not found: {edge.source_node_id}")
        if edge.target_node_id not in self.nodes:
            raise ValueError(f"Target node not found: {edge.target_node_id}")
        
        self.edges.append(edge)
    
    def get_next_nodes(self, current_node_id: str) -> List[Tuple[str, str]]:
        """
        获取当前节点的所有后继节点
        
        Returns:
            List[Tuple[str, str]]: [(target_node_id, transition_label), ...]
        """
        next_nodes = []
        for edge in self.edges:
            if edge.source_node_id == current_node_id:
                next_nodes.append((edge.target_node_id, edge.transition_label))
        return next_nodes
    
    def get_predecessors(self, node_id: str) -> List[str]:
        """获取指定节点的所有前驱节点"""
        predecessors = []
        for edge in self.edges:
            if edge.target_node_id == node_id:
                predecessors.append(edge.source_node_id)
        return predecessors
    
    def get_all_paths(self, include_endpoints: bool = False) -> List[List[str]]:
        """
        获取从START到END的所有可能路径
        
        Args:
            include_endpoints: 是否包含start和end节点 (默认False，不包含)
            
        Returns:
            List[List[str]]: 路径列表，每条路径是节点ID序列
        """
        if not self.start_node_id:
            raise ValueError("No start node found in the graph")
        
        all_paths = []
        
        def dfs(current_node_id: str, path: List[str], visited: Set[str]) -> None:
            """深度优先搜索查找所有路径"""
            path.append(current_node_id)
            visited.add(current_node_id)
            
            # 如果到达终止节点，保存路径
            if current_node_id in self.end_node_ids:
                all_paths.append(path.copy())
                path.pop()
                visited.remove(current_node_id)
                return
            
            # 探索所有后继节点
            has_next = False
            for next_node_id, _ in self.get_next_nodes(current_node_id):
                if next_node_id not in visited:  # 防止无限循环
                    has_next = True
                    dfs(next_node_id, path, visited)
            
            # 如果没有后继节点，也认为是一条有效路径
            if not has_next:
                all_paths.append(path.copy())
            
            path.pop()
            visited.remove(current_node_id)
        
        dfs(self.start_node_id, [], set())
        
        # 如果不包含端点，则去掉start和end
        if not include_endpoints:
            normalized_paths = []
            for path in all_paths:
                # 去掉start和end
                inner_path = [node for node in path if node not in ['start', 'end']]
                normalized_paths.append(inner_path)
            return normalized_paths
        
        return all_paths
    
    def validate_path(self, path: List[str]) -> Tuple[bool, str]:
        """
        验证路径是否在图中有效
        
        Args:
            path: 节点ID序列
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息或"valid")
        """
        if not path:
            return False, "Path is empty"
        
        if path[0] != self.start_node_id:
            return False, f"Path must start with {self.start_node_id}"
        
        for i in range(len(path) - 1):
            current_node = path[i]
            next_node = path[i + 1]
            
            # 检查是否存在边
            edge_exists = any(
                edge.source_node_id == current_node and edge.target_node_id == next_node
                for edge in self.edges
            )
            
            if not edge_exists:
                return False, f"No edge from {current_node} to {next_node}"
        
        if path[-1] not in self.end_node_ids:
            return False, f"Path must end with one of {self.end_node_ids}"
        
        return True, "valid"
    
    def to_dict(self) -> Dict:
        """转换为字典表示"""
        return {
            "scenario_id": self.scenario_id,
            "start_node_id": self.start_node_id,
            "end_node_ids": list(self.end_node_ids),
            "nodes": {
                node_id: {
                    "node_type": node.node_type.value,
                    "step_name": node.step_name,
                    "description": node.description,
                    "action_name": node.action_name,
                    "parameters": node.parameters
                }
                for node_id, node in self.nodes.items()
            },
            "edges": [
                {
                    "source": edge.source_node_id,
                    "target": edge.target_node_id,
                    "condition": edge.transition_condition.condition_name,
                    "description": edge.transition_condition.description,
                    "label": edge.transition_label
                }
                for edge in self.edges
            ]
        }
    
    def __repr__(self) -> str:
        return f"SOPGraph(scenario_id={self.scenario_id}, nodes={len(self.nodes)}, edges={len(self.edges)})"


# ==================== 在线教育SOP图构建 ====================

def build_online_education_sop_graph() -> SOPGraph:
    """
    构建在线教育平台客服SOP有向图
    
    流程：
    START -> step1_classification -> step2_description_check -> 
    [条件分支] -> step3_relevance_check -> step4_repeated_check -> 
    step5_emotion_check -> step6_resource_allocation -> step7_refund_branch ->
    [条件分支] -> step8_financial_review -> FINAL_ACTION -> END
    """
    graph = SOPGraph("online_education")
    
    # 1. 创建所有节点
    nodes = [
        SOPNode("start", NodeType.START, "START", "开始"),
        
        # 分类步骤
        SOPNode("step1", NodeType.ACTION, "step1_classification", 
                "字段分类 - 提取关键信息并分类"),
        
        # 问题确认 (决策节点)
        SOPNode("step2", NodeType.DECISION, "step2_description_check",
                "问题确认 - 检查问题描述清晰度",
                parameters={"decision_field": "DescriptionClear"}),
        
        # 清晰度不够 -> 引导
        SOPNode("action_guide", NodeType.ACTION, "action_guide",
                "引导用户", action_name="GUIDE"),
        
        # 课程关联性检查 (决策节点)
        SOPNode("step3", NodeType.DECISION, "step3_relevance_check",
                "课程关联性确认 - 检查问题与课程关联性",
                parameters={"decision_field": "QuestionRelevance"}),
        
        # 重复反馈检查 (决策节点)
        SOPNode("step4", NodeType.DECISION, "step4_repeated_check",
                "重复反馈检查 - 检查是否在7天内重复反馈",
                parameters={"decision_field": "RepeatedRaised"}),
        
        # 重复反馈 -> 审核
        SOPNode("action_review", NodeType.ACTION, "action_review",
                "审核处理", action_name="REVIEW"),
        
        # 情绪检查 (决策节点)
        SOPNode("step5", NodeType.DECISION, "step5_emotion_check",
                "情绪检查 - 检查学员情绪倾向",
                parameters={"decision_field": "EmotionTendency"}),
        
        # 不满情绪 -> 安抚
        SOPNode("action_comfort", NodeType.ACTION, "action_comfort",
                "安抚处理", action_name="COMFORT"),
        
        # 资源分配 (决策节点)
        SOPNode("step6", NodeType.ACTION, "step6_resource_allocation",
                "分配辅助资源 - 根据依赖度和关联性分配"),
        
        # 退费分支 (决策节点)
        SOPNode("step7", NodeType.DECISION, "step7_refund_branch",
                "退费需求分支 - 检查是否涉及退费",
                parameters={"decision_field": "RegardingRefund"}),
        
        # 财务审核 (决策节点)
        SOPNode("step8", NodeType.DECISION, "step8_financial_review",
                "财务审核 - 检查用户风险等级",
                parameters={"decision_field": "isRiskUser"}),
        
        # 退款
        SOPNode("action_refund", NodeType.ACTION, "action_refund",
                "退款处理", action_name="REFUND"),
        
        # 协商
        SOPNode("action_negotiate", NodeType.ACTION, "action_negotiate",
                "协商处理", action_name="NEGOTIATE"),
        
        # 分配资源计划
        SOPNode("action_plan", NodeType.ACTION, "action_plan",
                "分配资源计划", action_name="PLAN"),
        
        # 终止
        SOPNode("end", NodeType.END, "END", "流程结束"),
    ]
    
    for node in nodes:
        graph.add_node(node)
    
    # 2. 创建所有边
    edges = [
        # START -> step1
        SOPEdge("start", "step1",
                TransitionCondition("always", description="开始流程"),
                "start"),
        
        # step1 -> step2
        SOPEdge("step1", "step2",
                TransitionCondition("always", description="开始问题确认"),
                "confirm"),
        
        # step2 分支: 清晰 -> step3, 不清晰 -> GUIDE
        SOPEdge("step2", "step3",
                TransitionCondition("clear", description="问题明确"),
                "true"),
        SOPEdge("step2", "action_guide",
                TransitionCondition("unclear", description="问题模糊"),
                "false"),
        
        # GUIDE -> END
        SOPEdge("action_guide", "end",
                TransitionCondition("action_complete", description="引导完成"),
                "end"),
        
        # step3 分支: 相关 -> step4, 不相关 -> step6
        SOPEdge("step3", "step4",
                TransitionCondition("related", description="问题与课程相关"),
                "true"),
        SOPEdge("step3", "step6",
                TransitionCondition("not_related", description="问题与课程无关"),
                "false"),
        
        # step4 分支: 重复 -> REVIEW, 首次 -> step5
        SOPEdge("step4", "action_review",
                TransitionCondition("repeated", description="重复反馈"),
                "true"),
        SOPEdge("step4", "step5",
                TransitionCondition("first_time", description="首次反馈"),
                "false"),
        
        # REVIEW -> END
        SOPEdge("action_review", "end",
                TransitionCondition("action_complete", description="审核完成"),
                "end"),
        
        # step5 分支: 不满 -> COMFORT, 平稳 -> step6
        SOPEdge("step5", "action_comfort",
                TransitionCondition("dissatisfied", description="用户不满"),
                "Dissatisfied"),
        SOPEdge("step5", "step6",
                TransitionCondition("calm", description="用户平稳"),
                "Calm"),
        
        # COMFORT -> END
        SOPEdge("action_comfort", "end",
                TransitionCondition("action_complete", description="安抚完成"),
                "end"),
        
        # step6 -> step7
        SOPEdge("step6", "step7",
                TransitionCondition("resource_allocated", description="资源已分配"),
                "continue"),
        
        # step7 分支: 有退费需求 -> step8, 无 -> PLAN
        SOPEdge("step7", "step8",
                TransitionCondition("refund_required", description="需要退费"),
                "true"),
        SOPEdge("step7", "action_plan",
                TransitionCondition("no_refund", description="不需要退费"),
                "false"),
        
        # PLAN -> END
        SOPEdge("action_plan", "end",
                TransitionCondition("action_complete", description="计划完成"),
                "end"),
        
        # step8 分支: 风险用户 -> NEGOTIATE, 非风险 -> REFUND
        SOPEdge("step8", "action_negotiate",
                TransitionCondition("risk_user", description="风险用户"),
                "true"),
        SOPEdge("step8", "action_refund",
                TransitionCondition("normal_user", description="非风险用户"),
                "false"),
        
        # REFUND -> END
        SOPEdge("action_refund", "end",
                TransitionCondition("action_complete", description="退款完成"),
                "end"),
        
        # NEGOTIATE -> END
        SOPEdge("action_negotiate", "end",
                TransitionCondition("action_complete", description="协商完成"),
                "end"),
    ]
    
    for edge in edges:
        graph.add_edge(edge)
    
    return graph


def build_ecommerce_refund_sop_graph() -> SOPGraph:
    """
    构建电商退款场景SOP有向图
    
    流程：
    START -> step1_classification -> step2_core_intention ->
    step3_shipping_status -> 
    [条件分支] -> step4_credit_level / step5_responsibility ->
    [条件分支] -> step6_refund_reasonable / step7_emotion_status ->
    step8_provided_document -> FINAL_ACTION -> END
    
    系统变量：
    - ShippingStatus: "Unshipped"/"Shipping"/"Signed"
    - CreditLevel: "High"/"Medium"/"Low"
    """
    graph = SOPGraph("ecommerce_refund")
    
    # 1. 创建所有节点
    nodes = [
        SOPNode("start", NodeType.START, "START", "开始"),
        
        # 分类步骤
        SOPNode("step1", NodeType.ACTION, "step1_classification",
                "字段分类 - 提取核心需求、凭证、责任、理由和情绪"),
        
        # 核心诉求判断 (记录节点，真正的决策在step3根据CoreIntention+ShippingStatus组合判断)
        SOPNode("step2", NodeType.ACTION, "step2_core_intention",
                "核心诉求记录 - 记录用户是换货还是退款"),
        
        # 物流状态 (决策节点)
        SOPNode("step3", NodeType.DECISION, "step3_shipping_status",
                "物流状态判断 - 检查商品物流状态",
                parameters={"decision_field": "ShippingStatus"}),
        
        # 用户信用等级 (决策节点)
        SOPNode("step4", NodeType.DECISION, "step4_credit_level",
                "用户信用等级判断 - 检查用户信用等级",
                parameters={"decision_field": "CreditLevel"}),
        
        # 责任判定 (决策节点)
        SOPNode("step5", NodeType.DECISION, "step5_responsibility",
                "责任判定 - 判断售后问题责任归属",
                parameters={"decision_field": "Responsibility"}),
        
        # 退款理由合理性 (决策节点)
        SOPNode("step6", NodeType.DECISION, "step6_refund_reasonable",
                "退款理由合理性 - 检查用户退款理由是否合理",
                parameters={"decision_field": "RefundReasonable"}),
        
        # 用户情绪状态 (决策节点)
        SOPNode("step7", NodeType.DECISION, "step7_emotion_status",
                "用户情绪状态 - 检查用户情绪",
                parameters={"decision_field": "EmotionStatus"}),
        
        # 是否提供凭证 (决策节点)
        SOPNode("step8", NodeType.DECISION, "step8_provided_document",
                "凭证检查 - 检查用户是否提供售后凭证",
                parameters={"decision_field": "ProvidedDocument"}),
        
        # 换货动作
        SOPNode("action_exchange", NodeType.ACTION, "action_exchange",
                "处理换货", action_name="Exchange"),
        
        # 拦截物流
        SOPNode("action_interception", NodeType.ACTION, "action_interception",
                "拦截物流", action_name="Interception"),
        
        # 退款动作
        SOPNode("action_refund", NodeType.ACTION, "action_refund",
                "处理退款", action_name="Refund"),
        
        # 要求支付运费
        SOPNode("action_pay_fee", NodeType.ACTION, "action_pay_fee",
                "要求支付运费", action_name="PayFee"),
        
        # 安排上门取件
        SOPNode("action_collection_service", NodeType.ACTION, "action_collection_service",
                "安排上门取件", action_name="CollectionService"),
        
        # 安抚用户
        SOPNode("action_comfort", NodeType.ACTION, "action_comfort",
                "安抚用户情绪", action_name="Comfort"),
        
        # 拒绝请求
        SOPNode("action_reject", NodeType.ACTION, "action_reject",
                "拒绝请求", action_name="Reject"),
        
        # 安抚并赔偿
        SOPNode("action_comfort_compensation", NodeType.ACTION, "action_comfort_compensation",
                "安抚并赔偿用户", action_name="Comfort+Compensation"),
        
        # 补充凭证
        SOPNode("action_supplementary", NodeType.ACTION, "action_supplementary",
                "请求补充凭证", action_name="Supplementary"),
        
        # 终止
        SOPNode("end", NodeType.END, "END", "流程结束"),
    ]
    
    for node in nodes:
        graph.add_node(node)
    
    # 2. 创建所有边
    edges = [
        # START -> step1
        SOPEdge("start", "step1",
                TransitionCondition("always", description="开始流程"),
                "start"),
        
        # step1 -> step2
        SOPEdge("step1", "step2",
                TransitionCondition("always", description="进行核心诉求判断"),
                "continue"),
        
        # ========== step2分支：核心诉求 ==========
        # step2 -> step3 (无论是Exchange还是ReturnOrRefund都进入step3)
        SOPEdge("step2", "step3",
                TransitionCondition("always", description="进行物流状态判断"),
                "continue"),
        
        # ========== step3分支：物流状态 (Exchange分支) ==========
        # Exchange + Unshipped -> Exchange -> END
        SOPEdge("step3", "action_exchange",
                TransitionCondition("exchange_unshipped", 
                                    description="换货且未发货"),
                "exchange_unshipped"),
        
        # Exchange + Shipping -> Interception -> END
        SOPEdge("step3", "action_interception",
                TransitionCondition("exchange_shipping",
                                    description="换货且在途中"),
                "exchange_shipping"),
        
        # Exchange + Signed -> step4 (需要检查信用等级)
        SOPEdge("step3", "step4",
                TransitionCondition("exchange_signed",
                                    description="换货且已签收"),
                "exchange_signed"),
        
        # ========== step3分支：物流状态 (ReturnOrRefund分支) ==========
        # ReturnOrRefund + Unshipped -> Refund -> END
        SOPEdge("step3", "action_refund",
                TransitionCondition("refund_unshipped",
                                    description="退款且未发货"),
                "refund_unshipped"),
        
        # ReturnOrRefund + Shipping -> Interception -> END
        SOPEdge("step3", "action_interception",
                TransitionCondition("refund_shipping",
                                    description="退款且在途中"),
                "refund_shipping"),
        
        # ReturnOrRefund + Signed -> step5 (需要检查责任)
        SOPEdge("step3", "step5",
                TransitionCondition("refund_signed",
                                    description="退款且已签收"),
                "refund_signed"),
        
         # ========== step5分支：责任 (ReturnOrRefund + Signed) ==========
         # 无论User还是Merchant，都进入step4检查信用等级
         # ReturnOrRefund + User -> step4 (需要检查信用等级)
         SOPEdge("step5", "step4",
                 TransitionCondition("user_responsibility",
                                     description="用户责任"),
                 "user"),
         
         # ReturnOrRefund + Merchant -> step4 (需要检查信用等级)
         SOPEdge("step5", "step4",
                 TransitionCondition("merchant_responsibility",
                                     description="商户责任"),
                 "merchant"),
        
         # ========== step4分支：信用等级 ==========
         # ===== 分支A：来自step3 (Exchange + Signed) =====
         # Exchange + High/Medium -> Exchange -> END
         SOPEdge("step4", "action_exchange",
                 TransitionCondition("exchange_high_or_medium_credit",
                                     description="换货且高或中信用"),
                 "exchange_high_medium"),
         
         # Exchange + Low -> PayFee -> END
         SOPEdge("step4", "action_pay_fee",
                 TransitionCondition("exchange_low_credit",
                                     description="换货且低信用"),
                 "exchange_low"),
         
         # ===== 分支B：来自step5 (ReturnOrRefund + Merchant + Signed) =====
         # Merchant + High -> Comfort+Compensation -> END
         SOPEdge("step4", "action_comfort_compensation",
                 TransitionCondition("merchant_high_credit",
                                     description="商户责任且高信用"),
                 "merchant_high"),
         
          # Merchant + Medium/Low -> step7 (需要检查情绪)
          SOPEdge("step4", "step7",
                  TransitionCondition("merchant_medium_low_credit",
                                      description="商户责任且中低信用"),
                  "merchant_medium_low"),
          
          # ===== 分支C：来自step5 (ReturnOrRefund + User + Signed) =====
          # User + High/Medium -> CollectionService -> END
          SOPEdge("step4", "action_collection_service",
                  TransitionCondition("user_high_or_medium_credit",
                                      description="用户责任且高或中信用"),
                  "user_high_medium"),
          
          # User + Low -> step6 (需要检查理由合理性)
          SOPEdge("step4", "step6",
                  TransitionCondition("user_low_credit",
                                      description="用户责任且低信用"),
                  "user_low"),
        
        # ========== step6分支：退款理由合理性 (User + Signed) ==========
        # Reasonable -> step8 (需要检查凭证)
        SOPEdge("step6", "step8",
                TransitionCondition("reasonable",
                                    description="退款理由合理"),
                "reasonable"),
        
        # Unreasonable -> Reject -> END
        SOPEdge("step6", "action_reject",
                TransitionCondition("unreasonable",
                                    description="退款理由不合理"),
                "unreasonable"),
        
        # ========== step7分支：情绪状态 (Merchant + Medium/Low) ==========
        # Calm -> CollectionService -> END
        SOPEdge("step7", "action_collection_service",
                TransitionCondition("calm",
                                    description="用户情绪平静"),
                "calm"),
        
        # Dissatisfied -> Comfort -> END
        SOPEdge("step7", "action_comfort",
                TransitionCondition("dissatisfied",
                                    description="用户情绪不满"),
                "dissatisfied"),
        
        # ========== step8分支：凭证 (User + Reasonable) ==========
        # True -> CollectionService -> END
        SOPEdge("step8", "action_collection_service",
                TransitionCondition("document_provided",
                                    description="提供了凭证"),
                "provided"),
        
        # False -> Supplementary -> END
        SOPEdge("step8", "action_supplementary",
                TransitionCondition("document_not_provided",
                                    description="未提供凭证"),
                "not_provided"),
        
        # ========== 所有动作 -> END ==========
        SOPEdge("action_exchange", "end",
                TransitionCondition("action_complete", description="换货完成"),
                "end"),
        
        SOPEdge("action_interception", "end",
                TransitionCondition("action_complete", description="拦截完成"),
                "end"),
        
        SOPEdge("action_refund", "end",
                TransitionCondition("action_complete", description="退款完成"),
                "end"),
        
        SOPEdge("action_pay_fee", "end",
                TransitionCondition("action_complete", description="运费处理完成"),
                "end"),
        
        SOPEdge("action_collection_service", "end",
                TransitionCondition("action_complete", description="取件服务完成"),
                "end"),
        
        SOPEdge("action_comfort", "end",
                TransitionCondition("action_complete", description="安抚完成"),
                "end"),
        
        SOPEdge("action_reject", "end",
                TransitionCondition("action_complete", description="拒绝完成"),
                "end"),
        
        SOPEdge("action_comfort_compensation", "end",
                TransitionCondition("action_complete", description="赔偿完成"),
                "end"),
        
        SOPEdge("action_supplementary", "end",
                TransitionCondition("action_complete", description="补充凭证完成"),
                "end"),
    ]
    
    for edge in edges:
        graph.add_edge(edge)
    
    return graph


def build_telecom_package_sop_graph() -> SOPGraph:
    """
    构建电信套餐办理场景SOP有向图
    
    流程：
    START -> step1_classification -> step2_consumption_type ->
    [step3/step4/step5] ->
    [step6] -> [step7] -> FINAL_ACTION -> END
    
    系统变量：
    - PackageStatus: "Contracted"/"NoContract"
    - Penalty: int (违约金金额)
    """
    graph = SOPGraph("telecom_package")
    
    # 1. 创建所有节点
    nodes = [
        SOPNode("start", NodeType.START, "START", "开始"),
        
        # 分类步骤
        SOPNode("step1", NodeType.ACTION, "step1_classification",
                "字段分类 - 提取ConsumptionType、ApplicationTendency、ConsumptionProfile、EmotionTag"),
        
        # 消费意图判断 (决策节点)
        SOPNode("step2", NodeType.DECISION, "step2_consumption_type",
                "用户消费意图判断 - Enquiry/Change/Cancel",
                parameters={"decision_field": "ConsumptionType"}),
        
        # 消费画像判断 (记录节点，仅限Enquiry，记录用户画像但不分支)
        SOPNode("step3", NodeType.ACTION, "step3_consumption_profile",
                "用户消费画像记录 - Data/Voice"),
        
        # 套餐状态判断 (决策节点，仅限Change)
        SOPNode("step4", NodeType.DECISION, "step4_package_status",
                "用户套餐状态判断 - Contracted/NoContract",
                parameters={"decision_field": "PackageStatus"}),
        
        # 合约违约金情况 (决策节点，仅限Cancel或Change+Contracted)
        SOPNode("step5", NodeType.DECISION, "step5_penalty_check",
                "合约违约金情况判断 - Penalty=0/Penalty>0",
                parameters={"decision_field": "Penalty"}),
        
        # 用户办理倾向判断 (决策节点，仅限Enquiry)
        SOPNode("step6", NodeType.DECISION, "step6_application_tendency",
                "用户办理倾向判断 - Agree/Reject/Hesitate",
                parameters={"decision_field": "ApplicationTendency"}),
        
        # 用户情绪判断 (决策节点，可能在多个分支中)
        SOPNode("step7", NodeType.DECISION, "step7_emotion_tag",
                "用户情绪判断 - Calm/Discontent",
                parameters={"decision_field": "EmotionTag"}),
        
        # 变更套餐动作
        SOPNode("action_changeorder", NodeType.ACTION, "action_changeorder",
                "处理变更套餐", action_name="ChangeOrder"),
        
        # 委婉结束对话
        SOPNode("action_goodbye", NodeType.ACTION, "action_goodbye",
                "委婉结束对话", action_name="GoodBye"),
        
        # 转人工处理
        SOPNode("action_transhuman", NodeType.ACTION, "action_transhuman",
                "转人工处理", action_name="TransHuman"),
        
        # 终止
        SOPNode("end", NodeType.END, "END", "流程结束"),
    ]
    
    for node in nodes:
        graph.add_node(node)
    
    # 2. 创建所有边
    edges = [
        # START -> step1
        SOPEdge("start", "step1",
                TransitionCondition("always", description="开始流程"),
                "start"),
        
        # step1 -> step2
        SOPEdge("step1", "step2",
                TransitionCondition("always", description="进行消费意图判断"),
                "continue"),
        
        # ========== step2分支：ConsumptionType ==========
        # Enquiry -> step3
        SOPEdge("step2", "step3",
                TransitionCondition("enquiry", description="用户咨询"),
                "enquiry"),
        
        # Change -> step4
        SOPEdge("step2", "step4",
                TransitionCondition("change", description="用户更换套餐"),
                "change"),
        
        # Cancel -> step5
        SOPEdge("step2", "step5",
                TransitionCondition("cancel", description="用户取消套餐"),
                "cancel"),
        
        # ========== step3分支：ConsumptionProfile (Enquiry) ==========
        # 任意 -> step6
        SOPEdge("step3", "step6",
                TransitionCondition("always", description="进行办理倾向判断"),
                "continue"),
        
        # ========== step4分支：PackageStatus (Change) ==========
        # NoContract -> ChangeOrder -> END
        SOPEdge("step4", "action_changeorder",
                TransitionCondition("nocontract", description="无合约直接变更"),
                "nocontract"),
        
        # Contracted -> step5
        SOPEdge("step4", "step5",
                TransitionCondition("contracted", description="检查违约金"),
                "contracted"),
        
        # ========== step5分支：Penalty (Change+Contracted 或 Cancel) ==========
        # Penalty=0 -> ChangeOrder -> END
        SOPEdge("step5", "action_changeorder",
                TransitionCondition("no_penalty", description="无违约金直接变更"),
                "no_penalty"),
        
        # Penalty>0 -> step7
        SOPEdge("step5", "step7",
                TransitionCondition("has_penalty", description="有违约金检查情绪"),
                "has_penalty"),
        
        # ========== step6分支：ApplicationTendency (Enquiry) ==========
        # Agree -> step4
        SOPEdge("step6", "step4",
                TransitionCondition("agree", description="用户同意办理"),
                "agree"),
        
        # Reject / Hesitate -> GoodBye -> END
        SOPEdge("step6", "action_goodbye",
                TransitionCondition("reject_or_hesitate", description="拒绝或犹豫"),
                "reject_hesitate"),
        
        # ========== step7分支：EmotionTag ==========
        # Calm -> ChangeOrder -> END
        SOPEdge("step7", "action_changeorder",
                TransitionCondition("calm", description="情绪平静直接变更"),
                "calm"),
        
        # Discontent -> TransHuman -> END
        SOPEdge("step7", "action_transhuman",
                TransitionCondition("discontent", description="情绪不满转人工"),
                "discontent"),
        
        # ========== 所有动作 -> END ==========
        SOPEdge("action_changeorder", "end",
                TransitionCondition("action_complete", description="变更完成"),
                "end"),
        
        SOPEdge("action_goodbye", "end",
                TransitionCondition("action_complete", description="结束对话"),
                "end"),
        
        SOPEdge("action_transhuman", "end",
                TransitionCondition("action_complete", description="转接完成"),
                "end"),
    ]
    
    for edge in edges:
        graph.add_edge(edge)
    
    return graph


def build_property_service_sop_graph() -> SOPGraph:
    """
    构建物业服务场景SOP有向图
    
    流程说明：
    1. step1: 字段分类 (CoreIntention, EmotionTag, RepairItemCategory, RelatedScope, EmergencyLevel)
    2. step2: 核心意图判断 (Payment/Complaint/Repair)
    3. step3: 房屋状态判断 (仅限Payment/Complaint) -> Occupied/Rented/UnOccupied
    4. step4: 事项范围判断 (仅限Repair) -> Personal/Public
    5. step5: 报修范围确认 (Repair分支)
    6. step6: 缴费状态判断 (Payment/Complaint + Occupied/Rented) 或 (Repair + Personal)
    7. step7: 情绪判断 (Complaint分支)
    8. step8: 紧急程度判断 (Repair时所有路径都需要：Personal+Settled 和 Public)
    
    系统变量：
    - HouseStatus: "Occupied"/"Rented"/"UnOccupied"
    - FeePaymentStatus: "Settled"/"Unpaid"
    """
    graph = SOPGraph("property_service")
    
    # 1. 创建所有节点
    nodes = [
        SOPNode("start", NodeType.START, "START", "开始"),
        
        # 分类步骤
        SOPNode("step1", NodeType.ACTION, "step1_classification",
                "字段分类 - 提取核心意图、情绪、报修类别、范围、紧急程度"),
        
        # 核心意图判断 (决策节点)
        SOPNode("step2", NodeType.DECISION, "step2_core_intention",
                "核心意图判断 - 判断用户核心意图",
                parameters={"decision_field": "CoreIntention"}),
        
        # 房屋状态判断 (决策节点 - 仅限Payment/Complaint)
        SOPNode("step3", NodeType.DECISION, "step3_house_status",
                "房屋状态判断 - 检查房屋居住状态",
                parameters={"decision_field": "HouseStatus"}),
        
        # 报修类别记录 (记录节点 - 仅限Repair，记录报修类别但不分支)
        SOPNode("step4", NodeType.ACTION, "step4_repair_category",
                "报修类别记录 - 记录报修事项类别"),
        
        # 报修范围确认 (决策节点 - Repair分支)
        SOPNode("step5", NodeType.DECISION, "step5_repair_scope_check",
                "报修范围确认 - 确认报修事项范围分类",
                parameters={"decision_field": "RelatedScope"}),
        
        # 缴费状态判断 (决策节点 - 用于 Payment/Complaint)
        SOPNode("step6", NodeType.DECISION, "step6_fee_payment_status",
                "缴费状态判断 - 检查物业费缴费状态",
                parameters={"decision_field": "FeePaymentStatus"}),
        
        # 缴费状态判断 (决策节点 - 用于 Repair)
        SOPNode("step6_repair", NodeType.DECISION, "step6_repair_fee_payment_status",
                "缴费状态判断(报修) - 检查物业费缴费状态",
                parameters={"decision_field": "FeePaymentStatus"}),
        
        # 情绪判断 (决策节点 - Complaint分支)
        SOPNode("step7", NodeType.DECISION, "step7_emotion_tag",
                "情绪判断 - 检查用户情绪状态",
                parameters={"decision_field": "EmotionTag"}),
        
        # 紧急程度判断 (决策节点 - Repair + Public)
        SOPNode("step8", NodeType.DECISION, "step8_emergency_level",
                "紧急程度判断 - 检查事项紧急程度",
                parameters={"decision_field": "EmergencyLevel"}),
        
        # 动作节点
        # Payment分支
        SOPNode("action_payinformation", NodeType.ACTION, "action_payinformation",
                "提供缴费信息", action_name="PayInformation"),
        
        SOPNode("action_payment", NodeType.ACTION, "action_payment",
                "处理缴费", action_name="Payment"),
        
        # Complaint分支
        SOPNode("action_comfort", NodeType.ACTION, "action_comfort",
                "安抚住户", action_name="Comfort"),
        
        SOPNode("action_transhuman", NodeType.ACTION, "action_transhuman",
                "转人工处理", action_name="TransHuman"),
        
        # Repair分支
        SOPNode("action_reject", NodeType.ACTION, "action_reject",
                "委婉拒绝", action_name="Reject"),
        
        SOPNode("action_registration", NodeType.ACTION, "action_registration",
                "登记维修", action_name="Registration"),
        
        # 终止
        SOPNode("end", NodeType.END, "END", "流程结束"),
    ]
    
    for node in nodes:
        graph.add_node(node)
    
    # 2. 创建所有边
    edges = [
        # START -> step1
        SOPEdge("start", "step1",
                TransitionCondition("always", description="开始分类"),
                "start"),
        
        # step1 -> step2
        SOPEdge("step1", "step2",
                TransitionCondition("always", description="进行核心意图判断"),
                "continue"),
        
        # ========== step2分支：CoreIntention ==========
        # Payment -> step3
        SOPEdge("step2", "step3",
                TransitionCondition("payment", description="用户意图为缴费"),
                "Payment"),
        
        # Complaint -> step3
        SOPEdge("step2", "step3",
                TransitionCondition("complaint", description="用户意图为投诉"),
                "Complaint"),
        
        # Repair -> step4
        SOPEdge("step2", "step4",
                TransitionCondition("repair", description="用户意图为报修"),
                "Repair"),
        
        # ========== step3分支：HouseStatus (Payment/Complaint) ==========
        # Payment + UnOccupied -> PayInformation -> END
        SOPEdge("step3", "action_payinformation",
                TransitionCondition("payment_unoccupied", description="缴费+空置房"),
                "UnOccupied"),
        
        # Payment + Occupied/Rented -> step6 (缴费状态)
        SOPEdge("step3", "step6",
                TransitionCondition("payment_occupied_or_rented", description="缴费+自住/租赁房"),
                "Payment_Occupied_or_Rented"),
        
        # Complaint + UnOccupied -> step7 (情绪判断)
        SOPEdge("step3", "step7",
                TransitionCondition("complaint_unoccupied", description="投诉+空置房"),
                "Complaint_UnOccupied"),
        
        # Complaint + Occupied/Rented -> step6 (缴费状态)
        SOPEdge("step3", "step6",
                TransitionCondition("complaint_occupied_or_rented", description="投诉+自住/租赁房"),
                "Complaint_Occupied_or_Rented"),
        
        # ========== step4分支：RelatedScope (Repair) ==========
        # Repair -> step5 (继续范围确认)
        SOPEdge("step4", "step5",
                TransitionCondition("always", description="进行报修范围确认"),
                "continue"),
        
        # ========== step5分支：报修范围确认 ==========
        # Repair + Personal -> step6_repair (缴费状态-报修专用)
        SOPEdge("step5", "step6_repair",
                TransitionCondition("repair_personal", description="报修+个户"),
                "Personal"),
        
        # Repair + Public -> step8 (紧急程度)
        SOPEdge("step5", "step8",
                TransitionCondition("repair_public", description="报修+公共"),
                "Public"),
        
        # ========== step6分支：FeePaymentStatus / EmotionTag ==========
        # Payment + Settled -> PayInformation -> END
        SOPEdge("step6", "action_payinformation",
                TransitionCondition("payment_settled", description="缴费+已缴"),
                "Payment_Settled"),
        
        # Payment + Unpaid -> Payment -> END
        SOPEdge("step6", "action_payment",
                TransitionCondition("payment_unpaid", description="缴费+未缴"),
                "Payment_Unpaid"),
        
        # Complaint + Settled -> step7 (情绪判断)
        SOPEdge("step6", "step7",
                TransitionCondition("complaint_settled", description="投诉+已缴"),
                "Complaint_Settled"),
        
        # Complaint + Unpaid -> Payment -> END
        SOPEdge("step6", "action_payment",
                TransitionCondition("complaint_unpaid", description="投诉+未缴"),
                "Complaint_Unpaid"),
        
         # ========== step6_repair分支：FeePaymentStatus (Repair) ==========
         # Repair + Personal + Unpaid -> Reject -> END
         SOPEdge("step6_repair", "action_reject",
                 TransitionCondition("repair_personal_unpaid", description="报修+个户+未缴"),
                 "Unpaid"),
         
         # Repair + Personal + Settled -> step8 (继续判断紧急程度)
         SOPEdge("step6_repair", "step8",
                 TransitionCondition("repair_personal_settled", description="报修+个户+已缴→判断紧急程度"),
                 "Settled"),
         
         # ========== step7分支：EmotionTag (Complaint) ==========
        # Complaint + Calm -> Comfort -> END
        SOPEdge("step7", "action_comfort",
                TransitionCondition("calm", description="情绪平静"),
                "Calm"),
        
        # Complaint + Discontent -> TransHuman -> END
        SOPEdge("step7", "action_transhuman",
                TransitionCondition("discontent", description="情绪不满"),
                "Discontent"),
        
        # ========== step8分支：EmergencyLevel (Repair + Public) ==========
        # Repair + Public + Urgent -> TransHuman -> END
        SOPEdge("step8", "action_transhuman",
                TransitionCondition("repair_public_urgent", description="报修+公共+紧急"),
                "Urgent"),
        
        # Repair + Public + NoUrgent -> Registration -> END
        SOPEdge("step8", "action_registration",
                TransitionCondition("repair_public_nougent", description="报修+公共+普通"),
                "NoUrgent"),
        
        # ========== 所有动作 -> END ==========
        SOPEdge("action_payinformation", "end",
                TransitionCondition("action_complete", description="提供缴费信息完成"),
                "end"),
        
        SOPEdge("action_payment", "end",
                TransitionCondition("action_complete", description="缴费处理完成"),
                "end"),
        
        SOPEdge("action_comfort", "end",
                TransitionCondition("action_complete", description="安抚完成"),
                "end"),
        
        SOPEdge("action_transhuman", "end",
                TransitionCondition("action_complete", description="转接完成"),
                "end"),
        
        SOPEdge("action_reject", "end",
                TransitionCondition("action_complete", description="拒绝完成"),
                "end"),
        
        SOPEdge("action_registration", "end",
                TransitionCondition("action_complete", description="登记完成"),
                "end"),
    ]
    
    for edge in edges:
        graph.add_edge(edge)
    
    return graph


def build_logistics_delivery_sop_graph() -> SOPGraph:
    """
    构建快递物流场景SOP有向图
    
    流程说明：
    1. step1: 字段分类 (RiskStatus, InfoCompleteness, UserIntention, EmotionalState, EmergencyLevel, ComplaintValidity)
    2. step2: 风险控制标签 (Risk/Safe)
    3. step3: 信息完整度判断 (True/False)
    4. step4: 用户意图判断 (Urge/Complaint/Modify)
    5. step5: 订单状态查询 (Arrived/Delivered/Undelivered 与 UserIntention 组合)
    6. step6: 订单紧急程度判断 (Urgent/Normal)
    7. step7: 投诉合理性判断 (True/False)
    8. step8: 是否有保险 (True/False)
    9. step9: 用户情绪状态判断 (Calm/Dissatisfied)
    
    系统变量：
    - orderStatus: "Arrived"/"Delivered"/"Undelivered"
    - hasInsurance: True/False
    """
    graph = SOPGraph("logistics_delivery")
    
    # 1. 创建所有节点
    nodes = [
        SOPNode("start", NodeType.START, "START", "开始"),
        
        # 分类步骤
        SOPNode("step1", NodeType.ACTION, "step1_classification",
                "字段分类 - 提取RiskStatus、InfoCompleteness、UserIntention、EmotionalState、EmergencyLevel、ComplaintValidity"),
        
        # 风险控制标签 (决策节点)
        SOPNode("step2", NodeType.DECISION, "step2_risk_control",
                "风险控制标签 - 根据RiskStatus进行跳转",
                parameters={"decision_field": "RiskStatus"}),
        
        # 信息完整度判断 (决策节点)
        SOPNode("step3", NodeType.DECISION, "step3_info_completeness",
                "信息完整度判断 - 根据InfoCompleteness进行跳转",
                parameters={"decision_field": "InfoCompleteness"}),
        
        # 用户意图记录 (记录节点，真正的决策在step5根据UserIntention+orderStatus组合判断)
        SOPNode("step4", NodeType.ACTION, "step4_user_intention",
                "用户意图记录 - 记录UserIntention"),
        
        # 订单状态查询 (决策节点)
        SOPNode("step5", NodeType.DECISION, "step5_order_status",
                "订单状态查询 - 根据orderStatus和UserIntention进行跳转",
                parameters={"decision_field": "orderStatus"}),
        
        # 订单紧急程度判断 (决策节点)
        SOPNode("step6", NodeType.DECISION, "step6_emergency_level",
                "订单紧急程度判断 - 根据EmergencyLevel进行跳转",
                parameters={"decision_field": "EmergencyLevel"}),
        
        # 投诉合理性判断 (决策节点)
        SOPNode("step7", NodeType.DECISION, "step7_complaint_validity",
                "投诉合理性判断 - 根据ComplaintValidity进行跳转",
                parameters={"decision_field": "ComplaintValidity"}),
        
        # 是否有保险 (决策节点)
        SOPNode("step8", NodeType.DECISION, "step8_has_insurance",
                "是否有保险 - 根据hasInsurance进行跳转",
                parameters={"decision_field": "hasInsurance"}),
        
        # 用户情绪状态判断 (决策节点)
        SOPNode("step9", NodeType.DECISION, "step9_emotional_state",
                "用户情绪状态判断 - 根据EmotionalState进行跳转",
                parameters={"decision_field": "EmotionalState"}),
        
        # 动作节点
        SOPNode("action_interception", NodeType.ACTION, "action_interception",
                "对有风险的包裹进行拦截", action_name="Interception"),
        
        SOPNode("action_supplementary", NodeType.ACTION, "action_supplementary",
                "补充信息，提供订单号", action_name="Supplementary"),
        
        SOPNode("action_detail", NodeType.ACTION, "action_detail",
                "告知包裹的物流详情", action_name="Detail"),
        
        SOPNode("action_registration", NodeType.ACTION, "action_registration",
                "登记加急包裹物流", action_name="Registration"),
        
        SOPNode("action_reject", NodeType.ACTION, "action_reject",
                "委婉拒绝用户修改地址的请求", action_name="Reject"),
        
        SOPNode("action_makeupdiference", NodeType.ACTION, "action_makeupdiference",
                "启动补差价流程", action_name="MakeUpDifference"),
        
        SOPNode("action_modify", NodeType.ACTION, "action_modify",
                "修改地址", action_name="Modify"),
        
        SOPNode("action_comfort", NodeType.ACTION, "action_comfort",
                "安抚住户情绪", action_name="Comfort"),
        
        SOPNode("action_compensation", NodeType.ACTION, "action_compensation",
                "赔偿", action_name="Compensation"),
        
        SOPNode("action_transhuman", NodeType.ACTION, "action_transhuman",
                "转人工处理", action_name="TransHuman"),
        
        # 终止
        SOPNode("end", NodeType.END, "END", "流程结束"),
    ]
    
    for node in nodes:
        graph.add_node(node)
    
    # 2. 创建所有边
    edges = [
        # START -> step1
        SOPEdge("start", "step1",
                TransitionCondition("always", description="开始分类"),
                "start"),
        
        # step1 -> step2
        SOPEdge("step1", "step2",
                TransitionCondition("always", description="进行风险控制"),
                "continue"),
        
        # ========== step2分支：RiskStatus ==========
        # Risk -> Interception -> END
        SOPEdge("step2", "action_interception",
                TransitionCondition("risk", description="订单有风险"),
                "Risk"),
        
        # Safe -> step3
        SOPEdge("step2", "step3",
                TransitionCondition("safe", description="订单安全"),
                "Safe"),
        
        # ========== step3分支：InfoCompleteness ==========
        # False -> Supplementary -> END
        SOPEdge("step3", "action_supplementary",
                TransitionCondition("incomplete", description="信息不完整"),
                "False"),
        
        # True -> step4
        SOPEdge("step3", "step4",
                TransitionCondition("complete", description="信息完整"),
                "True"),
        
        # ========== step4分支：UserIntention ==========
        # 所有意图都进入step5
        SOPEdge("step4", "step5",
                TransitionCondition("always", description="进行订单状态查询"),
                "continue"),
        
        # ========== step5分支：orderStatus 与 UserIntention 的组合 ==========
        # ===== Urge + Arrived -> Detail -> END =====
        SOPEdge("step5", "action_detail",
                TransitionCondition("urge_arrived", description="催促且已到达"),
                "urge_arrived"),
        
        # ===== Urge + (Delivered/Undelivered) -> step6 =====
        SOPEdge("step5", "step6",
                TransitionCondition("urge_not_arrived", description="催促但未到达或已送达"),
                "urge_not_arrived"),
        
        # ===== Modify + Arrived -> Reject -> END =====
        SOPEdge("step5", "action_reject",
                TransitionCondition("modify_arrived", description="修改且已到达"),
                "modify_arrived"),
        
        # ===== Modify + Delivered -> MakeUpDifference -> END =====
        SOPEdge("step5", "action_makeupdiference",
                TransitionCondition("modify_delivered", description="修改且已送达"),
                "modify_delivered"),
        
        # ===== Modify + Undelivered -> Modify -> END =====
        SOPEdge("step5", "action_modify",
                TransitionCondition("modify_undelivered", description="修改且未送达"),
                "modify_undelivered"),
        
        # ===== Complaint + Arrived -> step7 =====
        SOPEdge("step5", "step7",
                TransitionCondition("complaint_arrived", description="投诉且已到达"),
                "complaint_arrived"),
        
        # ===== Complaint + (Delivered/Undelivered) -> step6 =====
        SOPEdge("step5", "step6",
                TransitionCondition("complaint_not_arrived", description="投诉但未到达或已送达"),
                "complaint_not_arrived"),
        
        # ========== step6分支：EmergencyLevel ==========
        # Urgent -> Registration -> END
        SOPEdge("step6", "action_registration",
                TransitionCondition("urgent", description="事项紧急"),
                "Urgent"),
        
        # Normal -> Detail -> END
        SOPEdge("step6", "action_detail",
                TransitionCondition("normal", description="事项正常"),
                "Normal"),
        
        # ========== step7分支：ComplaintValidity ==========
        # False -> Comfort -> END
        SOPEdge("step7", "action_comfort",
                TransitionCondition("invalid", description="投诉无效"),
                "False"),
        
        # True -> step8
        SOPEdge("step7", "step8",
                TransitionCondition("valid", description="投诉有效"),
                "True"),
        
        # ========== step8分支：hasInsurance ==========
        # True -> Compensation -> END
        SOPEdge("step8", "action_compensation",
                TransitionCondition("has_insurance", description="有保险"),
                "True"),
        
        # False -> step9
        SOPEdge("step8", "step9",
                TransitionCondition("no_insurance", description="无保险"),
                "False"),
        
        # ========== step9分支：EmotionalState ==========
        # Calm -> Comfort -> END
        SOPEdge("step9", "action_comfort",
                TransitionCondition("calm", description="情绪平静"),
                "Calm"),
        
        # Dissatisfied -> TransHuman -> END
        SOPEdge("step9", "action_transhuman",
                TransitionCondition("dissatisfied", description="情绪不满"),
                "Dissatisfied"),
        
        # ========== 所有动作 -> END ==========
        SOPEdge("action_interception", "end",
                TransitionCondition("action_complete", description="拦截完成"),
                "end"),
        
        SOPEdge("action_supplementary", "end",
                TransitionCondition("action_complete", description="补充信息完成"),
                "end"),
        
        SOPEdge("action_detail", "end",
                TransitionCondition("action_complete", description="告知详情完成"),
                "end"),
        
        SOPEdge("action_registration", "end",
                TransitionCondition("action_complete", description="登记完成"),
                "end"),
        
        SOPEdge("action_reject", "end",
                TransitionCondition("action_complete", description="拒绝完成"),
                "end"),
        
        SOPEdge("action_makeupdiference", "end",
                TransitionCondition("action_complete", description="补差完成"),
                "end"),
        
        SOPEdge("action_modify", "end",
                TransitionCondition("action_complete", description="修改完成"),
                "end"),
        
        SOPEdge("action_comfort", "end",
                TransitionCondition("action_complete", description="安抚完成"),
                "end"),
        
        SOPEdge("action_compensation", "end",
                TransitionCondition("action_complete", description="赔偿完成"),
                "end"),
        
        SOPEdge("action_transhuman", "end",
                TransitionCondition("action_complete", description="转接完成"),
                "end"),
    ]
    
    for edge in edges:
        graph.add_edge(edge)
    
    return graph


def build_airline_refund_sop_graph() -> SOPGraph:
    """
    构建在线航司改签退票场景SOP有向图
    
    流程说明：
    1. step1: 字段分类 (CoreDemand, ChangeReason, UserEmotion, DocumentValidity, IsInfoComplete)
    2. step2: 核心诉求判断 (RescheduleOrRefund/Complaint/Inqury)
    3. step3: 变更原因判断 (Personal/Airline/Weather) - 仅限RescheduleOrRefund
    4. step4: 会员等级判断 (Regular/VIP/Blacklist)
    5. step5: 信息是否完善判断 (Complete/Incomplete)
    6. step6: 用户情绪状态判断 (Normal/Urgent/Dissatisfied) - 仅限Complaint
    7. step7: 是否购买保险判断 (True/False)
    8. step8: 凭证是否合理判断 (Valid/Invalid)
    
    系统变量：
    - memberLevel: "VIP"/"Regular"/"Blacklist" - 用户会员等级
    - hasInsurance: True/False - 是否购买保险
    """
    graph = SOPGraph("airline_refund")
    
    # 1. 创建所有节点
    nodes = [
        SOPNode("start", NodeType.START, "START", "开始"),
        
        # 分类步骤
        SOPNode("step1", NodeType.ACTION, "step1_classification",
                "字段分类 - 提取CoreDemand、ChangeReason、UserEmotion、DocumentValidity、IsInfoComplete"),
        
        # 核心诉求判断 (决策节点)
        SOPNode("step2", NodeType.DECISION, "step2_core_demand",
                "核心诉求判断 - 根据CoreDemand进行跳转",
                parameters={"decision_field": "CoreDemand"}),
        
        # 变更原因判断 (决策节点 - 仅限RescheduleOrRefund)
        SOPNode("step3", NodeType.DECISION, "step3_change_reason",
                "变更原因判断 - 根据ChangeReason进行跳转",
                parameters={"decision_field": "ChangeReason"}),
        
        # 会员等级判断 (决策节点)
        SOPNode("step4", NodeType.DECISION, "step4_member_level",
                "会员等级判断 - 根据memberLevel进行跳转",
                parameters={"decision_field": "memberLevel"}),
        
        # 信息是否完善判断 (决策节点)
        SOPNode("step5", NodeType.DECISION, "step5_info_complete",
                "信息是否完善判断 - 根据IsInfoComplete进行跳转",
                parameters={"decision_field": "IsInfoComplete"}),
        
        # 用户情绪状态判断 (决策节点 - Complaint分支)
        SOPNode("step6", NodeType.DECISION, "step6_user_emotion",
                "用户情绪状态判断 - 根据UserEmotion进行跳转",
                parameters={"decision_field": "UserEmotion"}),
        
        # 是否购买保险判断 (决策节点)
        SOPNode("step7", NodeType.DECISION, "step7_has_insurance",
                "是否购买保险判断 - 根据hasInsurance进行跳转",
                parameters={"decision_field": "hasInsurance"}),
        
        # 凭证是否合理判断 (决策节点)
        SOPNode("step8", NodeType.DECISION, "step8_document_validity",
                "凭证是否合理判断 - 根据DocumentValidity进行跳转",
                parameters={"decision_field": "DocumentValidity"}),
        
        # 动作节点
        # 补充信息
        SOPNode("action_supplementary", NodeType.ACTION, "action_supplementary",
                "补充信息，提供订单号", action_name="Supplementary"),
        
        # 改签或退票
        SOPNode("action_reschedule_or_refund", NodeType.ACTION, "action_reschedule_or_refund",
                "办理改签或退票", action_name="RescheduleOrRefund"),
        
        # 转人工处理
        SOPNode("action_transhuman", NodeType.ACTION, "action_transhuman",
                "转人工处理", action_name="TransHuman"),
        
        # 拒绝请求
        SOPNode("action_reject", NodeType.ACTION, "action_reject",
                "委婉拒绝请求", action_name="Reject"),
        
        # 改签或退票并赔偿
        SOPNode("action_reschedule_or_refund_compensation", NodeType.ACTION, "action_reschedule_or_refund_compensation",
                "办理改签或退票并赔偿损失", action_name="RescheduleOrRefund+Compensation"),
        
        # 安抚住户情绪
        SOPNode("action_comfort", NodeType.ACTION, "action_comfort",
                "安抚住户情绪", action_name="Comfort"),
        
        # 告知包裹的物流详情
        SOPNode("action_enquiry", NodeType.ACTION, "action_enquiry",
                "告知包裹的物流详情", action_name="Enquiry"),
        
        # 改签或退票并启动补差价流程
        SOPNode("action_reschedule_or_refund_handling_fee", NodeType.ACTION, "action_reschedule_or_refund_handling_fee",
                "办理改签或退票并启动补差价流程", action_name="RescheduleOrRefund+HandlingFee"),
        
        # 赔偿
        SOPNode("action_compensation", NodeType.ACTION, "action_compensation",
                "赔偿", action_name="Compensation"),
        
        # 终止
        SOPNode("end", NodeType.END, "END", "流程结束"),
    ]
    
    for node in nodes:
        graph.add_node(node)
    
    # 2. 创建所有边
    edges = [
        # START -> step1
        SOPEdge("start", "step1",
                TransitionCondition("always", description="开始分类"),
                "start"),
        
        # step1 -> step2
        SOPEdge("step1", "step2",
                TransitionCondition("always", description="进行核心诉求判断"),
                "continue"),
        
        # ========== step2分支：CoreDemand ==========
        # Inqury -> step5 (信息是否完善)
        SOPEdge("step2", "step5",
                TransitionCondition("inqury", description="用户为咨询"),
                "Inqury"),
        
        # Complaint -> step4 (会员等级)
        SOPEdge("step2", "step4",
                TransitionCondition("complaint", description="用户为投诉"),
                "Complaint"),
        
        # RescheduleOrRefund -> step3 (变更原因)
        SOPEdge("step2", "step3",
                TransitionCondition("reschedule_or_refund", description="用户为改签或退票"),
                "RescheduleOrRefund"),
        
        # ========== step3分支：ChangeReason (RescheduleOrRefund) ==========
        # Personal -> step5 (信息是否完善)
        SOPEdge("step3", "step5",
                TransitionCondition("personal", description="个人原因"),
                "Personal"),
        
        # Airline/Weather -> step4 (会员等级)
        SOPEdge("step3", "step4",
                TransitionCondition("airline_or_weather", description="航司或天气原因"),
                "Airline_or_Weather"),
        
        # ========== step4分支：memberLevel ==========
        # ===== 分支A：来自step2 (Complaint) =====
        # Regular -> step6 (情绪判断)
        SOPEdge("step4", "step6",
                TransitionCondition("complaint_regular", description="投诉+普通会员"),
                "Complaint_Regular"),
        
        # VIP -> TransHuman -> END
        SOPEdge("step4", "action_transhuman",
                TransitionCondition("complaint_vip", description="投诉+VIP会员"),
                "Complaint_VIP"),
        
        # Blacklist -> Reject -> END
        SOPEdge("step4", "action_reject",
                TransitionCondition("complaint_blacklist", description="投诉+黑名单"),
                "Complaint_Blacklist"),
        
        # ===== 分支B：来自step8 (RescheduleOrRefund+Personal+Valid) =====
        # Regular -> step7 (判断保险)
        SOPEdge("step4", "step7",
                TransitionCondition("reschedule_personal_valid_regular", description="改签+个人+凭证有效+普通"),
                "RescheduleOrRefund_Personal_Valid_Regular"),
        
        # VIP -> RescheduleOrRefund -> END
        SOPEdge("step4", "action_reschedule_or_refund",
                TransitionCondition("reschedule_personal_vip", description="改签+个人+VIP"),
                "RescheduleOrRefund_Personal_VIP"),
        
        # Blacklist -> Reject -> END
        SOPEdge("step4", "action_reject",
                TransitionCondition("reschedule_personal_blacklist", description="改签+个人+黑名单"),
                "RescheduleOrRefund_Personal_Blacklist"),
        
        # ===== 分支C：来自step3 (RescheduleOrRefund+Airline/Weather) =====
        # Regular/Blacklist -> RescheduleOrRefund -> END
        SOPEdge("step4", "action_reschedule_or_refund",
                TransitionCondition("reschedule_airline_regular_or_blacklist", description="改签+航司/天气+普通/黑名单"),
                "RescheduleOrRefund_Airline_Regular_Blacklist"),
        
        # VIP -> RescheduleOrRefund+Compensation -> END
        SOPEdge("step4", "action_reschedule_or_refund_compensation",
                TransitionCondition("reschedule_airline_vip", description="改签+航司/天气+VIP"),
                "RescheduleOrRefund_Airline_VIP"),
        
        # ========== step5分支：IsInfoComplete ==========
        # ===== 分支A：来自step2 (Inqury) =====
        # Incomplete -> Supplementary -> END
        SOPEdge("step5", "action_supplementary",
                TransitionCondition("inqury_incomplete", description="咨询+信息不完善"),
                "Inqury_Incomplete"),
        
        # Complete -> Enquiry -> END
        SOPEdge("step5", "action_enquiry",
                TransitionCondition("inqury_complete", description="咨询+信息完善"),
                "Inqury_Complete"),
        
        # ===== 分支B：来自step3 (RescheduleOrRefund+Personal) =====
        # Incomplete -> Supplementary -> END
        SOPEdge("step5", "action_supplementary",
                TransitionCondition("reschedule_personal_incomplete", description="改签+个人+信息不完善"),
                "RescheduleOrRefund_Personal_Incomplete"),
        
        # Complete + DocumentValidity=Invalid -> step8 (凭证判断)
        SOPEdge("step5", "step8",
                TransitionCondition("reschedule_personal_complete", description="改签+个人+信息完善"),
                "RescheduleOrRefund_Personal_Complete"),
        
        # ========== step6分支：UserEmotion (Complaint+Regular) ==========
        # Normal -> Comfort -> END
        SOPEdge("step6", "action_comfort",
                TransitionCondition("complaint_normal", description="投诉+正常情绪"),
                "Normal"),
        
        # Urgent/Dissatisfied -> step8 (凭证判断)
        SOPEdge("step6", "step8",
                TransitionCondition("complaint_urgent_or_dissatisfied", description="投诉+紧急/不满情绪"),
                "Urgent_or_Dissatisfied"),
        
        # ========== step7分支：hasInsurance (RescheduleOrRefund+Personal) =====
        # True -> RescheduleOrRefund -> END
        SOPEdge("step7", "action_reschedule_or_refund",
                TransitionCondition("has_insurance", description="有保险"),
                "True"),
        
        # False -> RescheduleOrRefund+HandlingFee -> END
        SOPEdge("step7", "action_reschedule_or_refund_handling_fee",
                TransitionCondition("no_insurance", description="无保险"),
                "False"),
        
        # ========== step8分支：DocumentValidity ==========
        # ===== 分支A：来自step5 (RescheduleOrRefund+Personal+Complete) =====
        # Invalid -> Supplementary -> END
        SOPEdge("step8", "action_supplementary",
                TransitionCondition("reschedule_personal_invalid", description="改签+个人+凭证无效"),
                "RescheduleOrRefund_Personal_Invalid"),
        
        # Valid -> step4 (会员等级)
        SOPEdge("step8", "step4",
                TransitionCondition("reschedule_personal_valid", description="改签+个人+凭证有效"),
                "RescheduleOrRefund_Personal_Valid"),
        
        # ===== 分支B：来自step6 (Complaint+Urgent/Dissatisfied) =====
        # Invalid -> Comfort -> END
        SOPEdge("step8", "action_comfort",
                TransitionCondition("complaint_invalid", description="投诉+无凭证"),
                "Complaint_Invalid"),
        
        # Valid -> Compensation -> END
        SOPEdge("step8", "action_compensation",
                TransitionCondition("complaint_valid", description="投诉+有凭证"),
                "Complaint_Valid"),
        
        # ========== 所有动作 -> END ==========
        SOPEdge("action_supplementary", "end",
                TransitionCondition("action_complete", description="补充信息完成"),
                "end"),
        
        SOPEdge("action_reschedule_or_refund", "end",
                TransitionCondition("action_complete", description="改签或退票完成"),
                "end"),
        
        SOPEdge("action_transhuman", "end",
                TransitionCondition("action_complete", description="转人工完成"),
                "end"),
        
        SOPEdge("action_reject", "end",
                TransitionCondition("action_complete", description="拒绝完成"),
                "end"),
        
        SOPEdge("action_reschedule_or_refund_compensation", "end",
                TransitionCondition("action_complete", description="改签或退票并赔偿完成"),
                "end"),
        
        SOPEdge("action_comfort", "end",
                TransitionCondition("action_complete", description="安抚完成"),
                "end"),
        
        SOPEdge("action_enquiry", "end",
                TransitionCondition("action_complete", description="查询完成"),
                "end"),
        
        SOPEdge("action_reschedule_or_refund_handling_fee", "end",
                TransitionCondition("action_complete", description="改签或退票并补差价完成"),
                "end"),
        
        SOPEdge("action_compensation", "end",
                TransitionCondition("action_complete", description="赔偿完成"),
                "end"),
    ]
    
    for edge in edges:
        graph.add_edge(edge)
    
    return graph


def get_sop_graph(scenario_id: str) -> SOPGraph:
    """
    根据场景ID获取SOP图
    
    Args:
        scenario_id: 场景ID，支持的场景:
            - online_education: 在线教育平台客服
            - ecommerce_refund: 电商退款
            - telecom_package: 电信套餐办理
            - property_service: 物业服务
            - logistics_delivery: 快递物流
            - airline_refund: 在线航司改签退票
        
    Returns:
        SOPGraph: SOP有向图
        
    Raises:
        ValueError: 未知的场景ID
    """
    graphs = {
        "online_education": build_online_education_sop_graph(),
        "ecommerce_refund": build_ecommerce_refund_sop_graph(),
        "telecom_package": build_telecom_package_sop_graph(),
        "property_service": build_property_service_sop_graph(),
        "logistics_delivery": build_logistics_delivery_sop_graph(),
        "airline_refund": build_airline_refund_sop_graph(),
    }
    
    if scenario_id not in graphs:
        raise ValueError(f"Unknown scenario_id: {scenario_id}. Supported: {list(graphs.keys())}")
    
    return graphs[scenario_id]
