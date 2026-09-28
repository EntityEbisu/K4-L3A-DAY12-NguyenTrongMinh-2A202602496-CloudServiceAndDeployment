# Báo cáo triển khai — K4 L3A Day 12

Báo cáo này ghi lại **những gì đã làm và đã kiểm chứng bằng output thật** cho từng
checkpoint. Mọi số liệu dưới đây được paste từ terminal, không ước lượng.

## Điểm hiện tại

```
  CP1 — 12-Factor Config, Health & Logging         13/13 test    15.0/15
  CP2 — Docker: multi-stage, bảo mật image         16/16 test    15.0/15
  CP3 — API Security: auth, rate limit, cost guard 22/22 test    20.0/20
  CP4 — Scaling & Reliability                      19/19 test    20.0/20
  CP5 — Cloud Deployment                           0/8 test      0.0/15
  Exercises — câu hỏi phản ánh                     0/10 câu      0.0/15
  TỔNG CUỐI                                                70.0/100
```

**70/100 đã xong và có bằng chứng. 30 điểm còn lại cần người học viên:**
CP5 cần deploy thật lên Render + điền `DEPLOYMENT.md`; `exercises.md` cần
10 câu trả lời bằng lời của học viên.

## Cách đọc

| File | Nội dung |
|---|---|
| [cp0-setup.md](cp0-setup.md) | Môi trường Python, `.env`, chuyện đáng lưu ý về `python` trên PATH |
| [cp1-config-health-logging.md](cp1-config-health-logging.md) | Settings, log JSON, `/health` |
| [cp2-docker.md](cp2-docker.md) | Dockerfile multi-stage, `.dockerignore`, compose, kết quả build thật |
| [cp3-security.md](cp3-security.md) | API key, rate limit, cost guard, `/ask` |
| [cp4-scaling-reliability.md](cp4-scaling-reliability.md) | Redis store, `/ready`, graceful shutdown, **bằng chứng scale 3 instance** |
| [cp5-deployment.md](cp5-deployment.md) | Việc còn làm để lấy 15 điểm CP5 |
| [bonus-cicd.md](bonus-cicd.md) | Workflow GitHub Actions, trạng thái badge |
| [decisions.md](decisions.md) | Các quyết định thiết kế và lý do |

## Nguyên tắc đã tuân thủ

- **Không secret nào** xuất hiện trong `documents/` hay commit. Chỉ ghi tên biến.
- **Không bịa số liệu.** Mọi dòng output dưới đây đến từ terminal thật.
- **Không sửa bộ test.** `tests/`, `grade.py`, `utils/`, `nginx/nginx.conf` giữ
  nguyên bản gốc của lab.
