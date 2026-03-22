import time
import os
import re
import json
from basereal import BaseReal
from logger import logger

_RUNTIME_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'runtime_config.json')
_DEFAULT_CONFIG = {
    "llm_api_key": "",
    "llm_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "llm_model": "qwen-plus",
    "system_prompt": "你是一个友善的AI助手。",
    "enable_emotion_tag": False,   # 是否让 LLM 输出情感标签（配合 Seed-TTS）
}

# 当 enable_emotion_tag=True 时，追加到 system_prompt 末尾的指令
_EMOTION_TAG_INSTRUCTION = """

# 语音控制规则（必须严格遵守，每句话都要带）
每一句话开头必须加控制指令，格式：[情绪-语速-语调-音量] 话术内容

控制指令维度（只能用以下选项，不可自定义）：
- 情绪：enthusiastic（热情）/ gentle（温柔）/ urgent（急促）/ calm（平静）/ playful（俏皮）
- 语速：fast / normal / slow
- 语调：high / normal / low
- 音量：loud / normal / soft

规则：
1. 每一句话都必须有控制指令，一条不能省；
2. 指令格式固定为四个维度用"-"连接，如 [enthusiastic-fast-high-loud]；
3. 指令后紧跟话术，不加空行，不加其他解释；
4. 根据语境自然切换情绪，不要每句都用同一个。

示例（两句话，每句都有指令）：
[enthusiastic-fast-high-loud] 家人们！今天直播间爆款口红终于补货了！
[gentle-slow-normal-soft] 敏感肌的宝宝们别担心，这款完全不刺激。"""

def _load_cfg() -> dict:
    cfg = dict(_DEFAULT_CONFIG)
    if os.path.exists(_RUNTIME_CONFIG_FILE):
        with open(_RUNTIME_CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg.update(json.load(f))
    if not cfg.get("llm_api_key"):
        cfg["llm_api_key"] = os.getenv("DASHSCOPE_API_KEY", "")
    return cfg

def _build_system_prompt(cfg: dict) -> str:
    prompt = cfg.get("system_prompt", "你是一个友善的AI助手。")
    if cfg.get("enable_emotion_tag"):
        prompt += _EMOTION_TAG_INSTRUCTION
    return prompt

def llm_response(message, nerfreal: BaseReal):
    start = time.perf_counter()
    cfg = _load_cfg()
    logger.info(f"[LLM] >>> 用户输入: {message}")
    logger.info(f"[LLM] 模型: {cfg['llm_model']}  base_url: {cfg['llm_base_url']}")
    from openai import OpenAI
    client = OpenAI(
        api_key=cfg["llm_api_key"],
        base_url=cfg["llm_base_url"],
    )
    end = time.perf_counter()
    logger.info(f"[LLM] 初始化耗时: {end-start:.3f}s")

    system_prompt = _build_system_prompt(cfg)
    logger.info(f"[LLM] system_prompt: {system_prompt[:80]}...")
    try:
        completion = client.chat.completions.create(
            model=cfg["llm_model"],
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': message},
            ],
            stream=True,
            stream_options={"include_usage": True}
        )
    except Exception as e:
        logger.error(f"[LLM] 请求失败: {e}")
        return

    result = ""
    full_reply = ""
    last_tag = ""   # 记录上一句的情感标签，供无标签句子继承
    first = True
    for chunk in completion:
        if len(chunk.choices) > 0:
            if first:
                end = time.perf_counter()
                logger.info(f"[LLM] 首token延迟: {end-start:.3f}s")
                first = False
            msg = chunk.choices[0].delta.content
            if not msg:
                continue
            full_reply += msg
            lastpos = 0
            for i, char in enumerate(msg):
                if char in ",.!;:，。！？：；":
                    result = result + msg[lastpos:i+1]
                    lastpos = i + 1
                    # 标签未闭合时不切句
                    if result.count('[') > result.count(']'):
                        continue
                    # 标签已闭合但正文内容太短（标签后实际内容 < 5字），继续积累
                    text_body = re.sub(r'\[.*?\]', '', result).strip()
                    if result.count('[') > 0 and len(text_body) < 5:
                        continue
                    if len(result) > 10:
                        # 若本片段没有标签，且上一句有标签，则继承
                        tag_match = re.match(r'^\s*\[([^\[\]]+)\]', result)
                        if tag_match:
                            last_tag = tag_match.group(0).strip()
                        elif last_tag and cfg.get("enable_emotion_tag"):
                            result = last_tag + ' ' + result
                            logger.info(f"[LLM→TTS] 继承标签: {last_tag}")
                        logger.info(f"[LLM→TTS] 发送片段: {result}")
                        nerfreal.put_msg_txt(result)
                        result = ""
            result = result + msg[lastpos:]
    end = time.perf_counter()
    logger.info(f"[LLM] 完整回复: {full_reply}")
    logger.info(f"[LLM] 总耗时: {end-start:.3f}s")
    if result:
        # 最后片段也继承标签
        tag_match = re.match(r'^\s*\[([^\[\]]+)\]', result)
        if not tag_match and last_tag and cfg.get("enable_emotion_tag"):
            result = last_tag + ' ' + result
        logger.info(f"[LLM→TTS] 发送最后片段: {result}")
    nerfreal.put_msg_txt(result)
