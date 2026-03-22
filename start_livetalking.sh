#!/bin/bash
# LiveTalking 启动脚本
# 使用 musetalk 模型 + xiaoqing avatar
#
# 使用前需设置环境变量（或在 runtime_config.json 里配置）：
#   export DASHSCOPE_API_KEY=sk-xxxx
#   或直接在页面 /dashboard.html 的"编辑"里填写 API Key

cd /data/home/jiangjinghao/LiveTalking
source venv/bin/activate

# HuggingFace 镜像（国内加速）
export HF_ENDPOINT=https://hf-mirror.com

python app.py \
    --transport webrtc \
    --model musetalk \
    --avatar_id xiaoqing \
    --listenport 5402 \
    "$@"
