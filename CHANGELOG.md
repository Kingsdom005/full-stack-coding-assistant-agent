# Changelog

本文档记录项目的所有 notable changes，格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 初始化项目结构

## [0.1.0] - 2026-05-31

### Added
- **核心架构**：实现基于多智能体协作的企业级全栈代码助手
- **Coordinator**：轻量级协调器，负责任务拆解和 DAG 调度
- **Agents**：
  - Frontend Agent：前端专家智能体（React/Vue/Angular）
  - Backend Agent：后端专家智能体（Python/Java/Node.js）
  - Test Agent：测试专家智能体（Jest + RTL / pytest）
  - Audit Agent：代码审计智能体（OWASP Top 10）
- **Model Router**：LiteLLM 统一接口，支持多模型切换和 Fallback
- **Context DB**：SQLite 零部署嵌入式数据库，存储任务、代码变更、API 契约、审计意见
- **Executor**：CodeBuddy CLI 集成，支持代码执行、测试运行、代码审查
- **规约驱动开发**：支持从 PDF/TXT/MD 文档加载需求
- **交互模式**：支持交互式开发，动态加载文档，迭代开发
- **输出管理**：自动生成项目输出目录，保存 Agent 执行 Trace
- **配置验证**：自动验证 .env 配置和 API Key
- **CI/CD**：GitHub Actions CI 流水线（lint + typecheck + test + build）
- **版本管理**：统一 VERSION 文件管理版本号，提供命令行工具

### Changed
- N/A（初始版本）

### Deprecated
- N/A（初始版本）

### Removed
- N/A（初始版本）

### Fixed
- N/A（初始版本）

### Security
- N/A（初始版本）

## 版本说明

- **[Unreleased]**：记录正在开发的功能
- **版本格式**：[主版本].[次版本].[修订号]（如 0.1.0）
- **分类**：
  - **Added**：新功能
  - **Changed**：现有功能的变更
  - **Deprecated**：即将移除的功能
  - **Removed**：已移除的功能
  - **Fixed**：Bug 修复
  - **Security**：安全问题修复

## 发布说明

### 发布流程

1. 更新 `CHANGELOG.md`，将 `[Unreleased]` 内容移动到新版本条目
2. 更新 `VERSION` 文件（使用 `python utils/version.py --bump patch`）
3. 创建 git tag（`git tag v0.1.0`）
4. 推送 tag（`git push origin v0.1.0`）
5. GitHub Actions CD 工作流自动触发，发布到 PyPI

### 预发布版本

对于预发布版本（如 `0.1.0-alpha.1`），在版本号后添加预发布标签：

```bash
python utils/version.py --bump patch --prerelease alpha.1
```

---

[0.1.0]: https://github.com/Kingsdom005/full-stack-coding-assistant-agent/releases/tag/v0.1.0
