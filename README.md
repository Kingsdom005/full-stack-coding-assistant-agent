# Full-Stack Coding Assistant Agent

企业级全栈代码助手智能体 - 多智能体协作架构

## 🐍 Python 版本要求

- **最低版本**: Python 3.11
- **推荐版本**: Python 3.13+ (性能最优)
- **已测试版本**: 3.11, 3.12, 3.13

### 检查 Python 版本

```bash
python --version
# 或
python3 --version
```

### 创建虚拟环境 (Python 3.13+)

```bash
# 使用 venv (推荐)
python -m venv venv
source venv/bin/activate

# 或使用 conda
conda create -n coding-agent python=3.13
conda activate coding-agent
```

---

## 架构概述

本项目实现了一个基于多智能体架构的企业级全栈代码助手，包含以下核心组件：

- **Coordinator** - 轻量级协调器，负责任务拆解和调度
- **Frontend Agent** - 前端专家智能体
- **Backend Agent** - 后端专家智能体
- **Test Agent** - 测试专家智能体
- **Audit Agent** - 代码审计智能体

## 技术栈

- **LiteLLM** - 统一大模型接口，支持多模型切换和 Fallback
- **SQLite** - 零部署嵌入式数据库 (Python 3.13+ 内置支持)
- **CodeBuddy CLI** - 代码执行和沙箱环境

## 项目结构

```
multi_agent_coding_assistant/
├── coordinator/          # 协调器和调度器
│   ├── coordinator.py   # 主协调器
│   └── dag.py          # DAG 任务调度器
├── agents/              # 智能体模块
│   ├── base_agent.py    # Agent 基类
│   ├── frontend_agent.py
│   ├── backend_agent.py
│   ├── test_agent.py
│   └── audit_agent.py
├── model/               # 模型路由
│   ├── model_router.py  # LiteLLM 封装
│   └── config.py        # 模型配置
├── storage/             # 数据存储
│   ├── context_db.py    # SQLite 操作封装
│   └── schema.sql       # 数据库表结构
├── executor/            # 代码执行器
│   └── cb_integration.py # CodeBuddy CLI 集成
├── config.yaml          # 应用配置
├── main.py             # 入口文件
├── run.sh              # 运行脚本
├── requirements.txt    # 依赖清单 (Python 3.13+)
├── pyproject.toml     # 项目元数据
├── .python-version     # Python 版本指定
├── .env.example        # 环境变量模板
└── .gitignore         # Git 忽略规则
```

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone git@github.com:Kingsdom005/full-stack-coding-assistant-agent.git
cd full-stack-coding-assistant-agent
git checkout develop  # 切换到开发分支
```

### 2. 创建虚拟环境 (Python 3.13+)

```bash
# 方法 1: 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 方法 2: 使用 conda
conda create -n coding-agent python=3.13
conda activate coding-agent
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
# 或
pip install -e ".[dev]"  # 包含开发依赖
```

### 4. 配置环境变量

```bash
cp .env.example .env
vim .env  # 编辑 .env，填写 TENCENT_API_KEY
```

**.env 文件最少配置：**

```bash
TENCENT_API_KEY=sk-your_actual_key_here
TENCENT_API_BASE=https://api.hunyuan.cloud.tencent.com/hyllm/v1
```

### 5. 运行项目

```bash
# 方法 1: 直接运行
python main.py "开发一个用户登录功能" "包含前后端实现"

# 方法 2: 使用运行脚本
chmod +x run.sh
./run.sh "开发一个用户登录功能" "包含前后端实现"
```

---

## 🔧 配置说明

### 模型配置 (`model/config.py`)

```python
MODEL_CONFIG = {
    "default": "hunyuan-lite",
    "agents": {
        "frontend": "hunyuan-lite",      # 前端 Agent 使用轻量模型
        "backend":  "hunyuan-standard",   # 后端 Agent 使用标准模型
        "test":     "hunyuan-lite",       # 测试 Agent 使用轻量模型
        "audit":    "hunyuan-pro",        # 审计 Agent 使用专业模型
    },
    "tencent": {
        "api_base": "https://api.hunyuan.cloud.tencent.com/hyllm/v1",
        "api_key": os.getenv("TENCENT_API_KEY"),
    },
    "fallback_chain": ["hunyuan-lite", "hunyuan-standard"],
}
```

### 获取 API Key

1. 访问 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 进入 "混元大模型" 产品页
3. 创建应用并获取 API Key

---

## 📊 运行示例

```bash
# 示例 1: 开发登录功能
python main.py "开发一个用户登录功能" "包含前后端实现，支持 JWT 认证"

# 示例 2: 开发 RESTful API
python main.py "开发一个博客 API" "支持 CRUD 操作，使用 FastAPI"

# 示例 3: 修复 Bug
python main.py "修复用户注册 Bug" "邮箱验证不生效"
```

**输出示例：**

```
============================================================
全栈代码助手智能体 (Full-Stack Coding Assistant Agent)
============================================================

[1/3] 初始化协调器...
[2/3] 提交任务: 开发一个用户登录功能
  主任务 ID: task_a1b2c3d4

[3/3] 开始执行任务...
------------------------------------------------------------
[backend] 执行中...
[frontend] 执行中...
[test] 执行中...
[audit] 执行中...
------------------------------------------------------------

执行结果:
============================================================

[task_a1b2c3d4_backend]:
  状态: completed

[task_a1b2c3d4_frontend]:
  状态: completed

[task_a1b2c3d4_test]:
  状态: completed

[task_a1b2c3d4_audit]:
  状态: completed

任务状态汇总:
============================================================
  backend: completed
  frontend: completed
  test: completed
  audit: completed

完成！
```

---

## 🏗️ 架构设计

### 分层混合架构

```
┌─────────────────────────────────────────┐
│           User / API Layer              │
└──────────────────┬──────────────────────┘
                   │
┌─────────────────────────────────────────┐
│         Coordinator (Lite)              │
│   - 任务拆解  - DAG 调度  - 上下文管理  │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
┌───────▼───┐ ┌───▼──────┐ ┌▼──────────┐
│ Frontend  │ │ Backend  │ │   Test    │
│  Agent    │ │  Agent   │ │   Agent   │
└───────────┘ └──────────┘ └───────────┘
                                    │
┌───────────────────────────────────▼─────┐
│            Audit Agent                   │
│     (异步审计，不阻塞主流程)              │
└─────────────────────────────────────────┘

        共享上下文 (SQLite)
```

### 模型路由策略

- 默认使用腾讯混元免费模型 (`hunyuan-lite`)
- 各 Agent 可配置不同模型
- 支持 Fallback 链式降级

### 数据存储设计

使用 SQLite 零部署方案 (Python 3.13+ 内置支持)，设计四张核心表：

- `tasks` - 任务记录
- `code_changes` - 代码变更记录
- `api_contracts` - 前后端接口契约
- `audit_reports` - 审计意见

---

## 🧪 测试

```bash
# 运行单元测试
pytest tests/

# 运行测试并生成覆盖率报告
pytest --cov=agents --cov=coordinator --cov=model --cov=storage --cov-report=html
```

---

## 📁 分支策略

本项目采用 **Git Flow** 分支策略：

- `main` - 生产分支，稳定版本
- `develop` - 开发集成分支
- `feature/*` - 功能分支
- `bugfix/*` - Bug 修复分支
- `hotfix/*` - 紧急修复分支

### 开发流程

```bash
# 1. 切换到 develop 分支
git checkout develop

# 2. 创建功能分支
git checkout -b feature/new-feature

# 3. 开发并提交
git add -A
git commit -m "feat: 新功能描述"

# 4. 推送到远程
git push origin feature/new-feature

# 5. 创建 Pull Request 合并到 develop
```

---

## 🤝 贡献指南

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 License

MIT License

---

## 📧 联系方式

- 作者: Your Name
- 邮箱: your.email@example.com
- GitHub: [@Kingsdom005](https://github.com/Kingsdom005)
