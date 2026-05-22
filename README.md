# ASR Test Platform

基于 `docs/project_preview.txt` 生成的项目骨架，包含：

- `backend/`：FastAPI 后端骨架，预留模型管理、音频处理、推理服务和引擎适配层。
- `frontend/`：Vue3 + Vite 前端骨架，包含调试页和模型管理页。
- `docker-compose.yml`：用于同时拉起前后端开发环境的基础编排。

## 目录

```text
backend/
frontend/
docker-compose.yml
README.md
```

## 后端启动

```bash
cd .
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
uvicorn backend.src.main:app --reload --host 0.0.0.0 --port 8000
```

## 前端启动

```bash
cd frontend
npm install
npm run dev
```

## 当前状态

- 后端接口已经可启动，但 ASR 引擎仍是占位实现。
- 前端页面已经接好基础路由和接口调用。
- 真正的音频上传、预处理、模型推理和性能指标采集还需要继续补充。
