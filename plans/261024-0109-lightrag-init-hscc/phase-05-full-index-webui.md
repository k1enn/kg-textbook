# Phase 5: Index full + WebUI + query sanity

## Context
* Ước tính capcuu: 74K token ≈ 105 chunk 700 ≈ 210 lời gọi → 40 đến 60 phút với 3 luồng. hstc: 140K ≈ 200 chunk → 1 đến 1.5 giờ. Thực tế lấy giây/chunk từ pilot × số chunk. Chạy capcuu trước, hstc sau bằng `pixi run index byt_hstc_2015`.
* `lightrag-server` đọc `.env`; cấu hình chunk/embedding phải trùng Core, nếu không upload qua WebUI sẽ tạo chunk lệch. Quy ước: nạp tài liệu chỉ qua `pixi run index`, WebUI chỉ duyệt, query, gộp thực thể.

## Overview
Priority P1. Chạy `pixi run index` qua đêm hoặc trong tmux, resumable. Sau đó `pixi run serve`, duyệt đồ thị, gộp trùng bằng tay, 20 câu hỏi `mix` vs `naive`.

## Steps
1. Tham số cuối từ pilot đã ghi vào `index.py` (hoặc flag). `pixi run clean-kg kg/<doc>` nếu từng chạy thử trước đó với tham số khác.
2. `tmux new -s idx 'pixi run index 2>&1 | tee -a index.log'`. Theo dõi: `grep -c done index.log`, `nvidia-smi`, `ollama ps`.
3. Ngắt giữa chừng (mất điện, Ctrl C) → chạy lại `pixi run index`: doc đã xong bị bỏ qua, doc dở làm lại từ chunk cache.
4. Xong: `pixi run python scripts/stats.py kg/byt_capcuu_coban_2014` → dán vào `reports/full-index.md`. Kỳ vọng: nút ≥ 1.000, cạnh ≥ 1.500, cô lập < 25%.
5. `cp .env.example .env` (laptop), `pixi run serve` → http://127.0.0.1:9621. Xác nhận server đọc đúng `WORKING_DIR`, số doc = số bài.
6. Gộp trùng: trong WebUI tìm các cặp viết tắt/đầy đủ (ví dụ "ARDS" và "hội chứng suy hô hấp cấp tiến triển", "SNK" và "sốc nhiễm khuẩn"). Gộp tay 20 đến 30 cặp bậc cao nhất. Ghi danh sách vào `reports/merges.md` để làm lại được sau rebuild (WebUI merge gọi `amerge_entities`, không tự lặp lại).
7. Query sanity: 20 câu tự đặt từ 5 bài (có số trang), chạy `mix` (top_k 20, chunk_top_k 8, max_total_tokens 8000) và `naive`. Chấm tay đúng/sai/thiếu. Ghi `reports/qa-sanity.md`. Mỗi câu ≈ 10 đến 20 giây.
8. Tiêu chí đi tiếp (report gốc, kết luận): `mix` không thua `naive` → dùng cả 2; `mix` thua rõ → KG chỉ dùng để duyệt, hỏi đáp dùng `naive`.

## Files
* create `plans/261024-0109-lightrag-init-hscc/reports/full-index.md`, `merges.md`, `qa-sanity.md`
* laptop only: `.env` (gitignore), `kg/*/` (gitignore)

## Acceptance
* Tất cả bài `processed`, 0 failed. Stats đạt ngưỡng bước 4.
* WebUI mở được, graph hiện, query `mix` trả lời tiếng Việt có trích dẫn chunk.
* `pixi run index` lần 2 kết thúc < 1 phút không gọi LLM.

## Commit
```
git add plans && git commit -m "docs: full index stats, merges, qa sanity for BYT HSTC"
```

## Risks
* Tóm tắt khi gộp (`force_llm_summary_on_merge=20`) với SLM có thể đổi sang tiếng Anh hoặc bịa → kiểm 10 mô tả nút bậc cao; tệ thì nâng ngưỡng lên 50.
* Server và index cùng chạy → 2 bản model trong VRAM (num_ctx khác) → OOM/tràn CPU. Chỉ chạy 1 trong 2.
* Query 8K context với `top_k=20` vẫn có thể vượt `num_ctx` 10240 khi mô tả thực thể dài → giảm `top_k` 15.
