#!/usr/bin/env bash
# 阶段 0 骨架一键启动：安装依赖并启动监控系统。
set -e
cd "$(dirname "$0")"

echo "[1/3] 安装后端依赖 ..."
pip3 install -q -r backend/requirements.txt

echo "[2/3] 运行异常检测自测 ..."
python3 backend/tests/test_detector.py

echo "[3/3] 启动服务 → 浏览器打开 http://localhost:8000"
python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
