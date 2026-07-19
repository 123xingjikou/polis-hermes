# ecosystem/core/memory_cascade.py
"""
记忆级联 - 复用 evolution 的知识池实现 Hermes 记忆接口

设计理念：
- 将 Agent 的体验事件写入 EvolutionDB 的知识池
- 支持按 Agent ID 检索相关记忆
- 支持记忆演化（遗忘、合并）
"""

import json
import time
import hashlib
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger("polis.memory_cascade")

@dataclass
class MemoryEntry:
    """记忆条目"""
    entry_id: str
    content: str
    memory_type: str
    agent_id: str
    importance: float
    created_at: float
    metadata: dict

class MemoryCascade:
    """
    记忆级联系统
    
    将 Hermes 的记忆操作映射到 EvolutionDB 的知识池
    """
    
    def __init__(self, data_dir: str = None):
        import os
        self.data_dir = data_dir or os.environ.get(
            "CITY_STATE_DATA_DIR",
            r"C:\Users\dfhai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a45044b9f3d6718577ed1f8\city_state_data\ecosystem"
        )
        self._db = None
        self._init_db()
    
    def _init_db(self):
        """延迟初始化数据库连接"""
        if self._db is None:
            import sqlite3
            from pathlib import Path
            db_path = Path(self.data_dir) / "state" / "evolution.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(str(db_path))
            self._db.row_factory = sqlite3.Row
            # 启用 WAL 模式
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA busy_timeout=30000")
            # 确保表存在
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_pool (
                    knowledge_id TEXT PRIMARY KEY,
                    knowledge_type TEXT,
                    content TEXT,
                    creator_id TEXT,
                    generation INTEGER,
                    utility_score REAL,
                    usage_count INTEGER DEFAULT 0,
                    inherited_count INTEGER DEFAULT 0,
                    created_at REAL
                )
            """)
            self._db.commit()
    
    def ingest(self, agent_id: str, event: Dict) -> str:
        """
        将事件写入记忆
        
        Args:
            agent_id: Agent ID
            event: 事件字典，包含 type, content, severity 等
        
        Returns:
            记忆条目 ID
        """
        self._init_db()
        
        entry_id = hashlib.md5(f"{agent_id}{time.time()}{event}".encode()).hexdigest()[:12]
        memory_type = event.get("type", "event")
        content = json.dumps(event) if isinstance(event, dict) else str(event)
        importance = min(1.0, max(0.0, event.get("severity", 0.5)))
        
        self._db.execute(
            "INSERT INTO knowledge_pool "
            "(knowledge_id, knowledge_type, content, creator_id, generation, utility_score, created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (entry_id, memory_type, content, agent_id, 0, importance, time.time())
        )
        self._db.commit()
        
        logger.debug(f"Memory ingested: {entry_id} for {agent_id}")
        return entry_id
    
    def retrieve(self, agent_id: str, query: str = None, limit: int = 10) -> List[Dict]:
        """
        检索 Agent 的相关记忆
        
        Args:
            agent_id: Agent ID
            query: 查询关键词（可选）
            limit: 返回数量限制
        
        Returns:
            记忆条目列表
        """
        self._init_db()
        
        cursor = self._db.cursor()
        if query:
            # 简化版：按内容匹配
            cursor.execute(
                "SELECT * FROM knowledge_pool "
                "WHERE creator_id = ? AND content LIKE ? "
                "ORDER BY utility_score DESC, created_at DESC LIMIT ?",
                (agent_id, f"%{query}%", limit)
            )
        else:
            cursor.execute(
                "SELECT * FROM knowledge_pool WHERE creator_id = ? "
                "ORDER BY utility_score DESC, created_at DESC LIMIT ?",
                (agent_id, limit)
            )
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def evolve(self, agent_id: str) -> Dict:
        """
        记忆演化：遗忘低重要性记忆，合并相似记忆
        
        Returns:
            {"forgotten": N, "merged": M}
        """
        self._init_db()
        
        stats = {"forgotten": 0, "merged": 0}
        
        # 遗忘：utility_score < 0.1 且 30 天未访问
        threshold = time.time() - 30 * 24 * 3600
        cursor = self._db.cursor()
        cursor.execute(
            "DELETE FROM knowledge_pool "
            "WHERE creator_id = ? AND utility_score < 0.1 AND created_at < ?",
            (agent_id, threshold)
        )
        stats["forgotten"] = cursor.rowcount
        
        # 重要性衰减
        cursor.execute(
            "UPDATE knowledge_pool SET utility_score = utility_score * 0.95 "
            "WHERE creator_id = ?",
            (agent_id,)
        )
        
        self._db.commit()
        logger.info(f"Memory evolved for {agent_id}: {stats}")
        return stats
    
    def close(self):
        if self._db:
            self._db.close()
            self._db = None