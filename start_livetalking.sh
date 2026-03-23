#!/bin/bash
# LiveTalking 启动脚本
# 使用 musetalk 模型 + xiaoqing avatar
#
# 使用前需设置环境变量（或在 runtime_config.json 里配置）：
#   export DASHSCOPE_API_KEY=sk-xxxx
#   或直接在页面 /dashboard.html 的"编辑"里填写 API Key

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/livetalking.pid"

cd "$SCRIPT_DIR"

# 检查是否已有实例在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "LiveTalking 已在运行 (PID=$OLD_PID)，请先执行 stop_livetalking.sh 停止。"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

source venv/bin/activate

# HuggingFace 镜像（国内加速）
export HF_ENDPOINT=https://hf-mirror.com

python app.py \
    --transport webrtc \
    --model musetalk \
    --avatar_id xiaoqing \
    --tts seedtts \
    --listenport 5402 \
    "$@" &

echo $! > "$PID_FILE"
echo "LiveTalking 已启动 (PID=$(cat $PID_FILE))，日志: $SCRIPT_DIR/livetalking.log"
echo "访问: http://172.18.140.100:5402/dashboard.html"
