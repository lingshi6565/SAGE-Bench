#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM部署配置
LLM Deployment Configuration

定义vLLM服务器和其他LLM的配置参数
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class VLLMServerConfig:
    """vLLM服务器配置"""
    
    model_path: str                 # 模型路径
    port: int = 8000               # 服务端口
    host: str = "0.0.0.0"          # 绑定地址
    tensor_parallel_size: int = 1  # 张量并行度
    pipeline_parallel_size: int = 1 # 管道并行度
    gpu_memory_utilization: float = 0.9  # GPU内存使用率
    max_model_len: Optional[int] = None  # 最大模型长度
    dtype: str = "auto"            # 数据类型
    seed: int = 42                 # 随机种子
    max_num_seqs: int = 256         # 最大序列数（batch处理）
    enable_prefix_caching: bool = True  # 启用前缀缓存加速
    
    # 其他参数
    extra_args: Dict[str, Any] = None
    
    def to_command_args(self) -> list:
        """转换为命令行参数"""
        args = [
            "python", "-m", "vllm.entrypoints.openai.api_server",
            "--model", self.model_path,
            "--port", str(self.port),
            "--host", self.host,
            "--tensor-parallel-size", str(self.tensor_parallel_size),
            "--pipeline-parallel-size", str(self.pipeline_parallel_size),
            "--gpu-memory-utilization", str(self.gpu_memory_utilization),
            "--dtype", self.dtype,
            "--seed", str(self.seed),
            "--max-num-seqs", str(self.max_num_seqs),
        ]
        
        if self.enable_prefix_caching:
            args.append("--enable-prefix-caching")
        
        if self.max_model_len:
            args.extend(["--max-model-len", str(self.max_model_len)])
        
        if self.extra_args:
            for key, value in self.extra_args.items():
                args.append(f"--{key}")
                if value is not True:
                    args.append(str(value))
        
        return args


@dataclass
class LLMClientConfig:
    """LLM客户端配置"""
    
    client_type: str                # 客户端类型: "vllm_local", "vllm_chat", "openai_api"
    base_url: Optional[str] = None  # 服务器URL (对于本地vLLM)
    api_key: Optional[str] = None   # API密钥 (对于OpenAI)
    model_name: str = "default"     # 模型名称
    timeout: int = 300              # 超时时间
    max_retries: int = 3            # 最大重试次数
    temperature: float = 0.7        # 采样温度
    top_p: float = 0.95             # Top-p采样
    max_tokens: int = 1024          # 最大生成token数
    batch_size: int = 1             # 批处理大小（用于并行评测）


# ==================== 预设配置 ====================

# 在线教育场景的用户模型配置
ONLINE_EDUCATION_USER_MODEL_CONFIG = LLMClientConfig(
    client_type="vllm_chat",
    base_url="http://localhost:8000",
    model_name="user_model",
    temperature=0.8,  # 稍微高一些以增加多样性
    max_tokens=512,
)

# 在线教育场景的客服模型配置
ONLINE_EDUCATION_AGENT_MODEL_CONFIG = LLMClientConfig(
    client_type="vllm_chat",
    base_url="http://localhost:8001",
    model_name="agent_model",
    temperature=0.3,  # 较低温度以获得一致的行为
    max_tokens=1024,
)

# 在线教育场景的Judge模型配置
ONLINE_EDUCATION_JUDGE_CONFIG = LLMClientConfig(
    client_type="vllm_chat",
    base_url="http://localhost:8002",
    model_name="judge_model",
    temperature=0.2,  # 最低温度以确保评估的一致性
    max_tokens=1024,
)

# ==================== vLLM服务器配置 ====================

# ========== 默认配置 (推荐用于4卡GPU) ==========
# 用户模型服务器配置 (1张GPU)
USER_MODEL_VLLM_SERVER_CONFIG = VLLMServerConfig(
    model_path="Qwen/Qwen2.5-14B-Instruct",
    port=8000,
    tensor_parallel_size=1,
    gpu_memory_utilization=0.8,
    max_num_seqs=256,
    enable_prefix_caching=True,
)

# 客服模型服务器配置 (1张GPU)
AGENT_MODEL_VLLM_SERVER_CONFIG = VLLMServerConfig(
    model_path="Qwen/Qwen2.5-32B-Instruct",
    port=8001,
    tensor_parallel_size=1,
    gpu_memory_utilization=0.8,
    max_num_seqs=256,
    enable_prefix_caching=True,
)

# 评判模型服务器配置 (1张GPU)
JUDGE_MODEL_VLLM_SERVER_CONFIG = VLLMServerConfig(
    model_path="Qwen/Qwen2.5-14B-Instruct",
    port=8002,
    tensor_parallel_size=1,
    gpu_memory_utilization=0.8,
    max_num_seqs=256,
    enable_prefix_caching=True,
)

# ========== 8卡GPU配置 ==========
# 每个模型使用2张GPU (tensor parallel)
USER_MODEL_VLLM_SERVER_CONFIG_8GPU = VLLMServerConfig(
    model_path="Qwen/Qwen2.5-14B-Instruct",
    port=8000,
    tensor_parallel_size=2,
    gpu_memory_utilization=0.85,
    max_num_seqs=512,
    enable_prefix_caching=True,
)

AGENT_MODEL_VLLM_SERVER_CONFIG_8GPU = VLLMServerConfig(
    model_path="Qwen/Qwen2.5-32B-Instruct",
    port=8001,
    tensor_parallel_size=2,
    gpu_memory_utilization=0.85,
    max_num_seqs=512,
    enable_prefix_caching=True,
)

JUDGE_MODEL_VLLM_SERVER_CONFIG_8GPU = VLLMServerConfig(
    model_path="Qwen/Qwen2.5-14B-Instruct",
    port=8002,
    tensor_parallel_size=2,
    gpu_memory_utilization=0.85,
    max_num_seqs=512,
    enable_prefix_caching=True,
)

# ==================== API配置示例 ====================

# OpenAI API配置
OPENAI_API_CONFIG = LLMClientConfig(
    client_type="openai_api",
    base_url="https://api.openai.com/v1",
    api_key="sk-xxx",  # 需要填入实际的API密钥
    model_name="gpt-3.5-turbo",
)


def get_deployment_config(scenario_id: str, role: str):
    """
    获取部署配置
    
    Args:
        scenario_id: 场景ID (如"online_education")
        role: 角色 ("user_model", "agent_model", "judge")
        
    Returns:
        LLMClientConfig: 配置对象
    """
    if scenario_id == "online_education":
        if role == "user_model":
            return ONLINE_EDUCATION_USER_MODEL_CONFIG
        elif role == "agent_model":
            return ONLINE_EDUCATION_AGENT_MODEL_CONFIG
        elif role == "judge":
            return ONLINE_EDUCATION_JUDGE_CONFIG
    
    raise ValueError(f"Unknown scenario_id or role: {scenario_id}/{role}")


def get_vllm_server_config(num_gpus: int = 4, role: str = "user"):
    """
    根据GPU数量获取vLLM服务器配置
    
    Args:
        num_gpus: 可用GPU数量 (4 或 8)
        role: 角色 ("user", "agent", "judge")
        
    Returns:
        VLLMServerConfig: 服务器配置
        
    Example:
        # 4卡GPU配置
        user_config = get_vllm_server_config(num_gpus=4, role="user")
        
        # 8卡GPU配置
        agent_config = get_vllm_server_config(num_gpus=8, role="agent")
    """
    if num_gpus == 4:
        # 4卡：每个模型独占1张GPU
        if role == "user":
            return USER_MODEL_VLLM_SERVER_CONFIG
        elif role == "agent":
            return AGENT_MODEL_VLLM_SERVER_CONFIG
        elif role == "judge":
            return JUDGE_MODEL_VLLM_SERVER_CONFIG
    elif num_gpus == 8:
        # 8卡：每个模型使用2张GPU (tensor parallel)
        if role == "user":
            return USER_MODEL_VLLM_SERVER_CONFIG_8GPU
        elif role == "agent":
            return AGENT_MODEL_VLLM_SERVER_CONFIG_8GPU
        elif role == "judge":
            return JUDGE_MODEL_VLLM_SERVER_CONFIG_8GPU
    else:
        raise ValueError(f"Unsupported number of GPUs: {num_gpus}. Use 4 or 8.")
