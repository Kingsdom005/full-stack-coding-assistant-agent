"""
SQLite 上下文数据库操作封装
零部署方案 - 整个数据库是一个文件
"""

import sqlite3
import json
from typing import Optional, List, Dict
from datetime import datetime
from model.config import DATABASE_CONFIG


class ContextDB:
    """SQLite 上下文数据库操作类"""

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化数据库

        Args:
            db_path: 数据库路径，None 则使用配置文件中的默认值
        """
        self.db_path = db_path or DATABASE_CONFIG["path"]
        self._init_db()

    def _init_db(self):
        """初始化数据库，执行 schema.sql"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建 tables（如果不存在）
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                result TEXT,
                error TEXT
            );

            CREATE TABLE IF NOT EXISTS code_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                change_type TEXT NOT NULL,
                diff TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            );

            CREATE TABLE IF NOT EXISTS api_contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                request_schema TEXT,
                response_schema TEXT,
                status TEXT DEFAULT 'draft',
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            );

            CREATE TABLE IF NOT EXISTS audit_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                agent_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                file_path TEXT,
                line_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id)
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
            CREATE INDEX IF NOT EXISTS idx_code_changes_task_id ON code_changes(task_id);
            CREATE INDEX IF NOT EXISTS idx_api_contracts_task_id ON api_contracts(task_id);
            CREATE INDEX IF NOT EXISTS idx_audit_reports_task_id ON audit_reports(task_id);
        """)

        conn.commit()
        conn.close()

    # ==================== Task 操作 ====================

    def create_task(self, task_id: str, description: str) -> int:
        """创建新任务"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (task_id, description) VALUES (?, ?)",
            (task_id, description)
        )
        task_pk = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_pk

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """更新任务状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE tasks
               SET status = ?, result = ?, error = ?, updated_at = CURRENT_TIMESTAMP
               WHERE task_id = ?""",
            (status, result, error, task_id)
        )
        conn.commit()
        conn.close()

    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务详情"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            columns = ["id", "task_id", "description", "status",
                      "created_at", "updated_at", "result", "error"]
            return dict(zip(columns, row))
        return None

    # ==================== Code Changes 操作 ====================

    def log_code_change(
        self,
        task_id: str,
        agent_type: str,
        file_path: str,
        change_type: str,
        diff: Optional[str] = None,
    ):
        """记录代码变更"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO code_changes
               (task_id, agent_type, file_path, change_type, diff)
               VALUES (?, ?, ?, ?, ?)""",
            (task_id, agent_type, file_path, change_type, diff)
        )
        conn.commit()
        conn.close()

    # ==================== API Contracts 操作 ====================

    def save_api_contract(
        self,
        task_id: str,
        endpoint: str,
        method: str,
        request_schema: Optional[Dict] = None,
        response_schema: Optional[Dict] = None,
        created_by: str = "backend",
    ):
        """保存前后端接口契约"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO api_contracts
               (task_id, endpoint, method, request_schema, response_schema, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                endpoint,
                method,
                json.dumps(request_schema) if request_schema else None,
                json.dumps(response_schema) if response_schema else None,
                created_by,
            )
        )
        conn.commit()
        conn.close()

    def get_api_contracts(self, task_id: str) -> List[Dict]:
        """获取任务的接口契约列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM api_contracts WHERE task_id = ?",
            (task_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        columns = ["id", "task_id", "endpoint", "method",
                  "request_schema", "response_schema", "status",
                  "created_by", "created_at"]
        return [dict(zip(columns, row)) for row in rows]

    # ==================== Audit Reports 操作 ====================

    def add_audit_report(
        self,
        task_id: str,
        agent_type: str,
        severity: str,
        message: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
    ):
        """添加审计意见"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO audit_reports
               (task_id, agent_type, severity, message, file_path, line_number)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (task_id, agent_type, severity, message, file_path, line_number)
        )
        conn.commit()
        conn.close()

    def get_audit_reports(self, task_id: str) -> List[Dict]:
        """获取任务的审计报告"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM audit_reports WHERE task_id = ? ORDER BY severity",
            (task_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        columns = ["id", "task_id", "agent_type", "severity",
                  "message", "file_path", "line_number", "created_at"]
        return [dict(zip(columns, row)) for row in rows]
