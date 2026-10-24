# Phase 4: Index script + prune bám nguồn + pilot 3 bài

## Context
* Report gốc "Cấu hình khởi điểm" và đòn bẩy 2, 4, 5. API xác nhận từ `examples/lightrag_ollama_demo.py` và `docs/ProgramingWithCore.md` (main 10/2026).
* `ollama_model_complete` đọc tên model từ `llm_model_name`; `host`, `timeout`, `options` đi qua `llm_model_kwargs`. Embedding: `ollama_embed` đã là `EmbeddingFunc` (1024, 8192, bge-m3:latest).
* Bám nguồn: prune sau index (xem bước 1), thay validator của 1.5.8.

## Overview
Priority P1. `scripts/index.py` nạp từng file md làm 1 document (id = tên file), resumable nhờ `doc_status` + LLM cache. `scripts/stats.py` đọc working dir, in chỉ số sức khoẻ. Pilot = 3 bài đầu vào `kg/pilot`, lặp tối đa 3 vòng chỉnh tham số.

## Steps
1. `scripts/index.py --md <dir> --kg <workdir> [--only 01,02,03] [--llm ...]` (code thật trong file). LightRAG 1.5.7 (PyPI mới nhất) chưa có `kg_extraction_validator` (chỉ ở main 1.5.8), nên sau khi nạp xong chạy `prune()`: xoá nút có tên (sau `normalize_entity_name`, gộp khoảng trắng, casefold) không nằm trong chunk nguồn nào của nó, qua `lightrag.utils_graph.adelete_by_entity` có truyền `entity_chunks`, `relation_chunks` (bản public `rag.adelete_by_entity` bỏ sót 2 store này, merge sau sẽ kéo lại chunk id cũ). Mỗi lần xoá ghi lại graphml + 2 vdb nên prune lần đầu của sách dày hơi chậm. So khớp bỏ hết khoảng trắng. `default_llm_timeout=600` (worker cắt ở 2x). Tên đã xoá dồn vào `<kg>/pruned.json`. Ollama host mặc định `127.0.0.1:11434` (biến `OLLAMA_HOST`), embedding dùng thẳng `ollama_embed` (bge-m3:latest, 1024).
2. Idempotent: id = tên file. Id đã có thì không `ainsert` lại (1.5.7 ghi thêm dòng `dup-*` FAILED). Doc `failed` (1.5.7 không tự retry) → `adelete_by_doc_id` rồi nạp lại, chunk đã xong ăn LLM cache. Doc dở (pending/processing) → `apipeline_process_enqueue_documents()` cuối run. Đổi prompt/schema/chunk → `pixi run clean-kg kg/pilot` rồi chạy lại.
3. `scripts/stats.py <workdir>`: đọc `kv_store_doc_status.json` (status, `metadata.llm_truncation`), `kv_store_text_chunks.json` (số chunk), `graph_chunk_entity_relation.graphml` qua networkx (nút, cạnh, % nút cô lập, phân bố `entity_type`, loại ngoài 10 + `khac`), `kv_store_llm_response_cache.json` (tổng ký tự response / 3.45 / số chunk ≈ token out/chunk; tỉ lệ cạnh có keywords bắt đầu bằng prefix hợp lệ). In bảng 1 màn hình. Tên file/khóa phải đối chiếu với working dir thật sau lần chạy đầu.
4. Pilot: `pixi run pilot` (Bài 1 đến 3 của capcuu ≈ 22 trang ≈ 12K token ≈ 18 chunk ≈ 40 lời gọi ≈ 10 đến 15 phút). Ghi `time`, log vào `kg/pilot/index.log`.
5. Đọc stats + mở `graph_chunk_entity_relation.graphml` bằng WebUI (`pixi run serve kg/pilot`) xem 20 nút bậc cao nhất có hợp lý không.
6. Kiểm Ollama cắt input: `grep -c 'truncating input' ollama.log`. Gleaning gửi lại prompt + câu trả lời 1 + `num_predict` 3000 có thể vượt `num_ctx` 8192 → nếu có: `num_ctx` 12288 + `OLLAMA_NUM_PARALLEL=2` (cùng VRAM), hoặc gleaning 0.
7. Vòng chỉnh (tối đa 3): token out/chunk < 400 → thêm ví dụ thứ 2 hoặc giảm chunk 500; cảnh báo truncation → tăng `num_predict` 4000; nhiều loại ngoài schema → siết guidance; nhiều thực thể bị prune (> 40%) → mô hình đang paraphrase, thêm câu "nguyên văn" đậm hơn trong ví dụ.
8. Ghi kết quả pilot vào `plans/261024-0109-lightrag-init-hscc/reports/pilot.md`: tham số cuối, stats, giây/chunk, tok/s.

## Files
* create `/home/k1en/kg-textbooks/scripts/index.py`
* create `/home/k1en/kg-textbooks/scripts/stats.py`
* create `plans/261024-0109-lightrag-init-hscc/reports/pilot.md`

## Acceptance
* 3 doc `processed`, 0 `failed`, 0 truncation.
* Token out/chunk ≥ 400. Nút cô lập < 30%. Loại ngoài schema < 10% số nút. Quan hệ có mã hợp lệ trong keywords ≥ 60% (merge sort lại keywords nên không xét vị trí đầu). 0 dòng `truncating input` trong `ollama.log`. Prune drop < 40%.
* Chạy `pixi run pilot` lần 2 không gọi LLM (log không có insert mới, thời gian < 1 phút).

## Commit
```
git add scripts plans && git commit -m "feat: lightrag index script with grounding prune, pilot stats"
```

## Risks
* `num_ctx` 8192 nhưng prompt hệ thống + chunk + gleaning ≈ 5K đến 6K token; nếu ví dụ YAML dài thì vượt → log Ollama cảnh báo truncation input. Giữ YAML < 120 dòng.
* Ollama vẫn nạp model với context riêng cho mỗi `num_ctx` khác nhau → index và server (10240) không chạy cùng lúc.
* Prune so khớp sau `normalize_entity_name`; drop nhiều thì xem 20 tên in trong log `prune:` để biết lỗi khớp hay mô hình bịa.
