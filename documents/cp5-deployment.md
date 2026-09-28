# CP5 — Cloud Deployment

**Điểm:** 0/15 — **CHƯA LÀM**
**Lệnh kiểm tra:** `pytest tests/test_cp5.py -v`

## Trạng thái

CP5 là checkpoint **duy nhất còn thiếu**, và là phần **không thể làm thay bạn**
vì cần tài khoản Render, dashboard, và tên miền công khai thật.

Kết quả `grade.py` hiện tại:

```
  CP5 — Cloud Deployment: service chạy thật        0/8 test (5 bỏ qua)    0.0/15
```

## Những gì đã chuẩn bị sẵn

| Hạng mục | Trạng thái |
|---|---|
| `Dockerfile` | ✅ production-ready, đã build thật (310MB), chạy non-root, có HEALTHCHECK, đọc `$PORT` |
| `render.yaml` | ✅ có sẵn từ lab — Blueprint tạo web service + Key Value (Redis), `REDIS_URL` tự nối |
| `/health` | ✅ trả 200, không phụ thuộc dependency |
| `/ready` | ✅ trả 503 nếu Redis chết |
| `/ask` | ✅ 401 không có khoá, 200 có khoá |
| Code local | ✅ chạy thật trong container, đã kiểm chứng bằng curl |

Nói cách khác: **deploy không gặp rào cản kỹ thuật nào.** Chỉ còn thao tác tài
khoản.

## Việc cần làm — theo đúng thứ tự

### 1. Đẩy code lên GitHub (chưa có gì cần sửa thêm)

```bash
git push origin main
gh repo view --json visibility
```

Repo **phải public** — `test_badge_bao_passing` trong bonus tải badge không
cần auth.

### 2. Tạo Blueprint trên Render

1. <https://render.com> → **New** → **Blueprint** → chọn repo
   `K4-L3A-DAY12-NguyenTrongMinh-2A202602496-CloudServiceAndDeployment`
2. Render đọc `render.yaml`: tạo web service `day12-agent` (docker, `plan:
   free`) + Key Value `day12-redis`, tự nối `REDIS_URL` qua `fromService`.
3. Khi hỏi `AGENT_API_KEY` → sinh khoá khác khoá local:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
4. **Create**, chờ build xanh (3–6 phút).

### 3. Xác minh (các request online duy nhất)

```bash
URL=https://<domain-cua-ban>.onrender.com
curl -i "$URL/health"     # mong đợi 200 {"status":"ok",...}
curl -i "$URL/ready"      # mong đợi 200 {"status":"ready","redis":true}
curl -i -X POST "$URL/ask" -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'   # mong đợi 401
```

**Chẩn đoán khi đỏ:**

| Triệu chứng | Nguyên nhân |
|---|---|
| `/ready` trả 503 | `REDIS_URL` chưa gắn vào service agent. Dashboard → Environment |
| Health check timeout | App đang bind `127.0.0.1` hoặc cố định cổng 8000 thay vì đọc `$PORT` |
| Container restart liên tục | Thiếu `AGENT_API_KEY` → `ValidationError` lúc khởi động |
| Request đầu chậm 30–60s | Free tier ngủ đông — **bình thường**, không phải lỗi |

### 4. Biến môi trường LLM trên Render — tuỳ chọn

**Bắt buộc:** không dùng `127.0.0.1`. Trong container Render ở Oregon,
`127.0.0.1` là chính container đó.

| | Không set (đơn giản) | Dùng provider cloud |
|---|---|---|
| `LLM_MODE` | không set → `mock` | `real` |
| `LLM_BASE_URL` | không set | URL provider, có TLS |
| `LLM_MODEL` | không set | tên model |
| `LLM_API_KEY` | không set | **secret trên Render** |
| CP5 | xanh | xanh |

**Khuyến nghị: bắt đầu bằng "không set".** CP5 không đòi LLM thật, bản deploy
mock luôn xanh và không tốn tiền. Đổi sang `real` sau khi CP5 đã xanh — không
cần sửa code, chỉ thêm biến rồi deploy lại.

### 5. Tạo Deploy Hook + GitHub Secrets (cho phần bonus)

- Render → service → **Settings** → **Deploys** → **Create Deploy Hook** → copy
  URL.
- GitHub → **Settings** → **Secrets and variables** → **Actions**:
  - tab **Secrets** → `RENDER_DEPLOY_HOOK_URL` (bắt buộc, không công khai)
  - tab **Variables** → `PUBLIC_URL`, và `DEPLOY_ENABLED` = `"false"` lúc đầu

### 6. Điền `DEPLOYMENT.md`

Máy kiểm tra rất chặt, cần đúng:

- **Không còn chuỗi `(điền` nào** trong cả file (`require_filled()` quét toàn bộ).
- Viết tên biến **có backtick**: `` `AGENT_API_KEY` `` — **không** viết
  `AGENT_API_KEY: <giá trị>`, vì `test_khong_lo_secret_trong_tai_lieu` soi regex
  `AGENT_API_KEY\s*[:=]\s*(\S+)` và fail nếu thấy chuỗi ASCII ≥12 ký tự.
- Xoá hẳn mục "Nếu Dùng Phương Án Dự Phòng" ở cuối file.
- Trong "Kết Quả Chạy Thật", paste **nguyên output thật** từ terminal.
- Ảnh: `screenshots/dashboard.png` + `screenshots/health.png`.

| Mục | Giá trị |
|---|---|
| Họ và tên | Nguyen Trong Minh |
| Mã học viên | 2A202602496 |
| Repo | https://github.com/EntityEbisu/K4-L3A-DAY12-NguyenTrongMinh-2A202602496-CloudServiceAndDeployment |
| Public URL | https://\<domain\>.onrender.com |
| Platform | Render (Blueprint, docker runtime) |
| Ngày deploy | 2026-09-28 |

### 7. Thêm `DEPLOY_API_KEY` vào `.env` local (tuỳ chọn)

Đặt **đúng khoá đã dán trên Render** để bật thêm test
`test_ask_hoat_dong_voi_key_that`. Không commit — `.env` đã gitignore.

## Giới hạn Render free tier (đã kiểm chứng từ tài liệu Render)

- Web service: **512 MB RAM**, ngủ sau **15 phút** không có request, tỉnh dậy
  mất **~1 phút** → request đầu có thể chậm 30–60s. `test_cp5.py` có
  `FIRST_CALL_TIMEOUT = 60.0` nên chịu được, nhưng nên `curl` một lần cho nó
  tỉnh trước khi chạy test.
- **750 instance giờ/tháng** cho cả workspace. Một service thức suốt = 744
  giờ, gần hết hạn mức. **Không** bật pinger (UptimeRobot…) giữ service sống —
  nó sẽ đốt hết quota.
- Key Value (Redis): **chỉ 1 instance free mỗi workspace**, **chỉ in-memory, không
  persist** — restart là mất sạch lịch sử hội thoại. Không ảnh hưởng test
  (TTL chỉ 7 ngày, test không cần dữ liệu sống qua restart), nhưng nên nói ra
  khi Lab Coach hỏi.
- Instance mới chạy **Valkey 8** (fork Redis 7.2.4) → tương thích thả lỏng với
  `redis-py`, `requirements.txt` không cần đổi.

## Phương án dự phòng (tối đa 9/15)

Nếu không đăng ký được Render: đặt `LOCAL_FALLBACK=true` trong `.env`, chạy
`docker compose up -d`, chụp màn hình vào `screenshots/`. Test CP5 tự chuyển
sang kiểm tra `http://localhost:8000`. Vẫn hơn là bỏ trắng.
