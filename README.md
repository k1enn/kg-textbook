- nvidia-smi phải báo CUDA Version 12 trở lên.
- Cần có git, tmux và đã login gh.
- Nếu laptop đang chạy Ollama native thì tắt nó, vì nó chiếm cổng 11434: sudo systemctl disable --now ollama

# Cài đặt
```bash
curl -fsSL https://pixi.sh/install.sh | PIXI_VERSION=v0.81.0 bash
exec $SHELL
gh repo clone k1enn/kg-textbooks && cd kg-textbooks
pixi install --all --locked
```

# Bật Ollama và tải model:
tmux new -d -s ollama 'pixi run ollama-serve 2>&1 | tee -a ollama.log'
pixi run ollama-pull
pixi run -e ollama ollama run --verbose qwen3:4b-instruct-2507-q4_K_M 'Trả lời đúng 1 dòng JSON: {"ok": true}'
nvidia-smi
Đạt khi eval rate ≥ 30 tok/s và VRAM < 5GB.
