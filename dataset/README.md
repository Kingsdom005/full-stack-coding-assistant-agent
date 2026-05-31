# 测试数据集 (Test Dataset)

全栈代码助手智能体的系统测试用例集，覆盖不同的输入场景。

## 目录结构

```
dataset/
├── README.md                          # 本文件
├── plain_text/                        # 纯文本描述用例
│   ├── small_task.txt                 # 少量文本（~30字）
│   └── large_task.txt                 # 大段文本（~1000字）
├── spec_docs/                         # 仅项目说明书用例
│   ├── spec_simple.txt                # 简单 TXT 说明书
│   ├── spec_simple.pdf                # 简单 PDF 说明书
│   ├── spec_detailed.md               # 详细 MD 说明书
│   ├── spec_detailed.pdf              # 详细 PDF 说明书
│   └── generate_pdf.py                # PDF 生成脚本
├── combined/                          # 说明书 + 文本描述组合
│   ├── spec_ecommerce.md              # 电商项目说明书
│   └── text_companion.txt             # 附加文本描述
└── edge_cases/                        # 边界/特殊场景
    ├── chinese_spec.md                # 全中文项目说明书
    └── minimal_desc.txt               # 极简描述（4字）
```

---

## 一、生成 PDF 说明书

部分测试用例需要 PDF 文件，先运行生成脚本：

```bash
cd dataset/spec_docs
pip install fpdf2
python generate_pdf.py
```

生成后确认文件：
```bash
ls -la spec_simple.pdf spec_detailed.pdf
```

---

## 二、测试用例与测试指令

### 场景 1：少量纯文本描述

**用例文件**: `dataset/plain_text/small_task.txt`

仅一句话描述简单功能，验证系统对短文本的处理能力。

#### 测试指令

```bash
# 方式 A: 命令行直接传入
python main.py "开发一个用户登录功能，包含用户名和密码输入框，登录按钮，以及登录成功后的欢迎页面。"

# 方式 B: 从文件读取（借助 bash）
python main.py "$(cat dataset/plain_text/small_task.txt)"

# 方式 C: 交互模式直接输入
python main.py
# 在 "项目描述>" 提示后粘贴文件内容
```

**预期行为**: 系统应正确解析短描述，生成完整的前后端、测试、审计代码。

---

### 场景 2：大段纯文本描述

**用例文件**: `dataset/plain_text/large_task.txt`

长文本多段落描述，包含 Markdown 标题、列表，验证系统对复杂结构文本的解析。

#### 测试指令

```bash
# 方式 A: 从文件读取直接传入
python main.py "$(cat dataset/plain_text/large_task.txt)"

# 方式 B: 使用 ./run.sh 脚本
bash run.sh "$(cat dataset/plain_text/large_task.txt)"

# 方式 C: 交互模式
python main.py
# 粘贴 dataset/plain_text/large_task.txt 的全部内容
```

**预期行为**: 系统应理解多层级、结构化的需求，正确规划 Agent 任务，输出完整的项目代码。

---

### 场景 3：仅 TXT 格式项目说明书

**用例文件**: `dataset/spec_docs/spec_simple.txt`

标准的项目需求说明书（TXT 格式），包含分隔线、编号、层级结构。

#### 测试指令

```bash
# 交互模式: 使用 file: 语法加载
python main.py
# 在提示符输入: file:dataset/spec_docs/spec_simple.txt

# 或者交互模式内使用 load 命令（先进入再 load）
python main.py
# >>> load dataset/spec_docs/spec_simple.txt
# >>> (然后输入你的具体需求，如：请根据以上文档生成代码)
```

**预期行为**: 系统能正确读取 TXT 文件内容作为项目上下文，结合用户输入的指令生成代码。

---

### 场景 4：仅 Markdown 格式项目说明书

**用例文件**: `dataset/spec_docs/spec_detailed.md`

详细的 Markdown 格式需求说明书，包含表格、代码块、目录结构。

#### 测试指令

```bash
# 交互模式: 使用 file: 语法加载 MD 文件
python main.py
# 输入: file:dataset/spec_docs/spec_detailed.md

# 或交互模式 load
python main.py
# >>> load dataset/spec_docs/spec_detailed.md
# >>> 开始开发在线考试系统，严格按文档要求
```

**预期行为**: 系统应能解析 Markdown 表格、代码块等复杂格式，准确理解需求。

---

### 场景 5：PDF 格式项目说明书（简单版）

**用例文件**: `dataset/spec_docs/spec_simple.pdf`（需先运行 `generate_pdf.py` 生成）

#### 测试指令

```bash
# 命令行 --pdf 参数
python main.py --pdf dataset/spec_docs/spec_simple.pdf

# 交互模式 file: 语法
python main.py
# 输入: file:dataset/spec_docs/spec_simple.pdf
```

**预期行为**: PDF 文本正确提取，系统基于提取的文本完成项目生成。

---

### 场景 6：PDF 格式项目说明书（详细版）

**用例文件**: `dataset/spec_docs/spec_detailed.pdf`（需先运行 `generate_pdf.py` 生成）

#### 测试指令

```bash
# 命令行 --pdf 参数
python main.py --pdf dataset/spec_docs/spec_detailed.pdf

# 交互模式 file: 语法
python main.py
# 输入: file:dataset/spec_docs/spec_detailed.pdf
```

**预期行为**: 较长的 PDF 内容也能正确提取并作为项目上下文。

---

### 场景 7：项目说明书 + 文本描述组合 (命令行模式)

**用例文件**: 
- `dataset/combined/spec_ecommerce.md` 
- `dataset/combined/text_companion.txt`

验证 `--pdf`（也支持 MD/TXT）+ 文本描述的合并能力。

#### 测试指令

```bash
# 方式 A: 命令行 --pdf + 文本描述
python main.py --pdf dataset/combined/spec_ecommerce.md "请基于以上文档，额外增加优惠券系统、秒杀活动和积分系统"

# 方式 B: 从 companion 文件读取文本描述
python main.py --pdf dataset/combined/spec_ecommerce.md "$(cat dataset/combined/text_companion.txt)"
```

**预期行为**: 文档内容和文本描述被正确合并为完整需求，两部分的指令都被执行。

---

### 场景 8：项目说明书 + 文本描述组合 (交互模式)

#### 测试指令

```bash
# 先 load 说明书，再输入附加需求
python main.py
# >>> load dataset/combined/spec_ecommerce.md
# 文档已加载...
# >>> 请基于以上文档实现代码，并额外增加优惠券系统、秒杀活动和积分系统
```

**预期行为**: 与场景 7 相同，交互模式下的 load + 输入 效果等价于命令行 `--pdf` + 描述。

---

### 场景 9：全中文项目说明书

**用例文件**: `dataset/edge_cases/chinese_spec.md`

全中文需求文档，验证系统对中文内容的处理能力。

#### 测试指令

```bash
python main.py
# 输入: file:dataset/edge_cases/chinese_spec.md

# 或命令行
python main.py --pdf dataset/edge_cases/chinese_spec.md
```

**预期行为**: 系统正确读取中文文档，输出的代码注释/命名也以中文语境理解。

---

### 场景 10：极简描述（边界情况）

**用例文件**: `dataset/edge_cases/minimal_desc.txt`

仅 4 个字的极限简洁描述。

#### 测试指令

```bash
python main.py "$(cat dataset/edge_cases/minimal_desc.txt)"
```

**预期行为**: 系统应能理解"计算器"的意图并生成合理的代码，不应因描述过短而崩溃。

---

## 三、批量测试脚本

可以将以下内容保存为 `dataset/run_all_tests.sh` 来快速执行所有测试（注意：每个测试都会调用 LLM，请确保 API Key 额度充足）：

```bash
#!/bin/bash
# 批量测试脚本（仅执行不依赖 PDF 的用例）
echo "=== Test 1: 少量纯文本 ==="
python main.py "$(cat dataset/plain_text/small_task.txt)"

echo "=== Test 2: 大段纯文本 ==="
python main.py "$(cat dataset/plain_text/large_task.txt)"

echo "=== Test 10: 极简描述 ==="
python main.py "$(cat dataset/edge_cases/minimal_desc.txt)"
```

---

## 四、验证 Trace 文件

每次执行后，查看 `output/` 下对应时间戳目录中的 `traces/` 子目录，确认每个 Agent 的输入输出都被正确记录：

```bash
# 找到最新输出目录
ls -t output/ | head -1

# 查看所有 trace 文件
ls -R output/$(ls -t output/ | head -1)/traces/

# 查看某个 trace 内容
cat output/$(ls -t output/ | head -1)/traces/backend/*.md
```
