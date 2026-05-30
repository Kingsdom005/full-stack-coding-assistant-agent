#!/bin/bash
# 全栈代码助手智能体 - 运行脚本

set -e  # 遇到错误立即退出

echo "============================================================"
echo "全栈代码助手智能体 - 启动脚本"
echo "============================================================"
echo ""

# 1. 检查 conda 环境
if [ -z "$CONDA_DEFAULT_ENV" ]; then
    echo "[1/5] 激活 Conda 环境: coding-agent"
    conda activate coding-agent
else
    echo "[1/5] 当前 Conda 环境: $CONDA_DEFAULT_ENV"
    if [ "$CONDA_DEFAULT_ENV" != "coding-agent" ]; then
        echo "  警告: 当前环境不是 coding-agent，正在切换..."
        conda activate coding-agent
    fi
fi

# 2. 检查 Python 版本
echo "[2/5] 检查 Python 版本..."
PYTHON_VERSION=$(python --version 2>&1)
echo "  $PYTHON_VERSION"
if [[ ! "$PYTHON_VERSION" =~ 3\.11 ]]; then
    echo "  警告: 建议使用 Python 3.11"
fi

# 3. 检查依赖
echo "[3/5] 检查依赖..."
if ! python -c "import litellm" 2>/dev/null; then
    echo "  依赖未安装，正在安装..."
    pip install -r requirements.txt
else
    echo "  依赖已安装"
fi

# 5. 检查 .env 文件
echo "[4/5] 检查环境配置..."
if [ ! -f ".env" ]; then
    echo "  .env 文件不存在，正在从模板创建..."
    cp .env.example .env
    echo "  请编辑 .env 文件，填写 TENCENT_API_KEY"
    echo "  然后重新运行此脚本"
    exit 1
fi

# 6. 检查 API Key 是否配置
if grep -q "YOUR_TENCENT_API_KEY" .env; then
    echo "  错误: 请先在 .env 文件中填写 TENCENT_API_KEY"
    echo "  编辑命令: vim .env"
    exit 1
fi

echo "[5/5] 启动项目..."
echo "============================================================"
echo ""

# 运行项目
if [ $# -eq 0 ]; then
    echo "用法: ./run.sh '任务描述' ['详细需求']"
    echo ""
    echo "示例:"
    echo "  ./run.sh '开发一个用户登录功能' '包含前后端实现'"
    exit 1
fi

python main.py "$@"
