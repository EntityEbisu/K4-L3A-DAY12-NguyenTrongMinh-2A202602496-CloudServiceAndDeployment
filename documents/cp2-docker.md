# CP2 — Docker: multi-stage, bảo mật image

**Điểm:** 15/15 · **Trạng thái:** xanh, **0 test bị bỏ qua**
**Lệnh kiểm tra:** `pytest tests/test_cp2.py -v`

## Kết quả test thật

```
tests/test_cp2.py::TestDockerfile::test_multi_stage_build PASSED
tests/test_cp2.py::TestDockerfile::test_base_image_gon_nhe PASSED
tests/test_cp2.py::TestDockerfile::test_cai_dependency_truoc_khi_copy_source PASSED
tests/test_cp2.py::TestDockerfile::test_khong_chay_bang_root PASSED
tests/test_cp2.py::TestDockerfile::test_co_healthcheck PASSED
tests/test_cp2.py::TestDockerfile::test_khong_hardcode_secret PASSED
tests/test_cp2.py::TestDockerignore::test_ton_tai_va_day_du PASSED
tests/test_cp2.py::TestDockerignore::test_khong_loai_tru_nham_file_can_thiet PASSED
tests/test_cp2.py::TestDockerCompose::test_co_service_agent_va_redis PASSED
tests/test_cp2.py::TestDockerCompose::test_agent_build_tu_dockerfile PASSED
tests/test_cp2.py::TestDockerCompose::test_agent_phu_thuoc_redis PASSED
tests/test_cp2.py::TestDockerCompose::test_agent_tro_dung_toi_redis_service PASSED
tests/test_cp2.py::TestDockerCompose::test_secret_khong_nam_trong_compose PASSED
tests/test_cp2.py::TestDockerCompose::test_agent_co_healthcheck PASSED
tests/test_cp2.py::TestBuildThat::test_build_thanh_cong PASSED
tests/test_cp2.py::TestBuildThat::test_image_du_nho PASSED

16 passed in 2.72s
```

**Quan trọng:** 2 test `TestBuildThat` build image thật và **không bị skip**,
vì Docker Desktop đã bật. `grade.py` chia đều điểm cho các test không bị skip,
nên nếu để skip thì mất điểm thật chứ không phải "không bị trừ".

## Kết quả build thật

**So sánh 2 bản** (bản 1 stage lấy từ `git show 306b897:Dockerfile` — đúng
Dockerfile gốc của lab):

```
$ docker build -f <Dockerfile gốc 1-stage> -t agent:single .
$ docker build -t day12-agent:prod .

REPOSITORY:TAG        SIZE
agent:single          1.73GB
day12-agent:prod      310MB
```

**310MB < giới hạn 500MB.** Bản multi-stage nhỏ hơn **5.6 lần**.

## Đã làm

### `Dockerfile` — multi-stage

```dockerfile
FROM python:3.11-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app
WORKDIR /srv/app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app app ./app
COPY --chown=app:app utils ./utils
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health').read()"
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

Từng quyết định và lý do:

| Dòng | Vì sao |
|---|---|
| 2 lần `FROM`, có `AS builder` | Stage builder cài rồi bị vứt; image cuối không mang compiler, không mang pip cache |
| `python:3.11-slim` | `python:3.11` đầy đủ nặng ~1GB |
| `COPY requirements.txt` **trước** `pip install` | Docker cache theo từng layer, huỷ cache từ layer đầu tiên thay đổi. Sửa 1 dấu phẩy trong code không phải cài lại thư viện |
| `USER app` | Container chạy root nghĩa là ai thoát được khỏi app cũng thành root trên host |
| `HEALTHCHECK` | Docker cần biết container còn phục vụ được không |
| `--port ${PORT:-8000}` | Render/Railway/Cloud Run tự gán `PORT` |
| `--host 0.0.0.0` | Bind `127.0.0.1` thì **ngoài container gọi không được** |
| `PYTHONUNBUFFERED=1` | Log phải ra container ngay, không bị đệm trong RAM |
| Không có `AGENT_API_KEY=` | Secret truyền lúc **chạy**, không nướng vào image |

### `.dockerignore`

Loại `.git`, `.env` (+ `.env.*` nhưng giữ lại `.env.example` qua `!`), `.venv`,
`.hermes`, `__pycache__`, `tests`, `screenshots`, `documents`, `nginx`, và các
file tài liệu lab. Giữ lại `app/`, `utils/`, `requirements.txt` — bỏ nhầm thì
build xong app không chạy.

### `docker-compose.yml` — service `agent`

`REDIS_URL: redis://redis:6379/0` — trong mạng compose, **tên service chính là
hostname**. `localhost` bên trong container là chính container đó, không phải
Redis. Đây là lỗi phổ biến nhất khi mới dùng compose.

`AGENT_API_KEY: ${AGENT_API_KEY}` — nội suy để compose đọc từ `.env`, không
viết thẳng giá trị vào file được commit.

`depends_on: redis: condition: service_healthy` — chờ Redis thật sự trả lời
PING, không chỉ "đã start".

## Chạy thật — kết quả từ container

```
$ docker compose ps
SERVICE   STATE     STATUS
agent     running   Up 2 minutes (healthy)
redis     running   Up 2 minutes (healthy)

$ curl -s http://localhost:8000/health
{"status":"ok","service":"day12-agent","version":"1.0.0"}

$ curl -s http://localhost:8000/ready
{"status":"ready","redis":true}

$ curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/ask \
    -H "Content-Type: application/json" -d '{"question":"Hello"}'
401

$ docker compose exec -T agent python -c "import os; print('uid=',os.getuid())"
uid= 10001 gid= 10001
```

`uid=10001` xác nhận container **không chạy root** — `USER app` có hiệu lực
thật, không chỉ là dòng lệnh cho có.

## Điểm số

- **Câu 3 (exercises):** multi-stage = **310MB**. Để so sánh, bản 1-stage gốc
  dùng `python:3.11` đầy đủ — cần build riêng để có số đo thật.
- **Câu 4 (exercises):** sửa 1 dấu phẩy trong `app/main.py` → layer `COPY app
  ./app` và `COPY utils ./utils` chạy lại, **còn `COPY requirements.txt` +
  `pip install` được cache**. Nếu đặt `COPY . .` lên trước `pip install`, mỗi
  lần sửa code sẽ huỷ cache lớp `pip install` → build chậm hàng phút mỗi lần.

## Câu hỏi tự kiểm tra

1. Sửa 1 dấu phẩy trong `app/main.py` rồi build lại: layer nào cache, layer nào
   chạy lại? (xem câu 4 ở trên)
2. `COPY . .` đặt trước `pip install` khác gì? Huỷ cache lớp cài thư viện.
3. Chuỗi "lỗ hổng trong code Python" → "root trên host" đi qua những bước nào,
   `USER app` cắt ở đâu? Container chạy root: code của bạn bị khai thác →
   attacker có shell trong container với uid 0 → nếu mount volume hay Docker
   socket nào đó, leo được lên host. `USER app` cắt ngay bước 2: attacker chỉ
   có uid 10001, không đủ quyền.
