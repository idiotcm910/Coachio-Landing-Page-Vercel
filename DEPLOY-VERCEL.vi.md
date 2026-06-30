# Hướng dẫn deploy Coachio Landing Page lên Vercel (FREE) — Tiếng Việt

Tài liệu này hướng dẫn **đầy đủ từ đầu đến cuối** cách deploy bản này lên **Vercel gói miễn phí (Hobby)**, dùng **Neon** (Postgres) + **Vercel Blob** (media). Không cần Redis, không cần thẻ tín dụng.

> **Kiến trúc:** 1 project Vercel chạy cả **Next.js** (frontend) lẫn **FastAPI** (backend, dạng Serverless Function ở `/api/*`). DB = **Neon**. Media = **Vercel Blob**. Job gửi broadcast chạy **Vercel Cron 1 lần/ngày**. Đơn hết hạn xử lý **lazy** (khi đọc, không cần job nền).

---

## Mục lục
1. [Chuẩn bị](#1-chuẩn-bị)
2. [Import repo vào Vercel](#2-import-repo-vào-vercel)
3. [Tạo Database Neon](#3-tạo-database-neon)
4. [Tạo Vercel Blob (media)](#4-tạo-vercel-blob-media)
5. [Thêm biến môi trường](#5-thêm-biến-môi-trường)
6. [Redeploy](#6-redeploy)
7. [Chạy migration (tạo bảng) — 1 lần](#7-chạy-migration-tạo-bảng--1-lần)
8. [Tạo tài khoản admin — 1 lần](#8-tạo-tài-khoản-admin--1-lần)
9. [Cron gửi broadcast](#9-cron-gửi-broadcast)
10. [Chạy thử](#10-chạy-thử)
11. [Giới hạn gói FREE & lưu ý](#11-giới-hạn-gói-free--lưu-ý)
12. [Xử lý lỗi thường gặp](#12-xử-lý-lỗi-thường-gặp)

---

## 1. Chuẩn bị
- Tài khoản **GitHub** (đã có repo này), **Vercel** (free), sẽ tạo **Neon** + **Blob** ngay trong Vercel.
- Trên **máy của bạn** (để chạy migration + tạo admin 1 lần): **Node 20+**, **pnpm 10+**, **Python 3.12+**, và **Vercel CLI** (`npm i -g vercel`).
- (Tùy chọn) Key dịch vụ ngoài — **để trống vẫn deploy được**, tính năng tương ứng tắt cho tới khi điền:
  - `RESEND_API_KEY` + `RESEND_FROM_EMAIL` → gửi email (receipt, broadcast).
  - `SEPAY_*` → thanh toán SePay/VietQR.
  - `META_DEFAULT_PIXEL_ID` + `META_DEFAULT_CAPI_TOKEN` → tracking Meta.

---

## 2. Import repo vào Vercel
1. Vào https://vercel.com → **Add New → Project**.
2. Chọn repo GitHub `Coachio-Landing-Page-Vercel` → **Import**.
3. Framework Vercel tự nhận **Next.js**; Install Command để mặc định (`pnpm install`). Bấm **Deploy**.

> ⚠️ **Lần deploy đầu có thể BÁO ĐỎ** vì chưa có DB và biến môi trường — **bình thường**. Làm tiếp bước 3–6 rồi redeploy là xanh.

---

## 3. Tạo Database Neon
1. Vào **project → tab Storage → Create Database → chọn Neon (Postgres)**.
2. Đặt tên (vd `neon-coachio`), **Region: Singapore (sin1)** (gần VN), Free tier → **Create**.
3. Khi hỏi **connect vào project** → chọn project Coachio của bạn (Production + Preview + Development).
4. Vercel **tự thêm** vào Environment Variables của project:
   - **`POSTGRES_URL`** — chuỗi **pooled** (host có `-pooler`), app dùng lúc chạy.
   - **`POSTGRES_URL_NON_POOLING`** — chuỗi **non-pooling**, dùng để chạy migration.
   > Tích hợp Neon của Vercel tạo `POSTGRES_URL` + `POSTGRES_URL_NON_POOLING` — app tự đọc, **KHÔNG cần thêm `DATABASE_URL` thủ công** trên Vercel. Migration tự ưu tiên `POSTGRES_URL_NON_POOLING`.
   > Không phải copy tay. Vào **Settings → Environment Variables** thấy các biến `POSTGRES_URL*` là OK.

---

## 4. Tạo Vercel Blob (media)
1. **Storage → Create → Blob**.
2. **Store Name**: vd `coachio-media`. **Region**: Singapore (sin1). **Access: Public** ✅
   > Phải chọn **Public** vì media là ảnh hiển thị trên trang landing công khai — khách ẩn danh phải xem được. (URL là chuỗi hash ngẫu nhiên nên vẫn khó đoán.)
3. **Create** → connect vào project → Vercel tự thêm **`BLOB_READ_WRITE_TOKEN`**.

---

## 5. Thêm biến môi trường
Vào **project → Settings → Environment Variables**, thêm các biến sau (áp dụng cho cả Production & Preview):

| Biến | Bắt buộc | Giá trị |
|---|---|---|
| `POSTGRES_URL` | ✅ (tự có từ bước 3 — do Neon integration tạo) | Neon pooled — app tự đọc, không cần set thêm |
| `POSTGRES_URL_NON_POOLING` | ✅ (tự có từ bước 3 — do Neon integration tạo) | Neon non-pooling — dùng cho migration, tự đọc |
| `BLOB_READ_WRITE_TOKEN` | ✅ (tự có từ bước 4) | Vercel Blob |
| `SECRET_KEY` | ✅ | chuỗi ngẫu nhiên — tạo bằng `openssl rand -hex 32` |
| `CRON_SECRET` | ✅ | chuỗi tự đặt (bảo vệ endpoint cron) |
| `FRONTEND_URL` | ✅ | domain Vercel (vd `https://coachio-xxx.vercel.app`) — **điền sau khi biết domain** (xem bước 6) |
| `RESEND_API_KEY` / `RESEND_FROM_EMAIL` | tùy chọn | gửi email |
| `SEPAY_BANK_NAME` / `SEPAY_ACCOUNT_NUMBER` (+ SEPAY_*) | tùy chọn | thanh toán |
| `META_DEFAULT_PIXEL_ID` / `META_DEFAULT_CAPI_TOKEN` | tùy chọn | tracking |

> Không cần `REDIS_URL`, `S3_*`, `BUNNY_*` — bản này đã bỏ.

---

## 6. Redeploy
1. Sau khi đủ env (ít nhất các dòng **bắt buộc**; `FRONTEND_URL` có thể điền tạm rồi sửa) → tab **Deployments → … (deploy mới nhất) → Redeploy**.
2. Deploy xong sẽ có **domain** (vd `https://coachio-xxx.vercel.app`). Quay lại **Settings → Environment Variables**, set **`FRONTEND_URL`** = domain đó → **Redeploy** lần nữa.

---

## 7. Chạy migration (tạo bảng) — 1 lần
Vercel không có "release phase", nên chạy migration **1 lần từ máy bạn** (sạch & chắc chắn nhất):

```bash
# 1) Clone repo (nếu chưa) và link vào project Vercel
git clone git@github.com:idiotcm910/Coachio-Landing-Page-Vercel.git
cd Coachio-Landing-Page-Vercel
vercel link                       # chọn đúng project Coachio

# 2) Kéo biến môi trường (gồm POSTGRES_URL_NON_POOLING) về máy
#    LƯU Ý: phải có --environment=production, vì env pull mặc định lấy "development"
#    (chỉ có VERCEL_OIDC_TOKEN), còn biến Neon/Blob nằm ở production.
vercel env pull .env.local --environment=production
grep -E 'POSTGRES_URL' .env.local   # phải thấy POSTGRES_URL + POSTGRES_URL_NON_POOLING

# 3) Cài deps backend + chạy migration
cd apps/api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# nạp URL non-pooling rồi chạy migration
# Alembic tự ưu tiên POSTGRES_URL_NON_POOLING (Vercel-Neon) → DATABASE_URL_UNPOOLED → POSTGRES_URL
export $(grep -E '^POSTGRES_URL_NON_POOLING=' ../../.env.local | xargs)
.venv/bin/alembic upgrade head
```
> Alembic tự ưu tiên `POSTGRES_URL_NON_POOLING` (Vercel-Neon) rồi fallback `DATABASE_URL_UNPOOLED` → `POSTGRES_URL` → `DATABASE_URL`. Chạy xong sẽ tạo toàn bộ bảng funnel trên Neon.

---

## 8. Tạo tài khoản admin — 1 lần
Vẫn ở thư mục `apps/api` (env đã pull ở bước 7):
```bash
export $(grep -E '^DATABASE_URL=' ../../.env.local | xargs)
.venv/bin/python -m app.scripts.create_admin --email ban@email.com --password 'matkhau-manh-cua-ban'
```
Tài khoản này dùng để đăng nhập `/admin`.

---

## 9. Cron gửi broadcast
- Đã khai sẵn trong `vercel.json`: Vercel Cron gọi `POST /api/v1/cron/dispatch-broadcasts` **1 lần/ngày** (giới hạn gói Hobby), kèm header `Authorization: Bearer $CRON_SECRET`.
- Không cần làm gì thêm. Muốn **gửi ngay** (test thủ công):
  ```bash
  curl -X POST "https://<domain>.vercel.app/api/v1/cron/dispatch-broadcasts" \
       -H "Authorization: Bearer <CRON_SECRET của bạn>"
  ```

---

## 10. Chạy thử
Mở domain Vercel và làm theo:
1. Vào `https://<domain>/admin` → đăng nhập bằng admin vừa tạo (bước 8).
2. Tạo 1 **Product** (loại `digital`, có giá).
3. Tạo 1 **Funnel** trỏ tới product → soạn landing → **Publish** (đổi trạng thái sang active).
4. Mở trang landing công khai: `https://<domain>/funnels/<slug>` → kiểm tra hiển thị (200).
5. Thử **thu lead** + **checkout** → tạo đơn (nếu có `SEPAY_*` thì ra QR; không có thì vẫn tạo đơn PENDING).
6. (Tùy chọn) Upload ảnh trong admin → kiểm tra ảnh hiện trên landing (Blob Public hoạt động).

---

## 11. Giới hạn gói FREE & lưu ý
- **Cron 1 lần/ngày** (Hobby): email broadcast bị trễ tối đa ~1 ngày. Đơn hết hạn KHÔNG bị ảnh hưởng (xử lý lazy khi đọc).
- **Cold start**: hàm serverless + Neon autosuspend → request đầu sau khi rảnh chậm vài trăm ms. Neon tự thức dậy (không cần bấm restore như Supabase).
- **Blob free 256MB**, **Neon free 0.5GB / 100 CU-hours/tháng** — đủ cho demo.
- **ToS Hobby** thiên về **phi thương mại** — hợp để chạy thử / template. Bán hàng thật nên cân nhắc gói Pro.

---

## 12. Xử lý lỗi thường gặp
- **Deploy đỏ lần đầu** → thiếu env/DB. Làm đủ bước 3–5 rồi Redeploy.
- **Build lỗi `-r ../apps/api/requirements.txt`** (Vercel Python không thấy file) → mở `api/requirements.txt`, thay dòng `-r ...` bằng **dán thẳng nội dung** `apps/api/requirements.txt` vào, commit lại.
- **`vercel env pull` chỉ ra `VERCEL_OIDC_TOKEN`** (thiếu DATABASE_URL...) → bạn đang kéo môi trường `development`. Chạy lại với **`--environment=production`**. Nếu vẫn thiếu → vào **Storage → database Neon → Connect Project** và tick cả 3 môi trường. Cách chắc nhất: copy thẳng `DATABASE_URL_UNPOOLED` từ dashboard rồi `export DATABASE_URL_UNPOOLED='...'` trước khi chạy `alembic upgrade head`.
- **Migration lỗi do pooler** (prepared statement / DDL) → đảm bảo đang dùng **`DATABASE_URL_UNPOOLED`** (bước 7), không dùng URL pooled để chạy alembic.
- **Ảnh không hiện trên landing** → Blob store phải là **Public** (bước 4). Nếu lỡ tạo Private, tạo store mới Public và cập nhật `BLOB_READ_WRITE_TOKEN`.
- **Upload ảnh lỗi** → kiểm tra `BLOB_READ_WRITE_TOKEN` đã có; nếu Vercel đổi `x-api-version` của Blob API, báo lại để cập nhật `app/services/blob_storage_service.py`.
- **Cron không chạy** → kiểm tra `CRON_SECRET` đã set; xem tab **Deployments → Cron** trên Vercel; test thủ công bằng lệnh curl ở bước 9.
- **Đăng nhập `/admin` lỗi** → đã chạy migration (bước 7) + tạo admin (bước 8) chưa; `SECRET_KEY` đã set chưa.

---

Có lỗi mà chưa rõ → chụp log Vercel/Neon gửi để được hỗ trợ. Chúc deploy thành công! 🚀
