# ecosystem/core/plugins/social_graph.py
"""
社交图谱插件 - 管理 Agent 间的社交关系

设计理念：
- 支持好友、敌人、中立关系
- 支持关系强度和信任度
"""

import json
import time
import sqlite3
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger("polis.social_graph")

class SocialGraph:
    """
    社交图谱系统
    
    管理 Agent 间的关系网络
    """
    
    RELATION_TYPES = {
        "friend": 1.0,
        "ally": 0.7,
        "neutral": 0.0,
        "rival": -0.5,
        "enemy": -1.0,
    }
    
    def __init__(self, data_dir: str = None):
        import os
        self.data_dir = data_dir or os.environ.get(
            "CITY_STATE_DATA_DIR",
            r"C:\Users\dfhai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a45044b9f3d6718577ed1f8\city_state_data\ecosystem"
        )
        self._db = None
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        if self._db is None:
            db_path = Path(self.data_dir) / "state" / "social.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(str(db_path))
            self._db.row_factory = sqlite3.Row
            self._db.execute("PRAGMA journal_mode=WAL")
            
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS relationships (
                    agent_a TEXT,
                    agent_b TEXT,
                    relation_type TEXT,
                    strength REAL DEFAULT 0,
                    trust REAL DEFAULT 0,
                    created_at REAL,
                    updated_at REAL,
                    PRIMARY KEY (agent_a, agent_b)
                )
            """)
            self._db.commit()
    
    def set_relation(self, agent_a: str, agent_b: str, 
                     relation_type: str, strength: float = None) -> bool:
        """设置关系"""
        self._init_db()
        
        if strength is None:
            strength = self.RELATION_TYPES.get(relation_type, 0.0)
        
        try:
            # 使用简单的 INSERT OR REPLACE
            self._db.execute(
                "INSERT OR REPLACE INTO relationships "
                "(agent_a, agent_b, relation_type, strength, trust, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (agent_a, agent_b, relation_type, strength, 0, time.time(), time.time())
            )
            self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Set relation failed: {e}")
            return False
    
    def get_relation(self, agent_a: str, agent_b: str) -> Dict:
        """获取关系"""
        self._init_db()
        cursor = self._db.cursor()
        cursor.execute(
            "SELECT * FROM relationships WHERE agent_a = ? AND agent_b = ?",
            (agent_a, agent_b)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {"agent_a": agent_a, "agent_b": agent_b, "relation_type": "none", "strength": 0}
    
    def get_friends(self, agent_id: str, min_strength: float = 0.5) -> List[str]:
        """获取好友列表"""
        self._init_db()
        cursor = self._db.cursor()
        cursor.execute(
            "SELECT agent_b FROM relationships WHERE agent_a = ? AND strength >= ?",
            (agent_id, min_strength)
        )
        return [row[0] for row in cursor.fetchall()]
    
    def get_enemies(self, agent_id: str) -> List[str]:
        """获取敌人列表"""
        self._init_db()
        cursor = self._db.cursor()
        cursor.execute(
            "SELECT agent_b FROM relationships WHERE agent_a = ? AND strength < 0",
            (agent_id,)
        )
        return [row[0] for row in cursor.fetchall()]
    
    def update_trust(self, agent_a: str, agent_b: str, delta: float) -> bool:
        """更新信任度"""
        self._init_db()
        try:
            self._db.execute(
                "UPDATE relationships SET trust = trust + ?, updated_at = ? WHERE agent_a = ? AND agent_b = ?",
                (delta, time.time(), agent_a, agent_b)
            )
            self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Update trust failed: {e}")
            return False
    
    def close(self):
        if self._db:
            self._db.close()
            self._db = None