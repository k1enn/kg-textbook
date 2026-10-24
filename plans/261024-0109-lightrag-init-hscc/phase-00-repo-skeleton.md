# Phase 0: Repo skeleton + pixi lock (VM)

## Overview
Priority P1. Git repo, `pixi.toml` + `pixi.lock` (1 công cụ cho Python 3.12, PyPI deps, Ollama, task), `.gitignore`, `.env.example`. Đổi từ uv + Makefile theo yêu cầu "1 chỗ khoá version + cài đặt".

## Đã làm
* `git init -b main`. Pixi v0.81.0 (`requires-pixi >= 0.81`), platform `linux-64` khai `cuda = "12"`.
* Env `default`: conda `python 3.12.*`; PyPI `lightrag-hku[api]==1.5.7`, `ollama` (client, 1.5.7 không khai, nếu thiếu thì pipmaster tự cài lúc chạy), `pymupdf==1.28.2`, `networkx`, `pyyaml`.
* Env `ollama` (tách riêng, không Python): conda `ollama==0.32.15 cuda_129*`. Tách để VM lock không phải cài 850MB và để tên conda `ollama` không đè gói PyPI `ollama`.
* Task: `parse [doc] [profile]`, `pilot [doc]`, `index [doc]`, `serve [kg]`, `clean-kg <kg>`, `ollama-serve`, `ollama-pull`. Xem `pixi task list`.
* `.env.example` chỉ cho `lightrag-server`; working dir đi qua `pixi run serve <kg>`, PROMPT_DIR mặc định `./prompts`.

## Acceptance
* `pixi lock --check` pass (đã chạy ở VM). `pixi run --frozen -n parse byt_hstc_2015 hstc` in đúng lệnh.

## Commit (user chạy)
```
git add -A && git commit -m "chore: init pixi workspace, layout"
```

## Risks
* Không khoá `exclude-newer`: lock lấy bản mới nhất lúc 24/10 (khoảng 40 gói ra trong 2 tuần trước). Lock vẫn ghim đúng version, 2 máy giống nhau.
