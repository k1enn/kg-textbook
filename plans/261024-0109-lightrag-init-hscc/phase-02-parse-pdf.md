# Phase 2: Parse PDF → markdown từng bài

## Context
2 tài liệu, 2 cấu trúc khác nhau → `parse_pdf.py` có `--profile {capcuu,hstc}`.

| | `byt_capcuu_coban_2014.pdf` (chính) | `byt_hstc_2015.pdf` |
|---|---|---|
| Nguồn | Bộ Y tế, Cục QLKCB, NXB Y học 2014, JICA. Chủ biên Lương Ngọc Khuê, Đặng Quốc Tuấn (Bộ môn HSCC HMU); soạn: Đỗ Ngọc Sơn, Đào Xuân Cơ, Nguyễn Trung Nguyên (Bạch Mai) | QĐ 1493/QĐ-BYT 2015 |
| Trang, ký tự, token | 148, 256K, ~74K | 216, 482K, ~140K |
| Text layer | Word 2010, sạch, 0 lỗi `ƣ` | Word 2007, 146 lỗi `ƣ` |
| Ảnh | 34 hình minh hoạ (bỏ qua) | ít |
| Cấu trúc | 16 bài. Dòng `Bài N` đứng riêng, tiêu đề ở dòng sau. Mỗi bài: MỤC TIÊU (1, 2, 3...), NỘI DUNG (mục 1, 2, 3...), TÀI LIỆU THAM KHẢO. Phần A lý thuyết (13 bài), phần B kỹ thuật (3 bài) | 30 đến 40 bài. Tiêu đề IN HOA 1 đến 2 dòng ngay trước `1. ĐẠI CƯƠNG`, mục 1 đến 7 |
| Phần đầu | bìa, lời nói đầu, mục lục ≈ 150 dòng | quyết định, mục lục, viết tắt ≈ 190 dòng |

## Overview
Priority P1. `scripts/parse_pdf.py <pdf> <outdir> --profile capcuu|hstc [--clean]` deterministic. Mỗi bài 1 file `NN-slug.md`, H1 là tiêu đề. Phần đầu → `00-front.md` (không index). Bỏ "TÀI LIỆU THAM KHẢO" (tên tác giả thành thực thể rác).

## Steps
1. Đọc từng trang bằng `pymupdf` `page.get_text()` (pymupdf4llm 1.28 kéo onnxruntime + model layout 43MB, 2.0 chỉ là gói rỗng 5 ngày tuổi). Font Symbol (U+F0xx) map sang ↑ ↓ ≥ ≤ μ β Δ →.
2. Mỗi trang bỏ dòng chỉ là số trang, bỏ dòng header lặp (≥ 50% số trang). Nối trang bằng `\n`.
3. Chuẩn hoá: thay `ƣ→ư`, `Ƣ→Ư`, `unicodedata.normalize("NFC")`, gộp ≥ 3 dòng trống thành 2.
4. Tách bài theo profile:
   * `capcuu`: điểm cắt = dòng khớp `^\**\s*Bài\s+(\d+)\s*\**$`. Tiêu đề = các dòng không rỗng tiếp theo cho tới trước `MỤC TIÊU` (tối đa 3 dòng). Cắt bỏ từ dòng `TÀI LIỆU THAM KHẢO` tới hết bài (bỏ luôn CÂU HỎI LƯỢNG GIÁ: đáp án sai thành sự thật giả). Giữ MỤC TIÊU (ngắn, có ích cho câu hỏi tự học).
   * `hstc`: điểm cắt = `^\**\s*1\.\s*ĐẠI CƯƠNG`. Tiêu đề = tối đa 3 dòng IN HOA liền trước.
5. Slug: NFD → bỏ dấu → ascii lower → `[^a-z0-9]+` → `-`, cắt 60. File `f"{n:02d}-{slug}.md"`, nội dung `# {title}\n\n{body}`.
6. `--clean`: `shutil.rmtree(outdir)` trước khi ghi.
7. In: số bài, tổng ký tự, ước token (`chars/3.45`), bài < 1.500 ký tự (cảnh báo).
8. Laptop: `pixi run parse` (capcuu) và `pixi run parse byt_hstc_2015 hstc`.
9. Kiểm: `ls data/md/byt_capcuu_coban_2014 | wc -l` = 17 (16 bài + front); `grep -rl 'ƣ' data/md | wc -l` = 0; `grep -l 'TÀI LIỆU THAM KHẢO' data/md/*/*.md | wc -l` = 0; đọc 2 file bằng mắt.
10. Commit `data/md/`.

## Files
* create `/home/k1en/kg-textbooks/scripts/parse_pdf.py`
* create `/home/k1en/kg-textbooks/data/md/byt_capcuu_coban_2014/*.md`, `data/md/byt_hstc_2015/*.md`
* modify `pixi.toml` (task `parse` nhận `doc profile`)

## Acceptance
* `pixi run parse` 2 lần → `git status` không đổi.
* capcuu: 16 bài, bài 1 là "Nhận định và kiểm soát ban đầu bệnh nhân cấp cứu", tổng 158K ký tự (~46K token). Mốc 230K cũ đếm cả mục lục, TLTK, câu hỏi lượng giá, phác đồ bài 6, bảng kiểm thực hành; pymupdf đếm cả PDF chỉ 191K.
* hstc: 30 đến 41 bài, 0 ký tự `ƣ`, 34 bài = mục lục, tổng 316K ký tự (~92K token); bài 33, 34 ngắn thật (~1.1K). Bài 30 mở bằng `1. KHÁI NIỆM CƠ BẢN` nên regex nhận cả `KHÁI NIỆM`.

## Commit
```
git add scripts/parse_pdf.py data/md pixi.toml && git commit -m "feat: parse BYT cap cuu + HSTC pdfs into per-lesson markdown"
```

## Risks
* Kiểm danh sách tiêu đề in ra sau mỗi lần sửa regex.
* Phần B kỹ thuật (bài 14 đến 16) nhiều bước thao tác, ít bệnh/thuốc → đồ thị thưa ở đó là bình thường.
* Mục lục capcuu ghi trang lệch (bài 8 trang 53 < bài 7 trang 55) → không dùng mục lục để tách, chỉ dùng dòng `Bài N`.
