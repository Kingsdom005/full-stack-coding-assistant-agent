# Full-Stack Coding Assistant Agent

企业级全栈代码助手智能体 - 多智能体协作架构

## 架构概述

本项目实现了一个基于多智能体架构的企业级全栈代码助手，包含以下核心组件：

- **Coordinator** - 轻量级协调器，负责任务拆解和调度
- **Frontend Agent** - 前端专家智能体
- **Backend Agent** - 后端专家智能体
- **Test Agent** - 测试专家智能体
- **Audit Agent** - 代码审计智能体

## 技术栈

- **LiteLLM** - 统一大模型接口，支持多模型切换和 Fallback
- **SQLite** - 零部署嵌入式数据库
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
└── requirements.txt    # 依赖清单
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置模型

编辑 `model/config.py`，设置腾讯混元 API Key：

```python
"tencent": {
    "api_base": "https://api.hunyuan.cloud.tencent.com/hyllm/v1",
    "api_key": "YOUR_TENCENT_API_KEY",
}
```

### 运行

```bash
python main.py
```

## 架构设计

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

使用 SQLite 零部署方案，设计四张核心表：

- `tasks` - 任务记录
- `code_changes` - 代码变更记录
- `api_contracts` - 前后端接口契约
- `audit_reports` - 审计意见

## License

MIT
