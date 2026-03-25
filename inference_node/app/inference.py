"""
DeepSeek API 调用封装（使用 OpenAI SDK，兼容 DeepSeek 官方接口）。
"""
import os
import time

from openai import AsyncOpenAI


async def run_inference(prompt: str, max_tokens: int, temperature: float) -> dict:
    """
    调用 DeepSeek Chat Completions API，返回 {result, duration_ms}。
    按官方文档：base_url="https://api.deepseek.com"，model="deepseek-chat"
    """
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    t0 = time.monotonic()
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
        stream=False,
    )

    result = response.choices[0].message.content
    duration_ms = int((time.monotonic() - t0) * 1000)
    return {"result": result, "duration_ms": duration_ms}
