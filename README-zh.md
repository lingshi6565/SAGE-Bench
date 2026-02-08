# SAGE-Bench客服场景多轮对话评测框架 - 使用指南

## 📋 目录

- [简介](#简介)
- [GPU资源分配策略](#gpu资源分配策略)
- [快速开始](#快速开始)
- [命令详解](#命令详解)
  - [cleanup-gpu - GPU清理](#cleanup-gpu---gpu清理)
  - [start_servers - 启动服务](#start_servers---启动服务)
  - [eval-server - vLLM评测](#eval-server---vllm评测)
  - [eval-api - API评测](#eval-api---api评测)
  - [eval-voting - 多模型投票评测](#eval-voting---多模型投票评测)
  - [re-score - 重新评分](#re-score---重新评分)
- [评测策略](#评测策略)
- [常见问题](#常见问题)
- [高级用法](#高级用法)

---

## 简介

本评测框架是一个生产级别的多轮对话评测系统,支持:

- ✅ **多场景评测**: 在线教育、电商退款、电信套餐、物业服务、航空改签、物流配送
- ✅ **灵活部署**: 支持本地vLLM部署和远程API调用
- ✅ **智能评测**: 代码计算指标(分类准确率、路径正确性、动作正确性) + 模型判断指标(话术质量)
- ✅ **三角色模拟**: User模型、Agent模型(被测)、Judge模型
- ✅ **多种评测策略**: Intent均衡、路径覆盖、混合策略
- ✅ **多模型投票**: 支持多个Judge模型同时评测并投票决策

**核心脚本**: `run.sh`

---

## GPU资源分配策略

框架采用**统一的GPU分配策略**,根据可用GPU数量(4卡或8卡)自动配置:

### 4卡配置

| 角色 | GPU分配 | 张量并行度 | 说明 |
|------|---------|-----------|------|
| **User模型** | GPU 0 | TP=1 | 用户模拟 |
| **Agent模型** | GPU 1 (或 GPU 1+3*) | TP=1 (或 TP=2*) | 被测客服模型 |
| **Judge模型** | GPU 2 | TP=1 | 评判模型 |
| **预留** | GPU 3 | - | 供大模型使用 |

> *注: 72B大模型会自动使用GPU 1+3进行张量并行(TP=2)

### 8卡配置

| 角色 | GPU分配 | 张量并行度 | 说明 |
|------|---------|-----------|------|
| **User模型** | GPU 0-1 | TP=2 | 用户模拟 |
| **Agent模型** | GPU 2-3 (或 GPU 2,3,5,6*) | TP=2 (或 TP=4*) | 被测客服模型 |
| **Judge模型** | GPU 4-5 | TP=2 | 评判模型 |
| **预留** | GPU 6-7 | - | 供大模型使用 |

> *注: 72B大模型会自动使用GPU 2,3,5,6进行张量并行(TP=4)

### 显存管理

- **GPU内存使用率**: 
  - 4卡配置: 80% (预留20%缓冲)
  - 8卡配置: 85% (预留15%缓冲)
- **最大并发序列数**:
  - 4卡配置: 256
  - 8卡配置: 512

---

## 快速开始

### 0. 环境准备

```bash
# 安装依赖
pip install vllm openai anthropic requests

# 检查GPU状态
nvidia-smi
```

### 1. 清理GPU显存 (可选)

如果GPU显存未释放或有残留进程:

```bash
bash run.sh cleanup-gpu
```

### 2. 启动User和Judge服务

```bash
bash run.sh start_servers \
    --num-gpus 4 \
    --user-model Qwen/Qwen2.5-14B-Instruct \
    --judge-model Qwen/Qwen2.5-14B-Instruct
```

### 3. 运行评测

#### 方式1: 使用本地vLLM服务

```bash
bash run.sh eval-server \
    --num-gpus 4 \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct \
    --agent-model-path Qwen/Qwen2.5-32B-Instruct \
    --num-users 20 \
    --max-turns 30
```

#### 方式2: 使用API服务

```bash
bash run.sh eval-api \
    --scenario online_education \
    --model gpt-4.1 \
    --api-key YOUR_OPENAI_KEY \
    --agent-model-type api \
    --agent-model-url https://api.openai.com/v1 \
    --agent-model-name gpt-4.1 \
    --num-users 2 \
    --max-turns 10
```

#### 方式3: 多模型投票评测

```bash
bash run.sh eval-voting \
    --scenario online_education \
    --judge-models "gpt-4-turbo,claude-3.5-sonnet,gemini-pro" \
    --api-keys "sk-xxx,sk-yyy,sk-zzz" \
    --api-urls "https://api.openai.com/v1,https://api.anthropic.com/v1,https://api.gemini.com/v1" \
    --agent-model-type vllm \
    --num-gpus 4 \
    --num-users 20 \
    --max-turns 30
```

### 4. 查看结果

```bash
# 查看评测报告
cat results/online_education/*_summary.json

# 查看详细对话
cat results/online_education/*_dialogues.jsonl
```

---

## 命令详解

### cleanup-gpu - GPU清理

**功能**: 强制清理GPU显存中的所有vLLM进程

**用法**:
```bash
bash run.sh cleanup-gpu
```

**清理策略**:
1. 杀死所有vllm相关进程 (`pkill -9 -f vllm`)
2. 清理特定端口(8000, 8001, 8002)的占用进程
3. 使用`nvidia-smi`清理所有GPU计算进程
4. 使用`fuser`清理占用`/dev/nvidia*`设备的进程
5. 解析`nvidia-smi`完整输出查找残留进程

**何时使用**:
- GPU显存未释放
- 端口被占用无法启动新服务
- 出现"CUDA out of memory"错误
- 评测完成后想彻底清理资源

---

### start_servers - 启动服务

**功能**: 启动User模型和Judge模型的vLLM服务

**基础用法**:
```bash
bash run.sh start_servers --num-gpus 4
```

**完整参数**:
```bash
bash run.sh start_servers \
    --num-gpus 4 \
    --user-model Qwen/Qwen2.5-14B-Instruct \
    --judge-model Qwen/Qwen2.5-14B-Instruct \
    --log-dir ./vllm_logs
```

**参数说明**:
- `--num-gpus NUM`: GPU数量,必须是4或8 (默认: 4)
- `--user-model PATH`: User模型路径 (默认: Qwen/Qwen2.5-14B-Instruct)
- `--judge-model PATH`: Judge模型路径 (默认: Qwen/Qwen2.5-14B-Instruct)
- `--log-dir DIR`: 日志目录 (默认: ./vllm_logs)

**启动后验证**:
```bash
# 检查User模型
curl http://localhost:8000/v1/models

# 检查Judge模型
curl http://localhost:8002/v1/models
```

**服务端口**:
- User模型: `http://localhost:8000`
- Agent模型: `http://localhost:8001` (在eval-server时启动)
- Judge模型: `http://localhost:8002`

---

### eval-server - vLLM评测

**功能**: 使用本地vLLM Server进行评测,自动启动Agent模型服务

**单场景评测**:
```bash
bash run.sh eval-server \
    --num-gpus 4 \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct \
    --agent-model-path Qwen/Qwen2.5-32B-Instruct \
    --num-users 20 \
    --max-turns 30
```

**多场景评测**:
```bash
bash run.sh eval-server \
    --num-gpus 4 \
    --scenarios-list online_education,ecommerce_refund,telecom_package \
    --model Qwen2.5-32B-Instruct \
    --agent-model-path Qwen/Qwen2.5-32B-Instruct \
    --num-users 20 \
    --max-turns 30
```

**使用混合评测策略**:
```bash
bash run.sh eval-server \
    --num-gpus 4 \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct \
    --agent-model-path Qwen/Qwen2.5-32B-Instruct \
    --max-turns 30 \
    --evaluation-strategy mixed \
    --samples-per-intent 3 \
    --min-samples-per-path 5
```

**跳过Agent启动(使用已运行的服务)**:
```bash
bash run.sh eval-server \
    --num-gpus 4 \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct \
    --skip-agent-startup \
    --agent-model-port 8001
```

**完整参数**:
- `--num-gpus NUM`: GPU数量 (4或8, 默认: 4)
- `--scenario SCENARIO`: 单个场景名称
- `--scenarios-list LIST`: 多个场景,逗号分隔 (例: `online_education,ecommerce_refund`)
- `--model MODEL`: 客服模型名称 (用于结果命名, 默认: Qwen2.5-32B-Instruct)
- `--agent-model-path PATH`: 客服模型路径 (默认: Qwen/Qwen2.5-32B-Instruct)
- `--agent-model-port PORT`: 客服模型端口 (默认: 8001)
- `--skip-agent-startup`: 跳过客服模型启动 (如果已有服务在运行)
- `--output DIR`: 输出目录 (默认: ./results)
- `--num-users NUM`: 用户数量 (默认: 20)
- `--max-turns NUM`: 最大对话轮次 (默认: 30)
- `--max-workers NUM`: 并发worker数 (默认: 16)
- `--evaluation-strategy STR`: 评测策略 (`intent_based`/`mixed`/`path_coverage`, 默认: `intent_based`)
- `--samples-per-intent NUM`: 每个Intent采样数 (默认: 3, 用于mixed策略)
- `--min-samples-per-path NUM`: 每条路径最小测试次数 (默认: 5, 用于mixed策略)
- `--log-dir DIR`: 日志目录 (默认: ./vllm_logs)

**智能模型检测**:
- ✅ 自动检测已运行的Agent服务,避免重复启动
- ✅ 72B大模型自动使用更多GPU(4卡配置用2张,8卡配置用4张)
- ✅ 支持Qwen3模型自动加载chat template

**输出结果**:
```
results/
└── online_education/
    ├── Qwen2.5-32B-Instruct_20240315_dialogues.jsonl  # 详细对话
    └── Qwen2.5-32B-Instruct_20240315_summary.json     # 评测报告
```

---

### eval-api - API评测

**功能**: 使用远程API进行评测,不需要GPU资源

**基础用法**:
```bash
bash run.sh eval-api \
    --scenario online_education \
    --model gpt-4.1 \
    --api-key YOUR_OPENAI_KEY \
    --agent-model-type api \
    --agent-model-url https://api.openai.com/v1 \
    --agent-model-name gpt-4.1 \
    --num-users 2 \
    --max-turns 10
```

**多场景API评测**:
```bash
bash run.sh eval-api \
    --scenarios-list online_education,ecommerce_refund \
    --model gpt-4.1 \
    --api-key YOUR_KEY \
    --agent-model-type api \
    --agent-model-url https://api.openai.com/v1 \
    --agent-model-name gpt-4.1
```

**完整参数**:
- `--scenario SCENARIO`: 单个场景名称
- `--scenarios-list LIST`: 多个场景,逗号分隔
- `--model MODEL`: Judge模型名称 (必需)
- `--api-key KEY`: Judge模型API密钥 (必需)
- `--agent-model-type TYPE`: 客服模型类型 (`api`或`vllm`)
- `--agent-model-url URL`: 客服模型API地址
- `--agent-model-name NAME`: 客服模型名称
- `--output DIR`: 输出目录 (默认: ./results)
- `--num-users NUM`: 用户数量 (默认: 2)
- `--max-turns NUM`: 最大对话轮次 (默认: 10)
- `--max-workers NUM`: 并发worker数 (默认: 16)
- `--evaluation-strategy STR`: 评测策略 (默认: `intent_based`)
- `--samples-per-intent NUM`: 每个Intent采样数 (默认: 3)
- `--min-samples-per-path NUM`: 每条路径最小测试次数 (默认: 5)

**适用场景**:
- 评测闭源模型(GPT-4, Claude, Gemini等)
- 没有GPU资源
- 需要快速验证(小规模测试)

---

### eval-voting - 多模型投票评测

**功能**: 使用多个Judge模型同时评测并投票决策,提高评测可靠性

**完整示例**:
```bash
bash run.sh eval-voting \
    --scenario online_education \
    --judge-models "gpt-4-turbo,claude-3.5-sonnet,gemini-pro" \
    --api-keys "sk-xxx,sk-yyy,sk-zzz" \
    --api-urls "https://api.openai.com/v1,https://api.anthropic.com/v1,https://api.gemini.com/v1" \
    --agent-model-type vllm \
    --num-gpus 4 \
    --num-users 20 \
    --max-turns 30
```

**Agent使用vLLM + Judge使用API**:
```bash
bash run.sh eval-voting \
    --scenario online_education \
    --judge-models "gpt-4-turbo,claude-3.5-sonnet" \
    --api-keys "sk-xxx,sk-yyy" \
    --api-urls "https://api.openai.com/v1,https://api.anthropic.com/v1" \
    --agent-model-type vllm \
    --agent-model-path Qwen/Qwen2.5-32B-Instruct \
    --num-gpus 4
```

**Agent和Judge都使用API**:
```bash
bash run.sh eval-voting \
    --scenario online_education \
    --judge-models "gpt-4,claude-3-opus" \
    --api-keys "sk-xxx,sk-yyy" \
    --api-urls "https://api.openai.com/v1,https://api.anthropic.com/v1" \
    --agent-model-type api \
    --agent-model-url https://api.openai.com/v1 \
    --agent-model-name gpt-4 \
    --agent-api-key YOUR_KEY
```

**完整参数**:
- `--scenario SCENARIO`: 单个场景名称
- `--scenarios-list LIST`: 多个场景,逗号分隔
- `--judge-models MODELS`: Judge模型名称列表,逗号分隔 (必需)
- `--api-keys KEYS`: 对应模型的API密钥列表,逗号分隔 (必需)
- `--api-urls URLS`: 对应模型的API地址列表,逗号分隔 (必需)
- `--agent-model-type TYPE`: 客服模型类型 (`api`或`vllm`)
- `--agent-model-path PATH`: 客服模型路径 (vllm类型时使用)
- `--agent-model-url URL`: 客服模型URL (api类型时使用)
- `--agent-model-port PORT`: 客服模型端口 (vllm类型时使用, 默认: 8001)
- `--agent-api-key KEY`: 客服模型API密钥 (api类型时使用)
- `--agent-model-name NAME`: 客服模型名称 (api类型时使用)
- `--num-gpus NUM`: GPU数量 (vllm类型时使用, 默认: 4)
- `--skip-agent-startup`: 跳过Agent模型启动
- `--output DIR`: 输出目录 (默认: ./results)
- `--num-users NUM`: 用户数量 (默认: 2)
- `--max-turns NUM`: 最大对话轮次 (默认: 10)
- `--max-workers NUM`: 并发worker数 (默认: 16)
- `--evaluation-strategy STR`: 评测策略 (默认: `intent_based`)
- `--samples-per-intent NUM`: 每个Intent采样数 (默认: 3)
- `--min-samples-per-path NUM`: 每条路径最小测试次数 (默认: 5)

**投票机制**:
- 每个Judge模型独立评测
- 对于分类结果,采用多数投票
- 对于话术质量,取平均分
- 提高评测的客观性和可靠性

**优势**:
- ✅ 消除单一模型的偏见
- ✅ 提高评测准确性
- ✅ 适用于高风险评测场景

---

### re-score - 重新评分

**功能**: 使用新的Judge模型对已有对话进行重新评分,无需重新生成对话

**基础用法**:
```bash
bash run.sh re-score \
    --num-gpus 4 \
    --dialogue-file results/online_education/dialogues.jsonl \
    --judge-model Qwen2.5-14B-Instruct \
    --judge-model-path Qwen/Qwen2.5-14B-Instruct
```

**使用API模型重新评分**:
```bash
bash run.sh re-score \
    --dialogue-file results/online_education/dialogues.jsonl \
    --judge-model gpt-4 \
    --model-type api \
    --api-key YOUR_KEY \
    --api-url https://api.openai.com/v1
```

**跳过Judge启动(使用已运行的服务)**:
```bash
bash run.sh re-score \
    --dialogue-file results/online_education/dialogues.jsonl \
    --judge-model Qwen2.5-14B-Instruct \
    --skip-judge-startup \
    --judge-model-port 8002
```

**完整参数**:
- `--dialogue-file FILE`: 对话文件路径 (必需, .jsonl格式)
- `--num-gpus NUM`: GPU数量 (4或8, vllm类型时使用, 默认: 4)
- `--judge-model MODEL`: Judge模型名称 (默认: Qwen2.5-14B-Instruct)
- `--judge-model-path PATH`: Judge模型路径 (vllm类型时使用, 默认: Qwen/Qwen2.5-14B-Instruct)
- `--judge-model-port PORT`: Judge模型端口 (默认: 8002)
- `--skip-judge-startup`: 跳过Judge模型启动
- `--output DIR`: 输出目录 (默认: ./results)
- `--model-type TYPE`: 模型类型 (`vllm`或`api`, 默认: vllm)
- `--api-key KEY`: API密钥 (api类型时必需)
- `--api-url URL`: API地址 (api类型时必需)

**使用场景**:
- 更换Judge模型后重新评分
- 对比不同Judge模型的评分差异
- 修复评分错误
- 添加新的评分维度

**输出**:
```
results/
└── dialogues_rescored_1710512345.jsonl  # 重新评分后的对话
```

---

## 评测策略

框架支持三种评测策略,可通过`--evaluation-strategy`参数指定:

### 1. Intent均衡策略 (`intent_based`)

**默认策略**,确保每种用户意图都被充分测试。

**特点**:
- 为每个用户意图生成固定数量的测试用例
- 保证不同意图的测试覆盖均衡
- 适用于需要全面覆盖各种用户需求的场景

**配置**:
```bash
--evaluation-strategy intent_based \
--samples-per-intent 3  # 每个Intent生成3个测试用例
```

**适用场景**:
- 通用评测
- 意图分类能力测试
- 均衡覆盖各种用户需求

### 2. 路径覆盖策略 (`path_coverage`)

**路径优先**,确保SOP图中的每条路径都被充分测试。

**特点**:
- 遍历SOP图的所有可能路径
- 每条路径至少测试N次
- 适用于需要验证流程完整性的场景

**配置**:
```bash
--evaluation-strategy path_coverage \
--min-samples-per-path 5  # 每条路径至少测试5次
```

**适用场景**:
- SOP流程验证
- 路径跳转逻辑测试
- 边界case覆盖

### 3. 混合策略 (`mixed`)

**结合Intent均衡和路径覆盖**,提供最全面的测试。

**特点**:
- 先基于Intent生成基础测试集
- 再补充未覆盖的路径
- 保证Intent和路径的双重覆盖

**配置**:
```bash
--evaluation-strategy mixed \
--samples-per-intent 3 \
--min-samples-per-path 5
```

**适用场景**:
- 生产环境全面评测
- 高质量benchmark构建
- 需要同时验证意图理解和流程执行

### 策略对比

| 策略 | Intent覆盖 | 路径覆盖 | 测试用例数 | 适用场景 |
|------|-----------|---------|----------|---------|
| `intent_based` | ⭐⭐⭐ | ⭐ | 中等 | 通用评测 |
| `path_coverage` | ⭐ | ⭐⭐⭐ | 多 | 流程验证 |
| `mixed` | ⭐⭐⭐ | ⭐⭐⭐ | 最多 | 全面评测 |

---

## 常见问题

### Q1: GPU显存不足怎么办?

**症状**:
```
RuntimeError: CUDA out of memory
```

**解决方案**:

1. **清理GPU显存**:
```bash
bash run.sh cleanup-gpu
```

2. **降低并发数**:
```bash
--max-workers 8  # 从16降低到8
```

3. **使用更多GPU**:
```bash
--num-gpus 8  # 从4卡升级到8卡
```

4. **降低GPU内存使用率** (修改run.sh):
```bash
# 将gpu_memory_utilization从0.8改为0.7
gpu_memory_utilization=0.7
```

### Q2: 端口被占用怎么办?

**症状**:
```
Error: Port 8001 is already in use
```

**解决方案**:

1. **清理端口**:
```bash
bash run.sh cleanup-gpu  # 会自动清理8000/8001/8002端口
```

2. **手动清理特定端口**:
```bash
lsof -ti:8001 | xargs kill -9
```

3. **使用不同端口**:
```bash
--agent-model-port 8003
```

### Q3: 服务启动很慢怎么办?

**正常情况**:
- 大模型(32B+)启动需要**30-60秒**
- 超大模型(72B+)启动需要**60-120秒**

**异常情况**:

1. **检查日志**:
```bash
tail -f vllm_logs/客服模型.log
```

2. **检查GPU状态**:
```bash
nvidia-smi
```

3. **检查模型路径**:
```bash
ls -lh /path/to/model/
```

### Q4: 如何复用已启动的服务?

**场景**: Agent模型已经在运行,不想重新启动

**解决方案**:

```bash
# 方法1: 使用--skip-agent-startup
bash run.sh eval-server \
    --skip-agent-startup \
    --agent-model-port 8001

# 方法2: 框架会自动检测
# 如果检测到PID文件且服务在运行,会自动跳过启动
bash run.sh eval-server \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct
```

### Q5: 如何评测多个场景?

**方法1: 使用--scenarios-list** (推荐):
```bash
bash run.sh eval-server \
    --scenarios-list online_education,ecommerce_refund,telecom_package \
    --model Qwen2.5-32B-Instruct
```

**方法2: 循环脚本**:
```bash
for scenario in online_education ecommerce_refund telecom_package; do
    bash run.sh eval-server \
        --scenario $scenario \
        --model Qwen2.5-32B-Instruct \
        --skip-agent-startup  # 复用Agent服务
done
```

### Q6: 如何对比不同Judge模型的评分?

**步骤**:

1. **使用Judge A评测并保存对话**:
```bash
bash run.sh eval-server \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct
# 结果保存在: results/online_education/*_dialogues.jsonl
```

2. **使用Judge B重新评分**:
```bash
bash run.sh re-score \
    --dialogue-file results/online_education/*_dialogues.jsonl \
    --judge-model gpt-4 \
    --model-type api \
    --api-key YOUR_KEY
```

3. **对比评分差异**:
```python
import json

# 读取两个评分结果
with open('dialogues_rescored_xxx.jsonl') as f:
    rescored = [json.loads(line) for line in f]

# 对比分析
for i, dialogue in enumerate(rescored):
    original_score = dialogue.get('original_judge_score')
    new_score = dialogue.get('judge_score')
    print(f"Dialogue {i}: {original_score} -> {new_score}")
```

### Q7: 如何调试评测结果?

**启用详细日志**:
```bash
# 查看实时日志
tail -f vllm_logs/*-run.log

# 查看模型日志
tail -f vllm_logs/客服模型.log
tail -f vllm_logs/评判模型.log
```

**分析评测报告**:
```bash
# 查看summary.json
cat results/online_education/*_summary.json | jq .

# 提取关键指标
cat results/online_education/*_summary.json | jq '.metrics'
```

**检查单个对话**:
```bash
# 查看第一条对话
head -1 results/online_education/*_dialogues.jsonl | jq .

# 查看失败的对话
cat results/online_education/*_dialogues.jsonl | jq 'select(.evaluation.overall_score < 0.5)'
```

---

## 高级用法

### 1. 批量评测多个模型

```bash
#!/bin/bash

models=(
    "Qwen/Qwen2.5-32B-Instruct"
    "Qwen/Qwen2.5-72B-Instruct"
    "meta-llama/Llama-3-70B-Instruct"
)

for model in "${models[@]}"; do
    model_name=$(basename "$model")
    
    echo "评测模型: $model_name"
    
    bash run.sh eval-server \
        --num-gpus 4 \
        --scenario online_education \
        --model "$model_name" \
        --agent-model-path "$model" \
        --num-users 20 \
        --max-turns 30
    
    # 清理GPU显存
    bash run.sh cleanup-gpu
    sleep 10
done
```

### 2. 自定义并发控制

```bash
# 高并发(适用于API模式或强大GPU)
bash run.sh eval-api \
    --scenario online_education \
    --model gpt-4 \
    --api-key YOUR_KEY \
    --max-workers 32

# 低并发(适用于GPU显存紧张)
bash run.sh eval-server \
    --num-gpus 4 \
    --scenario online_education \
    --model Qwen2.5-72B-Instruct \
    --max-workers 4
```

### 3. 分阶段评测流程

```bash
# 第1阶段: 启动持久化服务
bash run.sh start_servers --num-gpus 4

# 第2阶段: 小规模测试(验证配置)
bash run.sh eval-server \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct \
    --num-users 2 \
    --max-turns 5 \
    --skip-agent-startup

# 第3阶段: 全规模评测
bash run.sh eval-server \
    --scenarios-list online_education,ecommerce_refund,telecom_package \
    --model Qwen2.5-32B-Instruct \
    --num-users 50 \
    --max-turns 30 \
    --skip-agent-startup

# 第4阶段: 使用不同Judge重新评分
bash run.sh re-score \
    --dialogue-file results/online_education/*_dialogues.jsonl \
    --judge-model gpt-4 \
    --model-type api \
    --api-key YOUR_KEY
```

### 4. 多Judge投票评测(生产级)

```bash
# 使用3个不同的Judge模型进行投票
bash run.sh eval-voting \
    --scenario online_education \
    --judge-models "gpt-4-turbo,claude-3.5-sonnet,gemini-1.5-pro" \
    --api-keys "$OPENAI_KEY,$ANTHROPIC_KEY,$GOOGLE_KEY" \
    --api-urls "https://api.openai.com/v1,https://api.anthropic.com/v1,https://generativelanguage.googleapis.com/v1beta" \
    --agent-model-type vllm \
    --agent-model-path Qwen/Qwen2.5-32B-Instruct \
    --num-gpus 4 \
    --num-users 100 \
    --max-turns 30 \
    --evaluation-strategy mixed
```

### 5. 结果分析脚本

```bash
#!/bin/bash

# 汇总所有场景的评测结果
echo "场景,模型,总分,分类准确率,路径正确性,动作正确性,话术质量"

for result_file in results/*/*_summary.json; do
    scenario=$(basename $(dirname "$result_file"))
    model=$(jq -r '.model_name' "$result_file")
    overall=$(jq -r '.overall_score' "$result_file")
    classification=$(jq -r '.metrics[] | select(.metric_name=="classification_accuracy") | .score' "$result_file")
    path=$(jq -r '.metrics[] | select(.metric_name=="path_correctness") | .score' "$result_file")
    action=$(jq -r '.metrics[] | select(.metric_name=="final_actions_correctness") | .score' "$result_file")
    chat=$(jq -r '.metrics[] | select(.metric_name=="chat_quality") | .score' "$result_file")
    
    echo "$scenario,$model,$overall,$classification,$path,$action,$chat"
done
```



---

## 附录

### 支持的场景列表

| 场景ID | 场景名称 | 说明 |
|--------|---------|------|
| `online_education` | 在线教育 | 课程咨询、学习问题、退费等 |
| `ecommerce_refund` | 电商退款 | 退货、换货、售后处理 |
| `telecom_package` | 电信套餐 | 套餐变更、流量咨询 |
| `property_service` | 物业服务 | 报修、投诉、缴费 |
| `airline_refund` | 航空改签 | 改签、退票、航班咨询 |
| `logistics_delivery` | 物流配送 | 物流查询、配送问题 |

### 日志文件说明

```
vllm_logs/
├── 用户模型.log              # User模型运行日志
├── 用户模型.pid              # User模型进程ID
├── 评判模型.log              # Judge模型运行日志
├── 评判模型.pid              # Judge模型进程ID
├── Qwen2.5-32B-Instruct-客服模型.log   # Agent模型运行日志
├── Qwen2.5-32B-Instruct-客服模型.pid   # Agent模型进程ID
└── Qwen2.5-32B-Instruct-20240315-run.log  # 评测运行日志
```

### 评测指标说明

| 指标 | 权重 | 说明 |
|------|------|------|
| **分类准确率** | 30% | Agent的分类输出与Ground Truth的匹配度 |
| **路径正确性** | 30% | Agent的SOP路径与预期路径的匹配度 |
| **动作正确性** | 20% | Agent的最终动作与预期动作的匹配度 |
| **话术质量** | 20% | Agent回复的自然度、准确性、友好度 |

**综合得分计算**:
```
逻辑能力 = (分类准确率×30% + 路径正确性×30% + 动作正确性×20%) / 80%
话术能力 = 话术质量 × 100%
总分 = 逻辑能力×80% + 话术能力×20%
```

### 环境变量

```bash
# 设置日志目录
export LOG_DIR="/path/to/logs"

# 设置结果目录
export OUTPUT_DIR="/path/to/results"

# 设置默认模型路径
export USER_MODEL_PATH="Qwen/Qwen2.5-14B-Instruct"
export JUDGE_MODEL_PATH="Qwen/Qwen2.5-14B-Instruct"
export AGENT_MODEL_PATH="Qwen/Qwen2.5-32B-Instruct"
```

### 故障排查检查清单

- [ ] GPU状态正常 (`nvidia-smi`)
- [ ] 端口未被占用 (`lsof -i:8000,8001,8002`)
- [ ] 模型路径正确 (`ls /path/to/model/`)
- [ ] 依赖已安装 (`pip list | grep vllm`)
- [ ] 显存充足 (至少50GB空闲)
- [ ] 日志无错误 (`tail vllm_logs/*.log`)
- [ ] 服务可访问 (`curl localhost:8000/v1/models`)

---

## 技术支持

如有问题,请提供以下信息:

1. **错误日志**: `vllm_logs/*-run.log`的最后50行
2. **GPU状态**: `nvidia-smi`的输出
3. **命令**: 完整的运行命令
4. **环境**: Python版本、vLLM版本、CUDA版本

---

**框架版本**: v2.0  
**最后更新**: 2024-03-15  
**作者**: 评测框架开发组
