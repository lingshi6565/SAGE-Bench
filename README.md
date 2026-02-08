# SAGE-Bench Multi-turn Dialogue Evaluation Framework - User Guide

## 📋 Table of Contents

- [Introduction](#introduction)
- [GPU Resource Allocation Strategy](#gpu-resource-allocation-strategy)
- [Quick Start](#quick-start)
- [Command Reference](#command-reference)
  - [cleanup-gpu - GPU Cleanup](#cleanup-gpu---gpu-cleanup)
  - [start_servers - Start Services](#start_servers---start-services)
  - [eval-server - vLLM Evaluation](#eval-server---vllm-evaluation)
  - [eval-api - API Evaluation](#eval-api---api-evaluation)
  - [eval-voting - Multi-Model Voting Evaluation](#eval-voting---multi-model-voting-evaluation)
  - [re-score - Re-scoring](#re-score---re-scoring)
- [Evaluation Strategies](#evaluation-strategies)
- [FAQ](#faq)
- [Advanced Usage](#advanced-usage)

---

## Introduction

This evaluation framework is a production-grade multi-turn dialogue evaluation system that supports:

- ✅ **Multi-scenario Evaluation**: Online education, e-commerce refund, telecom packages, property services, airline rebooking, logistics delivery
- ✅ **Flexible Deployment**: Support for local vLLM deployment and remote API calls
- ✅ **Intelligent Evaluation**: Code-computed metrics (classification accuracy, path correctness, action correctness) + model-judged metrics (response quality)
- ✅ **Three-role Simulation**: User model, Agent model (under test), Judge model
- ✅ **Multiple Evaluation Strategies**: Intent-balanced, path coverage, mixed strategies
- ✅ **Multi-model Voting**: Support for multiple Judge models to evaluate and vote simultaneously

**Core Script**: `run.sh`

---

## GPU Resource Allocation Strategy

The framework adopts a **unified GPU allocation strategy**, automatically configured based on available GPU count (4 or 8 cards):

### 4-GPU Configuration

| Role | GPU Allocation | Tensor Parallel | Description |
|------|----------------|-----------------|-------------|
| **User Model** | GPU 0 | TP=1 | User simulation |
| **Agent Model** | GPU 1 (or GPU 1+3*) | TP=1 (or TP=2*) | Agent model under test |
| **Judge Model** | GPU 2 | TP=1 | Evaluation model |
| **Reserved** | GPU 3 | - | For large models |

> *Note: 72B models automatically use GPU 1+3 for tensor parallelism (TP=2)

### 8-GPU Configuration

| Role | GPU Allocation | Tensor Parallel | Description |
|------|----------------|-----------------|-------------|
| **User Model** | GPU 0-1 | TP=2 | User simulation |
| **Agent Model** | GPU 2-3 (or GPU 2,3,5,6*) | TP=2 (or TP=4*) | Agent model under test |
| **Judge Model** | GPU 4-5 | TP=2 | Evaluation model |
| **Reserved** | GPU 6-7 | - | For large models |

> *Note: 72B models automatically use GPU 2,3,5,6 for tensor parallelism (TP=4)

### Memory Management

- **GPU Memory Utilization**: 
  - 4-GPU config: 80% (20% buffer reserved)
  - 8-GPU config: 85% (15% buffer reserved)
- **Max Concurrent Sequences**:
  - 4-GPU config: 256
  - 8-GPU config: 512

---

## Quick Start

### 0. Environment Setup

```bash
# Install dependencies
pip install vllm openai anthropic requests

# Check GPU status
nvidia-smi
```

### 1. Cleanup GPU Memory (Optional)

If GPU memory is not released or there are residual processes:

```bash
bash run.sh cleanup-gpu
```

### 2. Start User and Judge Services

```bash
bash run.sh start_servers \
    --num-gpus 4 \
    --user-model Qwen/Qwen2.5-14B-Instruct \
    --judge-model Qwen/Qwen2.5-14B-Instruct
```

### 3. Run Evaluation

#### Method 1: Using Local vLLM Service

```bash
bash run.sh eval-server \
    --num-gpus 4 \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct \
    --agent-model-path Qwen/Qwen2.5-32B-Instruct \
    --num-users 20 \
    --max-turns 30
```

#### Method 2: Using API Service

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

#### Method 3: Multi-Model Voting Evaluation

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

### 4. View Results

```bash
# View evaluation report
cat results/online_education/*_summary.json

# View detailed dialogues
cat results/online_education/*_dialogues.jsonl
```

---

## Command Reference

### cleanup-gpu - GPU Cleanup

**Function**: Force cleanup of all vLLM processes in GPU memory

**Usage**:
```bash
bash run.sh cleanup-gpu
```

**Cleanup Strategy**:
1. Kill all vllm-related processes (`pkill -9 -f vllm`)
2. Clean up processes occupying specific ports (8000, 8001, 8002)
3. Use `nvidia-smi` to clean all GPU compute processes
4. Use `fuser` to clean processes occupying `/dev/nvidia*` devices
5. Parse complete `nvidia-smi` output to find residual processes

**When to Use**:
- GPU memory not released
- Ports occupied and unable to start new services
- "CUDA out of memory" errors
- Want to thoroughly clean resources after evaluation

---

### start_servers - Start Services

**Function**: Start User model and Judge model vLLM services

**Basic Usage**:
```bash
bash run.sh start_servers --num-gpus 4
```

**Full Parameters**:
```bash
bash run.sh start_servers \
    --num-gpus 4 \
    --user-model Qwen/Qwen2.5-14B-Instruct \
    --judge-model Qwen/Qwen2.5-14B-Instruct \
    --log-dir ./vllm_logs
```

**Parameter Description**:
- `--num-gpus NUM`: Number of GPUs, must be 4 or 8 (default: 4)
- `--user-model PATH`: User model path (default: Qwen/Qwen2.5-14B-Instruct)
- `--judge-model PATH`: Judge model path (default: Qwen/Qwen2.5-14B-Instruct)
- `--log-dir DIR`: Log directory (default: ./vllm_logs)

**Verify After Startup**:
```bash
# Check User model
curl http://localhost:8000/v1/models

# Check Judge model
curl http://localhost:8002/v1/models
```

**Service Ports**:
- User model: `http://localhost:8000`
- Agent model: `http://localhost:8001` (started during eval-server)
- Judge model: `http://localhost:8002`

---

### eval-server - vLLM Evaluation

**Function**: Evaluate using local vLLM Server, automatically starts Agent model service

**Single Scenario Evaluation**:
```bash
bash run.sh eval-server \
    --num-gpus 4 \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct \
    --agent-model-path Qwen/Qwen2.5-32B-Instruct \
    --num-users 20 \
    --max-turns 30
```

**Multi-Scenario Evaluation**:
```bash
bash run.sh eval-server \
    --num-gpus 4 \
    --scenarios-list online_education,ecommerce_refund,telecom_package \
    --model Qwen2.5-32B-Instruct \
    --agent-model-path Qwen/Qwen2.5-32B-Instruct \
    --num-users 20 \
    --max-turns 30
```

**Using Mixed Evaluation Strategy**:
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

**Skip Agent Startup (Use Running Service)**:
```bash
bash run.sh eval-server \
    --num-gpus 4 \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct \
    --skip-agent-startup \
    --agent-model-port 8001
```

**Full Parameters**:
- `--num-gpus NUM`: Number of GPUs (4 or 8, default: 4)
- `--scenario SCENARIO`: Single scenario name
- `--scenarios-list LIST`: Multiple scenarios, comma-separated (e.g., `online_education,ecommerce_refund`)
- `--model MODEL`: Agent model name (for result naming, default: Qwen2.5-32B-Instruct)
- `--agent-model-path PATH`: Agent model path (default: Qwen/Qwen2.5-32B-Instruct)
- `--agent-model-port PORT`: Agent model port (default: 8001)
- `--skip-agent-startup`: Skip agent model startup (if service already running)
- `--output DIR`: Output directory (default: ./results)
- `--num-users NUM`: Number of users (default: 20)
- `--max-turns NUM`: Maximum dialogue turns (default: 30)
- `--max-workers NUM`: Number of concurrent workers (default: 16)
- `--evaluation-strategy STR`: Evaluation strategy (`intent_based`/`mixed`/`path_coverage`, default: `intent_based`)
- `--samples-per-intent NUM`: Samples per intent (default: 3, for mixed strategy)
- `--min-samples-per-path NUM`: Minimum tests per path (default: 5, for mixed strategy)
- `--log-dir DIR`: Log directory (default: ./vllm_logs)

**Intelligent Model Detection**:
- ✅ Automatically detects running Agent service to avoid duplicate startup
- ✅ 72B models automatically use more GPUs (2 cards for 4-GPU config, 4 cards for 8-GPU config)
- ✅ Supports automatic loading of chat template for Qwen3 models

**Output Results**:
```
results/
└── online_education/
    ├── Qwen2.5-32B-Instruct_20240315_dialogues.jsonl  # Detailed dialogues
    └── Qwen2.5-32B-Instruct_20240315_summary.json     # Evaluation report
```

---

### eval-api - API Evaluation

**Function**: Evaluate using remote API, no GPU resources required

**Basic Usage**:
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

**Multi-Scenario API Evaluation**:
```bash
bash run.sh eval-api \
    --scenarios-list online_education,ecommerce_refund \
    --model gpt-4.1 \
    --api-key YOUR_KEY \
    --agent-model-type api \
    --agent-model-url https://api.openai.com/v1 \
    --agent-model-name gpt-4.1
```

**Full Parameters**:
- `--scenario SCENARIO`: Single scenario name
- `--scenarios-list LIST`: Multiple scenarios, comma-separated
- `--model MODEL`: Judge model name (required)
- `--api-key KEY`: Judge model API key (required)
- `--agent-model-type TYPE`: Agent model type (`api` or `vllm`)
- `--agent-model-url URL`: Agent model API URL
- `--agent-model-name NAME`: Agent model name
- `--output DIR`: Output directory (default: ./results)
- `--num-users NUM`: Number of users (default: 2)
- `--max-turns NUM`: Maximum dialogue turns (default: 10)
- `--max-workers NUM`: Number of concurrent workers (default: 16)
- `--evaluation-strategy STR`: Evaluation strategy (default: `intent_based`)
- `--samples-per-intent NUM`: Samples per intent (default: 3)
- `--min-samples-per-path NUM`: Minimum tests per path (default: 5)

**Use Cases**:
- Evaluate closed-source models (GPT-4, Claude, Gemini, etc.)
- No GPU resources available
- Quick validation needed (small-scale testing)

---

### eval-voting - Multi-Model Voting Evaluation

**Function**: Use multiple Judge models to evaluate simultaneously and vote for decision-making, improving evaluation reliability

**Full Example**:
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

**Agent Using vLLM + Judge Using API**:
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

**Both Agent and Judge Using API**:
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

**Full Parameters**:
- `--scenario SCENARIO`: Single scenario name
- `--scenarios-list LIST`: Multiple scenarios, comma-separated
- `--judge-models MODELS`: List of Judge model names, comma-separated (required)
- `--api-keys KEYS`: List of API keys for corresponding models, comma-separated (required)
- `--api-urls URLS`: List of API URLs for corresponding models, comma-separated (required)
- `--agent-model-type TYPE`: Agent model type (`api` or `vllm`)
- `--agent-model-path PATH`: Agent model path (when using vllm type)
- `--agent-model-url URL`: Agent model URL (when using api type)
- `--agent-model-port PORT`: Agent model port (when using vllm type, default: 8001)
- `--agent-api-key KEY`: Agent model API key (when using api type)
- `--agent-model-name NAME`: Agent model name (when using api type)
- `--num-gpus NUM`: Number of GPUs (when using vllm type, default: 4)
- `--skip-agent-startup`: Skip Agent model startup
- `--output DIR`: Output directory (default: ./results)
- `--num-users NUM`: Number of users (default: 2)
- `--max-turns NUM`: Maximum dialogue turns (default: 10)
- `--max-workers NUM`: Number of concurrent workers (default: 16)
- `--evaluation-strategy STR`: Evaluation strategy (default: `intent_based`)
- `--samples-per-intent NUM`: Samples per intent (default: 3)
- `--min-samples-per-path NUM`: Minimum tests per path (default: 5)

**Voting Mechanism**:
- Each Judge model evaluates independently
- For classification results, majority voting is used
- For response quality, average scoring is used
- Improves evaluation objectivity and reliability

**Advantages**:
- ✅ Eliminates single model bias
- ✅ Improves evaluation accuracy
- ✅ Suitable for high-stakes evaluation scenarios

---

### re-score - Re-scoring

**Function**: Re-score existing dialogues with a new Judge model without regenerating dialogues

**Basic Usage**:
```bash
bash run.sh re-score \
    --num-gpus 4 \
    --dialogue-file results/online_education/dialogues.jsonl \
    --judge-model Qwen2.5-14B-Instruct \
    --judge-model-path Qwen/Qwen2.5-14B-Instruct
```

**Re-score Using API Model**:
```bash
bash run.sh re-score \
    --dialogue-file results/online_education/dialogues.jsonl \
    --judge-model gpt-4 \
    --model-type api \
    --api-key YOUR_KEY \
    --api-url https://api.openai.com/v1
```

**Skip Judge Startup (Use Running Service)**:
```bash
bash run.sh re-score \
    --dialogue-file results/online_education/dialogues.jsonl \
    --judge-model Qwen2.5-14B-Instruct \
    --skip-judge-startup \
    --judge-model-port 8002
```

**Full Parameters**:
- `--dialogue-file FILE`: Dialogue file path (required, .jsonl format)
- `--num-gpus NUM`: Number of GPUs (4 or 8, when using vllm type, default: 4)
- `--judge-model MODEL`: Judge model name (default: Qwen2.5-14B-Instruct)
- `--judge-model-path PATH`: Judge model path (when using vllm type, default: Qwen/Qwen2.5-14B-Instruct)
- `--judge-model-port PORT`: Judge model port (default: 8002)
- `--skip-judge-startup`: Skip Judge model startup
- `--output DIR`: Output directory (default: ./results)
- `--model-type TYPE`: Model type (`vllm` or `api`, default: vllm)
- `--api-key KEY`: API key (required when using api type)
- `--api-url URL`: API URL (required when using api type)

**Use Cases**:
- Re-score after changing Judge model
- Compare scoring differences between different Judge models
- Fix scoring errors
- Add new scoring dimensions

**Output**:
```
results/
└── dialogues_rescored_1710512345.jsonl  # Re-scored dialogues
```

---

## Evaluation Strategies

The framework supports three evaluation strategies, specified via the `--evaluation-strategy` parameter:

### 1. Intent-Balanced Strategy (`intent_based`)

**Default strategy**, ensures each user intent is thoroughly tested.

**Features**:
- Generate fixed number of test cases for each user intent
- Ensure balanced test coverage across different intents
- Suitable for scenarios requiring comprehensive coverage of various user needs

**Configuration**:
```bash
--evaluation-strategy intent_based \
--samples-per-intent 3  # Generate 3 test cases per intent
```

**Use Cases**:
- General evaluation
- Intent classification capability testing
- Balanced coverage of various user needs

### 2. Path Coverage Strategy (`path_coverage`)

**Path-first**, ensures every path in the SOP graph is thoroughly tested.

**Features**:
- Traverse all possible paths in the SOP graph
- Each path tested at least N times
- Suitable for scenarios requiring process integrity verification

**Configuration**:
```bash
--evaluation-strategy path_coverage \
--min-samples-per-path 5  # Test each path at least 5 times
```

**Use Cases**:
- SOP process verification
- Path transition logic testing
- Edge case coverage

### 3. Mixed Strategy (`mixed`)

**Combines intent balance and path coverage**, provides most comprehensive testing.

**Features**:
- First generate base test set based on intent
- Then supplement uncovered paths
- Ensure dual coverage of intent and path

**Configuration**:
```bash
--evaluation-strategy mixed \
--samples-per-intent 3 \
--min-samples-per-path 5
```

**Use Cases**:
- Production environment comprehensive evaluation
- High-quality benchmark construction
- Need to verify both intent understanding and process execution

### Strategy Comparison

| Strategy | Intent Coverage | Path Coverage | Test Cases | Use Cases |
|----------|----------------|---------------|------------|-----------|
| `intent_based` | ⭐⭐⭐ | ⭐ | Medium | General evaluation |
| `path_coverage` | ⭐ | ⭐⭐⭐ | Many | Process verification |
| `mixed` | ⭐⭐⭐ | ⭐⭐⭐ | Most | Comprehensive evaluation |

---

## FAQ

### Q1: What to do if GPU memory is insufficient?

**Symptoms**:
```
RuntimeError: CUDA out of memory
```

**Solutions**:

1. **Clean up GPU memory**:
```bash
bash run.sh cleanup-gpu
```

2. **Reduce concurrency**:
```bash
--max-workers 8  # Reduce from 16 to 8
```

3. **Use more GPUs**:
```bash
--num-gpus 8  # Upgrade from 4 to 8 cards
```

4. **Lower GPU memory utilization** (modify run.sh):
```bash
# Change gpu_memory_utilization from 0.8 to 0.7
gpu_memory_utilization=0.7
```

### Q2: What to do if port is occupied?

**Symptoms**:
```
Error: Port 8001 is already in use
```

**Solutions**:

1. **Clean up port**:
```bash
bash run.sh cleanup-gpu  # Automatically cleans ports 8000/8001/8002
```

2. **Manually clean specific port**:
```bash
lsof -ti:8001 | xargs kill -9
```

3. **Use different port**:
```bash
--agent-model-port 8003
```

### Q3: What to do if service startup is slow?

**Normal situations**:
- Large models (32B+) take **30-60 seconds** to start
- Extra-large models (72B+) take **60-120 seconds** to start

**Abnormal situations**:

1. **Check logs**:
```bash
tail -f vllm_logs/客服模型.log
```

2. **Check GPU status**:
```bash
nvidia-smi
```

3. **Check model path**:
```bash
ls -lh /path/to/model/
```

### Q4: How to reuse already started services?

**Scenario**: Agent model is already running, don't want to restart

**Solutions**:

```bash
# Method 1: Use --skip-agent-startup
bash run.sh eval-server \
    --skip-agent-startup \
    --agent-model-port 8001

# Method 2: Framework automatically detects
# If PID file detected and service running, automatically skips startup
bash run.sh eval-server \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct
```

### Q5: How to evaluate multiple scenarios?

**Method 1: Use --scenarios-list** (recommended):
```bash
bash run.sh eval-server \
    --scenarios-list online_education,ecommerce_refund,telecom_package \
    --model Qwen2.5-32B-Instruct
```

**Method 2: Loop script**:
```bash
for scenario in online_education ecommerce_refund telecom_package; do
    bash run.sh eval-server \
        --scenario $scenario \
        --model Qwen2.5-32B-Instruct \
        --skip-agent-startup  # Reuse Agent service
done
```

### Q6: How to compare scores from different Judge models?

**Steps**:

1. **Evaluate with Judge A and save dialogues**:
```bash
bash run.sh eval-server \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct
# Results saved in: results/online_education/*_dialogues.jsonl
```

2. **Re-score with Judge B**:
```bash
bash run.sh re-score \
    --dialogue-file results/online_education/*_dialogues.jsonl \
    --judge-model gpt-4 \
    --model-type api \
    --api-key YOUR_KEY
```

3. **Compare scoring differences**:
```python
import json

# Read two scoring results
with open('dialogues_rescored_xxx.jsonl') as f:
    rescored = [json.loads(line) for line in f]

# Comparative analysis
for i, dialogue in enumerate(rescored):
    original_score = dialogue.get('original_judge_score')
    new_score = dialogue.get('judge_score')
    print(f"Dialogue {i}: {original_score} -> {new_score}")
```

### Q7: How to debug evaluation results?

**Enable verbose logging**:
```bash
# View real-time logs
tail -f vllm_logs/*-run.log

# View model logs
tail -f vllm_logs/客服模型.log
tail -f vllm_logs/评判模型.log
```

**Analyze evaluation report**:
```bash
# View summary.json
cat results/online_education/*_summary.json | jq .

# Extract key metrics
cat results/online_education/*_summary.json | jq '.metrics'
```

**Check individual dialogues**:
```bash
# View first dialogue
head -1 results/online_education/*_dialogues.jsonl | jq .

# View failed dialogues
cat results/online_education/*_dialogues.jsonl | jq 'select(.evaluation.overall_score < 0.5)'
```

---

## Advanced Usage

### 1. Batch Evaluate Multiple Models

```bash
#!/bin/bash

models=(
    "Qwen/Qwen2.5-32B-Instruct"
    "Qwen/Qwen2.5-72B-Instruct"
    "meta-llama/Llama-3-70B-Instruct"
)

for model in "${models[@]}"; do
    model_name=$(basename "$model")
    
    echo "Evaluating model: $model_name"
    
    bash run.sh eval-server \
        --num-gpus 4 \
        --scenario online_education \
        --model "$model_name" \
        --agent-model-path "$model" \
        --num-users 20 \
        --max-turns 30
    
    # Clean up GPU memory
    bash run.sh cleanup-gpu
    sleep 10
done
```

### 2. Custom Concurrency Control

```bash
# High concurrency (for API mode or powerful GPUs)
bash run.sh eval-api \
    --scenario online_education \
    --model gpt-4 \
    --api-key YOUR_KEY \
    --max-workers 32

# Low concurrency (for tight GPU memory)
bash run.sh eval-server \
    --num-gpus 4 \
    --scenario online_education \
    --model Qwen2.5-72B-Instruct \
    --max-workers 4
```

### 3. Phased Evaluation Workflow

```bash
# Phase 1: Start persistent services
bash run.sh start_servers --num-gpus 4

# Phase 2: Small-scale testing (validate configuration)
bash run.sh eval-server \
    --scenario online_education \
    --model Qwen2.5-32B-Instruct \
    --num-users 2 \
    --max-turns 5 \
    --skip-agent-startup

# Phase 3: Full-scale evaluation
bash run.sh eval-server \
    --scenarios-list online_education,ecommerce_refund,telecom_package \
    --model Qwen2.5-32B-Instruct \
    --num-users 50 \
    --max-turns 30 \
    --skip-agent-startup

# Phase 4: Re-score with different Judge
bash run.sh re-score \
    --dialogue-file results/online_education/*_dialogues.jsonl \
    --judge-model gpt-4 \
    --model-type api \
    --api-key YOUR_KEY
```

### 4. Multi-Judge Voting Evaluation (Production-Grade)

```bash
# Use 3 different Judge models for voting
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

### 5. Result Analysis Script

```bash
#!/bin/bash

# Aggregate evaluation results from all scenarios
echo "Scenario,Model,Overall,Classification,Path,Action,Response"

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

## Appendix

### Supported Scenario List

| Scenario ID | Scenario Name | Description |
|-------------|---------------|-------------|
| `online_education` | Online Education | Course consultation, learning issues, refunds, etc. |
| `ecommerce_refund` | E-commerce Refund | Returns, exchanges, after-sales handling |
| `telecom_package` | Telecom Packages | Package changes, data consultation |
| `property_service` | Property Services | Repairs, complaints, payments |
| `airline_refund` | Airline Rebooking | Rebooking, refunds, flight inquiries |
| `logistics_delivery` | Logistics Delivery | Logistics queries, delivery issues |

### Log File Descriptions

```
vllm_logs/
├── 用户模型.log              # User model runtime log
├── 用户模型.pid              # User model process ID
├── 评判模型.log              # Judge model runtime log
├── 评判模型.pid              # Judge model process ID
├── Qwen2.5-32B-Instruct-客服模型.log   # Agent model runtime log
├── Qwen2.5-32B-Instruct-客服模型.pid   # Agent model process ID
└── Qwen2.5-32B-Instruct-20240315-run.log  # Evaluation run log
```

### Evaluation Metrics Description

| Metric | Weight | Description |
|--------|--------|-------------|
| **Classification Accuracy** | 30% | Match between Agent's classification output and Ground Truth |
| **Path Correctness** | 30% | Match between Agent's SOP path and expected path |
| **Action Correctness** | 20% | Match between Agent's final action and expected action |
| **Response Quality** | 20% | Naturalness, accuracy, friendliness of Agent's response |

**Overall Score Calculation**:
```
Logic Ability = (Classification×30% + Path×30% + Action×20%) / 80%
Response Ability = Response Quality × 100%
Overall Score = Logic Ability×80% + Response Ability×20%
```

### Environment Variables

```bash
# Set log directory
export LOG_DIR="/path/to/logs"

# Set results directory
export OUTPUT_DIR="/path/to/results"

# Set default model paths
export USER_MODEL_PATH="Qwen/Qwen2.5-14B-Instruct"
export JUDGE_MODEL_PATH="Qwen/Qwen2.5-14B-Instruct"
export AGENT_MODEL_PATH="Qwen/Qwen2.5-32B-Instruct"
```

### Troubleshooting Checklist

- [ ] GPU status normal (`nvidia-smi`)
- [ ] Ports not occupied (`lsof -i:8000,8001,8002`)
- [ ] Model path correct (`ls /path/to/model/`)
- [ ] Dependencies installed (`pip list | grep vllm`)
- [ ] Sufficient memory (at least 50GB free)
- [ ] Logs error-free (`tail vllm_logs/*.log`)
- [ ] Services accessible (`curl localhost:8000/v1/models`)

---

## Technical Support

If you encounter issues, please provide:

1. **Error logs**: Last 50 lines of `vllm_logs/*-run.log`
2. **GPU status**: Output of `nvidia-smi`
3. **Command**: Full command executed
4. **Environment**: Python version, vLLM version, CUDA version

---

**Framework Version**: v2.0  
**Last Updated**: 2024-03-15  
**Authors**: Evaluation Framework Development Team
