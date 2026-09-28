# BONUS — CI/CD với GitHub Actions

**Điểm:** chưa chấm được — workflow **chưa được push lên GitHub để chạy thật**
**Lệnh kiểm tra:** `pytest tests/test_bonus_cicd.py -v`

## Kết quả test thật

```
$ pytest tests/test_bonus_cicd.py -v -k "not badge_bao_passing"
tests/test_bonus_cicd.py::TestTrigger::test_chay_khi_push_va_pull_request PASSED
tests/test_bonus_cicd.py::TestJobTest::test_co_job_chay_pytest PASSED
tests/test_bonus_cicd.py::TestJobTest::test_khong_chay_test_can_deploy_trong_ci PASSED
tests/test_bonus_cicd.py::TestJobTest::test_co_cai_dependency PASSED
tests/test_bonus_cicd.py::TestJobBuild::test_co_buoc_build_docker_image PASSED
tests/test_bonus_cicd.py::TestJobDeploy::test_co_job_deploy PASSED
tests/test_bonus_cicd.py::TestJobDeploy::test_deploy_chi_chay_sau_khi_test_xanh PASSED
tests/test_bonus_cicd.py::TestJobDeploy::test_deploy_gioi_han_nhanh PASSED
tests/test_bonus_cicd.py::TestBaoMat::test_secret_lay_tu_github_secrets PASSED
tests/test_bonus_cicd.py::TestBaoMat::test_khong_hardcode_token PASSED
tests/test_bonus_cicd.py::TestBaoMat::test_action_duoc_ghim_phien_ban PASSED
tests/test_bonus_cicd.py::TestBadge::test_readme_co_badge PASSED

12 passed, 1 deselected in 0.21s
```

**12/12 test cấu trúc pass.** Test bị deselect là
`test_badge_bao_passing` — nó **tải badge từ GitHub** và đòi nội dung chứa
`passing`. Chưa push workflow thì badge chưa tồn tại, nên test này **bắt buộc
phải đợi tới lúc workflow chạy thật**. Đây không phải lỗi — nó đang kiểm tra
đúng thứ nó cần kiểm: workflow phải *chạy được*, không chỉ viết cho đẹp.

## Đã làm — `.github/workflows/ci.yml`

Ba job: `test` → `build` → `deploy`.

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

Chạy cả `pull_request` mới là phần giá trị nhất: lỗi bị bắt **trước khi** vào
nhánh chính, không phải sau.

### Job `test`

```yaml
- run: pytest tests/ -v --ignore=tests/test_cp5.py --ignore=tests/test_bonus_cicd.py
  env:
    AGENT_API_KEY: ci-dummy
    REDIS_URL: "fake://"
```

- `test_cp5.py` gọi vào bản deploy đang sống → trong CI luôn đỏ hoặc phải chờ
  mạng.
- `test_bonus_cicd.py` tự kiểm tra chính workflow này → vòng tròn.
- `env:` truyền biến giả vì runner không có `.env`. **Đây đúng là lợi ích của
  12-Factor**: cùng một code, môi trường khác nhau chỉ khác biến môi trường.
- Không truyền `LLM_*`: runner không có LMStudio, và `/ask` dùng mock nên không
  cần.

### Job `build`

```yaml
- run: docker build -t day12-agent:ci .
```

Bắt lỗi kiểu "file này chỉ có trên máy tôi" hoặc `.dockerignore` loại nhầm
thứ cần thiết — hai lỗi đều chỉ lộ ra lúc deploy là quá muộn.

### Job `deploy` — cổng chất lượng

```yaml
needs: [test, build]
if: github.ref == 'refs/heads/main' && github.event_name == 'push' && vars.DEPLOY_ENABLED == 'true'
```

- **`needs:`** xâu test và build thành dây chuyền. Job mặc định chạy **song
  song**; thiếu dòng này thì code hỏng vẫn lên production trong khi test đang
  đỏ.
- **`if:`** chỉ deploy từ nhánh chính, chỉ khi push, và chỉ khi đã bật cờ
  `DEPLOY_ENABLED`.

```yaml
- run: curl -fsS -X POST "${{ secrets.RENDER_DEPLOY_HOOK_URL }}"
- run: |
    sleep 45
    curl -fsS "${{ vars.PUBLIC_URL }}/health"
```

Deploy Hook của Render là **URL bí mật, không phải API token** — cất trong
GitHub Secrets. `curl -f` trả mã lỗi khi HTTP không phải 2xx, nên job đỏ khi
service chết, thay vì "deploy chạy xong" rồi im lặng.

### Bảo mật

- `actions/checkout@v4`, `actions/setup-python@v5` — **ghim phiên bản**, không
  dùng `@main`. `@main` nghĩa là mỗi lần chạy bạn thực thi phiên bản mới nhất
  của code người khác — họ đổi gì hôm nay bạn chịu nấy. Đây là con đường của
  các vụ tấn công chuỗi cung ứng.
- Deploy token nằm trong `${{ secrets.* }}`, không dán vào file YAML. Dán thẳng
  vào YAML thì nó nằm trong lịch sử git vĩnh viễn.

## Việc còn lại để nhận +10

Thứ tự có chủ ý — lần push đầu để có **một run xanh**, rồi mới bật deploy:

```bash
# 1. Push lần 1: DEPLOY_ENABLED=false → job test + build xanh, job deploy skip
git push origin main
gh run watch --exit-status

# 2. Trong GitHub Variables: đổi DEPLOY_ENABLED thành "true"

# 3. Push lần 2: job deploy chạy thật
git commit --allow-empty -m "CI: bat deploy job"
git push origin main
gh run watch --exit-status

# 4. Chấm bonus (bước online cuối cùng)
pytest tests/test_bonus_cicd.py -v
```

**Output mong đợi ở bước 4:** `13 passed`. Riêng `test_badge_bao_passing` tải
badge và đòi `passing` — nếu báo `failing`/`no status` thì workflow chưa từng
chạy xanh trên nhánh `main`, hoặc URL badge sai tên file.

**Nếu smoke test đỏ** vì Render chưa kịp build: tăng `sleep 45` → `sleep 90`
rồi push lại. Chỉ sửa một số, miễn phí.

## Lưu ý về CI

Job `test` trong CI dùng `pytest tests/ -v --ignore=tests/test_cp5.py
--ignore=tests/test_bonus_cicd.py`. Trên runner Linux không có Docker daemon
trong job test, nhưng 2 test `TestBuildThat` có mark `docker` và tự skip — vẫn
xanh. Job `build` chạy `docker build` thật trên runner.
