#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
支持LLM的完整评测脚本
Complete Evaluation Script with LLM Support

设计说明：
- User 模型：必须本地 vLLM (http://localhost:8000)
- Judge 模型：必须本地 vLLM (http://localhost:8002)
- Agent 模型：可以是本地 vLLM 或 OpenAI 兼容 API

使用方法：

# 方案1：全部本地vLLM
python run_evaluation_with_llm.py \
    --scenario online_education \
    --model my_model \
    --eval-mode vllm \
    --agent-model-type vllm \
    --output ./results \
    --verbose

# 方案2：Agent使用API（推荐准确度）
python run_evaluation_with_llm.py \
    --scenario online_education \
    --model my_model \
    --eval-mode api \
    --agent-model-type api \
    --agent-model-name gpt-4 \
    --api-key sk-xxx \
    --output ./results \
    --verbose

支持的场景 (Supported Scenarios):
  ✓ online_education         - 在线教育平台客服 (已完成)
  ✓ ecommerce_refund        - 电商退款 (已完成)
  ✓ telecom_package         - 电信套餐办理 (已完成)
  ✓ property_service        - 物业服务 (已完成)
  ✓ logistics_delivery      - 快递物流 (已完成)
  ✓ airline_refund          - 在线航司改签退票 (已完成)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
import concurrent.futures
import threading

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from framework import (
    get_scenario_config,
    get_sop_graph,
    UserProfile,
    UserModelFactory,
    AgentModel,
    DialogueSimulator,
    Evaluator,
    AdversarialIntensity,
)

from framework.llm_integration import (
    get_llm_client,
    LLMUserModel,
    LLMUserMessageGenerator,
    LLMJudge,
    MultiModelJudge,
)



# 导入所有场景的 prompt 模块
from framework.prompts import (
    online_education_prompts,
    ecommerce_refund_prompts,
    telecom_package_prompts,
    property_service_prompts,
    logistics_delivery_prompts,
    airline_refund_prompts,
)

from framework.config.llm_deployment_config import (
    LLMClientConfig,
)


# ==================== 辅助函数：支持多场景的 prompt 函数获取 ====================

def get_path_list_by_scenario(scenario_id: str):
    """
    根据场景ID获取对应的路径列表生成函数和意图映射
    
    Args:
        scenario_id: 场景ID
        
    Returns:
        tuple: (generate_path_list_func, get_intent_path_mapping_func)
    """
    # 导入所有场景的 PathList 模块
    from framework.sop import (
        online_education_PathList,
        ecommerce_refund_PathList,
        telecom_package_PathList,
        property_service_PathList,
        logistics_delivery_PathList,
        airline_refund_PathList,
    )
    
    pathlist_modules = {
        "online_education": online_education_PathList,
        "ecommerce_refund": ecommerce_refund_PathList,
        "telecom_package": telecom_package_PathList,
        "property_service": property_service_PathList,
        "logistics_delivery": logistics_delivery_PathList,
        "airline_refund": airline_refund_PathList,
    }
    
    if scenario_id not in pathlist_modules:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    
    module = pathlist_modules[scenario_id]
    return module.generate_path_list, module.get_intent_path_mapping


def get_agent_system_prompt_by_scenario(scenario_id: str) -> str:
    """
    根据场景ID获取对应的Agent系统提示词
    
    Args:
        scenario_id: 场景ID
        
    Returns:
        str: Agent系统提示词
    """
    prompt_modules = {
        "online_education": online_education_prompts,
        "ecommerce_refund": ecommerce_refund_prompts,
        "telecom_package": telecom_package_prompts,
        "property_service": property_service_prompts,
        "logistics_delivery": logistics_delivery_prompts,
        "airline_refund": airline_refund_prompts,
    }
    
    if scenario_id not in prompt_modules:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    
    module = prompt_modules[scenario_id]
    return module.AGENT_SYSTEM_PROMPT


def get_user_prompt_for_intent_by_scenario(scenario_id: str, user_intent: str, user_id: str, **kwargs) -> str:
    """
    根据场景ID获取对应的用户提示词
    
    Args:
        scenario_id: 场景ID
        user_intent: 用户意图
        user_id: 用户ID
        **kwargs: 其他参数
        
    Returns:
        str: 用户系统提示词
    """
    prompt_modules = {
        "online_education": online_education_prompts,
        "ecommerce_refund": ecommerce_refund_prompts,
        "telecom_package": telecom_package_prompts,
        "property_service": property_service_prompts,
        "logistics_delivery": logistics_delivery_prompts,
        "airline_refund": airline_refund_prompts,
    }
    
    if scenario_id not in prompt_modules:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    
    module = prompt_modules[scenario_id]
    return module.get_user_prompt_for_intent(user_intent, user_id, **kwargs)


def get_initial_state_for_intent_by_scenario(scenario_id: str, user_intent: str, sample_index: int = None) -> dict:
    """
    根据场景ID获取对应的初始状态
    
    Args:
        scenario_id: 场景ID
        user_intent: 用户意图
        sample_index: 指定采样哪个模板（None则随机选择）
        
    Returns:
        dict: 初始状态
    """
    prompt_modules = {
        "online_education": online_education_prompts,
        "ecommerce_refund": ecommerce_refund_prompts,
        "telecom_package": telecom_package_prompts,
        "property_service": property_service_prompts,
        "logistics_delivery": logistics_delivery_prompts,
        "airline_refund": airline_refund_prompts,
    }
    
    if scenario_id not in prompt_modules:
        raise ValueError(f"Unknown scenario: {scenario_id}")
    
    module = prompt_modules[scenario_id]
    return module.get_initial_state_for_intent(user_intent, sample_index)


class LLMEvaluationPipeline:
    """支持LLM的评测管道"""
    
    def __init__(
        self,
        scenario_id: str,
        model_name: str,
        output_dir: str,
        eval_mode: str = "vllm",  # "vllm", "api"
        user_model_url: str = "http://localhost:8000",
        agent_model_url: str = "http://localhost:8001",
        judge_model_url: str = "http://localhost:8002",
        api_key: Optional[str] = None,
        agent_model_type: str = "vllm",  # "vllm" 或 "api" (agent可以是本地或API，user和judge必须本地)
        agent_model_name: str = "gpt-3.5-turbo",  # API模式下的模型名
        max_turns: int = 10,
        verbose: bool = True,
    ):
        """
        初始化LLM评测管道
        
        设计说明：
        - User模型：必须本地vLLM (http://localhost:8000)
        - Judge模型：必须本地vLLM (http://localhost:8002)
        - Agent模型：可以是本地vLLM或API模型
        
        Args:
            scenario_id: 场景ID
            model_name: 模型名称
            output_dir: 输出目录
            eval_mode: 评测模式 (vllm本地/api API模式)
            user_model_url: 用户模型URL (固定本地vLLM)
            agent_model_url: 客服模型URL (本地vLLM时使用)
            judge_model_url: 评判模型URL (固定本地vLLM)
            api_key: API密钥 (agent为API模式时需要)
            agent_model_type: agent模型类型 (vllm本地/api API)
            agent_model_name: agent为API时的模型名称
            max_turns: 最大对话轮次
            verbose: 是否打印详细日志
        """
        self.scenario_id = scenario_id
        self.model_name = model_name
        self.output_dir = Path(output_dir)
        self.eval_mode = eval_mode
        self.max_turns = max_turns
        self.verbose = verbose
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载配置
        self.scenario_config = get_scenario_config(scenario_id)
        self.sop_graph = get_sop_graph(scenario_id)
        
        # 初始化LLM客户端
        self._init_llm_clients(
            eval_mode,
            user_model_url,
            agent_model_url,
            judge_model_url,
            api_key,
            agent_model_type,
            agent_model_name,
        )
        
        # 结果容器
        self.simulation_results = []
        self.evaluation_reports = []
        
        # 场景评测用时记录
        self.scenario_start_time = None
        self.scenario_end_time = None
        self.scenario_duration = 0.0
    
    def _init_llm_clients(
        self,
        eval_mode: str,
        user_model_url: str,
        agent_model_url: str,
        judge_model_url: str,
        api_key: Optional[str],
        agent_model_type: str = "vllm",
        agent_model_name: str = "gpt-3.5-turbo",
    ):
        """初始化LLM客户端
        
        设计说明：
        - User模型：必须本地vLLM
        - Judge模型：必须本地vLLM
        - Agent模型：可以是本地vLLM或API
        
        Args:
            eval_mode: 评测模式 (vllm/api)
            user_model_url: 用户模型URL (本地vLLM)
            agent_model_url: 客服模型URL (eval_mode=vllm时使用)
            judge_model_url: 评判模型URL (本地vLLM)
            api_key: API密钥 (agent_model_type=api时需要)
            agent_model_type: agent模型类型 (vllm/api)
            agent_model_name: agent为API时的模型名称
        """
        
        # eval_mode指定的是整体倾向，但实际以agent_model_type为准
        # eval_mode="vllm" 表示倾向本地，agent_model_type可覆盖
        # eval_mode="api" 表示倾向API，但User/Judge必须本地，agent可以跟随
        
        # 验证agent_model_type有效性
        if agent_model_type not in ["vllm", "api"]:
            raise ValueError(f"agent_model_type必须是'vllm'或'api'，收到: {agent_model_type}")
        
        # Agent为API模式时需要api_key
        if agent_model_type == "api" and not api_key:
            raise ValueError("Agent模型使用API模式需要提供 --api-key")
        
        # 辅助函数：从vLLM服务获取实际模型名称
        def get_vllm_model_name(base_url: str) -> str:
            """从vLLM服务获取实际的模型名称"""
            try:
                import requests
                response = requests.get(f"{base_url}/v1/models", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data") and len(data["data"]) > 0:
                        return data["data"][0]["id"]
            except Exception as e:
                if self.verbose:
                    print(f"警告: 无法从 {base_url} 获取模型名称: {e}")
            
            # 默认使用完整路径的模型名称 (vLLM会自动识别)
            return "auto"
        
        # User模型：必须本地vLLM
        user_model_name = get_vllm_model_name(user_model_url)
        self.user_llm_client = get_llm_client(
            "vllm_chat",
            base_url=user_model_url,
            model_name=user_model_name,
        )
        
        # Agent模型：可以是本地vLLM或API
        if agent_model_type == "vllm":
            agent_model_name_vllm = get_vllm_model_name(agent_model_url)
            self.agent_llm_client = get_llm_client(
                "vllm_chat",
                base_url=agent_model_url,
                model_name=agent_model_name_vllm,
            )
        else:  # api
            self.agent_llm_client = get_llm_client(
                "openai_api",
                base_url=agent_model_url,
                api_key=api_key,
                model_name=agent_model_name,
            )
        
        # Judge模型：必须本地vLLM
        judge_model_name = get_vllm_model_name(judge_model_url)
        self.judge_llm_client = get_llm_client(
            "vllm_chat",
            base_url=judge_model_url,
            model_name=judge_model_name,
        )
    
    def run_single_simulation(
        self,
        user_intent: str,
        user_id: str = None,
        path_config: Dict[str, Any] = None,
    ) -> tuple:
        """
        运行单次模拟
        
        Args:
            user_intent: 用户意图
            user_id: 用户ID
            path_config: 可选的路径配置,如果提供则生成符合该路径的system_info
            
        Returns:
            tuple: (simulation_result, evaluation_report)
        """
        
        if user_id is None:
            user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"运行模拟: {user_intent} (用户: {user_id})")
            if path_config:
                print(f"路径配置: {path_config.get('final_output', {}).get('Action', 'N/A')}")
            print(f"{'='*80}")
        
        # 创建用户模型
        intent_config = self.scenario_config.user_intents.get(user_intent)
        if not intent_config:
            raise ValueError(f"未知的用户意图: {user_intent}")
        
        user_profile = UserProfile(
            user_id=user_id,
            user_intent=user_intent,
            adversarial_intensity=intent_config.intensity_level.value,
            scenario_id=self.scenario_id,
        )
        
        user_system_prompt = get_user_prompt_for_intent_by_scenario(
            self.scenario_id,
            user_intent,
            user_profile.user_id,
        )
        
        # 生成system_info
        if path_config:
            # 从path_config生成system_info
            system_info = self._generate_system_info_from_path_config(path_config)
        else:
            # 使用原有逻辑，根据场景获取初始状态
            system_info = get_initial_state_for_intent_by_scenario(
                self.scenario_id,
                user_intent
            )
        
        # 使用LLM用户模型
        user_model = LLMUserModel(
            profile=user_profile,
            system_prompt=user_system_prompt,
            llm_client=self.user_llm_client,
            temperature=0.8,
            max_tokens=512,
        )
        
        # 创建客服模型
        # 根据场景ID获取对应的系统提示词
        agent_system_prompt = get_agent_system_prompt_by_scenario(self.scenario_id)
        
        agent_model = AgentModel(
            scenario_id=self.scenario_id,
            sop_graph=self.sop_graph,
            system_prompt=agent_system_prompt,
            use_llm_for_classification=False,  # 已废弃,使用use_llm_for_full_output
            llm_client=self.agent_llm_client,  # 传入agent LLM客户端
            use_llm_for_full_output=True,  # 使用LLM生成完整JSON输出(classification+path+finals+chat)
        )
        agent_model.scenario_id = self.scenario_id
        
        # 创建模拟器
        user_message_generator = LLMUserMessageGenerator(self.user_llm_client)
        
        simulator = DialogueSimulator(
            user_model=user_model,
            agent_model=agent_model,
            max_turns=self.max_turns,
            verbose=self.verbose,
        )
        
        # 使用LLM生成初始消息(根据用户画像动态生成,避免固定模板)
        initial_message = user_model.generate_initial_message()
        
        # context_data包含system_info,传递给simulator
        context_data = {"system_info": system_info}
        
        # 运行模拟
        if self.verbose:
            print(f"  [开始对话] 初始消息: {initial_message}")
            print(f"  [系统信息] {system_info}")
        
        simulation_result = simulator.run(
            initial_user_message=initial_message,
            context_data=context_data,
            user_message_generator=user_message_generator,
        )
        
        # 设置模型名称
        simulation_result.model_name = self.model_name
        
        if self.verbose:
            print(f"  [对话完成] 总轮数: {len(simulation_result.turns)}")
            if len(simulation_result.turns) == 0:
                print(f"  ⚠️  警告: 没有生成任何对话轮次!")
            for i, turn in enumerate(simulation_result.turns):
                print(f"    Turn {i}: U={turn.user_message[:50]}... | A={turn.agent_output.chat[:50]}...")


        # 评测 (使用LLM Judge 或 MultiModelVotingJudge)
        # 【投票模式】如果已设置 self.judge_model，则使用投票 Judge；否则创建单个 LLMJudge
        if hasattr(self, 'judge_model') and self.judge_model is not None:
            judge = self.judge_model
        else:
            # 非投票模式：创建单个 LLMJudge
            judge = LLMJudge(
                llm_client=self.judge_llm_client,
                temperature=0.2,
                max_tokens=1024,
            )

        evaluator = Evaluator(
            scenario_id=self.scenario_id,
            sop_graph=self.sop_graph,
            judge_model=judge,
        )
        
        evaluation_report = evaluator.evaluate_simulation(
            simulation_result=simulation_result,
        )
        
        # 保存结果
        self.simulation_results.append(simulation_result)
        self.evaluation_reports.append(evaluation_report)
        
        return simulation_result, evaluation_report
    
    def run_batch_simulations(
        self,
        user_intents: List[str] = None,
        num_users_per_intent: int = 1,
        max_workers: int = 1,  # 新增:并发数,默认1(串行)
    ) -> List[tuple]:
        """批量运行模拟
        
        Args:
            user_intents: 用户意图列表
            num_users_per_intent: 每个意图的用户数
            max_workers: 最大并发数 (1=串行,>1=并发)
        """
        
        # 记录场景开始时间
        import time
        self.scenario_start_time = time.time()
        
        if user_intents is None:
            user_intents = list(self.scenario_config.user_intents.keys())
            if self.verbose:
                print(f"\n[DEBUG] 自动使用所有intents: {user_intents}")
        else:
            if self.verbose:
                print(f"\n[DEBUG] 使用指定的intents: {user_intents}")
        
        results = []
        total_intents = len(user_intents)
        total_simulations = total_intents * num_users_per_intent
        current_simulation = 0
        
        # 打印顶部进度汇总
        print(f"\n{'='*80}")
        print(f"评测信息")
        print(f"{'='*80}")
        print(f"总Intent数: {total_intents}")
        print(f"每个Intent的用户数: {num_users_per_intent}")
        print(f"总评测数: {total_simulations}")
        print(f"并发数: {max_workers} {'(串行模式)' if max_workers == 1 else '(并发模式)'}")
        print(f"{'='*80}\n")
        
        # 线程安全的进度追踪
        progress_lock = threading.Lock()
        completed_count = [0]  # 使用列表以便在闭包中修改
        
        def run_single_with_progress(args):
            """包装函数:运行单次模拟并更新进度"""
            user_intent, user_idx, intent_idx = args
            user_id = f"user_{user_intent}_{user_idx:02d}"
            
            try:
                sim_result, eval_report = self.run_single_simulation(
                    user_intent=user_intent,
                    user_id=user_id,
                )
                
                # 线程安全地更新进度
                with progress_lock:
                    completed_count[0] += 1
                    current = completed_count[0]
                    percent = int(100 * current / total_simulations)
                    filled = int(40 * current / total_simulations)
                    bar = '=' * filled + '-' * (40 - filled)
                    score = eval_report.overall_score if eval_report else 0
                    print(f"  [{bar}] {percent}% ({current}/{total_simulations}) | {user_intent}[{user_idx+1}] ✓ (score: {score:.4f})")
                
                return (True, sim_result, eval_report, None)
                
            except Exception as e:
                with progress_lock:
                    completed_count[0] += 1
                    current = completed_count[0]
                    percent = int(100 * current / total_simulations)
                    filled = int(40 * current / total_simulations)
                    bar = '=' * filled + '-' * (40 - filled)
                    print(f"  [{bar}] {percent}% ({current}/{total_simulations}) | {user_intent}[{user_idx+1}] ✗ (错误: {str(e)[:30]}...)")
                
                if self.verbose:
                    import traceback
                    print(f"ERROR in {user_id}: {e}", file=sys.stderr)
                    traceback.print_exc()
                
                return (False, None, None, e)
        
        # 准备所有任务
        tasks = []
        for intent_idx, user_intent in enumerate(user_intents, 1):
            for user_idx in range(num_users_per_intent):
                tasks.append((user_intent, user_idx, intent_idx))
        
        # 根据max_workers选择串行或并发执行
        if max_workers == 1:
            # 串行模式:保持原有逻辑
            for task in tasks:
                result = run_single_with_progress(task)
                if result[0]:  # success
                    results.append((result[1], result[2]))
        else:
            # 并发模式
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_task = {executor.submit(run_single_with_progress, task): task for task in tasks}
                
                for future in concurrent.futures.as_completed(future_to_task):
                    result = future.result()
                    if result[0]:  # success
                        results.append((result[1], result[2]))
        
        # 显示Intent层级的汇总统计
        print(f"\n{'='*80}")
        print(f"Intent层级统计")
        print(f"{'='*80}")
        for user_intent in user_intents:
            intent_results = [(sim, rep) for sim, rep in results if sim.user_intent == user_intent]
            if intent_results:
                scores = [r[1].overall_score for r in intent_results if r[1]]
                if scores:
                    avg_score = sum(scores) / len(scores)
                    print(f"  {user_intent}: 平均分 {avg_score:.4f} ({len(scores)} 个模拟)")
        
        print(f"\n{'='*80}")
        print(f"✓ 所有评测完成: 共 {current_simulation} 个模拟")
        print(f"{'='*80}\n")
        
        # 记录场景结束时间
        self.scenario_end_time = time.time()
        self.scenario_duration = self.scenario_end_time - self.scenario_start_time
        print(f"场景总用时: {self.scenario_duration:.2f} 秒 ({self.scenario_duration/60:.2f} 分钟)\n")
        
        return results
    
    def save_results(self) -> Dict[str, Path]:
        """保存所有结果"""
        
        file_paths = {}
        timestamp = datetime.now().strftime("%Y%m%d")
        
        # 调试信息
        if self.verbose:
            print(f"\n[DEBUG] 保存结果: {len(self.simulation_results)} 个模拟结果")
            for i, sim_result in enumerate(self.simulation_results):
                print(f"  [{i}] simulation_id={sim_result.simulation_id}, turns={len(sim_result.turns)}")
        
        # 保存对话数据
        dialogues_file = self.output_dir / f"{self.model_name}_{timestamp}_dialogues.jsonl"
        dialogue_count = 0
        with open(dialogues_file, 'w', encoding='utf-8') as f:
            for sim_result in self.simulation_results:
                if self.verbose:
                    print(f"  写入simulation {sim_result.simulation_id}: {len(sim_result.turns)} turns")
                for turn in sim_result.turns:
                    record = {
                        "simulation_id": sim_result.simulation_id,
                        "model_name": sim_result.model_name,
                        "scenario_id": sim_result.scenario_id,
                        "user_intent": sim_result.user_intent,
                        "turn_id": turn.turn_id,
                        "user": turn.user_message,
                        "assistant": turn.agent_output.chat,
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    dialogue_count += 1
        
        if self.verbose:
            print(f"  ✓ 共写入 {dialogue_count} 条对话到 {dialogues_file}")
        
        file_paths["dialogues"] = dialogues_file
        
        # 保存完整结果
        results_file = self.output_dir / f"{self.model_name}_{timestamp}_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            all_results = {
                "metadata": {
                    "model_name": self.model_name,
                    "scenario_id": self.scenario_id,
                    "eval_mode": self.eval_mode,
                    "evaluation_timestamp": timestamp,
                    "total_simulations": len(self.simulation_results),
                },
                "simulations": [r.to_dict() for r in self.simulation_results],
                "evaluations": [r.to_dict() for r in self.evaluation_reports],
            }
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        file_paths["results"] = results_file
        
        # 保存汇总报告
        summary_file = self.output_dir / f"{self.model_name}_{timestamp}_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            summary = self._generate_summary()
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        file_paths["summary"] = summary_file
        
        return file_paths
    
    def run_mixed_evaluation(
        self, 
        samples_per_intent: int = 3,
        ensure_path_coverage: bool = True,
        min_samples_per_path: int = 10,
        max_workers: int = 1  # 新增:并发数,默认1(串行)
    ) -> List[tuple]:
        """
        混合评测策略: 既保证Intent均衡,又确保路径覆盖
        充分利用SOP图谱的PathList
        
        步骤:
        1. 先按Intent采样(Intent均衡采样)
        2. 统计每条路径的测试次数
        3. 补充不足min_samples_per_path次的路径
        
        Args:
            samples_per_intent: 每个Intent的采样数
            ensure_path_coverage: 是否确保所有路径都被覆盖
            min_samples_per_path: 每条路径的最小测试次数(默认10次)
            max_workers: 最大并发数 (1=串行,>1=并发)
            
        Returns:
            List[tuple]: 所有模拟结果和评测报告的列表
        """
        import random
        import time
        from collections import Counter
        
        self.scenario_start_time = time.time()
        
        # 根据场景ID获取对应的路径列表和意图映射
        generate_path_list, get_intent_path_mapping = get_path_list_by_scenario(self.scenario_id)
        
        path_list = generate_path_list()
        intent_mapping = get_intent_path_mapping()
        path_coverage_count = Counter()  # 统计每条路径被测试的次数
        results = []
        
        print(f"\n{'='*80}")
        print(f"混合评测策略: Intent均衡 + 路径全覆盖 (每条路径≥{min_samples_per_path}次)")
        print(f"{'='*80}")
        print(f"总路径数: {len(path_list)}")
        print(f"Intent数: {len(intent_mapping)}")
        print(f"每个Intent采样数: {samples_per_intent}")
        print(f"每条路径最小测试次数: {min_samples_per_path}")
        print(f"并发数: {max_workers} {'(串行模式)' if max_workers == 1 else '(并发模式)'}")
        print(f"{'='*80}\n")
        
        # === 阶段1: Intent均衡采样 ===
        print(f"\n【阶段1】Intent均衡采样")
        print(f"{'-'*80}")
        
        total_phase1 = len(intent_mapping) * samples_per_intent
        
        # 线程安全的计数器和锁
        progress_lock = threading.Lock()
        completed_count = [0]
        
        def run_phase1_task(args):
            """阶段1的单个任务执行函数"""
            intent, path_idx, path_config, task_id = args
            
            try:
                sim_result, eval_report = self.run_single_simulation(
                    user_intent=intent,
                    path_config=path_config
                )
                
                score = eval_report.overall_score if eval_report else 0
                
                # 线程安全地更新进度
                with progress_lock:
                    path_coverage_count[path_idx] += 1
                    completed_count[0] += 1
                    current = completed_count[0]
                    percent = int(100 * current / total_phase1)
                    print(f"    [{current}/{total_phase1}] ({percent}%) 路径{path_idx} ✓ (score: {score:.4f}) [路径{path_idx}已测{path_coverage_count[path_idx]}次]")
                
                return (True, sim_result, eval_report, path_idx, None)
                
            except Exception as e:
                with progress_lock:
                    completed_count[0] += 1
                    current = completed_count[0]
                    percent = int(100 * current / total_phase1)
                    print(f"    [{current}/{total_phase1}] ({percent}%) 路径{path_idx} ✗ (错误: {str(e)[:30]}...)")
                
                if self.verbose:
                    import traceback
                    traceback.print_exc()
                
                return (False, None, None, path_idx, e)
        
        # 准备所有阶段1任务
        phase1_tasks = []
        task_id = 0
        for intent, config in intent_mapping.items():
            possible_path_indices = config["possible_paths"]
            print(f"\n  Intent: {intent} (可能路径: {possible_path_indices})")
            
            for i in range(samples_per_intent):
                task_id += 1
                path_idx = random.choice(possible_path_indices)
                path_config = path_list[path_idx - 1]
                phase1_tasks.append((intent, path_idx, path_config, task_id))
        
        # 根据max_workers选择串行或并发执行
        if max_workers == 1:
            # 串行模式
            for task in phase1_tasks:
                result = run_phase1_task(task)
                if result[0]:  # success
                    results.append((result[1], result[2]))
        else:
            # 并发模式
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_task = {executor.submit(run_phase1_task, task): task for task in phase1_tasks}
                
                for future in concurrent.futures.as_completed(future_to_task):
                    result = future.result()
                    if result[0]:  # success
                        results.append((result[1], result[2]))
        
        covered_paths = set(path_coverage_count.keys())
        print(f"\n  阶段1完成: 覆盖了 {len(covered_paths)}/{len(path_list)} 条路径")
        print(f"  路径测试次数分布: {dict(sorted(path_coverage_count.items()))}")
        
        # === 阶段2: 补充不足的路径 ===
        if ensure_path_coverage:
            # 计算需要补充的路径
            all_path_indices = set(range(1, len(path_list) + 1))
            paths_need_补充 = []
            
            for path_idx in all_path_indices:
                current_count = path_coverage_count.get(path_idx, 0)
                needed = max(0, min_samples_per_path - current_count)
                if needed > 0:
                    paths_need_补充.append((path_idx, current_count, needed))
            
            if paths_need_补充:
                # 按需要补充次数排序(最需要补充的优先)
                paths_need_补充.sort(key=lambda x: x[2], reverse=True)
                total_补充 = sum(x[2] for x in paths_need_补充)
                
                print(f"\n【阶段2】补充不足{min_samples_per_path}次的路径")
                print(f"{'-'*80}")
                print(f"需要补充的路径: {len(paths_need_补充)}条")
                print(f"总共需要补充: {total_补充}次评测")
                print(f"{'-'*80}\n")
                
                # 准备所有阶段2任务
                phase2_tasks = []
                for path_idx, current_count, needed in paths_need_补充:
                    path_config = path_list[path_idx - 1]
                    
                    # 找到可以走这条路径的Intent (传入path_idx进行准确匹配)
                    suitable_intent = self._find_suitable_intent_for_path(
                        path_config, 
                        intent_mapping,
                        path_idx=path_idx  # 使用path_idx进行反向匹配
                    )
                    
                    if suitable_intent:
                        print(f"  路径{path_idx} (当前{current_count}次, 需补充{needed}次) → Intent:{suitable_intent}")
                        
                        # 为这条路径添加needed个任务
                        for i in range(needed):
                            phase2_tasks.append((path_idx, suitable_intent, path_config, i+1, needed))
                    else:
                        print(f"  路径{path_idx} (当前{current_count}次, 需补充{needed}次) ⚠️  无对应Intent,跳过")
                
                # 重置计数器用于阶段2
                completed_count[0] = 0
                
                def run_phase2_task(args):
                    """阶段2的单个任务执行函数"""
                    path_idx, suitable_intent, path_config, round_num, total_rounds = args
                    
                    try:
                        sim_result, eval_report = self.run_single_simulation(
                            user_intent=suitable_intent,
                            path_config=path_config
                        )
                        
                        score = eval_report.overall_score if eval_report else 0
                        
                        # 线程安全地更新进度
                        with progress_lock:
                            path_coverage_count[path_idx] += 1
                            completed_count[0] += 1
                            current = completed_count[0]
                            percent = int(100 * current / total_补充)
                            print(f"    [{current}/{total_补充}] ({percent}%) 路径{path_idx} 第{round_num}/{total_rounds}次 ✓ (score: {score:.4f})")
                        
                        return (True, sim_result, eval_report, path_idx, None)
                        
                    except Exception as e:
                        with progress_lock:
                            completed_count[0] += 1
                            current = completed_count[0]
                            percent = int(100 * current / total_补充)
                            print(f"    [{current}/{total_补充}] ({percent}%) 路径{path_idx} 第{round_num}/{total_rounds}次 ✗ (错误: {str(e)[:30]}...)")
                        
                        if self.verbose:
                            import traceback
                            traceback.print_exc()
                        
                        return (False, None, None, path_idx, e)
                
                # 根据max_workers选择串行或并发执行
                if max_workers == 1:
                    # 串行模式
                    for task in phase2_tasks:
                        result = run_phase2_task(task)
                        if result[0]:  # success
                            results.append((result[1], result[2]))
                else:
                    # 并发模式
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        future_to_task = {executor.submit(run_phase2_task, task): task for task in phase2_tasks}
                        
                        for future in concurrent.futures.as_completed(future_to_task):
                            result = future.result()
                            if result[0]:  # success
                                results.append((result[1], result[2]))
                
                print(f"\n  阶段2完成!")
            else:
                print(f"\n【阶段2】所有路径已满足最小测试次数要求,跳过补充")
        
        # 计算场景持续时间
        self.scenario_duration = time.time() - self.scenario_start_time
        
        # 统计最终的路径覆盖情况
        covered_paths = set(path_coverage_count.keys())
        满足要求的路径数 = sum(1 for count in path_coverage_count.values() if count >= min_samples_per_path)
        
        print(f"\n{'='*80}")
        print(f"混合评测完成!")
        print(f"{'='*80}")
        print(f"总评测数: {len(results)}")
        print(f"路径覆盖率: {len(covered_paths)}/{len(path_list)} ({100*len(covered_paths)/len(path_list):.1f}%)")
        print(f"满足最小测试次数的路径: {满足要求的路径数}/{len(path_list)} ({100*满足要求的路径数/len(path_list):.1f}%)")
        print(f"路径测试次数统计:")
        for path_idx in sorted(path_coverage_count.keys()):
            count = path_coverage_count[path_idx]
            status = "✓" if count >= min_samples_per_path else "✗"
            print(f"  路径{path_idx:2d}: {count:2d}次 {status}")
        print(f"总耗时: {self.scenario_duration:.1f}秒")
        print(f"{'='*80}\n")
        
        return results
    
    def _generate_system_info_from_path_config(self, path_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        从PathConfig生成对应的system_info
        确保生成的system_info能让规则引擎走到预期路径
        
        支持所有场景: online_education, ecommerce_refund, telecom_package, 
                  property_service, logistics_delivery, airline_refund
        
        Args:
            path_config: 路径配置字典
            
        Returns:
            Dict: 系统信息字典
        """
        classification = path_config["Classification_items"]
        scenario_id = self.scenario_id
        
        if scenario_id == "online_education":
            # 在线教育场景
            is_risk_user = path_config.get("isRiskUser")
            question_relevance = classification[1] if len(classification) > 1 and classification[1] is not None else True
            repeated_raised = classification[4] if len(classification) > 4 and classification[4] is not None else False
            
            system_info = {
                "isRiskUser": is_risk_user if is_risk_user != "none" else False,
                "CourseList": ["Python入门"] if question_relevance else [],
                "HistoricalComplaintRecords": repeated_raised,
                "QuestionTypeFor30Days": ["课程内容理解"] if repeated_raised else [],
            }
        
        elif scenario_id == "ecommerce_refund":
            # 电商退款场景
            # 字段顺序: CoreIntention, ProvidedDocument, Responsibility, RefundReasonable, EmotionStatus
            core_intention = classification[0] if len(classification) > 0 else "ReturnOrRefund"
            provided_doc = classification[1] if len(classification) > 1 else True
            responsibility = classification[2] if len(classification) > 2 else "Merchant"
            
            system_info = {
                "ShippingStatus": "Shipped" if provided_doc else "Unshipped",
                "CreditLevel": "High" if responsibility == "Merchant" else "Low",
            }
        
        elif scenario_id == "telecom_package":
            # 电信套餐场景
            # 字段顺序: ConsumptionType, ApplicationTendency, ConsumptionProfile, EmotionTag
            consumption_type = classification[0] if len(classification) > 0 else "Change"
            application_tendency = classification[1] if len(classification) > 1 else "Agree"
            
            system_info = {
                "PackageStatus": "Contracted" if consumption_type == "Change" else "NoContract",
                "Penalty": 100 if consumption_type == "Change" else 0,
            }
        
        elif scenario_id == "property_service":
            # 物业服务场景
            # 字段顺序: CoreIntention, EmotionTag, RepairItemCategory, RelatedScope, EmergencyLevel
            core_intention = classification[0] if len(classification) > 0 else "Repair"
            related_scope = classification[3] if len(classification) > 3 else "Personal"
            
            system_info = {
                "HouseStatus": "Occupied" if related_scope == "Personal" else "Rented",
                "FeePaymentStatus": "Settled" if core_intention != "Payment" else "Unpaid",
            }
        
        elif scenario_id == "logistics_delivery":
            # 物流配送场景
            # 字段顺序: RiskStatus, InfoCompleteness, UserIntention, EmotionalState, EmergencyLevel, ComplaintValidity
            risk_status = classification[0] if len(classification) > 0 else "Safe"
            emergency_level = classification[4] if len(classification) > 4 else "Normal"
            
            system_info = {
                "orderStatus": "Undelivered" if risk_status == "Safe" else "AtRisk",
                "hasInsurance": emergency_level == "Urgent",
            }
        
        elif scenario_id == "airline_refund":
            # 航空改签退票场景
            # 字段顺序: CoreDemand, ChangeReason, UserEmotion, DocumentValidity, IsInfoComplete
            doc_validity = classification[3] if len(classification) > 3 else "Valid"
            core_demand = classification[0] if len(classification) > 0 else "RescheduleOrRefund"
            
            system_info = {
                "memberLevel": "VIP" if doc_validity == "Valid" else "Regular",
                "hasInsurance": core_demand == "RescheduleOrRefund",
            }
        
        else:
            # 默认空值
            system_info = {}
        
        return system_info
    
    def _find_suitable_intent_for_path(
        self, 
        path_config: Dict[str, Any],
        intent_mapping: Dict[str, Dict],
        path_idx: int = None
    ) -> Optional[str]:
        """
        为给定路径配置找到合适的Intent
        
        新逻辑: 直接使用intent_mapping中的possible_paths进行反向匹配
        这是最准确的匹配方式,避免了场景特定的字段解析
        
        Args:
            path_config: 路径配置
            intent_mapping: Intent映射关系
            path_idx: 路径索引(从1开始),如果提供则优先使用
            
        Returns:
            str: 合适的Intent名称,如果没有则返回None
        """
        # 如果提供了path_idx,直接使用possible_paths反向匹配
        if path_idx is not None:
            import random
            # 收集所有包含该路径的intent
            candidate_intents = []
            for intent, config in intent_mapping.items():
                possible_paths = config.get("possible_paths", [])
                if path_idx in possible_paths:
                    candidate_intents.append(intent)
            
            # 从候选intent中随机选择一个
            if candidate_intents:
                return random.choice(candidate_intents)
            return None
        
        # # 【兼容旧逻辑】如果没有path_idx,使用原有的条件匹配(仅适用online_education场景)
        # classification = path_config["Classification_items"]
        # finals = path_config["final_output"]
        
        # # 提取关键条件(仅适用于online_education场景)
        # regarding_refund = classification[5] if len(classification) > 5 else None
        # emotion = classification[2] if len(classification) > 2 else None
        
        # # 根据条件匹配Intent
        # for intent, config in intent_mapping.items():
        #     # 检查required_conditions
        #     required = config.get("required_conditions", {})
        #     if required:
        #         if regarding_refund != required.get("RegardingRefund"):
        #             continue
            
        #     # 检查impossible_conditions
        #     impossible = config.get("impossible_conditions", {})
        #     if impossible:
        #         if regarding_refund == impossible.get("RegardingRefund", None):
        #             continue
        #         if emotion == impossible.get("EmotionTendency", None):
        #             continue
            
        #     # 如果通过所有检查,这个Intent可用
        #     return intent
        
        # return None
    
    def _generate_summary(self) -> Dict[str, Any]:
        """生成汇总报告"""
        if not self.evaluation_reports:
            return {
                "model_name": self.model_name,
                "scenario_id": self.scenario_id,
                "eval_mode": self.eval_mode,
                "total_simulations": 0,
                "overall_avg_score": 0.0,
                "overall_avg_metric_scores": {},
                "by_intent": {},
                "by_adversarial_intensity": {},
                "by_turn": {},
                "scenario_duration_seconds": 0.0,
            }
        
        intent_stats = {}
        intensity_stats = {}
        turn_stats = {}  # 按轮次统计
        

        # 按照意图、强度和轮次统计分数和指标
        for idx, report in enumerate(self.evaluation_reports):
            # 获取对应的simulation_result以得到轮次信息
            sim_result = None
            if idx < len(self.simulation_results):
                sim_result = self.simulation_results[idx]
            
            # 按意图统计
            intent = report.user_intent
            if intent not in intent_stats:
                intent_stats[intent] = {
                    "count": 0, 
                    "overall_scores": [],
                    "metric_scores": {},  # 记录每个指标的分数
                    "chat_quality_dimensions": {}  # 记录话术质量五维度
                }
            intent_stats[intent]["count"] += 1
            intent_stats[intent]["overall_scores"].append(report.overall_score)
            
            # 收集每个指标的分数
            for metric_score in report.metric_scores:
                metric_name = metric_score.metric_name
                if metric_name not in intent_stats[intent]["metric_scores"]:
                    intent_stats[intent]["metric_scores"][metric_name] = []
                intent_stats[intent]["metric_scores"][metric_name].append(metric_score.score)
                
                # 如果是chat_quality指标,额外提取五维度数据
                if metric_name == "chat_quality" and hasattr(metric_score, 'details') and metric_score.details:
                    avg_dims = metric_score.details.get("average_dimensions", {})
                    for dim_name, dim_value in avg_dims.items():
                        if dim_name not in intent_stats[intent]["chat_quality_dimensions"]:
                            intent_stats[intent]["chat_quality_dimensions"][dim_name] = []
                        intent_stats[intent]["chat_quality_dimensions"][dim_name].append(dim_value)
            
            # 按强度统计
            intensity = report.adversarial_intensity
            if intensity not in intensity_stats:
                intensity_stats[intensity] = {
                    "count": 0, 
                    "overall_scores": [],
                    "metric_scores": {},  # 记录每个指标的分数
                    "chat_quality_dimensions": {}  # 记录话术质量五维度
                }
            intensity_stats[intensity]["count"] += 1
            intensity_stats[intensity]["overall_scores"].append(report.overall_score)
            
            # 收集每个指标的分数
            for metric_score in report.metric_scores:
                metric_name = metric_score.metric_name
                if metric_name not in intensity_stats[intensity]["metric_scores"]:
                    intensity_stats[intensity]["metric_scores"][metric_name] = []
                intensity_stats[intensity]["metric_scores"][metric_name].append(metric_score.score)
                
                # 如果是chat_quality指标,额外提取五维度数据
                if metric_name == "chat_quality" and hasattr(metric_score, 'details') and metric_score.details:
                    avg_dims = metric_score.details.get("average_dimensions", {})
                    for dim_name, dim_value in avg_dims.items():
                        if dim_name not in intensity_stats[intensity]["chat_quality_dimensions"]:
                            intensity_stats[intensity]["chat_quality_dimensions"][dim_name] = []
                        intensity_stats[intensity]["chat_quality_dimensions"][dim_name].append(dim_value)
            
            # 按评测轮次统计 - 关键修改: 按照裁判评测的具体轮次分桶
            # 从metric_scores的details中获取evaluated_turns信息
            evaluated_turns = []
            if report.metric_scores and len(report.metric_scores) > 0:
                first_metric = report.metric_scores[0]
                if hasattr(first_metric, 'details') and first_metric.details:
                    evaluated_turns = first_metric.details.get('evaluated_turns', [])
            
            # 如果没有evaluated_turns信息,使用对话总长度作为fallback
            if not evaluated_turns and sim_result:
                evaluated_turns = [sim_result.dialogue_length - 1] if sim_result.dialogue_length > 0 else []
            
            # 对每个评测轮次,将分数归到对应的桶
            # 桶规则: 第1轮->桶1, 第5轮->桶5, 第10轮->桶10, 第15轮->桶15
            # 如果是最后一轮但不是标准轮次,根据对话长度分配桶
            for turn_idx in evaluated_turns:
                turn_num = turn_idx + 1  # 转换为1-based轮次号
                
                # 确定应该放入哪个桶
                if turn_num == 1 or turn_idx == 0:
                    turn_bucket = 1
                elif turn_num == 5 or turn_idx == 4:
                    turn_bucket = 5
                elif turn_num == 10 or turn_idx == 9:
                    turn_bucket = 10
                elif turn_num == 15 or turn_idx == 14:
                    turn_bucket = 15
                else:
                    # 最后一轮但不是标准评测轮次,根据对话长度分桶
                    if sim_result:
                        if sim_result.dialogue_length <= 5:
                            turn_bucket = 5
                        elif sim_result.dialogue_length <= 10:
                            turn_bucket = 10
                        else:
                            turn_bucket = 15
                    else:
                        continue
                
                if turn_bucket not in turn_stats:
                    turn_stats[turn_bucket] = {
                        "count": 0,
                        "overall_scores": [],
                        "metric_scores": {},
                        "chat_quality_dimensions": {}  # 记录话术质量五维度
                    }
                turn_stats[turn_bucket]["count"] += 1
                turn_stats[turn_bucket]["overall_scores"].append(report.overall_score)
                
                # 收集每个指标的分数
                for metric_score in report.metric_scores:
                    metric_name = metric_score.metric_name
                    if metric_name not in turn_stats[turn_bucket]["metric_scores"]:
                        turn_stats[turn_bucket]["metric_scores"][metric_name] = []
                    turn_stats[turn_bucket]["metric_scores"][metric_name].append(metric_score.score)
                    
                    # 如果是chat_quality指标,额外提取五维度数据
                    if metric_name == "chat_quality" and hasattr(metric_score, 'details') and metric_score.details:
                        avg_dims = metric_score.details.get("average_dimensions", {})
                        for dim_name, dim_value in avg_dims.items():
                            if dim_name not in turn_stats[turn_bucket]["chat_quality_dimensions"]:
                                turn_stats[turn_bucket]["chat_quality_dimensions"][dim_name] = []
                            turn_stats[turn_bucket]["chat_quality_dimensions"][dim_name].append(dim_value)
        
        # 计算平均分（总体分 + 每个指标分）
        for key in intent_stats:
            overall_scores = intent_stats[key]["overall_scores"]
            intent_stats[key]["avg_overall_score"] = sum(overall_scores) / len(overall_scores) if overall_scores else 0.0
            
            # 计算每个指标的平均分
            intent_stats[key]["avg_metric_scores"] = {}
            for metric_name, scores in intent_stats[key]["metric_scores"].items():
                intent_stats[key]["avg_metric_scores"][metric_name] = sum(scores) / len(scores) if scores else 0.0
            
            # 计算话术质量五维度平均分
            intent_stats[key]["avg_chat_quality_dimensions"] = {}
            for dim_name, dim_values in intent_stats[key]["chat_quality_dimensions"].items():
                intent_stats[key]["avg_chat_quality_dimensions"][dim_name] = sum(dim_values) / len(dim_values) if dim_values else 0.0
            
            # 计算逻辑得分
            if 'classification_accuracy' in intent_stats[key]["avg_metric_scores"] and \
               'path_correctness' in intent_stats[key]["avg_metric_scores"] and \
               'finals_correctness' in intent_stats[key]["avg_metric_scores"]:
                logic_score = (
                    intent_stats[key]["avg_metric_scores"]['classification_accuracy'] * 0.4 +
                    intent_stats[key]["avg_metric_scores"]['path_correctness'] * 0.4 +
                    intent_stats[key]["avg_metric_scores"]['finals_correctness'] * 0.2
                ) / 1.0
                intent_stats[key]["avg_metric_scores"]['logic_ability'] = logic_score
            
            # 移除原始数据列表，只保留统计结果
            intent_stats[key].pop("overall_scores", None)
            intent_stats[key].pop("metric_scores", None)
            intent_stats[key].pop("chat_quality_dimensions", None)
        
        for key in intensity_stats:
            overall_scores = intensity_stats[key]["overall_scores"]
            intensity_stats[key]["avg_overall_score"] = sum(overall_scores) / len(overall_scores) if overall_scores else 0.0
            
            # 计算每个指标的平均分
            intensity_stats[key]["avg_metric_scores"] = {}
            for metric_name, scores in intensity_stats[key]["metric_scores"].items():
                intensity_stats[key]["avg_metric_scores"][metric_name] = sum(scores) / len(scores) if scores else 0.0
            
            # 计算话术质量五维度平均分
            intensity_stats[key]["avg_chat_quality_dimensions"] = {}
            for dim_name, dim_values in intensity_stats[key]["chat_quality_dimensions"].items():
                intensity_stats[key]["avg_chat_quality_dimensions"][dim_name] = sum(dim_values) / len(dim_values) if dim_values else 0.0
            
            # 计算逻辑得分
            if 'classification_accuracy' in intensity_stats[key]["avg_metric_scores"] and \
               'path_correctness' in intensity_stats[key]["avg_metric_scores"] and \
               'finals_correctness' in intensity_stats[key]["avg_metric_scores"]:
                logic_score = (
                    intensity_stats[key]["avg_metric_scores"]['classification_accuracy'] * 0.4 +
                    intensity_stats[key]["avg_metric_scores"]['path_correctness'] * 0.4 +
                    intensity_stats[key]["avg_metric_scores"]['finals_correctness'] * 0.2
                ) / 1.0
                intensity_stats[key]["avg_metric_scores"]['logic_ability'] = logic_score
            
            # 移除原始数据列表，只保留统计结果
            intensity_stats[key].pop("overall_scores", None)
            intensity_stats[key].pop("metric_scores", None)
            intensity_stats[key].pop("chat_quality_dimensions", None)
        
        all_scores = [r.overall_score for r in self.evaluation_reports]
        overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0.0
        
        # 计算全局指标平均分
        global_metric_scores = {}
        global_chat_quality_dimensions = {}
        for report in self.evaluation_reports:
            for metric_score in report.metric_scores:
                metric_name = metric_score.metric_name
                if metric_name not in global_metric_scores:
                    global_metric_scores[metric_name] = []
                global_metric_scores[metric_name].append(metric_score.score)
                
                # 如果是chat_quality指标,额外提取五维度数据
                if metric_name == "chat_quality" and hasattr(metric_score, 'details') and metric_score.details:
                    avg_dims = metric_score.details.get("average_dimensions", {})
                    for dim_name, dim_value in avg_dims.items():
                        if dim_name not in global_chat_quality_dimensions:
                            global_chat_quality_dimensions[dim_name] = []
                        global_chat_quality_dimensions[dim_name].append(dim_value)
        
        global_avg_metric_scores = {}
        for metric_name, scores in global_metric_scores.items():
            global_avg_metric_scores[metric_name] = sum(scores) / len(scores) if scores else 0.0
        
        # 计算全局话术质量五维度平均分
        global_avg_chat_quality_dimensions = {}
        for dim_name, dim_values in global_chat_quality_dimensions.items():
            global_avg_chat_quality_dimensions[dim_name] = sum(dim_values) / len(dim_values) if dim_values else 0.0
        
        # 计算逻辑得分 = (0.4*classification + 0.4*path + 0.2*finals) / 1.0
        logic_score = 0.0
        if 'classification_accuracy' in global_avg_metric_scores and \
           'path_correctness' in global_avg_metric_scores and \
           'finals_correctness' in global_avg_metric_scores:
            logic_score = (
                global_avg_metric_scores['classification_accuracy'] * 0.4 +
                global_avg_metric_scores['path_correctness'] * 0.4 +
                global_avg_metric_scores['finals_correctness'] * 0.2
            ) / 1.0
            global_avg_metric_scores['logic_ability'] = logic_score
        
        # 计算按轮次的平均分
        for turn_count in turn_stats:
            overall_scores = turn_stats[turn_count]["overall_scores"]
            turn_stats[turn_count]["avg_overall_score"] = sum(overall_scores) / len(overall_scores) if overall_scores else 0.0
            
            # 计算每个指标的平均分
            turn_stats[turn_count]["avg_metric_scores"] = {}
            for metric_name, scores in turn_stats[turn_count]["metric_scores"].items():
                turn_stats[turn_count]["avg_metric_scores"][metric_name] = sum(scores) / len(scores) if scores else 0.0
            
            # 计算话术质量五维度平均分
            turn_stats[turn_count]["avg_chat_quality_dimensions"] = {}
            for dim_name, dim_values in turn_stats[turn_count]["chat_quality_dimensions"].items():
                turn_stats[turn_count]["avg_chat_quality_dimensions"][dim_name] = sum(dim_values) / len(dim_values) if dim_values else 0.0
            
            # 计算逻辑得分
            if 'classification_accuracy' in turn_stats[turn_count]["avg_metric_scores"] and \
               'path_correctness' in turn_stats[turn_count]["avg_metric_scores"] and \
               'finals_correctness' in turn_stats[turn_count]["avg_metric_scores"]:
                logic_score = (
                    turn_stats[turn_count]["avg_metric_scores"]['classification_accuracy'] * 0.4 +
                    turn_stats[turn_count]["avg_metric_scores"]['path_correctness'] * 0.4 +
                    turn_stats[turn_count]["avg_metric_scores"]['finals_correctness'] * 0.2
                ) / 1.0
                turn_stats[turn_count]["avg_metric_scores"]['logic_ability'] = logic_score
            
            # 移除原始数据列表，只保留统计结果
            turn_stats[turn_count].pop("overall_scores", None)
            turn_stats[turn_count].pop("metric_scores", None)
            turn_stats[turn_count].pop("chat_quality_dimensions", None)
        
        return {
            "model_name": self.model_name,
            "scenario_id": self.scenario_id,
            "eval_mode": self.eval_mode,
            "total_simulations": len(self.evaluation_reports),
            "scenario_duration_seconds": self.scenario_duration,
            "overall_avg_score": overall_avg,
            "overall_avg_metric_scores": global_avg_metric_scores,
            "overall_avg_chat_quality_dimensions": global_avg_chat_quality_dimensions,
            "by_intent": intent_stats,
            "by_adversarial_intensity": intensity_stats,
            "by_turn": turn_stats,
        }
    
    def print_summary(self):
        """打印汇总报告"""
        summary = self._generate_summary()
        
        print("\n" + "=" * 80)
        print("评测汇总")
        print("=" * 80)
        
        print(f"\n模型: {summary.get('model_name', 'N/A')}")
        print(f"场景: {summary.get('scenario_id', 'N/A')}")
        print(f"评测模式: {summary.get('eval_mode', 'N/A')}")
        print(f"总模拟数: {summary.get('total_simulations', 0)}")
        
        # 显示场景用时
        duration = summary.get('scenario_duration_seconds', 0.0)
        if duration > 0:
            print(f"场景总用时: {duration:.2f} 秒 ({duration/60:.2f} 分钟)")
        
        print(f"总体平均分: {summary.get('overall_avg_score', 0.0):.4f}")
        
        # 打印全局指标分数
        if 'overall_avg_metric_scores' in summary and summary['overall_avg_metric_scores']:
            print(f"\n全局指标得分:")
            for metric_name, score in summary['overall_avg_metric_scores'].items():
                if metric_name != "turn_level_evaluations":  # 跳过元数据指标
                    print(f"  {metric_name}: {score:.4f}")
        
        if summary.get('by_intent'):
            print(f"\n按用户意图统计:")
            for intent, stats in summary['by_intent'].items():
                print(f"  【{intent}】: {stats['avg_overall_score']:.4f} ({stats['count']}次)")
                if 'avg_metric_scores' in stats:
                    for metric_name, score in stats['avg_metric_scores'].items():
                        if metric_name != "turn_level_evaluations":
                            print(f"    - {metric_name}: {score:.4f}")
        
        if summary.get('by_adversarial_intensity'):
            print(f"\n按对抗强度统计:")
            for intensity, stats in summary['by_adversarial_intensity'].items():
                print(f"  【{intensity}】: {stats['avg_overall_score']:.4f} ({stats['count']}次)")
                if 'avg_metric_scores' in stats:
                    for metric_name, score in stats['avg_metric_scores'].items():
                        if metric_name != "turn_level_evaluations":
                            print(f"    - {metric_name}: {score:.4f}")
        
        if summary.get('by_turn'):
            print(f"\n按评测轮次统计:")
            # 按评测轮次桶排序显示 (1, 5, 10, 15)
            for turn_bucket in sorted(summary['by_turn'].keys()):
                stats = summary['by_turn'][turn_bucket]
                # 显示评测轮次标签
                if turn_bucket == 1:
                    turn_label = "第1轮"
                elif turn_bucket == 5:
                    turn_label = "第5轮"
                elif turn_bucket == 10:
                    turn_label = "第10轮"
                else:  # 15
                    turn_label = "第15轮"
                print(f"  【{turn_label}】: {stats['avg_overall_score']:.4f} ({stats['count']}次评测)")
                if 'avg_metric_scores' in stats:
                    for metric_name, score in stats['avg_metric_scores'].items():
                        if metric_name != "turn_level_evaluations":
                            print(f"    - {metric_name}: {score:.4f}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="支持LLM的多轮对话评测框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "--scenario",
        default="online_education",
        help="场景ID (✓已完成: online_education, ecommerce_refund, telecom_package, property_service, logistics_delivery, airline_refund)",
    )
    parser.add_argument(
        "--model",
        default="test_model",
        help="模型名称",
    )
    parser.add_argument(
        "--output",
        default="./results",
        help="输出目录",
    )
    parser.add_argument(
        "--eval-mode",
        default="voting",
        choices=["vllm", "api", "voting"],
        help="评测模式 (vllm本地/api API模式/voting多模型投票)",
    )
    parser.add_argument(
        "--user-model-url",
        default="http://localhost:8000",
        help="用户模型服务URL (固定本地vLLM)",
    )
    parser.add_argument(
        "--agent-model-url",
        default="http://localhost:8001",
        help="客服模型服务URL (本地vLLM时使用)",
    )
    parser.add_argument(
        "--agent-model-port",
        type=int,
        default=8001,
        help="客服模型服务端口 (本地vLLM时使用,投票模式时会动态设置)",
    )
    parser.add_argument(
        "--judge-model-url",
        default="http://localhost:8002",
        help="评判模型服务URL (固定本地vLLM)",
    )
    parser.add_argument(
        "--api-key",
        help="API密钥 (agent为api模式时需要)",
    )
    parser.add_argument(
        "--agent-model-type",
        default="vllm",
        choices=["vllm", "api"],
        help="agent模型类型 (vllm本地/api API) - user和judge必须本地",
    )
    parser.add_argument(
        "--agent-model-name",
        default="gpt-3.5-turbo",
        help="agent为API模式时的模型名称 (default: gpt-3.5-turbo)",
    )
    parser.add_argument(
        "--intents",
        nargs="+",
        help="指定要测试的用户意图 (如不指定则自动测试所有intents)",
    )
    parser.add_argument(
        "--num-users",
        type=int,
        default=1,
        help="每个用户意图的用户数",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="最大对话轮次",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=64,
        help="并发数 (default: 1串行, 推荐: 4-8并发). 注意:需确保模型服务器能支持并发请求",
    )
    parser.add_argument(
        "--evaluation-strategy",
        default="mixed",
        choices=["intent_based", "mixed", "path_coverage"],
        help="评测策略: intent_based(按Intent均衡), mixed(Intent均衡+路径补充), path_coverage(全路径覆盖)",
    )
    parser.add_argument(
        "--samples-per-intent",
        type=int,
        default=3,
        help="混合评测模式下,每个Intent的采样数 (仅在--evaluation-strategy=mixed时使用)",
    )
    parser.add_argument(
        "--min-samples-per-path",
        type=int,
        default=5,
        help="每条路径的最小测试次数 (仅在--evaluation-strategy=mixed或path_coverage时使用)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="打印详细日志",
    )
    parser.add_argument(
        "--judge-models",
        help="投票模式下Judge模型名称列表,逗号分隔 (例如: gpt-4.1,claude-3.5-sonnet,gemini-pro)",
    )
    parser.add_argument(
        "--api-keys",
        help="投票模式下对应模型的API密钥列表,逗号分隔",
    )
    parser.add_argument(
        "--api-urls",
        help="投票模式下对应模型的API地址列表,逗号分隔",
    )
    
    args = parser.parse_args()
    
    # 【投票模式】处理多模型参数
    if args.eval_mode == "voting":
        if not args.judge_models or not args.api_keys or not args.api_urls:
            print("错误: 投票模式需要提供 --judge-models, --api-keys, 和 --api-urls")
            sys.exit(1)
        
        # 解析模型、密钥、URL列表
        judge_models_list = [m.strip() for m in args.judge_models.split(',')]
        api_keys_list = [k.strip() for k in args.api_keys.split(',')]
        api_urls_list = [u.strip() for u in args.api_urls.split(',')]
        
        if not (len(judge_models_list) == len(api_keys_list) == len(api_urls_list)):
            print("错误: judge-models, api-keys, api-urls 的数量必须相同")
            sys.exit(1)
        
        # 创建多个judge，使用 MultiModelVotingJudge
        from framework.llm_integration import MultiModelVotingJudge
        
        judges = {}
        print(f"\n【投票模式】开始创建 {len(judge_models_list)} 个 Judge 模型...")
        print(f"  Judge 模型列表: {judge_models_list}")
        print(f"  API URLs: {api_urls_list}")
        
        for idx, (model_name, api_key, api_url) in enumerate(zip(judge_models_list, api_keys_list, api_urls_list)):
            try:
                print(f"\n  【Judge-{idx}】创建 {model_name}")
                print(f"    - API URL: {api_url}")
                print(f"    - API Key: {api_key[:20]}..." if len(api_key) > 20 else f"    - API Key: {api_key}")
                
                llm_client = get_llm_client(
                    "openai_api",
                    api_key=api_key,
                    base_url=api_url,
                    model_name=model_name,
                )
                judges[model_name] = LLMJudge(
                    llm_client=llm_client,
                    temperature=0.3,
                    max_tokens=1024,
                )
                print(f"    ✓ 创建成功")
            except Exception as e:
                print(f"    ✗ 创建失败: {e}")
                raise
        
        print(f"\n【投票模式】共成功创建 {len(judges)} 个 Judge 模型: {list(judges.keys())}")
        
        voting_judge = MultiModelVotingJudge(judges)
        # args.model = "voting_" + "_".join(judge_models_list)[:30]  # 简化模型名
        # 模型名有作为参数传入
        # 【投票模式特殊处理】如果agent是本地vLLM，根据port动态构建URL
        if args.agent_model_type == "vllm":
            args.agent_model_url = f"http://localhost:{args.agent_model_port}"
    else:
        voting_judge = None
    
    # 创建评测管道
    pipeline = LLMEvaluationPipeline(
        scenario_id=args.scenario,
        model_name=args.model,
        output_dir=args.output,
        eval_mode=args.eval_mode,
        user_model_url=args.user_model_url,
        agent_model_url=args.agent_model_url,
        judge_model_url=args.judge_model_url,
        api_key=args.api_key,
        agent_model_type=args.agent_model_type,
        agent_model_name=args.agent_model_name,
        max_turns=args.max_turns,
        verbose=args.verbose,
    )
    
    # 【投票模式】设置投票judge
    if args.eval_mode == "voting":
        pipeline.judge_model = voting_judge
    
    # 运行批量模拟
    print(f"\n开始评测: {args.model} / {args.scenario}")
    print(f"评测模式: {args.eval_mode}")
    print(f"评测策略: {args.evaluation_strategy}")
    print(f"输出目录: {args.output}")
    if args.intents:
        print(f"指定的intents: {args.intents}")
    else:
        print(f"未指定intents，将自动测试所有intents")
    print(f"每个intent的用户数: {args.num_users}")
    print(f"最大对话轮数: {args.max_turns}")
    if args.evaluation_strategy in ["mixed", "path_coverage"]:
        print(f"每个Intent采样数: {args.samples_per_intent}")
        print(f"每条路径最小测试次数: {args.min_samples_per_path}")
    
    # 根据评测策略选择运行方法
    if args.evaluation_strategy == "mixed":
        # 混合评测策略: Intent均衡 + 路径全覆盖
        results = pipeline.run_mixed_evaluation(
            samples_per_intent=args.samples_per_intent,
            ensure_path_coverage=True,
            min_samples_per_path=args.min_samples_per_path,
            max_workers=args.max_workers,  # 传递并发数
        )
    elif args.evaluation_strategy == "path_coverage":
        # 纯路径覆盖策略
        results = pipeline.run_mixed_evaluation(
            samples_per_intent=1,  # 每个Intent只采样1次
            ensure_path_coverage=True,  # 确保所有路径都覆盖
            min_samples_per_path=args.min_samples_per_path,
            max_workers=args.max_workers,  # 传递并发数
        )
    else:
        # 传统的Intent均衡策略
        results = pipeline.run_batch_simulations(
            user_intents=args.intents,
            num_users_per_intent=args.num_users,
            max_workers=args.max_workers,
        )
    
    print(f"\n✓ 完成 {len(results)} 次模拟")
    
    # 保存结果
    file_paths = pipeline.save_results()
    print(f"\n✓ 结果已保存:")
    for file_type, path in file_paths.items():
        print(f"  - {file_type}: {path}")
    
    # 打印汇总
    pipeline.print_summary()
    
    print("\n✓ 评测完成！")


if __name__ == "__main__":
    main()
