"""最终修复 README.md：
1. 删除第 243 行错误插入的"## 🧪 测试"
2. 删除第 388 行多余的"---"（让"技术细节深挖"内容紧跟标题）
3. 在"技术细节深挖"真正结束处（CI/CD 之前）插入"## 🧪 测试"
"""

with open("/home/liyanqi/cbworkspace/README.md", "r", encoding="utf-8") as f:
    lines = f.readlines()

# --- 修复 1：删除第 243 行（索引 242）的"## 🧪 测试" ---
# 同时删除后面多余的空行（243 和 244 行是\n）
idx_bad_test = None
for i, line in enumerate(lines):
    if line.strip() == "## 🧪 测试":
        # 确认位置（应该在配置说明和 Token 用量之间）
        idx_bad_test = i
        break

if idx_bad_test is not None:
    # 删除该行和后面一个空行
    del lines[idx_bad_test : idx_bad_test + 2]
    print(f"Deleted bad '## 🧪 测试' at line {idx_bad_test+1}")
else:
    print("WARNING: Could not find bad '## 🧪 测试'")

# --- 修复 2：删除"技术细节深挖"标题后多余的"---" ---
# 找到"## 🔬 技术细节深挖"，然后删除紧跟它的 ---"
idx_detail = None
for i, line in enumerate(lines):
    if "技术细节深挖" in line and line.startswith("## "):
        idx_detail = i
        break

if idx_detail is not None:
    # 检查后面几行是否有多余的 ---
    for offset in [3, 4, 5]:
        j = idx_detail + offset
        if j < len(lines) and lines[j].strip() == "---":
            del lines[j]
            print(f"Deleted extra '---' at line {j+1}")
            break

# --- 修复 3：在"技术细节深挖"真正结束后插入"## 🧪 测试" ---
# 找"## 🔄 CI/CD"（技术细节深挖之后的下一个 ## 章节）
insert_pos = None
for i, line in enumerate(lines):
    if line.startswith("## ") and "CI/CD" in line:
        insert_pos = i
        break

if insert_pos is not None:
    # 在 CI/CD 之前插入："---" + 空行 + "## 🧪 测试" + 空行
    lines = (
        lines[:insert_pos] + ["---\n", "\n", "## 🧪 测试\n", "\n"] + lines[insert_pos:]
    )
    print(f"Inserted '## 🧪 测试' before line {insert_pos+1}")
else:
    print("WARNING: Could not find '## 🔄 CI/CD' insertion point")

with open("/home/liyanqi/cbworkspace/README.md", "w", encoding="utf-8") as f:
    f.writelines(lines)

print("Done!")
