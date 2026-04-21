import sqlite3
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import json
import hashlib

from backend.config import settings

logger = logging.getLogger(__name__)


class MetadataDB:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(__file__).parent.parent
            db_path = str(base_dir / "data" / "metadata.db")
        
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                file_id TEXT PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT,
                size INTEGER,
                hash TEXT,
                created_at TEXT,
                modified_at TEXT,
                indexed_at TEXT,
                status TEXT DEFAULT 'pending',
                folder_source TEXT,
                chunk_count INTEGER DEFAULT 0,
                error_message TEXT,
                UNIQUE(path)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                folder_id TEXT PRIMARY KEY,
                path TEXT UNIQUE NOT NULL,
                name TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT,
                last_scan_at TEXT,
                document_count INTEGER DEFAULT 0,
                chunk_count INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_files_folder ON files(folder_source)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_files_status ON files(status)
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)
    
    def _compute_hash(self, file_path: str) -> str:
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error computing hash for {file_path}: {e}")
            return ""
    
    def add_file(
        self,
        path: str,
        filename: str,
        file_type: str,
        size: int,
        folder_source: str,
        hash: Optional[str] = None,
        status: str = "indexed"
    ) -> str:
        if hash is None:
            hash = self._compute_hash(path)
        
        file_id = hashlib.md5(path.encode()).hexdigest()
        now = datetime.now().isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO files 
                (file_id, path, filename, file_type, size, hash, indexed_at, status, folder_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (file_id, path, filename, file_type, size, hash, now, status, folder_source))
            
            conn.commit()
        finally:
            conn.close()
        
        return file_id
    
    def update_file_status(
        self,
        path: str,
        status: str,
        chunk_count: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            if chunk_count is not None:
                cursor.execute('''
                    UPDATE files SET status = ?, chunk_count = ?, error_message = ?
                    WHERE path = ?
                ''', (status, chunk_count, error_message, path))
            else:
                cursor.execute('''
                    UPDATE files SET status = ?, error_message = ?
                    WHERE path = ?
                ''', (status, error_message, path))
            
            conn.commit()
        finally:
            conn.close()
    
    def delete_file(self, path: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM files WHERE path = ?', (path,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def get_file(self, path: str) -> Optional[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM files WHERE path = ?', (path,))
            row = cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            
            return None
        finally:
            conn.close()
    
    def get_all_files(
        self,
        folder_filter: Optional[List[str]] = None,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            query = 'SELECT * FROM files WHERE 1=1'
            params = []
            
            if folder_filter:
                placeholders = ','.join(['?' for _ in folder_filter])
                query += f' AND folder_source IN ({placeholders})'
                params.extend(folder_filter)
            
            if status_filter:
                query += ' AND status = ?'
                params.append(status_filter)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        finally:
            conn.close()
    
    def get_folder_stats(self) -> Dict[str, Any]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    folder_source,
                    COUNT(*) as document_count,
                    SUM(chunk_count) as total_chunks,
                    SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as error_count
                FROM files
                GROUP BY folder_source
            ''')
            
            rows = cursor.fetchall()
            
            stats = {}
            for row in rows:
                stats[row[0]] = {
                    'document_count': row[1],
                    'total_chunks': row[2] or 0,
                    'error_count': row[3]
                }
            
            return stats
        finally:
            conn.close()
    
    def add_folder(
        self,
        folder_id: str,
        path: str,
        name: str,
        enabled: bool = True
    ) -> None:
        now = datetime.now().isoformat()
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO folders (folder_id, path, name, enabled, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (folder_id, path, name, 1 if enabled else 0, now))
            
            conn.commit()
        finally:
            conn.close()
    
    def get_folders(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM folders')
            rows = cursor.fetchall()
            
            columns = [desc[0] for desc in cursor.description]
            folders = []
            for row in rows:
                folder = dict(zip(columns, row))
                folder['enabled'] = bool(folder.get('enabled', 0))
                folders.append(folder)
            
            return folders
        finally:
            conn.close()
    
    def update_folder(
        self,
        folder_id: str,
        enabled: Optional[bool] = None,
        last_scan_at: Optional[str] = None,
        document_count: Optional[int] = None,
        chunk_count: Optional[int] = None
    ) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if enabled is not None:
            updates.append('enabled = ?')
            params.append(1 if enabled else 0)
        
        if last_scan_at is not None:
            updates.append('last_scan_at = ?')
            params.append(last_scan_at)
        
        if document_count is not None:
            updates.append('document_count = ?')
            params.append(document_count)
        
        if chunk_count is not None:
            updates.append('chunk_count = ?')
            params.append(chunk_count)
        
        if updates:
            params.append(folder_id)
            query = f'UPDATE folders SET {", ".join(updates)} WHERE folder_id = ?'
            
            cursor.execute(query, params)
            conn.commit()
        
        conn.close()
    
    def delete_folder(self, folder_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM folders WHERE folder_id = ?', (folder_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def clear_all(self) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM files')
            cursor.execute('DELETE FROM folders')
            conn.commit()
        finally:
            conn.close()


_db = None


def get_metadata_db() -> MetadataDB:
    global _db
    if _db is None:
        _db = MetadataDB()
    return _db