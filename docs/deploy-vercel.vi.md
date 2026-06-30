# Hướng dẫn deploy Coachio Landing Page lên Vercel (miễn phí)

> **Đây là bản Vercel Edition** — toàn bộ chạy trên Vercel Hobby (miễn phí).
> Dành cho demo, template, thử nghiệm. Hobby ToS phi-thương-mại.

---

## Mục lục

1. [Tổng quan kiến trúc & giới hạn free](#1-tổng-quan-kiến-trúc--giới-hạn-free)
2. [Chuẩn bị](#2-chuẩn-bị)
3. [Tạo Neon database qua Vercel](#3-tạo-neon-database-qua-vercel)
4. [Import repo vào Vercel](#4-import-repo-vào-vercel)
5. [Tạo Vercel Blob store](#5-tạo-vercel-blob-store)
6. [Cấu hình biến môi trường](#6-cấu-hình-biến-môi-trường)
7. [Deploy & chạy migration](#7-deploy--chạy-migration)
8. [Tạo tài khoản admin đầu tiên](#8-tạo-tài-khoản-admin-đầu-tiên)
9. [Bật Vercel Cron (broadcast)](#9-bật-vercel-cron-broadcast)
10. [Chạy thử](#10-chạy-thử)
11. [Giới hạn & lưu ý quan trọng](#11-giới-hạn--lưu-ý-quan-trọng)
12. [Khắc phục sự cố](#12-khắc-phục-sự-cố)

---

## 1. Tổng quan kiến trúc & giới hạn free

```
1 Vercel project (Hobby — miễn phí)
├── Next.js  (apps/web)               ← frontend (framework preset tự nhận)
├── api/index.py  → FastAPI ASGI      ← @vercel/python serverless function
│     vercel.json: /api/(.*) → /api/index
├── Vercel Cron (1x/ngày)             → /api/v1/cron/dispatch-broadcasts
└── Vercel Storage (cùng account):
      Neon Postgres (free tier)
      Vercel Blob (free tier)
```

**Những gì KHÔNG có trong bản Vercel Edition:**
- Không Redis (in-process cache, gần như no-op khi serverless)
- Không tính năng quà tặng ngoài (gift/gift-automation)
- Không background job liên tục (chỉ Vercel Cron 1x/ngày cho broadcast)
- Hết hạn đơn: lazy expiry — đơn PENDING quá hạn chỉ bị đánh dấu EXPIRED khi có ai đọc đơn đó, không cần cron

**Giới hạn Hobby (chấp nhận cho demo):**
| Hạng mục | Giới hạn |
|---|---|
| Cron | 1 job/ngày (broadcast trễ tối đa ~24 giờ) |
| Vercel Blob | 256 MB lưu trữ |
| Function timeout | 10–60 giây (Hobby); chỉnh qua `maxDuration` trong `vercel.json` |
| Cold start | Lần gọi đầu sau thời gian idle sẽ chậm 1–3 giây |
| ToS | Hobby cho phép dùng cá nhân / demo / template — **không dùng production thương mại** |

---

## 2. Chuẩn bị

Bạn cần:
- **Tài khoản [Vercel](https://vercel.com)** (miễn phí, Hobby plan)
- **Fork hoặc clone repo này** lên GitHub/GitLab của bạn (Vercel cần truy cập git)
- Máy tính có cài Python 3.12 và `pip` (để chạy migration tay nếu cần)
- *(Tùy chọn)* Tài khoản [Resend](https://resend.com) để gửi email; tài khoản SePay và Meta nếu muốn dùng thanh toán QR và tracking

**Lệnh sinh secret key** (dùng ở bước 6):
```bash
openssl rand -hex 32
```

---

## 3. Tạo Neon database qua Vercel

Neon là Postgres-as-a-service được tích hợp native vào Vercel. Bạn **không cần tài khoản Neon riêng** — tạo thẳng từ Vercel dashboard.

> **Thực hiện bước này SAU khi đã import repo vào Vercel** (bước 4). Nếu bạn chưa import, import trước rồi quay lại đây.

1. Trong Vercel project → tab **Storage** → nhấn **Create Database**.
2. Chọn **Neon (Postgres)** → nhấn **Continue**.
3. Đặt tên database (ví dụ: `coachio-db`), chọn region gần VN nhất (Singapore: `ap-southeast-1`).
4. Nhấn **Create** → Vercel tạo Neon database và **tự động inject** hai biến môi trường vào project của bạn:
   - `DATABASE_URL` — pooled connection string (host có đuôi `-pooler`), dùng cho runtime app.
   - `DATABASE_URL_UNPOOLED` — non-pooling URL, dùng cho Alembic migrations.
5. **Không cần copy tay** — Vercel inject tự động vào tất cả môi trường (Production, Preview, Development).

> **Tại sao cần 2 URL?** Neon transaction-pooler (dùng pooled URL) không hỗ trợ toàn bộ DDL lệnh của Alembic. `DATABASE_URL_UNPOOLED` (kết nối trực tiếp) giải quyết vấn đề này. Runtime app vẫn dùng `DATABASE_URL` (pooled) như bình thường.

> **Neon autosuspend:** database tự ngủ sau ~5 phút không có request và tự thức khi có request mới (cold-start ~vài trăm ms). Không cần resume thủ công.

---

## 4. Import repo vào Vercel

1. Đăng nhập [vercel.com](https://vercel.com) → nhấn **Add New… → Project**.
2. Chọn **Import Git Repository** → kết nối GitHub/GitLab → chọn repo `coachio-landing-page-vercel` của bạn.
3. Trong màn hình cấu hình project:
   - **Root Directory**: để **trống** (repo root)
   - **Framework Preset**: Vercel sẽ tự nhận **Next.js** — giữ nguyên
   - **Install Command**: `pnpm install --frozen-lockfile`
   - **Build Command**: `pnpm exec nx run web:build` (hoặc để Vercel tự nhận từ `package.json`)
4. **Chưa nhấn Deploy** — cần điền biến môi trường trước (bước 6).

> FastAPI được phục vụ bởi `api/index.py` theo cấu hình `vercel.json` — Vercel tự nhận Python runtime, không cần cấu hình thêm.

---

## 5. Tạo Vercel Blob store

Vercel Blob là nơi lưu file media (hình ảnh, tài liệu) thay cho S3/Bunny.

1. Trong Vercel dashboard → **Storage** (menu trên) → **Create** → chọn **Blob**.
2. Đặt tên store (ví dụ: `coachio-media`).
3. Nhấn **Connect to project** → chọn project bạn vừa import.
4. Sau khi tạo, vào store → tab **Quickstart** → copy giá trị **`BLOB_READ_WRITE_TOKEN`**.
   - Token có dạng `vercel_blob_rw_...`
5. Lưu token này để điền vào biến môi trường ở bước 6.

---

## 6. Cấu hình biến môi trường

Trong Vercel project → **Settings** → **Environment Variables** → thêm từng biến dưới đây.

### Biến bắt buộc

| Biến | Ví dụ / Cách lấy | Ghi chú |
|---|---|---|
| `DATABASE_URL` | **Auto-inject** bởi Neon integration (bước 3) | Pooled URL — Vercel tự set, không cần nhập tay |
| `DATABASE_URL_UNPOOLED` | **Auto-inject** bởi Neon integration (bước 3) | Non-pooling URL dùng cho Alembic — Vercel tự set |
| `SECRET_KEY` | `openssl rand -hex 32` | **Bắt buộc** — ký JWT admin |
| `BLOB_READ_WRITE_TOKEN` | Token từ Vercel Blob (bước 5) | **Bắt buộc** nếu dùng media upload |
| `CRON_SECRET` | Chuỗi ngẫu nhiên ≥ 16 ký tự | **Bắt buộc** — bảo vệ endpoint cron |
| `FRONTEND_URL` | `https://<project>.vercel.app` | URL domain Vercel của bạn |

> **Sinh CRON_SECRET:** `openssl rand -hex 16` hoặc tự đặt chuỗi bất kỳ ≥ 16 ký tự.

### Biến nên có

| Biến | Ghi chú |
|---|---|
| `ADMIN_EMAIL` | Email admin mặc định (dùng bởi script seed) |
| `NEXT_PUBLIC_BACKEND_URL` | Để **trống** hoặc `/api` — same-origin, Vercel tự xử lý |

### Biến tùy chọn (để trống vẫn deploy được)

| Biến | Mục đích |
|---|---|
| `RESEND_API_KEY` | Gửi email (receipt, broadcast); trống → email inert |
| `RESEND_FROM_EMAIL` | Địa chỉ email gửi đã verify trên Resend |
| `SEPAY_BANK_NAME` | Ngân hàng nhận tiền (ví dụ: `OCB`, `MBBank`) |
| `SEPAY_ACCOUNT_NUMBER` | Số tài khoản nhận thanh toán QR |
| `META_DEFAULT_PIXEL_ID` | Meta Pixel ID để tracking |
| `META_DEFAULT_CAPI_TOKEN` | Meta CAPI access token |
| `IPINFO_TOKEN` | Token IPInfo để geo advanced matching |

> Các biến optional để trống sẽ làm tính năng tương ứng không hoạt động (inert) nhưng app vẫn chạy bình thường.

### Thiết lập Environment scope

Với mỗi biến, chọn scope **Production** (và **Preview** nếu muốn). Không cần chọn Development vì local dev dùng `.env`.

---

## 7. Deploy & chạy migration

### 7.1. Deploy lần đầu

Sau khi điền xong biến môi trường → nhấn **Deploy** (hoặc quay lại tab Deployments → **Redeploy**).

Vercel sẽ:
1. Cài pnpm dependencies
2. Build Next.js (`apps/web`)
3. Đóng gói Python function (`api/index.py`)

Lần đầu build mất khoảng 2–5 phút. Khi thanh tiến trình xanh hoàn tất → app đã live.

### 7.2. Chạy Alembic migration

Vercel **không có release phase** như Railway/Heroku, nên bạn phải chạy migration riêng. Có 2 cách:

#### Cách A — Thêm vào Build Command (tự động mỗi lần deploy)

Trong Vercel project → **Settings** → **General** → **Build Command**, đổi thành:

```bash
cd apps/api && DATABASE_URL_UNPOOLED=$DATABASE_URL_UNPOOLED alembic upgrade head && cd ../.. && pnpm exec nx run web:build
```

> Cách này chạy migration tự động trước mỗi lần build, dùng `DATABASE_URL_UNPOOLED` (non-pooling) vì Neon transaction-pooler không hỗ trợ toàn bộ DDL của Alembic.
> **Lưu ý:** `DATABASE_URL_UNPOOLED` đã được Neon integration auto-inject — đảm bảo scope **Production** đã được set.

#### Cách B — Chạy tay một lần từ máy local (đơn giản hơn)

```bash
# Clone repo về máy (nếu chưa có)
git clone <your-repo-url>
cd <repo-dir>/apps/api

# Cài dependencies
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Chạy migration dùng Neon non-pooling URL (lấy từ Vercel → Storage → Neon → Connection Details)
DATABASE_URL_UNPOOLED="postgresql://...@ep-foo-bar.ap-southeast-1.aws.neon.tech/neondb" \
  alembic upgrade head
```

> Lấy `DATABASE_URL_UNPOOLED` từ Vercel project → **Storage** → database Neon → **Connection Details** → chọn tab **Direct**.
> Cách B là cách đơn giản nhất khi mới bắt đầu.

---

## 8. Tạo tài khoản admin đầu tiên

Sau khi migration chạy xong, tạo admin bằng script (chạy từ máy local, nhắm Neon):

```bash
cd apps/api
source .venv/bin/activate

DATABASE_URL="postgresql://...@ep-foo-bar.ap-southeast-1.aws.neon.tech/neondb" \
  python -m app.scripts.create_admin \
    --email admin@example.com \
    --password "MatKhauManh123!"
```

Thay URL bằng `DATABASE_URL_UNPOOLED` (hoặc `DATABASE_URL` pooled — script chạy được với cả hai).
Thay `admin@example.com` và mật khẩu bằng thông tin thật của bạn.

> Script này tạo admin hoặc cập nhật mật khẩu nếu email đã tồn tại. Chạy lại an toàn.

---

## 9. Bật Vercel Cron (broadcast)

Cron đã được cấu hình trong `vercel.json` của repo:

```json
{
  "crons": [
    {
      "path": "/api/v1/cron/dispatch-broadcasts",
      "schedule": "0 2 * * *"
    }
  ]
}
```

Vercel tự đọc cấu hình này khi deploy. Để xem và quản lý:

1. Vercel project → **Settings** → **Cron Jobs** — bạn sẽ thấy job `dispatch-broadcasts` chạy hàng ngày lúc 02:00 UTC (09:00 giờ Việt Nam).
2. Đảm bảo biến `CRON_SECRET` đã set (bước 6) — endpoint cron kiểm tra header này để tránh gọi trái phép.

**Test cron thủ công** (không cần đợi schedule):

```bash
curl -X POST \
  -H "Authorization: Bearer <CRON_SECRET>" \
  https://<project>.vercel.app/api/v1/cron/dispatch-broadcasts
```

Thay `<CRON_SECRET>` bằng giá trị bạn đã set và `<project>` bằng tên project Vercel.

---

## 10. Chạy thử

Sau khi deploy thành công, làm theo các bước sau để xác nhận mọi thứ hoạt động:

### Bước 1 — Mở trang và đăng nhập admin

Truy cập `https://<project>.vercel.app/admin` → đăng nhập bằng email/mật khẩu admin vừa tạo ở bước 8.

**Kỳ vọng:** Màn hình dashboard admin hiển thị, không có lỗi 500.

> Lần đầu mở trang sau thời gian idle có thể mất 1–3 giây (cold start) — bình thường.

### Bước 2 — Tạo sản phẩm

Admin → **Sản phẩm** → **Tạo mới** → điền tên, giá (VND), loại `digital` → Lưu.

**Kỳ vọng:** Sản phẩm xuất hiện trong danh sách.

### Bước 3 — Tạo funnel

Admin → **Funnels** → **Tạo mới** → điền tên, slug (ví dụ: `thu-nghiem`), chọn sản phẩm → Lưu.

**Kỳ vọng:** Funnel tạo thành công, có thể vào chỉnh sửa sections.

### Bước 4 — Publish funnel

Trong trang chỉnh sửa funnel → nhấn **Publish** → trạng thái chuyển sang `published`.

**Kỳ vọng:** Nút publish thành công, không lỗi.

### Bước 5 — Xem landing public

Mở trình duyệt → truy cập `https://<project>.vercel.app/funnels/thu-nghiem`.

**Kỳ vọng:** Landing page hiển thị đúng nội dung funnel.

### Bước 6 — Thu lead và checkout

1. Điền form lead trên landing page → submit → lead được ghi vào DB.
2. Nhấn nút checkout (nếu có) → màn hình hiển thị QR VietQR (nếu đã cấu hình SePay) hoặc thông báo chờ thanh toán.

**Kỳ vọng:**
- Nếu KHÔNG có SePay key: đơn tạo ở trạng thái PENDING, không crash.
- Nếu CÓ SePay key: QR VietQR hiển thị với số tiền và mã đơn hàng.

### Bước 7 — Kiểm tra đơn hàng

Admin → **Đơn hàng** → xem đơn vừa tạo.

**Kỳ vọng:** Đơn PENDING hiển thị trong danh sách, `expires_at` được set.

### Bước 8 — (Tùy chọn) Kiểm tra broadcast cron

```bash
curl -X POST \
  -H "Authorization: Bearer <CRON_SECRET>" \
  https://<project>.vercel.app/api/v1/cron/dispatch-broadcasts
```

**Kỳ vọng:** Response 200, body JSON có thông tin số broadcast đã xử lý (có thể là 0 nếu chưa có broadcast).

---

## 11. Giới hạn & lưu ý quan trọng

### Hobby ToS phi-thương-mại

Vercel Hobby plan không cho phép dùng cho ứng dụng thương mại. Repo này phù hợp cho:
- Demo cá nhân
- Template trình diễn
- Học tập và phát triển

Khi dùng thực tế, nâng lên Vercel Pro hoặc tự host.

### Broadcast trễ tối đa ~1 ngày

Cron chạy 1 lần/ngày. Nếu bạn tạo broadcast lúc 10:00 sáng và cron chạy lúc 09:00 thì phải đợi đến ngày hôm sau. Đây là trade-off của Hobby plan.

### Cold start

Lần đầu truy cập sau thời gian idle, FastAPI function cần khởi động. Thường mất 1–3 giây. Sau đó các request tiếp theo sẽ nhanh hơn (cho đến khi idle lại).

Neon database cũng autosuspend sau ~5 phút không có request và tự thức khi có request mới (cold-start DB ~vài trăm ms). Không cần thao tác thủ công — request tiếp theo sẽ tự kết nối lại.

### Vercel Blob 256 MB

Free tier giới hạn 256 MB lưu trữ. Đủ cho demo với ít file. Nếu cần nhiều hơn, nâng plan hoặc dùng Cloudflare R2 / S3.

### Lazy expiry đơn hàng

Không có background job liên tục. Đơn PENDING quá hạn (`expires_at`) chỉ bị đánh dấu EXPIRED **khi có request đọc đơn đó** (kiểm tra trạng thái hoặc tạo checkout mới). Danh sách đơn admin hiển thị theo thời gian ghi nhận, không tự cập nhật hàng loạt.

### NEXT_PUBLIC_BACKEND_URL = để trống (same-origin)

Trong Vercel Edition, FE và BE cùng domain. Client gọi `/api/...` tương đối — không cần `NEXT_PUBLIC_BACKEND_URL`. Để trống biến này trong Settings.

---

## 12. Khắc phục sự cố

### Trang trắng / 500 error sau deploy

1. Kiểm tra **Vercel Logs** → Function Logs → tìm dòng lỗi Python.
2. Nguyên nhân thường gặp: `DATABASE_URL` chưa set hoặc Neon integration chưa kết nối với project.
3. Vào Vercel → **Storage** → database Neon → **Connect to Project** nếu chưa kết nối.

### 502 Bad Gateway khi gọi API

Thường do connection DB thất bại:
- Kiểm tra `DATABASE_URL` đã được inject bởi Neon integration (xem trong **Settings** → **Environment Variables**).
- Neon autosuspend: database tự thức khi có request — cold-start lần đầu có thể chậm vài trăm ms nhưng sẽ tự hoàn thành, không cần resume thủ công.

### Cron không chạy

1. Kiểm tra `CRON_SECRET` đã set trong Environment Variables.
2. Vercel → **Settings** → **Cron Jobs** — xem status của job gần nhất.
3. Test thủ công bằng lệnh `curl` ở bước 9.

### Media upload lỗi

1. Kiểm tra `BLOB_READ_WRITE_TOKEN` đã set và đúng token từ Vercel Blob store.
2. Kiểm tra Blob store đã được Connect to project.

### Migration chưa chạy — bảng không tồn tại

Triệu chứng: `relation "funnel" does not exist` hoặc tương tự.

```bash
# Chạy lại migration từ máy local (cách B từ bước 7)
cd apps/api
DATABASE_URL_UNPOOLED="<neon-direct-url>" alembic upgrade head
```

### Email không gửi được

Nếu `RESEND_API_KEY` chưa set hoặc sai → email inert (không crash, chỉ không gửi). Kiểm tra log Vercel để xác nhận.

---

*Repo: [coachio-landing-page-vercel](https://github.com/sonlovinbot/coachio-landing-page-vercel)*
*Upstream: [coachio-landing-page](https://github.com/sonlovinbot/coachio-landing-page)*
