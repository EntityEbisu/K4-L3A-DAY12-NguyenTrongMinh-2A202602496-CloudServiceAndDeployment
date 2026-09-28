# CP1 — 12-Factor Config, Health & Logging

**Điểm:** 15/15 · **Trạng thái:** xanh
**Lệnh kiểm tra:** `pytest tests/test_cp1.py -v`

## Kết quả test thật

```
tests/test_cp1.py::TestConfig::test_settings_co_du_cac_truong PASSED
tests/test_cp1.py::TestConfig::test_doc_gia_tri_tu_bien_moi_truong PASSED
tests/test_cp1.py::TestConfig::test_gia_tri_mac_dinh_hop_ly PASSED
tests/test_cp1.py::TestConfig::test_thieu_api_key_thi_fail_fast PASSED
tests/test_cp1.py::TestConfig::test_khong_hardcode_secret PASSED
tests/test_cp1.py::TestStructuredLogging::test_log_event_tra_ve_json_hop_le PASSED
tests/test_cp1.py::TestStructuredLogging::test_log_event_gan_them_truong_tuy_y PASSED
tests/test_cp1.py::TestStructuredLogging::test_level_luon_viet_thuong PASSED
tests/test_cp1.py::TestStructuredLogging::test_log_ra_stdout_dung_mot_dong PASSED
tests/test_cp1.py::TestStructuredLogging::test_timestamp_dung_dinh_dang_iso PASSED
tests/test_cp1.py::TestHealthEndpoint::test_health_tra_ve_200 PASSED
tests/test_cp1.py::TestHealthEndpoint::test_health_khong_can_api_key PASSED
tests/test_cp1.py::TestHealthEndpoint::test_health_khong_phu_thuoc_dependency_nao PASSED

13 passed, 1 warning in 0.80s
```

## Đã làm

### `app/config.py` — 6 trường Settings

```python
port: int = 8000
agent_api_key: str          # KHÔNG có giá trị mặc định — cố ý
redis_url: str = "redis://localhost:6379/0"
rate_limit_per_minute: int = 10
monthly_budget_usd: float = 10.0
log_level: str = "INFO"
```

`agent_api_key` không có default. `test_thieu_api_key_thi_fail_fast` xoá biến
`AGENT_API_KEY` rồi khẳng định `Settings(_env_file=None)` ném `ValidationError`.

Ngoài ra có 4 trường LLM (`llm_mode`, `llm_base_url`, `llm_api_key`,
`llm_model`) — **không thuộc rubric**, xem [cp4-scaling-reliability.md](cp4-scaling-reliability.md#llm-provider).

### `app/logging_utils.py` — log một dòng JSON

```python
record = {
    "event": event,
    "level": level.lower(),
    "timestamp": utc_now_iso(),
    **fields,
}
line = json.dumps(record, ensure_ascii=False)
print(line, file=sys.stdout, flush=True)
return line
```

`ensure_ascii=False` giữ dấu tiếng Việt. **Không** `indent` — cloud gom log
theo dòng, JSON xuống dòng là một log bị vỡ thành nhiều mảnh.
`flush=True` để Docker/nhật ký cloud không bị đệm lại.

### `app/main.py` — `/health`

```python
def health():
    if lifecycle.shutting_down:
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    return {"status": "ok", "service": SERVICE_NAME, "version": SERVICE_VERSION}
```

Nhánh 503 viết luôn ở CP1 (thuộc CP4) để không phải sửa lại file sau.
`def health()` **không có tham số nào** — `test_health_khong_phu_thuoc_dependency_nao`
dùng `inspect.signature` và fail nếu có bất kỳ tham số.

## Câu hỏi tự kiểm tra

1. **Vì sao `agent_api_key` không có default?** Vì default nghĩa là app vẫn
   khởi động được khi bạn quên set secret trên cloud — nó chạy, trả lời
   request, và bạn chỉ biết có chuyện khi nhìn hoá đơn. Không default = fail
   fast lúc khởi động, lúc bạn còn đang nhìn màn hình và còn sửa được.
2. **Nếu `/health` gọi Redis thì chuyện gì xảy ra khi Redis chết một nhịp?**
   Liveness trả 503 → orchestrator thấy container "chết" → restart **toàn bộ
   cụm** → biến sự cố nhỏ (Redis chập chờn) thành sự cố lớn (mất dịch vụ).
3. **`ensure_ascii=False` giữ gì? Còn nếu `indent=2` thì cloud đọc log ra sao?**
   Giữ dấu tiếng Việt đọc được ngay. Còn `indent=2` thì một sự kiện in ra
   nhiều dòng, và cloud gom log theo dòng nên nó thành N mảnh vô nghĩa —
   lọc/đếm/cảnh báo theo `event` không còn tách được biên từng event.
