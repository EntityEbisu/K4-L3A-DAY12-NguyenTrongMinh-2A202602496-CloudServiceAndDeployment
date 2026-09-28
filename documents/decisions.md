# Quyết định thiết kế và lý do

Ghi lại các quyết định đã chốt trong quá trình làm bài. Đây là phần có giá trị
nhất khi Lab Coach hỏi "vì sao bạn làm thế" — vì một quyết định kèm lý do thể
hiện bạn hiểu, còn một quyết định trần không.

## 1. `LLM_MODE=mock` là mặc định, `real` là tuỳ chọn

**Quyết định:** `/ask` dùng `utils/mock_llm.py` trừ khi `LLM_MODE=real`.

**Lý do:** lab **cố ý** thiết kế vậy, và việc thay mock cho test sẽ làm hỏng
cả ba điều:

1. `test_cp3.py::test_ask_ghi_nhan_chi_phi` khẳng định `cost_usd > 0` **mỗi lần
   chạy**. LLM thật không bảo đảm điều đó.
2. `test_bonus_cicd.py` chạy pytest trên runner GitHub. Runner đó không có
   LMStudio → `/ask` fail → job `test` đỏ → `deploy` không chạy → badge đỏ.
3. Render free tier không tới được `127.0.0.1` của máy bạn.

**Cách vẫn dùng LLM thật:** set `LLM_MODE=real` ở **shell** khi chạy uvicorn.
Cùng một image, ba cấu hình, **không sửa một dòng code nào** — đó chính là ý
nghĩa của 12-Factor.

| Môi trường | `LLM_MODE` | `LLM_BASE_URL` | `LLM_MODEL` |
|---|---|---|---|
| Test / CI | `mock` | — | — |
| Máy bạn | `real` | `http://127.0.0.1:1234` | `ternary-bonsai-8b` |
| Render (tuỳ chọn) | `real` hoặc không set | provider cloud | tên model |

## 2. `.env` giữ `LLM_MODE=mock` vĩnh viễn, không bao giờ sửa

**Quyết định:** muốn dùng LMStudio thì ghi đè ở shell, **không** sửa `.env`.

**Lý do — cạm bẫy đã kiểm chứng trong `tests/conftest.py`:**

```python
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")          # nạp .env vào os.environ
except ImportError:
    pass

TEST_API_KEY = "test-api-key-cua-lab"
os.environ["AGENT_API_KEY"] = TEST_API_KEY   # ghi đè SAU
os.environ["REDIS_URL"] = "fake://"          # ghi đè SAU
```

Hai dòng ghi đè chạy **sau** `load_dotenv`, nên `AGENT_API_KEY` và `REDIS_URL`
luôn an toàn. **Nhưng `LLM_MODE` không nằm trong hai dòng đó.** `load_dotenv`
mặc định `override=False` — không ghi đè biến đã có, nhưng **có** đặt
`LLM_MODE` từ `.env` vào `os.environ` nếu biến đó chưa tồn tại.

Hệ quả nếu để `LLM_MODE=real` trong `.env`: **mọi lần chạy `pytest` cũng thành
`real`** → CP3/CP4 đỏ hàng loạt nếu LMStudio tắt.

Cách dùng đúng:

```bash
LLM_MODE=real .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
```

Biến của shell thắng `.env`, và chỉ đúng cho tiến trình đó.

## 3. Không dùng OAuth

**Quyết định:** xác thực bằng API key + `secrets.compare_digest`.

**Lý do:**

1. **Không nằm trong rubric.** `LAB_GUIDE.md`, `RUBRIC.md`, `CHECKPOINTS.md` và
   cả 5 file test đều không nhắc OAuth. Không test nào chấm nó.
2. **Nó sẽ cộng trừ.** OAuth thật cần client ID/secret, redirect URI, bảng
   session. Đăng ký app OAuth trên GitHub mất 10+ phút — không vừa trong lab
   session 240 phút. Rủi ro trượt CP3 (20đ) để đổi lấy 0đ là tỷ lệ xấu.
3. **Về mặt học thuật thì sai bài.** CP3 dạy đúng là *bằng chứng cấp ứng dụng là
   API key dùng constant-time compare*. OAuth trả lời cho bài toán khác: "nhiều
   người dùng có tài khoản riêng". Ở đây chỉ có vài client **đã biết trước**,
   API key là đủ và bề mặt tấn công nhỏ hơn.

## 4. UI demo là HTML thuần, không dùng Streamlit

**Quyết định:** trang demo tĩnh ở `/demo`, `fetch()` thuần, **không** thêm thư
viện nào.

**Lý do:** chuỗi phụ thuộc của Streamlit (pandas, pyarrow, altair, tornado)
nặng đáng kể, mà `test_cp2.py` chặn image **dưới 500 MB**. Đẩy Streamlit vào
image là rủi ro mất 15 điểm CP2 để đổi lấy một demo. HTML thuần thêm **0 byte**
vào image.

**Về mặt bảo mật:** trang demo **không nhúng API key**. Người dùng tự dán khoá
vào ô `password`, giữ trong `sessionStorage` của chính trình duyệt họ, và khoá
đó không bao giờ đi qua server của bạn.

## 5. Tách `app/llm_client.py` khỏi `utils/mock_llm.py`

**Quyết định:** hai provider riêng, chọn bằng `LLM_MODE`, chung interface.

**Lý do:** cùng trả về `{answer, tokens_in, tokens_out, cost_usd}` nên
`/ask` không cần biết đang nói chuyện với ai. Giữ `utils/mock_llm.py` **nguyên
bản** vì SUBMISSION.md yêu cầu bộ test và tiện ích của lab giữ nguyên.

## 6. `chat_completions_url()` chuẩn hoá `/v1`

**Quyết định:** hàm nhận cả `http://127.0.0.1:1234` lẫn `.../v1`.

**Lý do:** LMStudio, llama.cpp, vLLM, OpenAI đều phục vụ ở
`/v1/chat/completions`. Người dùng có thể cấu hình gốc rời hoặc đã kèm `/v1` —
hàm chấp nhận cả hai nên không bắt ai phải nhớ chính xác. (Viết `/v1/v1` thì
vẫn 404, nhưng đó là lỗi cấu hình chứ không phải lỗi code.)

## 7. `docker-compose.scale.yml` dùng `!reset` thay vì xoá `ports`

**Quyết định:** scale 3 instance qua nginx, file riêng, **không** sửa
`docker-compose.yml`.

**Lý do:** `docker-compose.yml` là file mà `test_cp2.py` đọc — sửa nó rủi ro
mất điểm CP2. Và `ports: "8000:8000"` là cổng **host**, nên `--scale agent=3`
gặp xung đột `port is already allocated` theo bản chất. `!reset` xoá đúng
khối `ports` cho các instance worker, để nginx làm cổng vào duy nhất.

## 8. Vì sao `.hermes/` và `documents/` có trong `.dockerignore`

**Quyết định:** loại khỏi build context.

**Lý do:** `.hermes/` là thư mục plan của công cụ, không thuộc bài nộp.
`documents/` là báo cáo Markdown — không cần thiết cho app chạy, đưa vào image
chỉ làm phình to. Cả hai đều đã được commit vào repo nên **không** liên quan
tới việc lộ `.env`.

## Điều chưa quyết

| Vấn đề | Trạng thái |
|---|---|
| Tên repo: `CloudServiceAndDeployment` (số ít) vs `CloudServicesAndDeployment` (số nhiều trong tài liệu) | **Sai tên = −5 điểm.** Cần hỏi Lab Coach trước khi nộp. Sửa mất ~10 phút: tạo repo mới đúng tên, `git remote set-url`, push, xoá repo cũ. |
| `LLM_MODE=real` trên Render hay không | Tuỳ chọn. Bắt đầu bằng mock cho chắc, chuyển sau khi CP5 xanh. |
