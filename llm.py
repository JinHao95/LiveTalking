import time
import os
import json
from basereal import BaseReal
from logger import logger

_RUNTIME_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'runtime_config.json')
_DEFAULT_CONFIG = {
    "llm_api_key": "",
    "llm_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "llm_model": "qwen-plus",
    "system_prompt": "你是一个友善的AI助手。",
}

def _load_cfg() -> dict:
    cfg = dict(_DEFAULT_CONFIG)
    if os.path.exists(_RUNTIME_CONFIG_FILE):
        with open(_RUNTIME_CONFIG_FILE, 'r', encoding='utf-8') as f:
            cfg.update(json.load(f))
    if not cfg.get("llm_api_key"):
        cfg["llm_api_key"] = os.getenv("DASHSCOPE_API_KEY", "")
    return cfg

def llm_response(message, nerfreal: BaseReal):
    start = time.perf_counter()
    cfg = _load_cfg()
    from openai import OpenAI
    client = OpenAI(
        api_key=cfg["llm_api_key"],
        base_url=cfg["llm_base_url"],
    )
    end = time.perf_counter()
    logger.info(f"llm Time init: {end-start}s")
    completion = client.chat.completions.create(
        model=cfg["llm_model"],
        messages=[
            {'role': 'system', 'content': cfg["system_prompt"]},
            {'role': 'user', 'content': message},
        ],
        stream=True,
        stream_options={"include_usage": True}
    )
    result = ""
    first = True
    for chunk in completion:
        if len(chunk.choices) > 0:
            if first:
                end = time.perf_counter()
                logger.info(f"llm Time to first chunk: {end-start}s")
                first = False
            msg = chunk.choices[0].delta.content
            lastpos = 0
            for i, char in enumerate(msg):
                if char in ",.!;:，。！？：；":
                    result = result + msg[lastpos:i+1]
                    lastpos = i + 1
                    if len(result) > 10:
                        logger.info(result)
                        nerfreal.put_msg_txt(result)
                        result = ""
            result = result + msg[lastpos:]
    end = time.perf_counter()
    logger.info(f"llm Time to last chunk: {end-start}s")
    nerfreal.put_msg_txt(result)
