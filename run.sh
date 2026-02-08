#!/bin/bash

##################################################################
# 综合评测框架脚本
# Comprehensive Evaluation Framework Script
#
# 功能:
# 1. 启动 User 和 Judge 服务
# 2. 评测模式：启动 vLLM Server
# 3. 评测模式：调用 API
# 4. 重新评分已有对话（更换 Judge 模型）
#
# GPU 分配策略 (统一规则):
# ┌─────────┬──────────────┬──────────────┬──────────────┬──────────┐
# │ GPU配置  │ User模型      │ 客服模型    │ Judge模型     │ 预留     │
# ├─────────┼──────────────┼──────────────┼──────────────┼──────────┤
# │ 4卡     │ GPU 0        │ GPU 1+3        │ GPU 2        │ GPU 3    │
# │ 8卡     │ GPU 0-1 (TP) │ GPU 2-3 (TP) │ GPU 4-5 (TP) │ GPU 6-7  │
# └─────────┴──────────────┴──────────────┴──────────────┴──────────┘
# 注: TP = Tensor Parallel (张量并行)
#
# 使用方法：
#   bash run.sh <command> [options]
#
# 命令:
#   start_servers      启动 User 和 Judge 服务
#   eval-server        使用 vLLM Server 进行评测
#   eval-api           使用 API 进行评测
#   eval-voting        使用多模型投票（Agent 自动启动/配置）进行评测
#   re-score           对已有对话进行重新评分
#   cleanup-gpu        清理GPU显存
#   help               显示帮助信息
#
# 示例:
#   bash run.sh start_servers --num-gpus 4
#   bash run.sh cleanup-gpu
#   bash run.sh eval-server --scenario online_education --model Qwen2.5-32B-Instruct --num-users 20
#   bash run.sh eval-api --scenario online_education --model gpt-4.1 --api-key YOUR_KEY
#   bash run.sh eval-voting --scenario online_education --agent-model-type vllm --num-gpus 4 \
#     --judge-models "gpt-4-turbo,claude-3.5-sonnet,gemini-pro" \
#     --api-keys "sk-xxx,sk-yyy,sk-zzz" \
#     --api-urls "https://api.openai.com/v1,https://api.anthropic.com/v1,https://api.gemini.com/v1"
#   bash run.sh re-score --dialogue-file results/dialogues.jsonl --judge-model Qwen2.5-14B-Instruct
##################################################################

set -e

# ==================== 颜色和格式 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ==================== 工具函数 ====================
# 检查端口是否已被占用
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        return 0  # 端口已被占用
    else
        return 1  # 端口未被占用
    fi
}

# 清理占用的端口
cleanup_port() {
    local port=$1
    if check_port "$port"; then
        echo -e "${YELLOW}端口 $port 已被占用，尝试释放...${NC}"
        
        # 找到占用端口的进程PID
        local pids=$(lsof -ti:$port 2>/dev/null || true)
        
        if [ -n "$pids" ]; then
            for pid in $pids; do
                echo -e "${YELLOW}杀死进程 PID: $pid (占用端口 $port)${NC}"
                
                # 找到所有子进程
                local child_pids=$(pgrep -P "$pid" 2>/dev/null || true)
                
                # 杀死主进程
                kill -9 "$pid" 2>/dev/null || true
                
                # 杀死所有子进程
                if [ -n "$child_pids" ]; then
                    for cpid in $child_pids; do
                        kill -9 "$cpid" 2>/dev/null || true
                    done
                fi
            done
        fi
        
        # 使用fuser作为备份清理方法
        fuser -k ${port}/tcp 2>/dev/null || true
        
        # 等待端口释放
        sleep 2
        
        # 验证端口是否已释放
        if check_port "$port"; then
            echo -e "${RED}⚠ 端口 $port 仍被占用，可能需要手动清理${NC}"
        else
            echo -e "${GREEN}✓ 端口 $port 已释放${NC}"
        fi
    fi
}

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

# 显示GPU状态
show_gpu_status() {
    if ! command -v nvidia-smi &> /dev/null; then
        echo -e "${YELLOW}⚠ nvidia-smi 不可用${NC}"
        return
    fi
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}GPU 状态概览${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    nvidia-smi --query-gpu=index,name,memory.used,memory.free,memory.total,utilization.gpu --format=csv 2>/dev/null || echo "无法查询GPU状态"
    
    local gpu_processes=$(nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv 2>/dev/null)
    if [ -n "$gpu_processes" ] && [ "$gpu_processes" != "pid, process_name, used_gpu_memory [MiB]" ]; then
        echo ""
        echo -e "${CYAN}GPU 计算进程:${NC}"
        echo "$gpu_processes"
    else
        echo ""
        echo -e "${GREEN}✓ 无GPU计算进程${NC}"
    fi
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# 强制清理GPU显存中的所有vLLM进程
force_cleanup_gpu() {
    echo -e "${YELLOW}强制清理GPU显存中的vLLM进程...${NC}"
    
    # 方法1: 杀死所有vllm相关进程
    echo -e "${YELLOW}杀死所有vllm进程...${NC}"
    pkill -9 -f "vllm.entrypoints" 2>/dev/null || true
    pkill -9 -f "vllm_server" 2>/dev/null || true
    pkill -9 -f "vllm/v1/engine" 2>/dev/null || true
    sleep 2
    
    # 方法2: 清理特定端口的进程
    echo -e "${YELLOW}清理端口占用...${NC}"
    for port in $USER_MODEL_PORT $AGENT_MODEL_PORT $JUDGE_MODEL_PORT; do
        cleanup_port "$port"
    done
    sleep 2
    
    # 方法3: 使用nvidia-smi清理所有GPU进程
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${YELLOW}清理GPU上的所有计算进程...${NC}"
        # 获取所有占用GPU的进程PID
        local gpu_pids=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | tr '\n' ' ')
        if [ -n "$gpu_pids" ]; then
            echo -e "${YELLOW}发现GPU进程: $gpu_pids${NC}"
            for pid in $gpu_pids; do
                if [ -n "$pid" ] && [ "$pid" != "" ] && [[ "$pid" =~ ^[0-9]+$ ]]; then
                    echo -e "${YELLOW}杀死GPU进程 PID: $pid${NC}"
                    kill -9 "$pid" 2>/dev/null || true
                fi
            done
        else
            echo -e "${GREEN}✓ nvidia-smi未显示GPU进程${NC}"
        fi
    fi
    
    # 方法4: 使用fuser查找占用/dev/nvidia*设备的进程（最底层最可靠）
    if command -v fuser &> /dev/null; then
        echo -e "${YELLOW}使用fuser清理占用GPU设备的进程...${NC}"
        # 查找所有占用nvidia设备的进程
        local fuser_output=$(fuser /dev/nvidia* 2>/dev/null)
        if [ -n "$fuser_output" ]; then
            # 提取所有PID并去重
            local fuser_pids=$(echo "$fuser_output" | tr ' ' '\n' | sort -u)
            local killed_count=0
            for fpid in $fuser_pids; do
                if [ -n "$fpid" ] && [[ "$fpid" =~ ^[0-9]+$ ]] && ps -p "$fpid" > /dev/null 2>&1; then
                    echo -e "${YELLOW}杀死占用GPU设备的进程 PID: $fpid${NC}"
                    kill -9 "$fpid" 2>/dev/null || true
                    killed_count=$((killed_count + 1))
                fi
            done
            echo -e "${GREEN}✓ 使用fuser清理了 $killed_count 个进程${NC}"
        else
            echo -e "${GREEN}✓ fuser未发现占用GPU设备的进程${NC}"
        fi
    fi
    
    # 方法5: 使用nvidia-smi直接解析输出（处理僵尸进程）
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${YELLOW}解析nvidia-smi完整输出查找残留进程...${NC}"
        local smi_output=$(nvidia-smi 2>/dev/null)
        if echo "$smi_output" | grep -q "Processes:"; then
            # 从nvidia-smi输出中提取所有PID
            local process_pids=$(echo "$smi_output" | awk '/Processes:/,0' | grep -E "^\|[[:space:]]*[0-9]+" | awk '{for(i=2;i<=NF;i++) if($i ~ /^[0-9]+$/ && $i > 100) {print $i; break}}' | sort -u)
            if [ -n "$process_pids" ]; then
                for ppid in $process_pids; do
                    if [ -n "$ppid" ] && [[ "$ppid" =~ ^[0-9]+$ ]]; then
                        # 检查进程是否存在
                        if ps -p "$ppid" > /dev/null 2>&1; then
                            echo -e "${YELLOW}杀死nvidia-smi中显示的进程 PID: $ppid${NC}"
                            kill -9 "$ppid" 2>/dev/null || true
                        else
                            echo -e "${YELLOW}进程 $ppid 已不存在（僵尸进程或已清理）${NC}"
                        fi
                    fi
                done
            fi
        fi
    fi
    
    # 等待GPU驱动释放显存
    echo -e "${CYAN}等待GPU驱动释放显存...${NC}"
    sleep 5
    echo -e "${GREEN}✓ GPU清理完成${NC}"
    
    # 显示当前GPU使用情况
    if command -v nvidia-smi &> /dev/null; then
        echo -e "${CYAN}当前GPU使用情况:${NC}"
        nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv,noheader 2>/dev/null || true
        echo ""
        echo -e "${CYAN}GPU计算进程:${NC}"
        nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv 2>/dev/null || echo "无占用GPU的进程"
    fi
}

show_progress() {
    local current=$1
    local total=$2
    local width=40
    local percent=$((current * 100 / total))
    local filled=$((percent * width / 100))
    
    printf "进度: ["
    printf "%${filled}s" | tr ' ' '='
    printf "%$((width - filled))s" | tr ' ' '-'
    printf "] %3d%% (%d/%d)\r" $percent $current $total
}

show_help() {
    cat << 'EOF'
综合评测框架脚本

用法: bash run.sh <command> [options]

【命令】

  cleanup-gpu        强制清理GPU显存中的所有vLLM进程
  start_servers      启动 User 和 Judge 服务
    选项:
      --num-gpus NUM             GPU数量 (默认: 4)
      --user-model PATH          User 模型路径 (默认: Qwen/Qwen2.5-14B-Instruct)
      --judge-model PATH         Judge 模型路径 (默认: Qwen/Qwen2.5-14B-Instruct)
      --log-dir DIR              日志目录 (默认: ./vllm_logs)

  eval-server        使用 vLLM Server 进行评测
    选项:
      --num-gpus NUM             GPU数量 (4或8, 默认: 4)
      --scenario SCENARIO        场景名称 (在线教育: online_education)
      --model MODEL              客服模型名称 (默认: Qwen2.5-32B-Instruct)
      --agent-model-path PATH    客服模型路径 (默认: Qwen/Qwen2.5-32B-Instruct)
      --agent-model-port PORT    客服模型端口 (默认: 8001)
      --skip-agent-startup       跳过客服模型启动
      --output DIR               输出目录 (默认: ./results)
      --num-users NUM            用户数 (默认: 20)
      --max-turns NUM            最大轮次 (默认: 30)
      --scenarios-list LIST      场景列表,逗号分隔 (示例: online_education,ecommerce_refund)
      --evaluation-strategy STR  评测策略 (intent_based/mixed/path_coverage, 默认: intent_based)
      --samples-per-intent NUM   每个Intent采样数 (默认: 3)
      --min-samples-per-path NUM 每条路径最小测试次数 (默认: 5)
      --log-dir DIR              日志目录 (默认: ./vllm_logs)

  eval-api           使用 API 进行评测
    选项:
      --scenario SCENARIO        场景名称 (必需)
      --model MODEL              Judge模型名称 (必需)
      --api-key KEY              API密钥 (必需)
  
  eval-voting        使用多模型投票进行评测（Judge同时调用三个API模型）
    选项:
      --scenario SCENARIO        场景名称 (必需)
      --judge-models MODELS      Judge模型名称列表,逗号分隔 (例如: gpt-4.1,claude-3.5-sonnet,gemini-pro, 必需)
      --api-keys KEYS            对应模型的API密钥列表,逗号分隔 (必需)
      --api-urls URLS            对应模型的API地址列表,逗号分隔 (必需)
      --agent-model-type TYPE    客服模型类型 (api或vllm)
      --agent-model-url URL      客服模型URL
      --agent-model-name NAME    客服模型名称
      --output DIR               输出目录 (默认: ./results)
      --num-users NUM            用户数 (默认: 2)
      --max-turns NUM            最大轮次 (默认: 10)
      --agent-model-type TYPE    客服模型类型 (api或vllm)
      --agent-model-url URL      客服模型URL
      --agent-model-name NAME    客服模型名称
      --output DIR               输出目录 (默认: ./results)
      --num-users NUM            用户数 (默认: 2)
      --max-turns NUM            最大轮次 (默认: 10)
      --scenarios-list LIST      场景列表,逗号分隔
      --evaluation-strategy STR  评测策略 (intent_based/mixed/path_coverage, 默认: intent_based)
      --samples-per-intent NUM   每个Intent采样数 (默认: 3)
      --min-samples-per-path NUM 每条路径最小测试次数 (默认: 5)

  re-score           对已有对话进行重新评分
    选项:
      --num-gpus NUM             GPU数量 (4或8, 默认: 4)
      --dialogue-file FILE       对话文件路径 (必需)
      --judge-model MODEL        Judge模型名称 (默认: Qwen2.5-14B-Instruct)
      --judge-model-path PATH    Judge模型路径 (默认: Qwen/Qwen2.5-14B-Instruct)
      --judge-model-port PORT    Judge模型端口 (默认: 8002)
      --skip-judge-startup       跳过 Judge 模型启动
      --output DIR               输出目录 (默认: ./results)
      --model-type TYPE          模型类型 (vllm或api, 默认: vllm)
      --api-key KEY              如果使用API，提供API密钥
      --api-url URL              如果使用API，提供API地址

【示例】

  # 0. 清理GPU显存（当发现GPU显存未释放时）
  bash run.sh cleanup-gpu

  # 1. 启动服务
  bash run.sh start_servers --num-gpus 4 \
      --user-model Qwen/Qwen2.5-14B-Instruct \
      --judge-model Qwen/Qwen2.5-14B-Instruct

  # 2. 使用vLLM Server评测多个场景 (传统Intent均衡策略)
  bash run.sh eval-server \
      --num-gpus 4 \
      --scenarios-list online_education,ecommerce_refund,telecom_package \
      --model Qwen2.5-32B-Instruct \
      --num-users 20 \
      --max-turns 30

  # 2b. 使用混合评测策略 (Intent均衡 + 路径全覆盖)
  bash run.sh eval-server \
      --num-gpus 4 \
      --scenario online_education \
      --model Qwen2.5-32B-Instruct \
      --max-turns 30 \
      --evaluation-strategy mixed \
      --samples-per-intent 3 \
      --min-samples-per-path 5

  # 3. 使用API评测 (Judge和Agent都用API，不需要GPU)
  bash run.sh eval-api \
      --scenarios-list online_education,ecommerce_refund \
      --model gpt-4.1 \
      --api-key YOUR_KEY \
      --agent-model-type api \
      --agent-model-url https://api.openai.com/v1 \
      --agent-model-name gpt-4.1 \
      --num-users 2 \
      --max-turns 10

  # 4. 重新评分
  bash run.sh re-score \
      --num-gpus 4 \
      --dialogue-file results/online_education/dialogues.jsonl \
      --judge-model Qwen2.5-32B-Instruct \
      --model-type vllm

EOF
}

# ==================== 启动服务函数 ====================
# 默认配置
NUM_GPUS=4  # 支持 4 或 8
USER_MODEL_PATH="${USER_MODEL_PATH:-Qwen/Qwen2.5-14B-Instruct}"
AGENT_MODEL_PATH="${AGENT_MODEL_PATH:-Qwen/Qwen2.5-14B-Instruct}"
JUDGE_MODEL_PATH="${JUDGE_MODEL_PATH:-Qwen/Qwen2.5-14B-Instruct}"
SKIP_AGENT=false

USER_MODEL_PORT=8000
AGENT_MODEL_PORT=8001
JUDGE_MODEL_PORT=8002

# 根据GPU数量设置张量并行度
# 4卡: 每个模型1卡
# 8卡: 每个模型2卡
if [ "$NUM_GPUS" = "4" ]; then
    USER_MODEL_TENSOR_PARALLEL=1
    AGENT_MODEL_TENSOR_PARALLEL=1
    JUDGE_MODEL_TENSOR_PARALLEL=1
    MAX_NUM_SEQS=256
elif [ "$NUM_GPUS" = "8" ]; then
    USER_MODEL_TENSOR_PARALLEL=2
    AGENT_MODEL_TENSOR_PARALLEL=2
    JUDGE_MODEL_TENSOR_PARALLEL=2
    MAX_NUM_SEQS=512
else
    echo -e "${RED}错误: NUM_GPUS必须是4或8${NC}"
    exit 1
fi
# 日志目录 (默认值，可以通过命令行参数覆盖)
LOG_DIR="${LOG_DIR:-./vllm_logs}"

# 关闭函数
stop_server() {
    local name=$1
    local model_label=${2:-""}  # 可选的模型标签
    
    # 如果提供了model_label,使用它来生成文件名；否则使用name
    local file_prefix="${name}"
    if [ -n "$model_label" ]; then
        file_prefix="${model_label}-${name}"
    fi
    
    local pid_file="$LOG_DIR/${file_prefix}.pid"
    
    echo -e "${YELLOW}停止 $name...${NC}"
    
    # 根据模型名称确定端口
    local port=""
    case "$name" in
        "用户模型")
            port=$USER_MODEL_PORT
            ;;
        "客服模型")
            port=$AGENT_MODEL_PORT
            ;;
        "评判模型")
            port=$JUDGE_MODEL_PORT
            ;;
        *)
            echo -e "${RED}未知模型: $name${NC}"
            return 1
            ;;
    esac
    
    # 1. 杀死主进程和所有子进程
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}主进程 PID: $pid (端口: $port)${NC}"
            
            # 找到所有子进程和孙进程(递归查找)
            local all_child_pids=$(pstree -p "$pid" 2>/dev/null | grep -o '([0-9]\+)' | grep -o '[0-9]\+' | grep -v "^$pid$" || true)
            
            # 先尝试优雅关闭主进程
            kill "$pid" 2>/dev/null || true
            sleep 2
            
            # 检查主进程是否已停止
            if ! kill -0 "$pid" 2>/dev/null; then
                echo -e "${GREEN}✓ $name 主进程已停止${NC}"
            else
                echo -e "${YELLOW}$name 未响应，强制停止主进程...${NC}"
                kill -9 "$pid" 2>/dev/null || true
                sleep 1
            fi
            
            # 强制清理所有子进程和孙进程
            if [ -n "$all_child_pids" ]; then
                echo -e "${YELLOW}清理所有子进程 ($(echo $all_child_pids | wc -w)个)...${NC}"
                for cpid in $all_child_pids; do
                    if [ -n "$cpid" ] && kill -0 "$cpid" 2>/dev/null; then
                        kill -9 "$cpid" 2>/dev/null || true
                    fi
                done
                sleep 1
            fi
            
            rm "$pid_file"
        else
            echo -e "${YELLOW}$name (PID: $pid) 未运行${NC}"
            rm "$pid_file"
        fi
    else
        echo -e "${YELLOW}未找到 $name 的PID文件${NC}"
    fi
    
    # 2. 通过端口精确清理残留进程（只清理该端口的进程）
    if [ -n "$port" ]; then
        echo -e "${YELLOW}清理端口 $port 的残留进程...${NC}"
        # 清理占用该端口的所有进程
        local port_pids=$(lsof -ti:$port 2>/dev/null || true)
        if [ -n "$port_pids" ]; then
            for ppid in $port_pids; do
                echo -e "${YELLOW}杀死端口 $port 进程 PID: $ppid${NC}"
                kill -9 "$ppid" 2>/dev/null || true
            done
        fi
        
        # 额外清理：通过进程名+端口精确匹配
        pkill -9 -f "vllm.*--port $port" 2>/dev/null || true
        pkill -9 -f "vllm.*--port=$port" 2>/dev/null || true
    fi
    
    # 等待进程完全停止
    sleep 2
    echo -e "${GREEN}✓ $name 已完全停止${NC}"
}


# 检查GPU显存是否足够
check_gpu_memory() {
    local gpu_id=$1
    local required_gb=${2:-50}  # 默认需要50GB
    
    if ! command -v nvidia-smi &> /dev/null; then
        echo -e "${YELLOW}⚠ nvidia-smi 不可用，跳过显存检查${NC}"
        return 0
    fi
    
    local free_memory=$(nvidia-smi --id=$gpu_id --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null)
    if [ -z "$free_memory" ]; then
        echo -e "${YELLOW}⚠ 无法查询GPU $gpu_id 的显存${NC}"
        return 0
    fi
    
    local free_gb=$((free_memory / 1024))
    echo -e "${CYAN}GPU $gpu_id 可用显存: ${free_gb}GB${NC}"
    
    if [ $free_gb -lt $required_gb ]; then
        echo -e "${RED}✗ GPU $gpu_id 可用显存不足: ${free_gb}GB < ${required_gb}GB${NC}"
        return 1
    fi
    
    echo -e "${GREEN}✓ GPU $gpu_id 显存充足${NC}"
    return 0
}

# 启动函数
start_server_single() {
    local name=$1
    local model_path=$2
    local port=$3
    local tensor_parallel=$4
    local max_num_seqs=${5:-256}  # 默认256
    local gpu_devices=${6:-"0"}   # 指定使用的GPU（如 "0" 或 "0,1"）
    local model_label=${7:-""}    # 可选的模型标签,用于生成日志和PID文件名
    
    # 如果提供了model_label,使用它来生成文件名；否则使用name
    local file_prefix="${name}"
    if [ -n "$model_label" ]; then
        file_prefix="${model_label}-${name}"
    fi
    
    local log_file="$LOG_DIR/${file_prefix}.log"
    
    echo -e "${YELLOW}启动 $name (端口 $port, 张量并行=$tensor_parallel, GPU=$gpu_devices, max_num_seqs=$max_num_seqs)...${NC}"
    
    # 检查GPU显存
    IFS=',' read -ra GPUS <<< "$gpu_devices"
    for gpu in "${GPUS[@]}"; do
        if ! check_gpu_memory "$gpu" 50; then
            echo -e "${RED}GPU $gpu 显存不足，尝试清理该模型的旧进程...${NC}"
            # 只清理当前模型的旧进程，不影响其他模型
            stop_server "$name" 2>/dev/null || true
            sleep 3
            # 再次检查
            if ! check_gpu_memory "$gpu" 50; then
                echo -e "${RED}清理后显存仍然不足，启动可能失败${NC}"
                echo -e "${YELLOW}提示: 如果其他模型也占用了GPU $gpu，请手动停止它们${NC}"
            fi
        fi
    done
    
    # 根据GPU数量设置GPU内存使用率
    local gpu_memory_utilization=0.8
    if [ "$NUM_GPUS" = "8" ]; then
        gpu_memory_utilization=0.85
    fi
    
    
    # 因此所有模型使用相同的启动命令
    
    # 指定GPU设备并启动vLLM服务器
    # qwen3 --chat-template ./qwen3_nonthinking.jinja
    # 获取模型的基础名称（去掉路径部分）
    model_name=$(basename "$model_path")

    # 初始化额外参数变量
    extra_args=""

    # 检查模型名称是否包含 qwen3 或 Qwen3（不区分大小写）
    if [[ "${model_name,,}" == *"qwen3"* ]]; then
        extra_args="--chat-template ./qwen3_nonthinking.jinja"
    fi
    # 启动 vLLM 服务器
    CUDA_VISIBLE_DEVICES=$gpu_devices python -m vllm.entrypoints.openai.api_server \
        --model "$model_path" \
        --port "$port" \
        --host "0.0.0.0" \
        --tensor-parallel-size "$tensor_parallel" \
        --gpu-memory-utilization "$gpu_memory_utilization" \
        --max-num-seqs "$max_num_seqs" \
        --enable-prefix-caching \
        --dtype auto \
        --seed 42 \
        $extra_args \
        > "$log_file" 2>&1 &
    
    # CUDA_VISIBLE_DEVICES=$gpu_devices python -m vllm.entrypoints.openai.api_server \
    #     --model "$model_path" \
    #     --port "$port" \
    #     --host "0.0.0.0" \
    #     --tensor-parallel-size "$tensor_parallel" \
    #     --gpu-memory-utilization "$gpu_memory_utilization" \
    #     --max-num-seqs "$max_num_seqs" \
    #     --enable-prefix-caching \
    #     --dtype auto \
    #     --seed 42 \
    #     > "$log_file" 2>&1 &
    
    local pid=$!
    echo -e "${GREEN}✓ $name 已启动 (PID: $pid)${NC}"
    echo "$pid" > "$LOG_DIR/${file_prefix}.pid"
    
    # 等待服务启动（大模型需要30-60秒）
    echo -e "${YELLOW}等待 $name 启动完成（可能需要30-60秒，请耐心等待...）${NC}"
    
    # 循环检查，每秒检查一次，最多等待60秒
    local retry_count=0
    local max_retries=120
    while [ $retry_count -lt $max_retries ]; do
        sleep 10
        retry_count=$((retry_count + 1))
        
        if check_port "$port"; then
            echo -e "${GREEN}✓ $name 已就绪 (http://localhost:$port)${NC}"
            return 0
        fi
        
        # 每10秒打印一次进度
        if [ $((retry_count % 10)) -eq 0 ]; then
            echo -e "${YELLOW}已等待 ${retry_count}秒，继续等待中...${NC}"
        fi
    done
    
    # 超时后检查
    if check_port "$port"; then
        echo -e "${GREEN}✓ $name 已就绪 (http://localhost:$port)${NC}"
        return 0
    else
        echo -e "${RED}✗ $name 启动失败（已等待60秒），请检查日志: $log_file${NC}"
        echo -e "${RED}最后20行日志：${NC}"
        cat "$log_file" | tail -20
        return 1
    fi
}

start_servers() {
    local num_gpus=4
    local user_model="Qwen/Qwen2.5-14B-Instruct"
    local judge_model="Qwen/Qwen2.5-14B-Instruct"
    # 清理旧进程
    echo -e "${YELLOW}清理可能的旧进程...${NC}"
    # 只清理对应的服务,不使用force_cleanup_gpu避免误杀
    stop_server "用户模型"
    stop_server "评判模型"
    while [[ $# -gt 0 ]]; do
        case $1 in
            --num-gpus)
                num_gpus="$2"
                shift 2
                ;;
            --user-model)
                user_model="$2"
                shift 2
                ;;
            --judge-model)
                judge_model="$2"
                shift 2
                ;;
            --log-dir)
                LOG_DIR="$2"
                shift 2
                ;;
            *)
                print_error "未知选项: $1"
                exit 1
                ;;
        esac
    done
    
    # 创建日志目录
    mkdir -p "$LOG_DIR"
    
    print_header "启动 User 和 Judge 服务"
    print_info "GPU数量: $num_gpus"
    print_info "User模型: $user_model"
    print_info "Judge模型: $judge_model"
    
    # 配置GPU分配 - 统一的分配策略
    # 4卡: User(GPU0), Agent(GPU1), Judge(GPU2), 预留GPU3
    # 8卡: User(GPU0-1), Agent(GPU2-3), Judge(GPU4-5), 预留GPU6-7
    if [ "$num_gpus" = "4" ]; then
        USER_MODEL_TENSOR_PARALLEL=1
        JUDGE_MODEL_TENSOR_PARALLEL=1
        USER_GPU_DEVICES="0"
        JUDGE_GPU_DEVICES="2"
        MAX_NUM_SEQS=256
    elif [ "$num_gpus" = "8" ]; then
        USER_MODEL_TENSOR_PARALLEL=2
        JUDGE_MODEL_TENSOR_PARALLEL=2
        USER_GPU_DEVICES="0,1"
        JUDGE_GPU_DEVICES="4,5"
        MAX_NUM_SEQS=512
    else
        echo -e "${RED}错误: --num-gpus 必须是 4 或 8${NC}"
        exit 1
    fi
    
    # 启动用户模型服务
    start_server_single "用户模型" "$user_model" "$USER_MODEL_PORT" "$USER_MODEL_TENSOR_PARALLEL" "$MAX_NUM_SEQS" "$USER_GPU_DEVICES" || {
    echo -e "${RED}用户模型启动失败${NC}"
    exit 1
    }
    
    # 启动评判模型服务
    start_server_single "评判模型" "$judge_model" "$JUDGE_MODEL_PORT" "$JUDGE_MODEL_TENSOR_PARALLEL" "$MAX_NUM_SEQS" "$JUDGE_GPU_DEVICES" || {
    echo -e "${RED}评判模型启动失败${NC}"
    exit 1
}
    print_success "服务启动完成"
}

# ==================== 评测函数 ====================
run_eval_server() {
    local scenario=""
    local model="Qwen2.5-32B-Instruct"
    local output_dir="./results"
    local num_users=20
    local max_turns=30
    local scenarios_list=""
    local agent_model_path="Qwen/Qwen2.5-32B-Instruct"
    local agent_model_port=8001
    local skip_agent_startup=false
    local num_gpus=4
    local evaluation_strategy="intent_based"
    local samples_per_intent=3
    local min_samples_per_path=5
    local max_workers=16
    local custom_log_dir=""
    
    local log_timestamp=$(date +"%Y%m%d")
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --num-gpus)
                num_gpus="$2"
                shift 2
                ;;
            --scenario)
                scenario="$2"
                shift 2
                ;;
            --model)
                model="$2"
                shift 2
                ;;
            --agent-model-path)
                agent_model_path="$2"
                shift 2
                ;;
            --agent-model-port)
                agent_model_port="$2"
                shift 2
                ;;
            --output)
                output_dir="$2"
                shift 2
                ;;
            --num-users)
                num_users="$2"
                shift 2
                ;;
            --max-turns)
                max_turns="$2"
                shift 2
                ;;
            --scenarios-list)
                scenarios_list="$2"
                shift 2
                ;;
            --skip-agent-startup)
                skip_agent_startup=true
                shift
                ;;
            --evaluation-strategy)
                evaluation_strategy="$2"
                shift 2
                ;;
            --samples-per-intent)
                samples_per_intent="$2"
                shift 2
                ;;
            --min-samples-per-path)
                min_samples_per_path="$2"
                shift 2
                ;;
            --max-workers)
                max_workers="$2"
                shift 2
                ;;
            --log-dir)
                custom_log_dir="$2"
                shift 2
                ;;
            *)
                print_error "未知选项: $1"
                exit 1
                ;;
        esac
    done
    
    if [ -n "$custom_log_dir" ]; then
        LOG_DIR="$custom_log_dir"
    fi
    mkdir -p "$LOG_DIR"
    
    # ==================== 新增：检测客服模型是否已在运行 ====================
    local agent_pid_file="$LOG_DIR/${model}-客服模型.pid"
    local agent_already_running=false
    
    if [ -f "$agent_pid_file" ]; then
        local agent_pid=$(cat "$agent_pid_file")
        # 检查进程是否存在
        if kill -0 "$agent_pid" 2>/dev/null; then
            # 检查端口是否被该进程占用
            if check_port "$agent_model_port"; then
                echo -e "${GREEN}✓ 检测到客服模型 ($model) 已在运行 (PID: $agent_pid, 端口: $agent_model_port)${NC}"
                echo -e "${CYAN}ℹ 跳过客服模型启动，直接使用现有服务${NC}"
                agent_already_running=true
                skip_agent_startup=true
            else
                echo -e "${YELLOW}⚠ PID文件存在但端口未占用，将重新启动客服模型${NC}"
                rm "$agent_pid_file"
            fi
        else
            echo -e "${YELLOW}⚠ PID文件存在但进程未运行，将重新启动客服模型${NC}"
            rm "$agent_pid_file"
        fi
    fi
    # ================================================================
    
    # 清理可能的旧客服模型进程（只在需要启动新服务时执行）
    if [ "$skip_agent_startup" = false ]; then
        echo -e "${YELLOW}清理可能的旧客服模型进程...${NC}"
        # 清理所有客服模型的PID文件(可能有多个不同模型的PID文件)
        for pid_file in "$LOG_DIR"/*-客服模型.pid "$LOG_DIR"/客服模型.pid; do
            if [ -f "$pid_file" ]; then
                # 提取模型标签(如果有)
                local filename=$(basename "$pid_file" .pid)
                if [[ "$filename" == *"-客服模型" ]]; then
                    local old_model_label="${filename%-客服模型}"
                    echo -e "${YELLOW}发现旧的客服模型PID文件: $old_model_label${NC}"
                    stop_server "客服模型" "$old_model_label"
                else
                    stop_server "客服模型"
                fi
            fi
        done
    fi
    
    local run_log="$LOG_DIR/${model}-${log_timestamp}-run.log"
    
    if [ -n "$scenarios_list" ]; then
        IFS=',' read -ra scenarios <<< "$scenarios_list"
    elif [ -n "$scenario" ]; then
        scenarios=("$scenario")
    else
        print_error "必须提供 --scenario 或 --scenarios-list"
        exit 1
    fi
    
    local total_scenarios=${#scenarios[@]}
    local current_scenario=0
    
    # 根据GPU数量配置客服模型
    if [ "$num_gpus" = "4" ]; then
        AGENT_MODEL_TENSOR_PARALLEL=1
        MAX_NUM_SEQS=256
        AGENT_GPU_DEVICES="1"
    elif [ "$num_gpus" = "8" ]; then
        AGENT_MODEL_TENSOR_PARALLEL=2
        MAX_NUM_SEQS=512
        AGENT_GPU_DEVICES="2,3"
    else
        print_error "--num-gpus 必须是 4 或 8"
        exit 1
    fi
    AGENT_MODEL_TENSOR_PARALLEL=2
    AGENT_GPU_DEVICES="1,3"
    MAX_NUM_SEQS=512
    # 启动客服模型服务（如果需要且没有跳过）
    if [ "$skip_agent_startup" = false ]; then
        print_header "启动客服模型服务" | tee -a "$run_log"
        print_info "GPU数量: $num_gpus" | tee -a "$run_log"
        print_info "客服模型: $agent_model_path" | tee -a "$run_log"
        print_info "端口: $agent_model_port" | tee -a "$run_log"
        print_info "GPU设备: $AGENT_GPU_DEVICES" | tee -a "$run_log"
        
        # 启动客服模型
        start_server_single "客服模型" "$agent_model_path" "$agent_model_port" "$AGENT_MODEL_TENSOR_PARALLEL" "$MAX_NUM_SEQS" "$AGENT_GPU_DEVICES" "$model" | tee -a "$run_log" || {
            echo -e "${RED}客服模型启动失败${NC}" | tee -a "$run_log"
            exit 1
        }
    elif [ "$agent_already_running" = true ]; then
        print_info "⊙ 使用已运行的客服模型服务" | tee -a "$run_log"
    else
        print_info "⊘ 跳过客服模型启动" | tee -a "$run_log"
    fi
    
    echo "" | tee -a "$run_log"
    
    for scenario in "${scenarios[@]}"; do
        current_scenario=$((current_scenario + 1))
        
        print_header "[$current_scenario/$total_scenarios] 评测场景: $scenario" | tee -a "$run_log"
        print_info "模型: $model | 用户数: $num_users | 最大轮次: $max_turns | 并发数: $max_workers" | tee -a "$run_log"
        
        scenario_output="$output_dir/$scenario"
        mkdir -p "$scenario_output"
        
        echo "" | tee -a "$run_log"
        python3 run_evaluation_with_llm.py \
            --scenario "$scenario" \
            --model "$model" \
            --eval-mode vllm \
            --output "$scenario_output" \
            --num-users "$num_users" \
            --max-turns "$max_turns" \
            --max-workers "$max_workers" \
            --evaluation-strategy "$evaluation_strategy" \
            --samples-per-intent "$samples_per_intent" \
            --min-samples-per-path "$min_samples_per_path" 2>&1 | tee -a "$run_log"
        
        echo "" | tee -a "$run_log"
        print_success "场景 [$current_scenario/$total_scenarios] 完成: $scenario" | tee -a "$run_log"
        echo "" | tee -a "$run_log"
    done
    
    print_success "所有场景评测完成" | tee -a "$run_log"
    print_info "日志文件: $run_log" | tee -a "$run_log"
    echo "清理所有占卡程序" | tee -a "$run_log"
    bash /kill_gpu_processes.sh --all | tee -a "$run_log"
}


run_eval_api() {
    local scenario=""
    local model=""
    local api_key=""
    local agent_model_type="api"
    local agent_model_url=""
    local agent_model_name=""
    local output_dir="./results"
    local num_users=2
    local max_turns=10
    local scenarios_list=""
    local evaluation_strategy="intent_based"
    local samples_per_intent=3
    local min_samples_per_path=5
    local max_workers=16  # API模式可以支持更高并发
    
    # 创建日志文件
    local log_timestamp=$(date +"%Y%m%d_%H%M%S")
    # local run_log="$LOG_DIR/${log_timestamp}-run.log"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --scenario)
                scenario="$2"
                shift 2
                ;;
            --model)
                model="$2"
                shift 2
                ;;
            --api-key)
                api_key="$2"
                shift 2
                ;;
            --agent-model-type)
                agent_model_type="$2"
                shift 2
                ;;
            --agent-model-url)
                agent_model_url="$2"
                shift 2
                ;;
            --agent-model-name)
                agent_model_name="$2"
                shift 2
                ;;
            --output)
                output_dir="$2"
                shift 2
                ;;
            --num-users)
                num_users="$2"
                shift 2
                ;;
            --max-turns)
                max_turns="$2"
                shift 2
                ;;
            --scenarios-list)
                scenarios_list="$2"
                shift 2
                ;;
            --evaluation-strategy)
                evaluation_strategy="$2"
                shift 2
                ;;
            --samples-per-intent)
                samples_per_intent="$2"
                shift 2
                ;;
            --min-samples-per-path)
                min_samples_per_path="$2"
                shift 2
                ;;
            --max-workers)
                max_workers="$2"
                shift 2
                ;;
            *)
                print_error "未知选项: $1"
                exit 1
                ;;
        esac
    done
    local run_log="$LOG_DIR/${model}-${log_timestamp}-run.log"
    # 验证必需参数
    if [ -z "$model" ]; then
        print_error "--model 是必需的" | tee -a "$run_log"
        exit 1
    fi
    if [ -z "$api_key" ]; then
        print_error "--api-key 是必需的" | tee -a "$run_log"
        exit 1
    fi
    
    # 如果提供了scenarios-list，使用列表；否则使用单个scenario
    if [ -n "$scenarios_list" ]; then
        IFS=',' read -ra scenarios <<< "$scenarios_list"
    elif [ -n "$scenario" ]; then
        scenarios=("$scenario")
    else
        print_error "必须提供 --scenario 或 --scenarios-list" | tee -a "$run_log"
        exit 1
    fi
    
    local total_scenarios=${#scenarios[@]}
    local current_scenario=0
    
    for scenario in "${scenarios[@]}"; do
        current_scenario=$((current_scenario + 1))
        
        print_header "[$current_scenario/$total_scenarios] 评测场景 (API): $scenario" | tee -a "$run_log"
        print_info "Judge模型: $model" | tee -a "$run_log"
        print_info "客服模型: $agent_model_name (类型: $agent_model_type)" | tee -a "$run_log"
        print_info "用户数: $num_users | 最大轮次: $max_turns" | tee -a "$run_log"
        
        scenario_output="$output_dir/$scenario"
        mkdir -p "$scenario_output"
        
        echo "" | tee -a "$run_log"
        python3 run_evaluation_with_llm.py \
            --scenario "$scenario" \
            --model "$model" \
            --eval-mode api \
            --api-key "$api_key" \
            --agent-model-type "$agent_model_type" \
            --agent-model-url "$agent_model_url" \
            --agent-model-name "$agent_model_name" \
            --output "$scenario_output" \
            --num-users "$num_users" \
            --max-turns "$max_turns" \
            --max-workers "$max_workers" \
            --evaluation-strategy "$evaluation_strategy" \
            --samples-per-intent "$samples_per_intent" \
            --min-samples-per-path "$min_samples_per_path" 2>&1 | tee -a "$run_log"
        
        echo "" | tee -a "$run_log"
        print_success "场景 [$current_scenario/$total_scenarios] 完成: $scenario" | tee -a "$run_log"
        echo "" | tee -a "$run_log"
    done
    
    print_success "所有场景API评测完成" | tee -a "$run_log"
    print_info "日志文件: $run_log" | tee -a "$run_log"
}

# ==================== 多模型投票评测函数 ====================

run_eval_voting() {
    local scenario=""
    local judge_models=""
    local api_keys=""
    local api_urls=""
    local agent_model_type="api"
    local agent_model_url="http://localhost:8001"
    local agent_model_name=""
    local agent_model_path="${AGENT_MODEL_PATH:-Qwen/Qwen2.5-32B-Instruct}"
    local agent_model_port=8001
    local skip_agent_startup=false
    local num_gpus=4
    local output_dir="./results"
    local num_users=2
    local max_turns=10
    local scenarios_list=""
    local evaluation_strategy="intent_based"
    local samples_per_intent=3
    local min_samples_per_path=5
    local max_workers=16  # API模式可以支持更高并发
    

    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --log-dir)
                custom_log_dir="$2"
                shift 2
                ;;
            --num-gpus)
                num_gpus="$2"
                shift 2
                ;;
            --model)
                model="$2"
                shift 2
                ;;
            --scenario)
                scenario="$2"
                shift 2
                ;;
            --judge-models)
                judge_models="$2"
                shift 2
                ;;
            --api-keys)
                api_keys="$2"
                shift 2
                ;;
            --api-urls)
                api_urls="$2"
                shift 2
                ;;
            --agent-model-type)
                agent_model_type="$2"
                shift 2
                ;;
            --agent-model-path)
                agent_model_path="$2"
                shift 2
                ;;
            --agent-model-url)
                agent_model_url="$2"
                shift 2
                ;;
            --agent-model-port)
                agent_model_port="$2"
                shift 2
                ;;
            --agent-api-key)
                agent_api_key="$2"
                shift 2
                ;;
            --agent-model-name)
                agent_model_name="$2"
                shift 2
                ;;
            --skip-agent-startup)
                skip_agent_startup=true
                shift
                ;;
            --output)
                output_dir="$2"
                shift 2
                ;;
            --num-users)
                num_users="$2"
                shift 2
                ;;
            --max-turns)
                max_turns="$2"
                shift 2
                ;;
            --scenarios-list)
                scenarios_list="$2"
                shift 2
                ;;
            --evaluation-strategy)
                evaluation_strategy="$2"
                shift 2
                ;;
            --samples-per-intent)
                samples_per_intent="$2"
                shift 2
                ;;
            --min-samples-per-path)
                min_samples_per_path="$2"
                shift 2
                ;;
            --max-workers)
                max_workers="$2"
                shift 2
                ;;
            *)
                print_error "未知选项: $1" | tee -a "$run_log"
                exit 1
                ;;
        esac
    done
    
        # 创建日志文件
    if [ -n "$custom_log_dir" ]; then
        LOG_DIR="$custom_log_dir"
    fi
    mkdir -p "$LOG_DIR"
    local log_timestamp=$(date +"%Y%m%d")
    local run_log="$LOG_DIR/${model}-${log_timestamp}-run.log"

    # 验证必需参数
    if [ -z "$judge_models" ]; then
        print_error "--judge-models 是必需的" | tee -a "$run_log"
        exit 1
    fi
    if [ -z "$api_keys" ]; then
        print_error "--api-keys 是必需的" | tee -a "$run_log"
        exit 1
    fi
    if [ -z "$api_urls" ]; then
        print_error "--api-urls 是必需的" | tee -a "$run_log"
        exit 1
    fi
    
    # 如果提供了scenarios-list，使用列表；否则使用单个scenario
    if [ -n "$scenarios_list" ]; then
        IFS=',' read -ra scenarios <<< "$scenarios_list"
    elif [ -n "$scenario" ]; then
        scenarios=("$scenario")
    else
        print_error "必须提供 --scenario 或 --scenarios-list" | tee -a "$run_log"
        exit 1
    fi
    
    local total_scenarios=${#scenarios[@]}
    local current_scenario=0
    
    # ==================== 【投票模式】Agent vLLM Server 自动启动 ====================
    # 仅当 agent-model-type 为 vllm 时启动
    if [ "$agent_model_type" = "vllm" ]; then
        print_header "多模型投票评测模式 - 自动启动客服vLLM Server" | tee -a "$run_log"
        print_info "客服模型类型: $agent_model_type (本地vLLM)" | tee -a "$run_log"
        
        # 检测客服模型是否已在运行
        local agent_pid_file="$LOG_DIR/${model}-客服模型.pid"
        local agent_already_running=false
        
        if [ -f "$agent_pid_file" ]; then
            local agent_pid=$(cat "$agent_pid_file")
            # 检查进程是否存在
            if kill -0 "$agent_pid" 2>/dev/null; then
                # 检查端口是否被该进程占用
                if check_port "$agent_model_port"; then
                    echo -e "${GREEN}✓ 检测到客服模型已在运行 (PID: $agent_pid, 端口: $agent_model_port)${NC}" | tee -a "$run_log"
                    echo -e "${CYAN}ℹ 跳过客服模型启动，直接使用现有服务${NC}" | tee -a "$run_log"
                    agent_already_running=true
                    skip_agent_startup=true
                else
                    echo -e "${YELLOW}⚠ PID文件存在但端口未占用，将重新启动客服模型${NC}" | tee -a "$run_log"
                    rm "$agent_pid_file"
                fi
            else
                echo -e "${YELLOW}⚠ PID文件存在但进程未运行，将重新启动客服模型${NC}" | tee -a "$run_log"
                rm "$agent_pid_file"
            fi
        fi
        
        # 清理可能的旧客服进程（只在需要启动新服务时执行）
        if [ "$skip_agent_startup" = false ]; then
            echo -e "${YELLOW}清理可能的旧客服模型进程...${NC}" | tee -a "$run_log"
            for pid_file in "$LOG_DIR"/*-客服模型.pid "$LOG_DIR"/客服模型.pid; do
                if [ -f "$pid_file" ]; then
                    local filename=$(basename "$pid_file" .pid)
                    if [[ "$filename" == *"-客服模型" ]]; then
                        local old_model_label="${filename%-客服模型}"
                        echo -e "${YELLOW}发现旧的客服模型PID文件: $old_model_label${NC}" | tee -a "$run_log"
                        stop_server "客服模型" "$old_model_label" 2>/dev/null || true
                    fi
                fi
            done
        fi
        
        # 根据模型大小和GPU数量配置客服模型
        # 检测model参数中是否包含72B字符串
        local is_large_model=false
        if [[ "$model" == *"72B"* ]]; then
            is_large_model=true
            echo -e "${CYAN}ℹ 检测到72B大模型: $model${NC}" | tee -a "$run_log"
        fi
        
        if [ "$num_gpus" = "4" ]; then
            # 4卡配置
            if [ "$is_large_model" = true ]; then
                # 72B模型使用2张卡（GPU 1 和 3）
                AGENT_MODEL_TENSOR_PARALLEL=2
                MAX_NUM_SEQS=256
                AGENT_GPU_DEVICES="1,3"
                echo -e "${CYAN}ℹ 72B模型配置: 使用2张GPU (1,3) 进行张量并行${NC}" | tee -a "$run_log"
            else
                # 32B或更小模型使用1张卡（GPU 1）
                AGENT_MODEL_TENSOR_PARALLEL=1
                MAX_NUM_SEQS=256
                AGENT_GPU_DEVICES="1"
            fi
            AGENT_MODEL_TENSOR_PARALLEL=2
            AGENT_GPU_DEVICES="1,3"
        elif [ "$num_gpus" = "8" ]; then
            # 8卡配置
            if [ "$is_large_model" = true ]; then
                # 72B模型使用4张卡（GPU 2,3 或其他组合）
                AGENT_MODEL_TENSOR_PARALLEL=4
                MAX_NUM_SEQS=512
                AGENT_GPU_DEVICES="2,3,5,6"
                echo -e "${CYAN}ℹ 72B模型配置: 使用4张GPU (2,3,5,6) 进行张量并行${NC}" | tee -a "$run_log"
            else
                # 32B或更小模型使用2张卡（GPU 2,3）
                AGENT_MODEL_TENSOR_PARALLEL=2
                MAX_NUM_SEQS=512
                AGENT_GPU_DEVICES="2,3"
            fi
        else
            print_error "--num-gpus 必须是 4 或 8" | tee -a "$run_log"
            exit 1
        fi
        
        # 启动客服模型服务（如果需要且没有跳过）
        if [ "$skip_agent_startup" = false ]; then
            print_header "启动客服模型服务（vLLM）" | tee -a "$run_log"
            print_info "GPU数量: $num_gpus" | tee -a "$run_log"
            print_info "客服模型: $agent_model_path" | tee -a "$run_log"
            print_info "端口: $agent_model_port" | tee -a "$run_log"
            print_info "GPU设备: $AGENT_GPU_DEVICES" | tee -a "$run_log"
            
            # 启动客服模型
            start_server_single "客服模型" "$agent_model_path" "$agent_model_port" "$AGENT_MODEL_TENSOR_PARALLEL" "$MAX_NUM_SEQS" "$AGENT_GPU_DEVICES"  2>&1 | tee -a "$run_log" || {
                echo -e "${RED}客服模型启动失败${NC}" | tee -a "$run_log"
                exit 1
            }
        elif [ "$agent_already_running" = true ]; then
            print_info "⊙ 使用已运行的客服模型服务 (http://localhost:$agent_model_port)" | tee -a "$run_log"
        else
            print_info "⊘ 跳过客服模型启动，使用外部服务: $agent_model_url" | tee -a "$run_log"
        fi
        
        echo "" | tee -a "$run_log"
    else
        #客服使用 API 模式
        print_header "多模型投票评测模式 (API模式)" | tee -a "$run_log"
        print_info "Judge模型列表: $judge_models (API调用)" | tee -a "$run_log"
        print_info "客服模型: $agent_model_name (API调用)" | tee -a "$run_log"
        print_info "Agent API地址: $agent_model_url" | tee -a "$run_log"
    fi
    
    echo "" | tee -a "$run_log"
    
    for scenario in "${scenarios[@]}"; do
        current_scenario=$((current_scenario + 1))
        
        print_header "[$current_scenario/$total_scenarios] 投票评测场景: $scenario" | tee -a "$run_log"
        
        scenario_output="$output_dir/$scenario"
        mkdir -p "$scenario_output"
        
        echo "" | tee -a "$run_log"
        python3 run_evaluation_with_llm.py \
            --scenario "$scenario" \
            --model "$model" \
            --eval-mode voting \
            --judge-models "$judge_models" \
            --api-keys "$api_keys" \
            --api-urls "$api_urls" \
            --agent-model-type "$agent_model_type" \
            --agent-model-url "$agent_model_url" \
            --api-key "$agent_api_key" \
            --agent-model-port "$agent_model_port" \
            --agent-model-name "$agent_model_name" \
            --output "$scenario_output" \
            --num-users "$num_users" \
            --max-turns "$max_turns" \
            --max-workers "$max_workers" \
            --evaluation-strategy "$evaluation_strategy" \
            --samples-per-intent "$samples_per_intent" \
            --min-samples-per-path "$min_samples_per_path" 2>&1 | tee -a "$run_log"
        
        echo "" | tee -a "$run_log"
        print_success "场景 [$current_scenario/$total_scenarios] 投票评测完成: $scenario" | tee -a "$run_log"
        echo "" | tee -a "$run_log"
    done
    
    print_success "所有场景投票评测完成" | tee -a "$run_log"
    print_info "日志文件: $run_log" | tee -a "$run_log"
}

# ==================== 重新评分函数 ====================

re_score_dialogues() {
    local dialogue_file=""
    local judge_model="Qwen2.5-14B-Instruct"
    local judge_model_path="Qwen/Qwen2.5-14B-Instruct"
    local judge_model_port=8002
    local output_dir="./results"
    local model_type="vllm"
    local api_key=""
    local api_url=""
    local skip_judge_startup=false
    local num_gpus=4
    
    # 创建日志文件
    local log_timestamp=$(date +"%Y%m%d_%H%M%S")
    local run_log="$LOG_DIR/${log_timestamp}-run.log"
    
    echo -e "${YELLOW}清理可能的旧评判模型进程...${NC}" | tee -a "$run_log"
    # 只需要stop_server就够了,不要调用cleanup_port避免误杀其他进程
    stop_server "评判模型" | tee -a "$run_log"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --num-gpus)
                num_gpus="$2"
                shift 2
                ;;
            --dialogue-file)
                dialogue_file="$2"
                shift 2
                ;;
            --judge-model)
                judge_model="$2"
                shift 2
                ;;
            --judge-model-path)
                judge_model_path="$2"
                shift 2
                ;;
            --judge-model-port)
                judge_model_port="$2"
                shift 2
                ;;
            --output)
                output_dir="$2"
                shift 2
                ;;
            --model-type)
                model_type="$2"
                shift 2
                ;;
            --api-key)
                api_key="$2"
                shift 2
                ;;
            --api-url)
                api_url="$2"
                shift 2
                ;;
            --skip-judge-startup)
                skip_judge_startup=true
                shift
                ;;
            *)
                print_error "未知选项: $1" | tee -a "$run_log"
                exit 1
                ;;
        esac
    done
    
    # 验证必需参数
    if [ -z "$dialogue_file" ]; then
        print_error "--dialogue-file 是必需的" | tee -a "$run_log"
        exit 1
    fi
    if [ ! -f "$dialogue_file" ]; then
        print_error "文件不存在: $dialogue_file" | tee -a "$run_log"
        exit 1
    fi
    
    print_header "重新评分已有对话" | tee -a "$run_log"
    print_info "对话文件: $dialogue_file" | tee -a "$run_log"
    print_info "Judge模型: $judge_model" | tee -a "$run_log"
    print_info "模型类型: $model_type" | tee -a "$run_log"
    print_info "GPU数量: $num_gpus" | tee -a "$run_log"
    
    # 根据GPU数量配置Judge模型
    if [ "$num_gpus" = "4" ]; then
        JUDGE_MODEL_TENSOR_PARALLEL=1
        MAX_NUM_SEQS=256
        JUDGE_GPU_DEVICES="2"
    elif [ "$num_gpus" = "8" ]; then
        JUDGE_MODEL_TENSOR_PARALLEL=2
        MAX_NUM_SEQS=512
        JUDGE_GPU_DEVICES="4,5"
    else
        print_error "--num-gpus 必须是 4 或 8" | tee -a "$run_log"
        exit 1
    fi
    
    print_info "GPU设备: $JUDGE_GPU_DEVICES" | tee -a "$run_log"
    
    # 启动评判模型服务（如果需要且没有跳过）
    if [ "$model_type" = "vllm" ] && [ "$skip_judge_startup" = false ]; then
        start_server_single "评判模型" "$judge_model_path" "$judge_model_port" "$JUDGE_MODEL_TENSOR_PARALLEL" "$MAX_NUM_SEQS" "$JUDGE_GPU_DEVICES" 2>&1 | tee -a "$run_log" || {
        echo -e "${RED}评判模型启动失败${NC}" | tee -a "$run_log"
        exit 1
    }
    fi
    
    # 计算总对话数
    local total_lines=$(wc -l < "$dialogue_file")
    
    mkdir -p "$output_dir"
    
    # 创建Python脚本进行重新评分
    python3 << PYTHON_SCRIPT 2>&1 | tee -a "$run_log"
import json
import sys
from pathlib import Path
import time

# 添加框架路径
sys.path.insert(0, '/0SAGE-bench/Mult-turn-dialogue')

from framework.evaluator.evaluator import ModelJudgedEvaluator
from framework.llm_integration.llm_client import LLMClient

# 初始化
dialogue_file = "$dialogue_file"
judge_model = "$judge_model"
output_dir = "$output_dir"
model_type = "$model_type"

# 初始化LLM客户端
if model_type == "vllm":
    llm_client = LLMClient(model_type="vllm", model_name=judge_model)
elif model_type == "api":
    llm_client = LLMClient(
        model_type="api",
        model_name=judge_model,
        api_key="$api_key",
        api_url="$api_url"
    )
else:
    print(f"不支持的模型类型: {model_type}", file=sys.stderr)
    sys.exit(1)

evaluator = ModelJudgedEvaluator(judge_model=llm_client, debug=False)

# 读取并重新评分
output_file = Path(output_dir) / f"dialogues_rescored_{int(time.time())}.jsonl"
total_lines = $total_lines
processed = 0

print(f"正在读取对话文件: {dialogue_file}")
print(f"输出文件: {output_file}")
print()

with open(dialogue_file, 'r') as infile, open(output_file, 'w') as outfile:
    for line in infile:
        try:
            dialogue_data = json.loads(line)
            
            # 提取对话信息
            dialogue = dialogue_data.get('dialogue', [])
            
            # 重新评分
            score_result = evaluator.evaluate_chat_quality(
                chat_text="\\n".join([msg.get('content', '') for msg in dialogue]),
                user_message=dialogue[0].get('content', '') if dialogue else "",
                dialogue_context=dialogue
            )
            
            # 更新对话数据
            dialogue_data['judge_score'] = score_result.get('score', 0)
            dialogue_data['judge_details'] = score_result.get('details', {})
            
            # 写入输出文件
            outfile.write(json.dumps(dialogue_data, ensure_ascii=False) + '\\n')
            
            processed += 1
            percent = int(100 * processed / total_lines)
            filled = int(40 * processed / total_lines)
            bar = '=' * filled + '-' * (40 - filled)
            print(f'重新评分: [{bar}] {percent}% ({processed}/{total_lines})', end='\r')
            
        except Exception as e:
            print(f"错误处理行 {processed + 1}: {e}", file=sys.stderr)
            continue

print(f'\\n重新评分完成: {output_file}')
PYTHON_SCRIPT
    
    print_success "重新评分完成" | tee -a "$run_log"
    print_info "日志文件: $run_log" | tee -a "$run_log"
}

# ==================== 主函数 ====================

main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    case "$1" in
        cleanup-gpu)
            print_header "清理GPU显存"
            echo ""
            echo -e "${CYAN}清理前状态:${NC}"
            show_gpu_status
            echo ""
            force_cleanup_gpu
            echo ""
            echo -e "${CYAN}清理后状态:${NC}"
            show_gpu_status
            print_success "清理完成"
            ;;
        start_servers)
            shift
            start_servers "$@"
            ;;
        eval-server)
            shift
            run_eval_server "$@"
            ;;
        eval-api)
            shift
            run_eval_api "$@"
            ;;
        eval-voting)
            shift
            run_eval_voting "$@"
            ;;
        re-score)
            shift
            re_score_dialogues "$@"
            ;;
        help)
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
