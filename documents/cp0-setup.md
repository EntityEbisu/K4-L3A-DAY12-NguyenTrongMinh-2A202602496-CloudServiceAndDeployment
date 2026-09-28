# CP0 — Setup

**Trạng thái:** xong
**Lệnh kiểm tra:** `pytest tests/ -v -m "not docker"`

## Môi trường

| Mục | Giá trị |
|---|---|
| Python | 3.11.15 (venv riêng tại `.venv/`) |
| Công cụ tạo venv | `uv 0.12.13` |
| Docker | 29.1.3 (Docker Desktop) |
| `python` trên PATH | **3.14.7 của Hermes, KHÔNG có fastapi** |

## Vấn đề đã gặp và cách xử lý

`python` trên PATH trỏ vào CPython 3.14.7 của Hermes Agent — **không có
fastapi**. Anaconda 3.13.9 cũng không có. Nếu chạy `pytest` bằng `python` trần
sẽ fail với `ModuleNotFoundError: No module named 'fastapi'`, dễ bị hiểu nhầm
là môi trường hỏng.

Cách xử lý: tạo venv riêng bằng `uv venv --python 3.11 .venv` (3.11.15 đã có
sẵn trong cache của uv), rồi **mọi lệnh trong báo cáo này đều gọi
`.venv/Scripts/python.exe -m pytest`**, không dùng `python` trần.

## `.env`

Tạo từ `.env.example`. Đã xác nhận `.env` **không** bị git theo dõi:

```
$ git check-ignore -v .env
.gitignore:2:.env	.env
```

`AGENT_API_KEY` được sinh bằng `secrets.token_urlsafe(32)`. Giá trị đó không
xuất hiện trong báo cáo này, không nằm trong commit, và không nằm trong bất
kỳ prompt nào.

## Kết quả CP0 (trước khi viết code)

```
= 66 failed, 7 passed, 5 skipped, 2 deselected, 1 warning, 16 errors in 7.03s =
```

**Đây là kết quả ĐÚNG.** Ở giai đoạn này hầu hết test phải đỏ vì code chưa
viết. Điều cần xác nhận là pytest **chạy được** và lỗi là `NotImplementedError`
chứ không phải `ModuleNotFoundError`. 16 `errors` ở đây là các fixture của
`test_cp5.py`/`test_bonus_cicd.py` dừng sớm vì `DEPLOYMENT.md` còn placeholder
và chưa có workflow — cũng đúng ở CP0.

## Câu hỏi tự kiểm tra

- Vì sao `.env` không được commit? Vì nó chứa `AGENT_API_KEY`. Lịch sử Git là
  bản ghi **vĩnh viễn** — xoá file ở commit sau không làm secret biến mất khỏi
  lịch sử, nên phải **rotate** khoá.
- Vì sao test đỏ ở CP0 là bình thường? Vì test là **đặc tả** của bài lab: chúng
  mô tả hành vi cần có, và bạn viết code để đạt chúng chứ không sửa chúng.
