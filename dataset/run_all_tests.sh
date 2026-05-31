#!/bin/bash
# 批量测试脚本 - 用于快速验证多场景
# 注意: 每个测试都会调用 LLM，确保 API Key 额度充足
# 用法: bash dataset/run_all_tests.sh

set -e

echo "========================================="
echo "全栈代码助手 - 测试集批量运行"
echo "========================================="
echo ""

# 先检查 PDF 是否已生成
if [ ! -f "dataset/spec_docs/spec_simple.pdf" ]; then
    echo "[预检] PDF 文件未生成，正在生成..."
    cd dataset/spec_docs
    pip install fpdf2 -q
    python generate_pdf.py
    cd ../..
fi

echo ""
echo "=== 测试 1: 少量纯文本 ==="
python main.py "$(cat dataset/plain_text/small_task.txt)"

echo ""
echo "=== 测试 2: 大段纯文本 ==="
python main.py "$(cat dataset/plain_text/large_task.txt)"

echo ""
echo "=== 测试 3: TXT 项目说明书 ==="
python main.py --pdf dataset/spec_docs/spec_simple.txt

echo ""
echo "=== 测试 4: MD 项目说明书 ==="
python main.py --pdf dataset/spec_docs/spec_detailed.md

echo ""
echo "=== 测试 5: PDF 简单说明书 ==="
python main.py --pdf dataset/spec_docs/spec_simple.pdf

echo ""
echo "=== 测试 6: PDF 详细说明书 ==="
python main.py --pdf dataset/spec_docs/spec_detailed.pdf

echo ""
echo "=== 测试 7: 说明书 + 文本描述组合 ==="
python main.py --pdf dataset/combined/spec_ecommerce.md "$(cat dataset/combined/text_companion.txt)"

echo ""
echo "=== 测试 8: 全中文说明书 ==="
python main.py --pdf dataset/edge_cases/chinese_spec.md

echo ""
echo "=== 测试 9: 极简描述 ==="
python main.py "$(cat dataset/edge_cases/minimal_desc.txt)"

echo ""
echo "========================================="
echo "全部测试完成！"
echo "请检查 output/ 目录下的输出和 traces/ 目录。"
echo "========================================="
