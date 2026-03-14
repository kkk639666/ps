# 🍅 番茄病虫害智能识别系统

基于深度学习的番茄叶片病虫害检测与识别平台，支持 Web 端单张识别、批量处理与历史追溯。

## 功能特性

- 🔍 **单张识别**：上传图片，即时显示原图、标注图、结论（虫害/病害/健康）与置信度
- 📦 **批量识别**：多文件异步处理，进度实时展示，支持导出 CSV/JSON
- 📋 **历史记录**：SQLite 持久化，分页浏览，支持查看历史标注图与检测框
- ⚙️ **参数设置**：动态调整检测阈值，无需重启服务
- 🌐 **Web 界面**：基于 Vue 3 + Element Plus 的响应式 SPA

## 识别流程

```
上传图片 → 虫害检测(YOLOv8) → [有虫] → 返回虫害结果+标注图
                              → [无虫] → 病害分类(ResNet) → 病害/健康
```

## 项目结构

```
ps/
├── web/
│   ├── backend/              # FastAPI 后端
│   │   ├── main.py           # 主应用、所有 API 端点
│   │   ├── inference.py      # 级联推理逻辑
│   │   ├── database.py       # SQLite ORM (SQLAlchemy)
│   │   ├── config.py         # 环境变量配置
│   │   ├── schemas.py        # Pydantic 请求/响应模型
│   │   ├── tasks.py          # 后台批量任务队列
│   │   ├── requirements.txt  # Python 依赖
│   │   ├── .env.example      # 配置模板
│   │   └── tests/
│   │       └── test_api.py   # pytest 测试
│   └── frontend/             # Vue 3 前端
│       ├── src/
│       │   ├── views/        # 页面组件
│       │   ├── api/          # Axios API 客户端
│       │   └── router/       # Vue Router
│       ├── package.json
│       └── vite.config.js
├── models/                   # 模型文件目录（需自行准备）
│   ├── pest_detect.pt        # YOLOv8 虫害检测模型
│   ├── disease_cls.pth       # ResNet 病害分类模型
│   └── disease_classes.json  # 病害类别名称（含示例）
├── scripts/
│   ├── dev.bat               # Windows CMD 一键启动（前后端）
│   └── dev.ps1               # Windows PowerShell 一键启动（调用 start.ps1）
├── Makefile                  # Linux/macOS 快速命令
├── start.ps1                 # Windows PowerShell 一键启动
└── README.md
```

## 快速开始

### 前置条件

- Python 3.10+
- Node.js 18+ / npm 9+
- （可选）CUDA 11.8+ 加速推理

### 第一步：准备模型文件

将训练好的模型放入项目根目录下的 `models/` 文件夹（目录已存在，无需创建）：

```
models/
├── pest_detect.pt          # YOLOv8 虫害检测模型（来自 runs/pest_detect/.../weights/best.pt）
├── disease_cls.pth         # ResNet 病害分类模型
└── disease_classes.json    # 分类标签（已提供示例，可直接使用或按需修改）
```

> ⚠️ 若模型文件不存在，系统仍可运行，识别时将返回「模型未加载」提示。
>
> `models/disease_classes.json` 已预置了10个番茄病害类别名称作为示例，若您使用不同的分类模型，请按相同格式（JSON 字符串数组）修改该文件。

### 第二步：安装 ML 依赖（如有模型）

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install ultralytics
```

### Windows 一键启动

```powershell
# 在项目根目录运行
.\start.ps1
```

脚本会自动：
1. 安装后端 Python 依赖
2. 在新窗口启动 FastAPI（端口 8000）
3. 安装前端 npm 依赖（首次）
4. 在新窗口启动 Vite（端口 5173）

访问 **http://localhost:5173** 使用 Web 界面。

若使用 CMD（命令提示符），也可运行：

```cmd
scripts\dev.bat
```

### Linux / macOS

```bash
# 安装依赖
make install

# 分别在两个终端运行：
make dev-backend     # 后端 → http://localhost:8000
make dev-frontend    # 前端 → http://localhost:5173
```

### 手动启动

**后端：**
```bash
cd web/backend
cp .env.example .env    # 按需修改配置
pip install -r requirements.txt
python main.py
# 或使用 uvicorn：uvicorn main:app --reload --port 8000
```

**前端：**
```bash
cd web/frontend
npm install
npm run dev
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET`  | `/api/health` | 健康检查 |
| `POST` | `/api/infer` | 单张推理 |
| `POST` | `/api/infer/batch` | 批量推理（返回 task_id） |
| `GET`  | `/api/tasks/{task_id}` | 查询批量任务状态 |
| `GET`  | `/api/history` | 历史记录（分页） |
| `GET`  | `/api/history/{id}` | 历史记录详情 |
| `GET`  | `/api/models` | 模型信息与当前阈值 |
| `POST` | `/api/settings` | 更新推理阈值 |

完整交互式文档：**http://localhost:8000/docs**

### API 使用示例（curl）

**单张识别：**
```bash
curl -X POST http://localhost:8000/api/infer \
  -F "file=@/path/to/leaf.jpg" \
  | python -m json.tool
```

**查询历史：**
```bash
curl "http://localhost:8000/api/history?page=1&page_size=10" | python -m json.tool
```

**更新阈值：**
```bash
curl -X POST http://localhost:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"pest_conf_threshold": 0.6, "disease_conf_threshold": 0.5}'
```

**批量识别：**
```bash
# 提交任务
TASK=$(curl -s -X POST http://localhost:8000/api/infer/batch \
  -F "files=@img1.jpg" -F "files=@img2.jpg" | python -c "import sys,json; print(json.load(sys.stdin)['task_id'])")

# 轮询结果
curl "http://localhost:8000/api/tasks/$TASK" | python -m json.tool
```

## 配置说明（.env）

```env
PORT=8000
MODELS_DIR=../../models          # 模型目录
STORAGE_DIR=./storage            # 上传图片与结果存储目录
PEST_CONF_THRESHOLD=0.5          # 虫害检测置信度阈值
DISEASE_CONF_THRESHOLD=0.5       # 病害分类置信度阈值
HEALTHY_THRESHOLD=0.8            # 健康判定阈值
MAX_BATCH_SIZE=50                # 单次批量最大图片数
MAX_WORKERS=2                    # 批量任务并发数
DATABASE_URL=sqlite:///./history.db
```

## 运行测试

```bash
# 后端单元/集成测试（不需要模型文件）
cd web/backend
pip install pytest httpx Pillow
pytest tests/test_api.py -v

# 或使用 Makefile
make test
```

## 响应格式示例

**`POST /api/infer` 响应：**
```json
{
  "result_type": "pest",
  "label": "pest",
  "label_zh": "检测到害虫",
  "confidence": 0.87,
  "elapsed_ms": 134.5,
  "boxes": [
    {"x1": 120, "y1": 80, "x2": 340, "y2": 260, "confidence": 0.87, "label": "pest"}
  ],
  "annotated_image_url": "/storage/outputs/annotated_abc123.jpg",
  "input_image_url": "/storage/uploads/upload_xyz.jpg",
  "message": "检测到 1 个害虫目标"
}
```

## 注意事项

- 上传的图片保存在 `web/backend/storage/uploads/`，标注结果图保存在 `storage/outputs/`
- 历史数据库文件：`web/backend/history.db`
- 批量任务状态保存在进程内存，重启服务后 task_id 失效
- Windows 上请确保使用 Python 3.10+ 并在 Anaconda/Miniconda 环境中运行