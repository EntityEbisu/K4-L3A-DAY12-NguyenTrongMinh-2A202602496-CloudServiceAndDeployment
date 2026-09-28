"""Client cho API OpenAI-compatible (LMStudio, llama.cpp, vLLM, OpenAI...).

Chỉ được dùng khi LLM_MODE=real. Mặc định /ask dùng utils/mock_llm.py —
xem get_provider() trong app/main.py.

Hợp đồng: complete() trả về đúng shape của utils.mock_llm.ask_llm
({answer, tokens_in, tokens_out, cost_usd}) nên hai provider hoán đổi
được bằng LLM_MODE mà không phải sửa /ask.

Cách dùng trực tiếp:
    from app.llm_client import complete
    result = complete("Deploy là gì?", history=[{"role": "user", "content": "..."}])
    result["answer"], result["tokens_in"], result["tokens_out"], result["cost_usd"]
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import get_settings

DEFAULT_TIMEOUT_SECONDS = 60.0

# Giá tham chiếu, cùng thang với utils/mock_llm.py
PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.00060


def chat_completions_url(base_url: str) -> str:
    """Chuẩn hoá base URL thành URL đầy đủ của /chat/completions.

    LMStudio, llama.cpp và vLLM đều phục vụ endpoint ở ``/v1/chat/completions``.
    Người dùng có thể cấu hình gốc rời (``http://127.0.0.1:1234``) hoặc đã
    kèm sẵn ``/v1``; hàm này chấp nhận cả hai. Viết ``/v1/v1`` vẫn 404, và
    đó là lỗi cấu hình chứ không phải lỗi code.
    """
    base = base_url.rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/chat/completions"


def is_configured() -> bool:
    """Đủ cấu hình để gọi API thật chưa?"""
    settings = get_settings()
    return bool(settings.llm_base_url and settings.llm_model)


def complete(question: str, history: list[dict] | None = None) -> dict:
    """Gọi /chat/completions, trả về cùng shape với utils.mock_llm.ask_llm."""
    settings = get_settings()
    if not is_configured():
        raise RuntimeError(
            "LLM_MODE=real nhung thieu LLM_BASE_URL hoac LLM_MODEL. "
            "Dat ca hai vao .env roi chay lai."
        )

    # history phải được gửi lên: nếu không, store vẫn ghi lịch sử nên test vẫn
    # xanh, nhưng LLM không thấy ngữ cảnh — tức tính năng chính của agent hỏng.
    messages = [
        {"role": turn.get("role", "user"), "content": turn.get("content", "")}
        for turn in (history or [])
    ]
    messages.append({"role": "user", "content": question})

    body = json.dumps(
        {"model": settings.llm_model, "messages": messages, "temperature": 0.7}
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    # LMStudio mặc định không yêu cầu khoá; provider cloud thì bắt buộc có.
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    request = urllib.request.Request(
        chat_completions_url(settings.llm_base_url),
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        raise RuntimeError(
            f"LLM tra ve {err.code}. Kiem tra LLM_MODEL co dung khong, va "
            "LLM_BASE_URL co tro den /v1/chat/completions khong."
        ) from err
    except urllib.error.URLError as err:
        raise RuntimeError(
            f"khong goi duoc LLM tai {settings.llm_base_url}: {err}. "
            "Neu la LMStudio, kiem tra server da chay va model da load chua."
        ) from err

    answer = payload["choices"][0]["message"]["content"]
    usage = payload.get("usage") or {}
    tokens_in = int(usage.get("prompt_tokens", 0))
    tokens_out = int(usage.get("completion_tokens", 0))

    return {
        "answer": answer,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(
            tokens_in / 1000 * PRICE_INPUT_PER_1K
            + tokens_out / 1000 * PRICE_OUTPUT_PER_1K,
            8,
        ),
    }
