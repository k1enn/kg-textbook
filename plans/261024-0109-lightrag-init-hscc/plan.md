---
title: "Init LightRAG local cho KG Hồi sức cấp cứu"
description: "Dựng pipeline PDF → LightRAG (Ollama, Qwen3 4B, bge-m3) chạy trên laptop GPU 6GB, pilot bằng BYT HSTC 2015, sau đó cắm sách HMU"
status: in-progress
priority: P2
effort: 10h
branch: main
tags: [infra, backend, experimental, lightrag, kg]
blockedBy: []
blocks: []
created: 2026-10-24
---

# Init LightRAG local cho KG Hồi sức cấp cứu

## Overview

Dựng pipeline PDF → markdown từng bài → LightRAG Core (JSON mode, schema HSCC, prune bám nguồn) → WebUI duyệt đồ thị. Runtime toàn bộ trên laptop Linux GPU 6GB (pixi: Python env + Ollama, không Docker). VM này chỉ soạn code, sync qua git. Tài liệu chính: `data/raw/byt_capcuu_coban_2014.pdf` (Bộ Y tế, NXB Y học 2014, chủ biên Đặng Quốc Tuấn Bộ môn HSCC HMU; 148 trang, 16 bài, ~74K token, text layer sạch). Tài liệu 2: `data/raw/byt_hstc_2015.pdf` (216 trang, ~140K token). Sách HMU thương mại cắm vào phase 6.

Brainstorm đã duyệt: [reports/261024-0109-brainstorm-lightrag-init-hscc.md](../../reports/261024-0109-brainstorm-lightrag-init-hscc.md). Nền nghiên cứu: [reports/KG y khoa SLM sách tiếng Việt.md](../../reports/KG%20y%20khoa%20SLM%20s%C3%A1ch%20ti%E1%BA%BFng%20Vi%E1%BB%87t.md).

## Ràng buộc

* git + `pixi.toml` + `pixi.lock` (Python 3.12, PyPI, Ollama). Mọi script chạy lại không đổi kết quả.
* Không Docker, không journal, không docs, không tests (CLAUDE.md). Không chạy commit, chỉ đưa lệnh.
* Local only. Model: `qwen3:4b-instruct-2507-q4_K_M` + `bge-m3` qua Ollama.
* Scope tự học: bỏ bộ vàng, NLI, ICD10, QLoRA, custom extractor.

## Phases

| Phase | Name | Status | Effort | Máy |
|-------|------|--------|--------|-----|
| 0 | [Repo skeleton + pixi lock](./phase-00-repo-skeleton.md) | Done | 1h | VM |
| 1 | [Laptop setup: Ollama + models + venv](./phase-01-laptop-setup.md) | Pending | 1h | laptop |
| 2 | [Parse PDF → markdown từng bài](./phase-02-parse-pdf.md) | Done (md đã sinh ở VM) | 2h | VM viết, laptop chạy |
| 3 | [Schema entity type HSCC (YAML)](./phase-03-schema-hscc.md) | Done | 1h | VM |
| 4 | [Index script + prune + pilot 3 bài](./phase-04-index-pilot.md) | Code done, chờ chạy laptop | 3h | laptop |
| 5 | [Index full + WebUI + query sanity](./phase-05-full-index-webui.md) | Pending | 2h + 1.5h GPU | laptop |
| 6 | [Onboard sách HMU](./phase-06-onboard-hmu-book.md) | Pending | tuỳ file | laptop |

## Dependencies

* Laptop: Linux, NVIDIA driver chạy được `nvidia-smi`, 6GB VRAM, sudo để cài Ollama + systemd override.
* Pixi ≥ 0.81 (tự tải Python 3.12, Ollama). LightRAG `lightrag-hku[api]==1.5.7`, `pymupdf==1.28.2`.
* Kwarg LightRAG đã đối chiếu với wheel 1.5.7 (VM, 24/10).

## Thứ tự chạy

VM: phase 0, 2, 3, code phase 4 (xong 24/10) → commit → laptop `git pull` → phase 1, 4, 5 → commit stats → phase 6 khi có sách.

## Lệch so với plan gốc (24/10)

* uv + Makefile + `setup_laptop.sh` → pixi (1 file khoá version + task). Ollama qua conda-forge, chạy bằng `pixi run ollama-serve` trong tmux, không systemd.
* `kg_extraction_validator` chưa có trên PyPI (1.5.7) → `prune()` sau index bằng `adelete_by_entity`. Lên 1.5.8 thì đổi sang hook.
* `pymupdf4llm` → `pymupdf` `get_text()`; map font Symbol sang ↑ ↓ ≥ ≤ μ β Δ →. Bỏ thêm CÂU HỎI LƯỢNG GIÁ (nằm sau TLTK).
* Thêm loại quan hệ `phan_biet_voi` (mỗi bài HSTC có mục chẩn đoán phân biệt).
* Ví dụ JSON trong YAML là khuôn placeholder, không phải ca ARDS thật (1.5.7 coi mục này là template; SLM dễ chép thực thể ví dụ).
* HSTC có 34 bài (không phải 33): bài 30 mở bằng `1. KHÁI NIỆM CƠ BẢN`.
* Ollama client PyPI khai tường minh (1.5.7 không khai, pipmaster sẽ tự cài lúc chạy).
