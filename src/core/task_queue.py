import sqlite3
import json
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path


class TaskQueue:
    """任务队列 - 管理异步任务"""
    
    def __init__(self, db_file: str = "data/tasks.db"):
        self.db_file = db_file
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                vendor_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                prompt TEXT,
                model TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT,
                error TEXT,
                progress REAL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_id ON tasks(task_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_vendor ON tasks(vendor_id)')
        
        conn.commit()
        conn.close()
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    def add_task(
        self,
        task_id: str,
        vendor_id: str,
        task_type: str,
        prompt: str,
        model: str = None,
        **kwargs
    ) -> bool:
        conn = self._get_conn()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        try:
            cursor.execute('''
                INSERT INTO tasks (task_id, vendor_id, task_type, prompt, model, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
            ''', (task_id, vendor_id, task_type, prompt, model, now, now))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def update_task(
        self,
        task_id: str,
        status: str = None,
        result: Dict = None,
        error: str = None,
        progress: float = None
    ) -> bool:
        conn = self._get_conn()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        updates = ["updated_at = ?"]
        params = [now]
        
        if status:
            updates.append("status = ?")
            params.append(status)
            if status in ["completed", "failed"]:
                updates.append("completed_at = ?")
                params.append(now)
        
        if result:
            updates.append("result = ?")
            params.append(json.dumps(result, ensure_ascii=False))
        
        if error:
            updates.append("error = ?")
            params.append(error)
        
        if progress is not None:
            updates.append("progress = ?")
            params.append(progress)
        
        params.append(task_id)
        
        cursor.execute(f'''
            UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?
        ''', params)
        
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_tasks(
        self,
        status: str = None,
        vendor_id: str = None,
        limit: int = 100
    ) -> List[Dict]:
        conn = self._get_conn()
        cursor = conn.cursor()
        
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if vendor_id:
            query += " AND vendor_id = ?"
            params.append(vendor_id)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def delete_task(self, task_id: str) -> bool:
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success
    
    def clear_completed_tasks(self, days: int = 7) -> int:
        conn = self._get_conn()
        cursor = conn.cursor()
        
        from datetime import timedelta
        date_limit = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            DELETE FROM tasks 
            WHERE status IN ('completed', 'failed') 
            AND completed_at < ?
        ''', (date_limit,))
        
        conn.commit()
        deleted = cursor.rowcount
        conn.close()
        return deleted
    
    def get_task_count(self, status: str = None) -> Dict[str, int]:
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = ?', (status,))
            count = cursor.fetchone()[0]
            conn.close()
            return {status: count}
        
        cursor.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status')
        rows = cursor.fetchall()
        conn.close()
        
        return {row[0]: row[1] for row in rows}
