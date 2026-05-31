with open("/home/liyanqi/cbworkspace/README.md", "r", encoding="utf-8") as f:
    lines = f.readlines()
with open("/tmp/readme_headers.txt", "w", encoding="utf-8") as out:
    for i, line in enumerate(lines):
        if line.startswith("## "):
            out.write(f"{i+1}: {line.strip()}\n")
print("Done, see /tmp/readme_headers.txt")
