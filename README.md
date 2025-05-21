# MinerU PDF 批量解析 Web 应用

本项目基于 [magic-pdf](https://github.com/opendatalab/MinerU) + FastAPI（后端）与 Vue3 + Element Plus（前端），实现了 PDF 文件的批量上传、异步批量解析（转 Markdown）、实时进度展示，以及批量下载解析结果。支持在 Ubuntu 22.04 环境下部署，并可通过局域网访问。

---

## 功能简介
- **批量上传 PDF 文件，支持拖拽与多选**
- **异步批量解析 PDF 为 Markdown，解析过程实时进度展示**
- **批量下载解析后的 Markdown 文件（zip 包）**
- **自动生成 Swagger API 文档页面，方便接口测试与后续开发**
- **前端界面美观友好，交互流畅，解析状态/进度一目了然**

---

## 环境准备

### 1. 后端环境（Python，推荐 Miniconda）

#### 1.1 创建并激活 Python 环境
```bash
conda create -n mineru_env python=3.12
conda activate mineru_env
```
或使用 venv：
```bash
python3 -m venv mineru_env
source mineru_env/bin/activate
```

#### 1.2 安装后端依赖
```bash
pip install -r requirements.txt
```
如未安装 magic-pdf，可单独安装：
```bash
pip install -U magic-pdf[full]
```

### 2. 前端环境（Node.js 16+，推荐使用 npm）

```bash
cd mineru_web/frontend
npm install
```

---

## 启动项目

### 1. 启动后端（FastAPI）
在 mineru_web 目录下运行：
```bash
uvicorn main:app --host 0.0.0.0 --port 8600 --reload
```
- `--host 0.0.0.0` 表示监听所有网卡，确保局域网其他设备可访问
- `--port 8600` 可根据需要修改端口

### 2. 启动前端（Vite + Vue3）
在 mineru_web/frontend 目录下运行：
```bash
npm run dev
```
默认端口 5173，浏览器访问 http://0.0.0.0:5173 或 http://<你的局域网IP>:5173

---

## 局域网访问说明
1. 启动后端服务后，使用 `ifconfig` 或 `ip addr` 查看本机局域网 IP，例如 `192.168.1.100`
2. 前端页面：在同一局域网其他设备浏览器访问 `http://0.0.0.0:5173` 或 `http://<你的局域网IP>:5173`
3. Swagger API 文档：访问 `http://0.0.0.0:8600/docs` 或 `http://<你的局域网IP>:8600/docs`
   - `http://0.0.0.0:8600` 或 `http://<你的局域网IP>:8600` （可用于自定义前端页面）

---

## 前后端主要功能与接口说明

### 前端主要功能
- 拖拽/多选批量上传 PDF
- 上传后自动发起解析任务，实时显示每个文件的解析进度与状态
- 全部解析成功后可一键批量下载 Markdown 结果（zip 包）

---

## 依赖说明

### 后端依赖（requirements.txt）
- fastapi
- uvicorn
- python-multipart
- magic-pdf

### 前端依赖（package.json）
- vue@3.x
- element-plus@2.x
- axios@1.x
- vite@4.x

---

## 端口与路径说明
- 后端接口默认监听 8600 端口（http://localhost:8600）
- 前端开发服务器默认监听 5173 端口（http://localhost:5173）
- 前端自动适配后端端口，无需手动修改
- 上传文件存储于 `uploads` 目录，解析结果存储于 `parsed_files` 目录

---

## 常见问题（FAQ）

### 1. magic-pdf 报 ImportError 或 pipeline 不可用？
请确保已安装 magic-pdf 的最新版，并使用如下导入方式：
```python
from magic_pdf.pipeline import pipeline
```
如仍有问题，可尝试 `pip install -U magic-pdf[full]`。

### 2. 解析进度不刷新/前端无法访问后端？
- 请确保后端已启动且监听 0.0.0.0:8600
- 前端与后端需在同一局域网内
- 检查浏览器控制台、后端日志，定位具体报错

### 3. 上传大文件或批量文件失败？
- 检查后端服务器内存、硬盘空间
- 如需支持更大文件，建议调整 FastAPI/uvicorn 的上传限制

### 4. 解析结果格式需求变更？
- 可在后端 pipeline 调用时修改 `output_type` 参数，如 `output_type="json"`

### 5. 依赖冲突或版本不兼容？
- 建议严格按照 requirements.txt 与 package.json 安装依赖
- 如遇到 Python 版本问题，推荐 Python 3.10~3.12

---

## 联系与反馈
如遇到问题或有新需求，欢迎在 [GitHub Issues](https://github.com/opendatalab/MinerU/issues) 提交反馈。
- 全程交互友好，错误/成功有即时提示

### 后端主要接口
- `POST /upload`：批量上传 PDF 文件
- `POST /parse_async`：异步批量解析，返回 task_id
- `GET /progress?task_id=xxx`：查询解析任务进度与状态
- `GET /download`：批量下载所有解析结果（zip 包）
- `GET /docs`：Swagger API 文档页面

---

## 目录结构
```
mineru_web/
├── main.py              # FastAPI 主程序（后端）
├── requirements.txt     # 后端依赖
├── uploads/             # 上传的 PDF 文件
├── parsed_files/        # 解析后的 Markdown 文件
├── frontend/            # 前端项目（Vue3+Element Plus+Vite）
│   ├── package.json     # 前端依赖与脚本
│   ├── index.html       # 前端入口
│   └── src/
│       ├── main.js      # Vue 启动入口
│       └── App.vue      # 主页面，交互逻辑
└── README.md
```

---

## 常见问题
- **端口被占用**：修改 `--port`（后端）或 `--port`（前端）参数，或释放端口
- **局域网无法访问**：确认防火墙已放行 8600（后端）和 5173（前端）端口，或关闭防火墙
- **magic-pdf 解析失败**：请确保 PDF 文件无损坏，且 magic-pdf 安装完整
- **前后端端口不一致**：如需跨端口部署，注意前端 axios 请求 `backend` 地址需与后端实际地址一致

---

## 联系与支持
如需进一步功能扩展或遇到问题，请在 issue 区留言，或直接联系开发者。
