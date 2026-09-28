# CP3 — API Security: auth, rate limit, cost guard

**Điểm:** 20/20 · **Trạng thái:** xanh
**Lệnh kiểm tra:** `pytest tests/test_cp3.py -v`

## Kết quả test thật

Chạy cùng CP1 để xác nhận phần làm thêm không phá gì:

```
$ pytest tests/test_cp1.py tests/test_cp3.py -q
35 passed, 1 warning in 1.01s
```

(13 của CP1 + 22 của CP3.)

## Ba lớp bảo vệ, ba câu hỏi khác nhau

| Lớp | Câu hỏi | Mã lỗi |
|---|---|---|
| Authentication | Bạn là ai? | 401 |
| Rate limiting | Bạn gọi có quá nhanh không? | 429 |
| Cost guard | Bạn đã tiêu hết ngân sách chưa? | 402 |

## Đã làm

### `app/auth.py` — so sánh khoá constant-time

```python
expected = get_settings().agent_api_key
provided = x_api_key or ""

if not secrets.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid or missing API key",
    )

return x_user_id or ANONYMOUS_USER
```

`test_so_sanh_key_chong_timing_attack` dùng `ast` để tìm **lời gọi thật**
`compare_digest` trong `app/auth.py` — nhắc trong comment không được, phải gọi.
`.encode("utf-8")` ở cả hai vế vì `compare_digest` chỉ nhận chuỗi ASCII.

`X-User-Id` là **đơn vị tính tiền và rate limit**, không phải danh tính đã
xác thực — nó tuỳ ý, client tự đặt. Không có nó thì ra `anonymous`.

### `app/rate_limiter.py` — sliding window bằng Sorted Set

```python
def hit_count(self, user_id, now=None):
    now = now if now is not None else time.time()
    key = self._key(user_id)
    self.client.zremrangebyscore(key, 0, now - WINDOW_SECONDS)
    return int(self.client.zcard(key))

def check(self, user_id, now=None):
    now = now if now is not None else time.time()
    key = self._key(user_id)

    if self.hit_count(user_id, now) >= self.limit:          # kiểm tra TRƯỚC
        raise HTTPException(status_code=429, detail="rate limit exceeded",
                            headers={"Retry-After": str(WINDOW_SECONDS)})

    self.client.zadd(key, {f"{now}:{uuid.uuid4().hex}": now})  # ghi nhận SAU
    self.client.expire(key, WINDOW_SECONDS)
```

Hai điểm dễ sai:

- **Kiểm tra trước, ghi sau.** Ghi trước rồi mới đếm sẽ chặn nhầm ngay ở
  request thứ `limit`.
- **Member phải DUY NHẤT** (`timestamp:uuid4`). Hai request cùng timestamp sẽ
  ghi đè nhau trong sorted set và ta đếm thiếu.

### `app/cost_guard.py` — ngân sách theo user/tháng

```python
def spent(self, user_id, month=None):
    raw = self.client.get(self._key(user_id, month))
    return 0.0 if raw is None else float(raw)

def check(self, user_id, estimated_cost=0.0, month=None):
    if self.spent(user_id, month) + estimated_cost > self.budget:
        raise HTTPException(status_code=402, detail="monthly budget exceeded")

def record(self, user_id, cost, month=None):
    key = self._key(user_id, month)
    total = self.client.incrbyfloat(key, cost)
    self.client.expire(key, KEY_TTL_SECONDS)
    return float(total)
```

- `>` chứ không phải `>=`: ngân sách bằng đúng số tiền vẫn còn hạn.
- `incrbyfloat` cộng dồn **nguyên tử trên server** — hai request song song không
  ghi đè lên nhau như đọc-rồi-ghi ở tầng ứng dụng.
- TTL 40 ngày để còn đối soát sang tháng sau.

### `app/main.py` — `/ask`

```python
limiter.check(user_id)      # 429
guard.check(user_id)        # 402

history = store.get_history(user_id)
provider = get_provider()
result = provider(payload.question, history)

store.append(user_id, "user", payload.question)
store.append(user_id, "assistant", result["answer"])
guard.record(user_id, result["cost_usd"])
log_event("ask_completed", user_id=user_id, ...)
```

**Thứ tự là điểm mấu chốt:** tiền mất ở bước gọi LLM. Kiểm tra sau khi đã gọi
thì vừa trả tiền vừa trả lỗi. `guard.record()` phải **sau** khi trả lời —
`test_ask_ghi_nhan_chi_phi` khẳng định nếu thiếu thì ngân sách không bao giờ
tăng và cost guard trở nên vô dụng.

`history_length` = `len(history)` **trước** khi append, nên lượt hỏi đầu là 0.

## Kiểm chứng thật trên container

```
$ curl -s -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
    -H "X-API-Key: <khoá> -H "X-User-Id: sv-real" -d '{"question":"Deploy la gi?"}'
{"answer":"Ngang gon: Deploy la gi phu thuoc vao ba yeu to — cau hinh qua bien moi truong, health check de orchestrator biet trang thai, va gioi han tai nguyen.","user_id":"sv-real","history_length":0,"cost_usd":2.265e-05,"tokens":{"in":3,"out":37}}
```

```
$ docker compose logs agent | grep ask_completed | tail -1
{"event": "ask_completed", "level": "info", "timestamp": "2026-09-28T09:05:37.062467+00:00", "user_id": "sv-real", "tokens_in": 3, "tokens_out": 37, "cost_usd": 2.265e-05}
```

Đây cũng là dòng log thật dùng cho **câu 2 của `exercises.md`**: một dòng JSON
cho phép hỏi *"user nào tiêu nhiều tiền nhất hôm nay"* và *"tỷ lệ lỗi 5 phút
qua là bao nhiêu"* — `print("đã trả lời xong")` không trả lời được câu nào.

## Câu hỏi tự kiểm tra

1. **Cửa sổ trượt vs phút đồng hồ:** với hạn 10/phút đếm theo phút đồng hồ, gửi
   10 lúc 10:00:59 + 10 lúc 10:01:01 = **20 request trong 2 giây** mà vẫn "đúng
   luật", vì mỗi phút đều chưa vượt 10.
2. **Rate limit vs cost guard:**
   - Rate limit cho qua, cost guard chặn: user gọi 3 request/phút (thấp hơn hạn
     10) nhưng mỗi request dài 50k token → tổng tiền vượt `MONTHLY_BUDGET_USD`.
   - Cost guard cho qua, rate limit chặn: user gửi 15 request nhỏ trong một phút
     (tổng tiền chưa tới ngân sách) → 429.
3. **Vì sao member ZSET phải là UUID chứ không phải timestamp thuần?** Vì hai
   request có thể trùng timestamp cùng mili-giây. Member trùng nghĩa là chỉ có
   1 entry, nên `zcard` đếm thiếu và hạn mức bị nới lỏng âm thầm.
4. **Vì sao 401 phải kiểm tra trước 429?** Request không có khoá dừng ở
   `Depends(verify_api_key)` — trước cả khi chạm vào `limiter.check`. Nếu ngược
   lại, kẻ xấu gửi request vô khoá cũng tiêu quota của người khác.
   `test_401_duoc_kiem_tra_truoc_429` kiểm tra đúng điều này.
