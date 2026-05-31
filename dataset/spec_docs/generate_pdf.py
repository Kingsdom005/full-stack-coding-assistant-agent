"""
生成 PDF 格式的项目说明书测试用例

使用方法:
    cd dataset/spec_docs
    pip install fpdf2
    python generate_pdf.py

输出文件:
    - spec_detailed.pdf  (详细项目说明书)
    - spec_simple.pdf    (简单项目说明书)
"""

import os
import sys

def generate_pdf():
    try:
        from fpdf import FPDF
    except ImportError:
        print("请先安装 fpdf2: pip install fpdf2")
        sys.exit(1)

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # ==== PDF 1: 详细项目说明书 ====
    pdf = FPDF()
    pdf.add_page()
    # 注册中文字体需要额外的字体文件, 这里用英文生成
    # 如需中文 PDF, 请参考 fpdf2 文档添加中文字体

    pdf.set_font("Courier", "B", 16)
    pdf.cell(0, 10, "Online Exam System - Project Spec", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Courier", "", 10)

    sections = [
        ("1. Project Background", 
         "An educational institution requires an online examination system\n"
         "for post-class quizzes, stage exams, and final assessments.\n"
         "The system should support multiple question types, automatic\n"
         "grading, and result analysis."),
        ("2. User Roles",
         "- Student: Take exams, view results\n"
         "- Teacher: Create question bank, compose exams, grade, analytics\n"
         "- Admin: User management, system configuration, statistics"),
        ("3. Core Features",
         "- Question Bank Management: Support single/multiple choice,\n"
         "  true/false, fill-in-blank, essay, coding questions\n"
         "- Exam Management: Manual/auto/random question composition\n"
         "- Anti-cheating: Tab switch detection, countdown, auto-submit\n"
         "- Grading System: Auto grading for objective questions,\n"
         "  manual grading for essays\n"
         "- Result Analytics: Individual/class reports, question analysis"),
        ("4. Technical Stack",
         "- Backend: Python FastAPI + SQLAlchemy + PostgreSQL\n"
         "- Frontend: React + TypeScript + Ant Design\n"
         "- Cache: Redis\n"
         "- Deployment: Docker + Nginx"),
        ("5. Non-functional Requirements",
         "- Concurrent users: 500+\n"
         "- API response time P99 < 500ms\n"
         "- System availability: 99.9%\n"
         "- Test coverage: backend >= 80%, frontend >= 60%\n"
         "- Password encryption: bcrypt\n"
         "- Auth: JWT + Refresh Token"),
    ]

    for title, content in sections:
        pdf.set_font("Courier", "B", 12)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_font("Courier", "", 10)
        for line in content.split("\n"):
            pdf.cell(0, 5, line, ln=True)
        pdf.ln(3)

    pdf.output("spec_detailed.pdf")
    print("已生成: spec_detailed.pdf")

    # ==== PDF 2: 简单项目说明书 ====
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Courier", "B", 14)
    pdf.cell(0, 10, "Personal Blog System - Project Spec v1.0", ln=True, align="C")
    pdf.ln(8)

    simple_sections = [
        ("1. Overview",
         "A lightweight personal blog system with frontend/backend\n"
         "separation. Users can publish articles, manage content,\n"
         "and interact with readers."),
        ("2. Features",
         "- Article Management: Markdown editor, search, categories, drafts\n"
         "- Comments: Nested replies (2 levels), moderation\n"
         "- User System: Registration, login, profile, avatar\n"
         "- Admin Panel: Dashboard, content management, site settings"),
        ("3. Tech Stack",
         "- Frontend: React + Next.js + Tailwind CSS\n"
         "- Backend: Node.js + Express + TypeScript\n"
         "- Database: MySQL\n"
         "- Deployment: Docker + Nginx"),
        ("4. Requirements",
         "- Page load time < 2s\n"
         "- API response < 500ms\n"
         "- XSS/SQL Injection/CSRF protection\n"
         "- Mobile responsive"),
    ]

    for title, content in simple_sections:
        pdf.set_font("Courier", "B", 11)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_font("Courier", "", 10)
        for line in content.split("\n"):
            pdf.cell(0, 5, line, ln=True)
        pdf.ln(3)

    pdf.output("spec_simple.pdf")
    print("已生成: spec_simple.pdf")


if __name__ == "__main__":
    generate_pdf()
