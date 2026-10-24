# Phase 6: Onboard sách HMU (khi có file)

## Context
* Chưa có PDF hợp pháp công khai. Ứng viên: "Hồi sức cấp cứu toàn tập" (Vũ Văn Đính, NXB Y học; bản web là scan 337MB/644 trang), "Hồi sức tích cực cơ bản" (Nguyễn Đạt Anh, Bạch Mai + Bộ môn HSCC HMU). Nguồn chính thống: thư viện HMU, mua.
* Report gốc bước 2 và 3 pipeline: soát 5 trang, font TCVN3/VNI, marker `--disable_ocr` khi text layer sạch, `--force_ocr` chỉ khi vỡ.

## Overview
Priority P2. Checklist tiếp nhận file → quyết định parser → tái dùng pipeline. Mỗi cuốn 1 working dir `kg/<doc>` (đồ thị riêng, đơn giản, không gộp tên thực thể chéo sách).

## Steps
1. Đặt file `data/raw/<doc>.pdf` (sách bản quyền: gitignore bằng cách thêm dòng `data/raw/<doc>.pdf` vào `.gitignore`, chỉ commit `data/md` nếu được phép, mặc định không commit).
2. Soát: `pdfinfo`, `pdffonts -l 5`, `pdftotext -f 10 -l 14 file.pdf - | head -60`.
   * Có font Unicode + text đọc được → đi bước 4.
   * Text ra ký tự lạ (Ò, ®, ¬, ¨) → font TCVN3/VNI → chuyển mã Unicode bằng bảng ánh xạ (VietUnicode) trong `parse_pdf.py` trước NFC, không OCR.
   * `pdffonts` rỗng hoặc text rỗng → scan → bước 3.
3. OCR trên laptop (GPU): `uv tool install marker-pdf` (torch ~3GB, cài riêng bằng uv tool để không vào lock dự án). `marker_single file.pdf --force_ocr --output_format markdown --output_dir data/work/<doc>`. Kiểm 5 trang ngẫu nhiên: đếm từ sai dấu / tổng từ; > 3% → thử `--languages vi` hoặc Tesseract `vie`; vẫn tệ → dừng, tìm bản có text layer.
4. Thêm profile tách chương mới vào `parse_pdf.py` (đã có 2 profile từ phase 2). Với sách: tách theo "Chương"/"Bài" + số, hoặc theo mục lục. Output `data/md/<doc>/`.
5. Đo token: `chars/3.45` → ước giờ chạy theo giây/chunk của pilot. Sách 600 trang ≈ 400K token ≈ 3 đến 4 giờ.
6. `pixi run index <doc>` → `pixi run serve kg/<doc>`. Lặp phase 5 bước 4 đến 7.
7. Nếu sách có nhiều thuật ngữ mới ngoài schema (ví dụ chống độc) → thêm loại vào YAML, rebuild chỉ cuốn đó.

## Files
* modify `/home/k1en/kg-textbooks/scripts/parse_pdf.py` (profile mới, bảng chuyển mã TCVN3/VNI nếu cần)
* modify `.gitignore`

## Acceptance
* 5 trang mẫu: lỗi dấu < 3%. `pixi run parse <doc> <profile>` deterministic.
* Index xong, stats đạt ngưỡng như phase 5.

## Commit
```
git add scripts .gitignore && git commit -m "feat: chapter split regex and legacy font conversion for HMU book"
```

## Risks
* Bản quyền: không commit PDF/md của sách thương mại lên remote công khai.
* OCR scan 600 trang trên GPU 6GB với marker: VRAM tranh với Ollama → dừng Ollama (`sudo systemctl stop ollama`) khi OCR, bật lại sau.
* Scan nghiêng/mờ → rơi dấu hàng loạt; không có cách rẻ để sửa, cần bản text layer.
