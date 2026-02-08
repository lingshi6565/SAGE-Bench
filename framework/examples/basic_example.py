#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基础示例 - 展示框架的核心功能
Basic Example - Demonstrates Framework Core Features

运行方法：
python examples/basic_example.py
"""

import sys
import json
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from framework.config import get_scenario_config, AdversarialIntensity
from framework.sop import get_sop_graph
from framework.models import UserProfile, UserModelFactory, AgentModel
from framework.core import DialogueSimulator
from framework.evaluator import Evaluator
from framework.prompts import (
    get_user_prompt_for_intent,
    get_initial_state_for_intent,
    get_initial_messages_for_intent,
)


def main():
    """运行基础示例"""
    
    print("=" * 80)
    print("多轮对话评测框架 - 基础示例")
    print("=" * 80)
    
    # ==================== 1. 加载场景配置 ====================
    print("\n[1/5] 加载场景配置...")
    scenario_id = "online_education"
    scenario_config = get_scenario_config(scenario_id)
    print(f"  ✓ 场景: {scenario_config.scenario_name}")
    print(f"  ✓ 用户意图数: {len(scenario_config.user_intents)}")
    print(f"  ✓ 可用意图: {list(scenario_config.user_intents.keys())}")
    
    # ==================== 2. 构建SOP图 ====================
    print("\n[2/5] 构建SOP图...")
    sop_graph = get_sop_graph(scenario_id)
    print(f"  ✓ 节点数: {len(sop_graph.nodes)}")
    print(f"  ✓ 边数: {len(sop_graph.edges)}")
    
    # 获取所有可能的路径
    all_paths = sop_graph.get_all_paths()
    print(f"  ✓ 所有可能路径数: {len(all_paths)}")
    print(f"  ✓ 示例路径: {all_paths[0] if all_paths else 'N/A'}")
    
    # ==================== 3. 创建用户模型 ====================
    print("\n[3/5] 创建用户模型...")
    
    # 选择一个意图
    user_intent = "seek_answer"
    print(f"  ✓ 选择意图: {user_intent}")
    
    # 创建用户画像
    user_profile = UserProfile(
        user_id="user_001",
        user_intent=user_intent,
        adversarial_intensity=AdversarialIntensity.WEAK.value,
        scenario_id=scenario_id,
        course_list=["Python入门"],
        historical_complaints=False,
        question_types_30days=["课程内容理解"],
        is_risk_user=False,
        patience_level=0.7,
        conciseness_level=0.6,
    )
    
    # 生成用户系统提示词
    user_system_prompt = get_user_prompt_for_intent(
        user_intent,
        user_profile.user_id,
        courses=", ".join(user_profile.course_list)
    )
    
    # 创建用户模型
    user_model = UserModelFactory.create_from_profile(
        user_profile,
        system_prompt=user_system_prompt
    )
    print(f"  ✓ 用户模型已创建: {user_profile.user_id}")
    print(f"  ✓ 用户意图: {user_profile.user_intent}")
    print(f"  ✓ 对抗强度: {user_profile.adversarial_intensity}")
    
    # ==================== 4. 创建客服模型 ====================
    print("\n[4/5] 创建客服模型...")
    
    from framework.prompts import AGENT_SYSTEM_PROMPT
    
    agent_model = AgentModel(
        scenario_id=scenario_id,
        sop_graph=sop_graph,
        system_prompt=AGENT_SYSTEM_PROMPT,
        use_llm_for_classification=False  # 这里用规则进行分类
    )
    print(f"  ✓ 客服模型已创建")
    print(f"  ✓ SOP场景: {scenario_id}")
    
    # ==================== 5. 运行对话模拟 ====================
    print("\n[5/5] 运行对话模拟...")
    
    # 获取初始消息
    initial_messages = get_initial_messages_for_intent(user_intent)
    initial_user_message = initial_messages[0] if initial_messages else "你好，我有个问题要咨询。"
    
    # 获取初始状态
    context_data = get_initial_state_for_intent(user_intent)
    
    # 创建模拟器
    simulator = DialogueSimulator(
        user_model=user_model,
        agent_model=agent_model,
        max_turns=5,
        verbose=True
    )
    
    # 运行模拟
    simulation_result = simulator.run(
        initial_user_message=initial_user_message,
        context_data=context_data
    )
    
    # ==================== 6. 评测结果 ====================
    print("\n" + "=" * 80)
    print("评测结果")
    print("=" * 80)
    
    evaluator = Evaluator(
        scenario_id=scenario_id,
        sop_graph=sop_graph,
        judge_model=None  # 没有裁判LLM时使用启发式规则
    )
    
    evaluation_report = evaluator.evaluate_simulation(
        simulation_result=simulation_result,
        expected_actions=None,
    )
    
    print(f"\n综合评分: {evaluation_report.overall_score:.2f}")
    print(f"\n各项指标:")
    for score in evaluation_report.metric_scores:
        print(f"  - {score.metric_name}: {score.score:.2f} (权重: {score.weight})")
        print(f"    说明: {score.explanation}")
    
    # ==================== 7. 输出结果 ====================
    print("\n" + "=" * 80)
    print("对话历史")
    print("=" * 80)
    
    for turn in simulation_result.turns:
        print(f"\n[轮次 {turn.turn_id}]")
        print(f"用户: {turn.user_message}")
        print(f"客服: {turn.agent_output.chat}")
        print(f"当前步骤: {turn.agent_output.current_step}")
        print(f"动作: {turn.agent_output.action}")
    
    # ==================== 8. 保存结果 ====================
    print("\n" + "=" * 80)
    print("保存结果")
    print("=" * 80)
    
    # 创建输出目录
    output_dir = project_root / "framework" / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    # 保存对话
    dialogue_file = output_dir / f"{simulation_result.simulation_id}_dialogues.jsonl"
    with open(dialogue_file, 'w', encoding='utf-8') as f:
        for turn in simulation_result.turns:
            f.write(json.dumps({
                "turn_id": turn.turn_id,
                "user": turn.user_message,
                "assistant": turn.agent_output.chat,
            }, ensure_ascii=False) + '\n')
    
    # 保存结果
    result_file = output_dir / f"{simulation_result.simulation_id}_results.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        results = {
            "simulation": simulation_result.to_dict(),
            "evaluation": evaluation_report.to_dict(),
        }
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ 对话已保存: {dialogue_file}")
    print(f"  ✓ 结果已保存: {result_file}")
    
    print("\n✓ 示例完成！")


if __name__ == "__main__":
    main()
