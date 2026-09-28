# Thông Tin Deploy — Checkpoint 5

> Điền file này sau khi deploy xong. `pytest tests/test_cp5.py` đọc file này
> để tìm địa chỉ service của bạn và gọi thử.
>
> **Chỉ ghi TÊN biến môi trường, tuyệt đối không dán giá trị API key vào đây.**
> Repo này công khai — dán khóa vào là mất khóa.

## Thông Tin Học Viên

| Mục | Nội dung |
|-----|----------|
| Họ và tên | Nguyễn Trọng Minh |
| Mã học viên | 2A202602496 |
| Repo | https://github.com/EntityEbisu/K4-L3A-DAY12-NguyenTrongMinh-2A202602496-CloudServiceAndDeployment |

## Service

| Mục | Nội dung |
|-----|----------|
| Public URL | https://day12-agent-3gtj.onrender.com |
| Platform | Render (Blueprint, docker runtime) |
| Ngày deploy | 28/09/2026 |

## Biến Môi Trường Đã Set Trên Cloud

Ghi tên biến và **nguồn giá trị**, không ghi giá trị:

| Biến | Đã set | Ghi chú |
|------|--------|---------|
| `PORT` | ✅ | platform tự gán |
| `AGENT_API_KEY` | ✅ | sinh bằng `secrets.token_urlsafe(32)`, đặt trong Render dashboard, không nằm trong repo |
| `REDIS_URL` | ✅ | Render Key Value `day12-redis`, tự gán qua `fromService` trong `render.yaml` |
| `RATE_LIMIT_PER_MINUTE` | ✅ | 10 |
| `MONTHLY_BUDGET_USD` | ✅ | 10.0 |
| `LOG_LEVEL` | ✅ | INFO |

## Lệnh Kiểm Tra

Thay `<URL>` bằng Public URL ở trên:

```bash
# 1. Liveness — mong đợi 200 {"status":"ok"}
curl -i <URL>/health

# 2. Readiness — mong đợi 200 {"status":"ready"} (đã nối được Redis)
curl -i <URL>/ready

# 3. Không có API key — mong đợi 401
curl -i -X POST <URL>/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'

# 4. Có API key — mong đợi 200 kèm câu trả lời
curl -i -X POST <URL>/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $AGENT_API_KEY" \
  -H "X-User-Id: sv-test" \
  -d '{"question":"Deploy là gì?"}'

# 5. Rate limit — gọi 15 lần, những lần cuối phải trả 429
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code} " -X POST <URL>/ask \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $AGENT_API_KEY" \
    -H "X-User-Id: sv-test" \
    -d '{"question":"test"}'
done; echo
```

## Kết Quả Chạy Thật

Dán output của các lệnh trên vào đây:

```
$ curl -i https://day12-agent-3gtj.onrender.com/health
HTTP/1.1 200 OK
Date: Mon, 28 Sep 2026 13:24:18 GMT
Content-Type: application/json
Transfer-Encoding: chunked
Connection: keep-alive
rndr-id: 649c7789-c7e9-4add
Server: cloudflare
vary: Accept-Encoding
x-render-origin-server: uvicorn
cf-cache-status: DYNAMIC
CF-RAY: a423114cfaac84a9-HKG
alt-svc: h3=":443"; ma=86400

{"status":"ok","service":"day12-agent","version":"1.0.0"}

$ curl -i https://day12-agent-3gtj.onrender.com/ready
HTTP/1.1 200 OK
Date: Mon, 28 Sep 2026 13:24:19 GMT
Content-Type: application/json
Transfer-Encoding: chunked
Connection: keep-alive
rndr-id: 3d3c63fc-8e87-46cf
Server: cloudflare
vary: Accept-Encoding
x-render-origin-server: uvicorn
cf-cache-status: DYNAMIC
CF-RAY: a42311515e6902cc-HKG
alt-svc: h3=":443"; ma=86400

{"status":"ready","redis":true}

$ curl -i -X POST https://day12-agent-3gtj.onrender.com/ask \
    -H "Content-Type: application/json" -d "{\"question\":\"Hello\"}"
HTTP/1.1 401 Unauthorized
Date: Mon, 28 Sep 2026 13:24:19 GMT
Content-Type: application/json
Transfer-Encoding: chunked
Connection: keep-alive
cf-cache-status: DYNAMIC
rndr-id: bada764b-89ab-4e1e
Server: cloudflare
vary: Accept-Encoding
x-render-origin-server: uvicorn
CF-RAY: a4231155bee5983b-HKG
alt-svc: h3=":443"; ma=86400

{"detail":"invalid or missing API key"}
```

**Ý nghĩa từng kết quả:**

- `/health` → **200**: liveness trả lời được mà không hề chạm vào Redis — cũng
  chính là endpoint mà `render.yaml` khai báo làm `healthCheckPath`.
- `/ready` → **200** với `"redis":true`: bằng chứng biến `REDIS_URL` đã được
  Render tự gắn từ Key Value `day12-redis` qua `fromService`, và app đã nối
  được tới Redis thật. Nếu biến này sai, đây là chỗ sẽ trả 503.
- `/ask` không khoá → **401** với `invalid or missing API key`: bằng chứng
  `AGENT_API_KEY` trên Render **đang có hiệu lực**. Nếu khoá sai, mọi request
  cũng 401 — nhưng khi đó ta không phân biệt được "khoá sai" với "khoá đúng
  nhưng hết hạn". Kiểm tra `/ready` 200 cùng lúc giúp xác nhận service thật
  sự đang chạy bình thường.

## Ảnh Chụp Màn Hình

Đặt ảnh trong thư mục `screenshots/`:

- `screenshots/dashboard.png` — trang quản lý service trên platform
- `screenshots/health.png` — kết quả gọi `/health` từ trình duyệt hoặc curl
