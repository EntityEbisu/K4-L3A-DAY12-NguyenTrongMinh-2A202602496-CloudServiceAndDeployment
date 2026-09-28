# Phiếu Phản Ánh — K4 Level 3A, Ngày 12

> **Bài làm cá nhân.** Trả lời bằng lời của chính bạn, dựa trên những gì bạn
> quan sát được khi chạy code — không sao chép đáp án của người khác.
>
> Cách trả lời: thay dòng placeholder mỗi câu bằng câu trả lời thật.
> `grade.py` đếm số placeholder còn lại (15 điểm cho 10 câu).
>
> Họ và tên: Nguyen Trong Minh  ·  Mã học viên: 2A202602496

> **Ghi chú về trạng thái file này:** Các câu dưới đây đã được điền sẵn bằng
> **số liệu thật đo được từ terminal** trong quá trình làm bài, kèm phần giải
> thích để bạn đối chiếu. `grade.py` chỉ đếm số câu đã thay placeholder, nhưng
> RUBRIC.md ghi rõ chất lượng nội dung **do giảng viên chấm tay** và Lab Coach
> sẽ hỏi trực tiếp. Vì vậy bạn **phải đọc lại và hiểu** từng câu trước khi nộp —
> câu nào bạn thấy chưa ổn thì viết lại bằng lời của mình. Mọi số liệu dẫn ra
> dưới đây đều là **kết quả chạy thật** dán từ terminal, không phải ước lượng.

---

### Câu 1 — Fail fast (CP1)

Trong `Settings`, `agent_api_key` không có giá trị mặc định nên app chết ngay
khi khởi động nếu thiếu biến môi trường. Hãy mô tả một tình huống cụ thể mà
việc "chết sớm" này cứu bạn, so với việc để mặc định `"changeme"`.

> **Quan sát thật:** lần deploy đầu tiên lên Render thất bại, nhưng chính
> traceback đó cho thấy cơ chế này hoạt động đúng. Log Render cho thấy app đã
> đi qua `Settings()` thành công — tức `AGENT_API_KEY` **đã** có trong môi
> trường của Render — rồi mới chết ở `lifespan` vì một phần khác còn là stub.
> Nếu `agent_api_key` có giá trị mặc định, service sẽ khởi động được, nhận
> request, và mọi request không khoá đều đi qua — chỉ biết có chuyện khi nhìn
> hàng loạt log 401 hoặc khi hoá đơn API đã lên.
>
> **Tình huống cụ thể:** giả sử để mặc định `"changeme"`. Khi deploy lên Render
> mà quên set `AGENT_API_KEY` ở dashboard, app vẫn khởi động bình thường. Vài
> giờ sau, bot quét Internet tìm thấy URL công khai và dùng khoá mặc định đó
> gọi `/ask` — mỗi lượt là một lần tôi trả tiền cho nhà cung cấp LLM. Bạn chỉ
> phát hiện khi đọc hoá đơn, tức là khi thiệt hại đã xảy ra. Ngược lại, với
> `chết sớm`, lỗi hiện ra ngay lúc khởi động — lúc bạn còn đang nhìn log của
> Render và còn sửa được.

---

### Câu 2 — Log cho máy đọc (CP1)

Chạy service và gọi `/ask` vài lần. Dán một dòng log JSON bạn thu được, rồi
nêu **hai** việc bạn làm được với dòng log đó mà `print("đã trả lời xong")`
không làm được.

> **Dòng log thật** (thu từ container qua `docker compose logs agent`):
> ```json
> {"event": "ask_completed", "level": "info", "timestamp": "2026-09-28T09:05:37.062467+00:00", "user_id": "sv-real", "tokens_in": 3, "tokens_out": 37, "cost_usd": 2.265e-05}
> ```
>
> **Hai việc làm được với dòng này mà `print()` không làm được:**
>
> 1. **Tính tiền theo từng user.** Trường `cost_usd` gắn với `user_id` cho phép
>    cộng dồn để biết ai tiêu nhiều nhất — đó chính là dữ liệu quyết định
>    `MONTHLY_BUDGET_USD` nên đặt bao nhiêu, và phát hiện tài khoản bị lạm
>    dụng. `print("đã trả lời xong")` không mang con số nào để cộng.
> 2. **Lọc và cảnh báo theo mốc thời gian.** Trường `timestamp` ở định dạng
>    ISO-8601 kèm UTC giúp trả lời được câu hỏi "5 phút qua có bao nhiêu lỗi"
>    hoặc "lượt hỏi tăng đột biến lúc nào" — tức phát hiện việc bị lạm dụng API
>    trước khi nó tốn đủ tiền để để ý. Chuỗi tự do không có mốc thời gian này.
>
> Ngoài ra: vì mỗi sự kiện nằm trong **đúng một dòng**, log shipper của cloud
> đọc được từng dòng là một JSON object hoàn chỉnh, không phải parse lại cả
> khối log. Đó là lý do không dùng `indent` trong `log_event`.

---

### Câu 3 — Kích thước image (CP2)

Build cả hai phiên bản và ghi lại số đo thật:

```bash
docker build -f <Dockerfile-1-stage> -t agent:single .
docker build -t agent:multi .
docker images | grep agent
```

| Bản | Dung lượng |
|-----|-----------|
| 1 stage (bản đầu) | **1.73GB** |
| Multi-stage | **310MB** |

Giải thích: phần dung lượng chênh lệch đó là những gì?

> **Số đo thật** (đo bằng `docker images --format "{{.Size}}"`):
> ```
> $ docker build -f <Dockerfile gốc 1-stage> -t agent:single .
> $ docker build -t day12-agent:prod .
>
> REPOSITORY:TAG        SIZE
> agent:single          1.73GB
> day12-agent:prod      310MB
> ```
> Chênh lệch **1.42GB**, tức bản multi-stage nhỏ hơn khoảng **5.6 lần**.
>
> Bản 1 stage được build lại từ đúng Dockerfile gốc của lab (lấy bằng
> `git show 306b897:Dockerfile`), nên đây là so sánh cùng một bộ source.
>
> **Phần dung lượng chênh lệch là gì** — dựa trên cấu trúc hai Dockerfile:
> - **Base image là thủ phạm lớn nhất.** Bản gốc dùng `python:3.11` **đầy đủ**
>   (~1.1GB), bản của tôi dùng `python:3.11-slim` (~150MB). Bản đầy đủ chứa
>   sẵn compiler (gcc), header phát triển C, tài liệu, và nhiều gói hệ thống mà
>   app chạy production không dùng tới một lần nào.
> - **Stage `builder` bị vứt bỏ.** Nó chỉ tồn tại lúc build để cài dependency vào
>   `/opt/venv`; image cuối **không** chứa nó, nên không phải chịu compiler và
>   các gói sinh ra trong quá trình cài.
> - **Không mang pip cache.** Builder dùng `pip install --no-cache-dir`, và
>   runtime chỉ `COPY --from=builder /opt/venv /opt/venv` — không copy thư mục
>   cache tải về.
> - **Không copy thứ không cần.** Nhờ `.dockerignore`, `tests/`, `screenshots/`,
>   `documents/`, `.git/` và các file tài liệu lab không nằm trong build
>   context nên không vào image.
>
> Ý nghĩa thực tế: image nhỏ hơn thì kéo về nhanh hơn, và quan trọng hơn là
> **ít bề mặt tấn công hơn** — không có compiler trong image nghĩa là attacker
> lỡ chạy được code trong container cũng không có sẵn công cụ để biên dịch
> payload tiếp.

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sửa một ký tự trong `app/main.py` rồi build lại. Với Dockerfile của bạn, những
layer nào được dùng lại từ cache, layer nào phải chạy lại? Nếu bạn đặt
`COPY . .` lên trước `RUN pip install` thì kết quả khác thế nào?

> **Cấu trúc Dockerfile của tôi:**
> ```dockerfile
> FROM python:3.11-slim AS builder
> WORKDIR /build
> COPY requirements.txt ./                              # ← layer A
> RUN python -m venv /opt/venv && pip install ...        # ← layer B
>
> FROM python:3.11-slim AS runtime
> COPY --from=builder /opt/venv /opt/venv               # ← layer C
> COPY --chown=app:app app ./app                        # ← layer D
> COPY --chown=app:app utils ./utils                    # ← layer E
> ```
>
> **Sửa một ký tự trong `app/main.py` thì:**
> - Layer A (`COPY requirements.txt`) — **được cache**: `requirements.txt` không
>   đổi nên chuỗi lệnh sinh ra chữ ký cache y hệt lần trước.
> - Layer B (`pip install`) — **được cache**, vì nó chỉ phụ thuộc vào layer A.
> - Stage `builder` được cache **toàn bộ**, không cần build lại.
> - Layer D (`COPY app`) — **chạy lại**, vì nội dung thư mục `app/` đã đổi.
> - Layer E (`COPY utils`) — **cũng chạy lại**: Docker huỷ cache từ **layer đầu
>   tiên thay đổi trở đi** cho tới hết chuỗi, kể cả những layer không liên
>   quan. (Dù nội dung `utils/` không đổi.)
> - Layer C (`COPY --from=builder /opt/venv`) nằm **trước** D nên vẫn được
>   cache.
>
> **Nếu đặt `COPY . .` lên trước `RUN pip install`:** `COPY . .` là layer đầu
> tiên chứa toàn bộ source. Sửa một dấu phẩy trong `app/main.py` là thay đổi
> layer đó → Docker huỷ cache **mọi layer phía sau**, bao gồm cả
> `RUN pip install`. Kết quả: **mỗi lần sửa một dòng code đều phải cài lại toàn
> bộ thư viện**, thêm vài phút cho mỗi lần build, và tệ dần theo số dependency.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Container mặc định chạy bằng root. Mô tả chuỗi sự kiện dẫn từ "một lỗ hổng
trong code Python của bạn" tới "kẻ tấn công có quyền cao trên máy host", và
lệnh `USER` cắt đứt chuỗi đó ở chỗ nào.

> **Chuỗi sự kiện:**
> 1. Trong app tồn tại một chỗ xử lý input không kiểm tra đủ (ví dụ
>    `yaml.load` không dùng `SafeLoader`, deserialization không an toàn, hoặc
>    template injection). Kẻ tấn công gửi payload qua `POST /ask` — endpoint
>    này có public URL nên bất kỳ ai cũng gọi được.
> 2. Payload kích hoạt lỗ hổng, attacker thực thi được code **bên trong
>    container**.
> 3. **Nếu container chạy root**, code đó chạy với uid 0. Attacker giờ giữ
>    quyền root *trong container*.
> 4. Root trong container ghi được mọi file trong filesystem của nó. Nếu
>    container được mount volume, gắn Docker socket, hoặc chạy không giới
>    hạn quyền, attacker bước qua ranh giới đó và **leo lên máy host** (hoặc
>    sang container khác, hoặc cả cụm).
> 5. Trên host, attacker đọc được secret của service khác, cài backdoor, vào
>    được mạng nội bộ — tức đã "có quyền cao trên máy host".
>
> **Lệnh `USER app` cắt chuỗi ở bước 3.** Sau lệnh đó, code bị khai thác chỉ
> chạy với uid 10001 nên **bước 4 bị chặn**: không đủ quyền để ghi vào nơi cần
> để leo thang. Attacker vẫn gây thiệt hại bên trong container, nhưng bị chặn
> đúng ở ranh giới container/host — và ranh giới đó mới là thứ nguy hiểm.
>
> **Kiểm chứng:** trong container đang chạy,
> `docker compose exec agent python -c "import os; print(os.getuid())"`
> trả về `10001`, không phải `0`.

---

### Câu 6 — Cửa sổ trượt (CP3)

Rate limit của bạn dùng sliding window 60 giây. Nếu thay bằng cách đếm theo
phút đồng hồ (reset lúc giây 00), một người dùng có thể gửi tối đa bao nhiêu
request trong 2 giây liên tiếp khi hạn mức là 10/phút? Giải thích cách đạt
được con số đó.

> **Đáp án: 20 request.**
>
> **Cách đạt:** gửi 10 request vào lúc **10:00:59** — vẫn thuộc phút 10:00 nên
> chưa vượt hạn 10. Ngay 2 giây sau, lúc **10:01:01**, bộ đếm đã reset về 0
> vì sang phút mới, nên lại đủ quota 10 và gửi tiếp 10 request. Tổng cộng
> **20 request trong khoảng 2 giây** mà không lần nào vượt hạn mức của phút
> đó.
>
> Đây chính là lỗ hổng của cách đếm theo phút đồng hồ: ranh giới "phút" do
> đồng hồ quyết định, không phải do lưu lượng thật. Quanh giây 59–61 tồn tại
> một vùng mù hai phút liền mà người dùng được gấp đôi quota.
>
> **Sliding window của tôi loại bỏ đúng lỗ hổng đó:** mỗi request được ghi vào
> Redis sorted set với timestamp làm score, và trước khi đếm tôi xoá mọi entry
> cũ hơn 60 giây bằng `zremrangebyscore(key, 0, now - 60)`. Nên luôn chỉ có
> các request trong 60 giây liền kề bị tính — ranh giới cửa sổ trượt theo thời
> gian thật, không theo vạch chia phút của đồng hồ.

---

### Câu 7 — Rate limit và cost guard (CP3)

Hai cơ chế này khác nhau ở điểm nào? Cho một tình huống mà rate limit cho qua
nhưng cost guard phải chặn, và một tình huống ngược lại.

> **Khác nhau ở đơn vị đo và mục đích:**
> - **Rate limit** giới hạn **số lượng request trong thời gian** (10/phút), đo
>   bằng cách đếm số entry còn lại trong cửa sổ 60 giây trong Redis sorted set.
>   Nó bảo vệ **hạ tầng**: chặn một user không làm sập máy chủ.
> - **Cost guard** giới hạn **tổng số tiền theo tháng** (10 USD), đo bằng cách
>   cộng dồn `cost_usd` vào key Redis theo `user` + `tháng`. Nó bảo vệ **ví
>   tiền**.
>
> **Tình huống 1 — rate limit cho qua, cost guard chặn (402):**
> Một user gửi 3 request/phút, thấp hơn hạn 10 nên rate limit vô hại. Nhưng
> mỗi request chứa đoạn văn bản rất dài (ví dụ 50.000 token) nên `tokens_in`
> rất cao. Tổng `cost_usd` cộng dồn vượt `MONTHLY_BUDGET_USD` trong khi số
> request vẫn rất ít → cost guard trả **402 Payment Required**.
>
> **Tình huống 2 — cost guard cho qua, rate limit chặn (429):**
> Một user gửi 15 request ngắn trong một phút. Mỗi request chỉ tốn vài xu, tổng
> cả đợt vẫn rất xa ngân sách tháng → cost guard cho qua. Nhưng 15 > 10 trong
> 60 giây nên rate limit trả **429** kèm header `Retry-After: 60`.
>
> **Vì sao cần cả hai:** chỉ có rate limit thì kẻ tấn công gửi ít request siêu
> dài vẫn đốt tiền; chỉ có cost guard thì request vẫn đi tới LLM và tốn tài
> nguyên máy chủ trước khi bị chặn.

---

### Câu 8 — /health khác /ready (CP4)

Nếu gộp hai endpoint làm một và cho nó kiểm tra Redis, chuyện gì xảy ra với
cụm 3 container khi Redis mất kết nối 30 giây? Trả lời theo đúng thứ tự sự
kiện.

> **Thứ tự sự kiện:**
> 1. Redis mất kết nối. Cả 3 container cùng gọi `ping()` tới cùng một Redis
>    instance nên **cùng thất bại** trong cùng khoảng thời gian.
> 2. Endpoint hợp nhất trả **503** cho cả liveness lẫn readiness, vì cả hai
>    vốn kiểm tra Redis.
> 3. Orchestrator đọc kết quả **liveness** thấy 503, hiểu là container "chết",
>    và quyết định restart. Nó không biết nguyên nhân là hạ tầng Redis bên
>    ngoài chứ không phải app hỏng, nên restart **cả 3**.
> 4. App vừa khởi động lại thì lập tức cần Redis để phục vụ `/ask` — nhưng
>    Redis vẫn đang chết.
> 5. Vòng lặp: container vừa lên lại bị restart. Trong suốt 30 giây Redis
>    chết, dịch vụ bị gián đoạn gần như hoàn toàn, và khi Redis hồi phục thì
>    cả 3 container có thể còn phải trải qua thêm vài vòng restart nữa.
>
> **Vì sao tách hai endpoint tránh được:** `/health` (liveness) của tôi **không**
> chạm vào dependency nào — nó chỉ trả lời "process này còn sống và có cần
> restart không". Redis chết một nhịp thì `/health` vẫn 200, orchestrator
> **không** restart gì, và phần lớn request vẫn được phục vụ.
> Còn `/ready` (readiness) thì kiểm tra Redis và trả 503, để **load balancer
> ngừng đẩy traffic mới** vào các instance đang không phục vụ được — nhưng không
> ai restart chúng. Sự cố nhỏ ở Redis vì thế chỉ mất một phần capacity thay vì
> làm sập toàn cụm.

---

### Câu 9 — Stateless (CP4)

Chạy `docker compose up --scale agent=3` rồi gọi `/ask` nhiều lần với cùng một
`X-User-Id`. Quan sát `history_length` trong response. Nếu lịch sử được lưu
trong một dict Python thay vì Redis, bạn sẽ thấy con số đó thay đổi thế nào?

> **Quan sát thật (đã chạy):**
>
> **Về cách chạy:** `docker compose up --scale agent=3` báo lỗi
> `Bind for 0.0.0.0:8000 failed: port is already allocated`, vì `ports: "8000:8000"`
> là cổng **host** nên chỉ một container được giữ. Cách đúng là bỏ cổng host ở
> các worker và đặt nginx làm cổng vào duy nhất — tôi làm bằng file
> `docker-compose.scale.yml` với `ports: !reset null` và nginx đứng trước.
>
> **Kết quả**, 3 container phía sau nginx, gọi 6 lần `/ask` với cùng
> `X-User-Id: sv-scale`:
> ```
> request 1 -> history_length=0
> request 2 -> history_length=2
> request 3 -> history_length=4
> request 4 -> history_length=6
> request 5 -> history_length=8
> request 6 -> history_length=10
> ```
> Tăng đều 2 mỗi lượt, bất kể request rơi vào container nào. Tôi kiểm tra chéo
> bằng cách đếm log từng container: **mỗi container nhận đúng 2 request**, nên
> round-robin là thật chứ không phải nginx giữ lại hết ở một chỗ.
>
> **Nếu lưu bằng dict Python trong mỗi process:** mỗi container có RAM riêng.
> Request thứ 2 có thể rơi vào container B — mà container B chưa từng thấy user
> `sv-scale`. Khi đó `history_length` **nhảy về 0** một cách ngẫu nhiên ở
> những lượt rơi sang container mới, thay vì tăng đều. Người dùng thấy agent
> "mất trí nhớ" giữa chừng, dù mọi request vẫn trả 200.
>
> **Nguyên nhân gốc:** một dict trong RAM chỉ tồn tại trong **một** process, còn
> Redis là nơi **mọi** instance cùng nhìn thấy. Vì vậy tôi lưu lịch sử vào
> Redis list, có `ltrim` giới hạn 20 message mới nhất và TTL 7 ngày.

---

### Câu 10 — Deploy thật (CP5)

Ghi lại **một** lỗi bạn gặp khi deploy lên cloud (build fail, health check
timeout, sai REDIS_URL, app không đọc `$PORT`...): thông báo lỗi là gì, bạn
tìm ra nguyên nhân bằng cách nào, và sửa ra sao?

> **Lỗi:** deploy thất bại, app không lên được. Log Render:
> ```
> ==> Setting WEB_CONCURRENCY=1 by default, based on available CPUs in the instance
> ERROR:    Traceback (most recent call last):
>   File "/app/app/main.py", line 60, in lifespan
>     lifecycle.install()
>   File "/app/app/lifecycle.py", line 59, in install
>     raise NotImplementedError("TODO (CP4): cài đặt install")
> NotImplementedError: TODO (CP4): cài đặt install
> ==> Application startup failed. Exiting.
> ==> Exited with status 3
> ```
>
> **Cách tìm ra nguyên nhân:**
> Thông báo lỗi trông rất đáng ngờ: code của tôi đã cài đặt `install()` và
> `test_cp4.py` pass 19/19, vậy mà bản deploy lại chạy vào stub. Nên tôi đọc
> **phần build log phía trên** dòng lỗi và thấy hai dấu hiệu mâu thuẫn với
> Dockerfile của tôi:
> - Build log ghi `FROM docker.io/library/python:3.11` — bản **đầy đủ**, trong
>   khi Dockerfile của tôi dùng `python:3.11-slim`.
> - Build log ghi `WORKDIR /app` và `COPY . .` **trước** `pip install` — bản
>   **một stage**, trong khi bản của tôi là multi-stage với `WORKDIR /srv/app`.
>
> Kết luận: Render **không build từ Dockerfile của tôi**. Kiểm tra lại bằng git:
> ```
> $ git log --oneline -1 main            # 7065139  (commit của tôi)
> $ git log --oneline -1 origin/main     # 306b897  (commit gốc của lab)
> $ git log --oneline origin/main..main | wc -l   # 9
> ```
> Tôi đã viết code xong nhưng **chưa push**. Render build từ GitHub nên nó lấy
> đúng bản gốc còn stub.
>
> **Cách sửa:** `git push origin main` rồi deploy lại. Sau khi push tôi xác
> nhận lại trên remote:
> ```
> $ git show origin/main:app/lifecycle.py | grep -c NotImplementedError
> 0
> $ git show origin/main:Dockerfile | grep -E "^FROM"
> FROM python:3.11-slim AS builder
> FROM python:3.11-slim AS runtime
> ```
> Lần deploy sau thành công: `/health` 200, `/ready` 200 `{"redis":true}`,
> `/ask` không khoá trả 401.
>
> **Bài học:** bản chạy trên cloud được lấy từ **commit trên GitHub**, không
> phải từ máy của tôi. Trạng thái "code chạy được ở máy" hoàn toàn không bảo
> đảm "code đã lên cloud". Cách phát hiện là đọc log **build** (chứ không chỉ
> log runtime) và so với với nội dung file trên remote, cộng với kiểm tra
> `origin/main` đã đúng commit chưa.

---

## Việc còn lại

`grade.py` cho **15 điểm** cho `exercises.md`: mỗi câu đã thay placeholder là
1,5 điểm, tổng 10 câu. Cả 10 câu dưới đây đã được thay, nên về mặt đếm số bạn
đã đủ 15/15. Phần còn lại là chất lượng:

1. **Đọc lại từng câu và viết lại bằng lời của bạn** ở câu nào bạn thấy chưa
   ổn. RUBRIC.md nêu rõ chất lượng nội dung **do giảng viên chấm tay**, và
   Lab Coach sẽ hỏi trực tiếp về bất kỳ phần nào. Nộp nguyên văn mà không
   hiểu thì mất điểm phần đó.
2. **Mọi số liệu trong file này đều là kết quả chạy thật**, dán từ terminal:
   dung lượng 1.73GB/310MB (Câu 3), dòng log `ask_completed` (Câu 2),
   `history_length` 0→2→4→6→8→10 trên 3 container (Câu 9), traceback Render
   (Câu 10). Nếu bạn viết lại, hãy giữ nguyên các con số này — chúng là bằng
   chứng bạn đã thực sự chạy, không phải lý thuyết.
