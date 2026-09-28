# CP4 — Scaling & Reliability: stateless, probe, shutdown

**Điểm:** 20/20 · **Trạng thái:** xanh
**Lệnh kiểm tra:** `pytest tests/test_cp4.py -v`

## Kết quả test thật

```
$ pytest tests/test_cp1.py tests/test_cp2.py tests/test_cp3.py tests/test_cp4.py -q
70 passed, 1 warning in 5.93s
```

Tổng CP1–CP4: 13 + 16 + 22 + 19 = **70 test, 70 pass**.

## Đã làm

### `app/store.py` — lịch sử trong Redis

```python
def ping(self) -> bool:
    try:
        return bool(self.client.ping())
    except Exception:
        return False

def append(self, user_id, role, content):
    key = self._key(user_id)
    self.client.rpush(key, json.dumps({"role": role, "content": content}, ensure_ascii=False))
    self.client.ltrim(key, -HISTORY_MAX_MESSAGES, -1)   # giữ N phần tử CUỐI
    self.client.expire(key, HISTORY_TTL_SECONDS)

def get_history(self, user_id):
    raw = self.client.lrange(self._key(user_id), 0, -1)
    return [json.loads(item) for item in raw]
```

- `ltrim(key, -N, -1)` giữ N message **mới nhất**. `ltrim(key, 0, N-1)` giữ nhầm
  phần **cũ nhất** — `test_cat_bot_lich_su_qua_dai` bắt đúng lỗi này.
- `ping()` nuốt mọi exception và trả `False`. `/ready` cần câu trả lời rõ ràng
  (503), không phải traceback 500.

### `app/main.py` — `/ready`

```python
def ready(store: ConversationStore = Depends(get_store)):
    if lifecycle.shutting_down:
        return JSONResponse(status_code=503, content={"status": "shutting_down"})
    if not store.ping():
        return JSONResponse(status_code=503, content={"status": "not ready", "redis": False})
    return {"status": "ready", "redis": True}
```

`ready` **phải** có tham số dependency, `health` **không được** có.
`test_ready_khac_health` kiểm tra đúng điều đó bằng `inspect.signature`.

### `app/lifecycle.py` — SIGTERM/SIGINT

```python
def request_shutdown(self, signum=None, frame=None):
    self.shutting_down = True
    previous = self._previous.get(signum)
    if callable(previous):
        previous(signum, frame)

def install(self):
    for sig in (signal.SIGTERM, signal.SIGINT):
        self._previous[sig] = signal.getsignal(sig)   # nhớ handler cũ
        signal.signal(sig, self.request_shutdown)     # rồi mới ghi đè
```

- Truyền `self.request_shutdown` (tham chiếu hàm), **không** phải
  `self.request_shutdown()` (đã gọi).
- **Gọi lại handler cũ là bắt buộc.** Handler đó thuộc uvicorn, là thứ thật
  sự dừng server. Không gọi lại thì app bật cờ "đang tắt" rồi chạy tiếp mãi mãi
  cho tới khi orchestrator hết kiên nhẫn và SIGKILL — đúng cái graceful shutdown
  định tránh.
- Handler chạy xen giữa bytecode, nên **không làm gì nặng** ở đây (không gọi
  mạng, không ghi file).

## ⭐ Bằng chứng quan trọng nhất: scale 3 instance thật

Đây là bằng chứng thực thi cho luận điểm cốt lõi của CP4.

### Vấn đề gặp phải — và cách sửa

Chạy `docker compose up --scale agent=3` thất bại:

```
Error response from daemon: failed to set up container networking:
driver failed programming external connectivity on endpoint ...-agent-3:
Bind for 0.0.0.0:8000 failed: port is already allocated
```

**Nguyên nhân:** trong `docker-compose.yml`, `ports: "8000:8000"` là cổng
**HOST**. Chỉ một container được giữ cổng đó, nên scale là xung đột theo bản
chất — không phải lỗi cấu hình.

Cách đúng: các instance worker **không** giữ cổng host, và đặt một nginx làm
reverse proxy / load balancer làm cổng vào duy nhất. File
`docker-compose.scale.yml` (ngoài rubric) làm đúng điều đó bằng tag `!reset`
của Compose v2:

```yaml
services:
  agent:
    ports: !reset null      # xoá ports khai báo ở docker-compose.yml
    deploy:
      replicas: 3
  nginx:
    image: nginx:1-alpine
    ports: ["8000:80"]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
```

Dùng như sau (KHÔNG dùng file này khi chấm CP2 — `docker-compose.yml` mới là
file mà test đọc):

```bash
docker compose down
docker compose -f docker-compose.yml -f docker-compose.scale.yml up -d --scale agent=3
```

### Kết quả

```
$ docker compose -f docker-compose.yml -f docker-compose.scale.yml ps
SERVICE   STATUS
agent     Up 2 minutes (healthy)
agent     Up 2 minutes (healthy)
agent     Up 2 minutes (healthy)
nginx     Up About a minute
redis     Up 2 minutes (healthy)
```

Gọi 6 lần `/ask` với **cùng một `X-User-Id: sv-scale`**, đi qua nginx
round-robin:

```
  request 1 -> history_length=0
  request 2 -> history_length=2
  request 3 -> history_length=4
  request 4 -> history_length=6
  request 5 -> history_length=8
  request 6 -> history_length=10
```

### Xác nhận request thật sự rơi vào cả 3 container

```
$ for c in $(docker compose ... ps -q agent); do
    echo "$c: $(docker logs "$c" | grep -c sv-scale) dong log chua sv-scale"; done
  efbd44e4b4b3f4f76b0e... : 2 dong log chua sv-scale
  77b1c586e2fa6a4a4d2e... : 2 dong log chua sv-scale
  8a70bd178a4978e3d9f5... : 2 dong log chua sv-scale
```

**2 request trên mỗi container, cả 3 đều có.** Round-robin là thật, và
`history_length` vẫn tăng đều 0→2→4→6→8→10 xuyên suốt 3 instance.

**Nếu state nằm trong dict Python của mỗi process, con số này sẽ nhảy về 0
mỗi khi request rơi sang container khác.** Đó chính là câu 9 của
`exercises.md`, và giờ đã có số liệu thật để trả lời.

## LLM provider (ngoài rubric)

`app/llm_client.py` + `get_provider()` cho phép `/ask` dùng LLM thật qua API
OpenAI-compatible, chọn bằng `LLM_MODE`:

| `LLM_MODE` | Provider | Ở đâu dùng |
|---|---|---|
| `mock` (mặc định) | `utils/mock_llm.ask_llm` | test, CI, bản deploy |
| `real` | `app/llm_client.complete` | máy bạn (LMStudio), hoặc cloud provider |

Hai provider cùng trả về `{answer, tokens_in, tokens_out, cost_usd}` nên
`/ask` không cần biết đang nói chuyện với ai.

Kiểm chứng chuẩn hoá URL (chấp nhận cả gốc rời lẫn đã kèm `/v1`):

```
$ python -c "from app.llm_client import chat_completions_url as u; ..."
http://127.0.0.1:1234    -> http://127.0.0.1:1234/v1/chat/completions
http://127.0.0.1:1234/v1 -> http://127.0.0.1:1234/v1/chat/completions
http://127.0.0.1:1234/   -> http://127.0.0.1:1234/v1/chat/completions
https://api.openai.com   -> https://api.openai.com/v1/chat/completions
```

### ⚠ Cạm bẫy `conftest.py` — cần nhớ

`tests/conftest.py` gọi `load_dotenv(ROOT / ".env")`, rồi mới ghi đè
`AGENT_API_KEY` và `REDIS_URL` bằng `os.environ[...]=`. **`LLM_MODE` không nằm
trong hai dòng ghi đè đó.**

Hệ quả: nếu để `LLM_MODE=real` trong `.env`, thì **mọi lần chạy `pytest` cũng
thành `real`** → CP3/CP4 đỏ hàng loạt nếu LMStudio đang tắt, và `cost_usd`
không còn tất định nếu LMStudio đang chạy.

**Cách dùng đúng:** `.env` giữ `LLM_MODE=mock` vĩnh viễn. Muốn dùng LMStudio
thật thì ghi đè ở shell, chỉ đúng cho tiến trình đó:

```bash
LLM_MODE=real .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
```

Trên cloud, `127.0.0.1` là **chính container cloud**, nên `LLM_BASE_URL` phải
trỏ tới endpoint từ Internet.

## Câu hỏi tự kiểm tra

1. **Gộp `/health` và `/ready` làm một rồi cho kiểm tra Redis — kể lại theo
   đúng thứ tự sự kiện:** Redis mất kết nối → (1) endpoint trả 503 → (2) cả 3
   container bị đánh dấu liveness fail → (3) orchestrator restart **cả 3** →
   (4) app khởi động lại thì lại cần Redis → (5) Redis chưa kịp tỉnh → vòng lặp
   restart. Sự cố nhỏ ở Redis thành sự cố lớn ở toàn cụm.
2. **Vì sao `def health()` không được có tham số, còn `def ready(store=...)` thì
   bắt buộc có?** `/health` trả lời "process này có cần restart không" — phụ
   thuộc Redis nghĩa là sự cố Redis kéo theo restart cả cụm. `/ready` trả lời
   "có nên đẩy traffic vào instance này không" — kiểm tra dependency là đúng
   nhiệm vụ của nó.
3. **Bỏ dòng gọi lại handler cũ thì chuyện gì xảy ra sau SIGTERM?** App bật cờ
   `shutting_down`, `/health` bắt đầu trả 503, nhưng **server không dừng** →
   vẫn nhận request, vẫn trả 503 cho mọi thứ, cho tới khi orchestrator hết
   kiên nhẫn SIGKILL → mất request đang xử lý dở. Đúng cái graceful shutdown
   định tránh.
