# ═══════════════════════════════════════════════════════════════════
# CP2 — Containerization (production-ready)
#
# Multi-stage: stage `builder` cài dependency vào /opt/venv rồi bị vứt đi;
# stage `runtime` chỉ COPY kết quả sang → image không mang theo compiler,
# không mang pip cache.
#
# Thứ tự lệnh quyết định tốc độ build: COPY requirements.txt → pip install
# → COPY code. Docker cache theo từng layer và huỷ cache từ layer đầu tiên
# thay đổi, nên sửa 1 dấu phẩy trong code không phải cài lại thư viện.
#
# Kiểm tra:  pytest tests/test_cp2.py -v
# Build thử: docker build -t day12-agent:prod .
#            docker images day12-agent:prod
# ═══════════════════════════════════════════════════════════════════

FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.txt ./

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


FROM python:3.11-slim AS runtime

# PYTHONUNBUFFERED: log phải ra container ngay, không bị đệm trong bộ nhớ.
# PYTHONDONTWRITEBYTECODE: không sinh .pyc rác trong filesystem container.
# PORT: cloud (Render/Railway/Cloud Run) tự gán PORT, không cố định 8000.
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# User thường. Container chạy root nghĩa là ai thoát được khỏi app cũng
# thành root trên host — lệnh USER cắt đứt chuỗi leo thang đó.
RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

WORKDIR /srv/app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app app ./app
COPY --chown=app:app utils ./utils

USER app

EXPOSE 8000

# 127.0.0.1 vì healthcheck chạy BÊN TRONG container, không đi qua network.
# Dùng $PORT để khớp với cổng uvicorn thật sự đang lắng nghe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8000')+'/health').read()"

# ${PORT:-8000}: cloud tự gán PORT, còn chạy tay thì rơi về 8000.
# 0.0.0.0 chứ không phải 127.0.0.1 — bind localhost thì ngoài container gọi
# không được.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
