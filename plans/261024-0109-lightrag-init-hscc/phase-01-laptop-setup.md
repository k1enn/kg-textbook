# Phase 1: Laptop setup (pixi: env + Ollama + models)

## Context
* Ollama từ conda-forge qua pixi (build CUDA 12.9, ~850MB). Không sudo, không systemd override.
* Env của task `ollama-serve`: `OLLAMA_NUM_PARALLEL=3`, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_KEEP_ALIVE=-1`. VRAM ≈ 4.2GB. Màn hình chạy GPU rời thì sửa `NUM_PARALLEL` = 2 trong `pixi.toml`.
* Cần: driver NVIDIA có `nvidia-smi` báo CUDA 12.x trở lên, `git`, `tmux`.

## Steps
1. `curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=v0.81.0 bash`, mở shell mới. `git clone` (hoặc `git pull`).
2. `pixi install --all --locked`.
3. `tmux new -d -s ollama 'pixi run ollama-serve 2>&1 | tee -a ollama.log'`, rồi `pixi run ollama-pull`.
4. Smoke LLM + tốc độ: `pixi run -e ollama ollama run --verbose qwen3:4b-instruct-2507-q4_K_M 'Trả lời đúng 1 dòng JSON: {"ok": true}'` → ghi `eval rate` vào `reports/bench.md` (giả định 45 tok/s).
5. Smoke embedding: `curl -s localhost:11434/api/embed -d '{"model":"bge-m3","input":"suy hô hấp cấp"}' | head -c 200`.
6. `nvidia-smi` khi model đã nạp: VRAM < 5GB, process là `ollama`.
7. Kwarg LightRAG đã đối chiếu với wheel 1.5.7 ở VM. Kiểm lại nhanh: `pixi run python -c "import inspect,lightrag; print(lightrag.__version__); print(inspect.signature(lightrag.LightRAG))" | tr , '\n' | grep -E "entity_extraction_use_json|entity_extract_max|force_llm_summary|chunk_token|max_parallel_insert"`.

## Files
* create `plans/261024-0109-lightrag-init-hscc/reports/bench.md` (tok/s, VRAM, version)

## Acceptance
* `pixi install --all --locked` lần 2 không tải gì; `ollama-pull` lần 2 không tải lại model.
* `pixi run -e ollama ollama list` có 2 model. `eval rate` ≥ 30 tok/s. Log `ollama-serve` có dòng nhận GPU CUDA.

## Commit
```
git add plans && git commit -m "docs: laptop bench"
```

## Risks
* Driver chỉ hỗ trợ CUDA 11 → `pixi install` báo thiếu `__cuda`. Nâng driver hoặc đổi build trong `pixi.toml`.
* Đã có Ollama native (systemd) giữ cổng 11434 → `ollama-serve` lỗi bind. Dừng bằng `sudo systemctl disable --now ollama`, model cũ ở `~/.ollama` vẫn dùng được.
* Lần chạy index đầu, tiktoken tải file BPE để đếm token chunk → cần mạng.
