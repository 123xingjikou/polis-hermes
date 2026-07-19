# ecosystem/core/plugins/reputation_assigner.py
"""
声誉分配器 - 管理 Agent 声誉和治理参与

设计理念：
- 基于 Agent 行为更新声誉
- 支持提案和投票
"""

import json
import time
import sqlite3
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger("polis.reputation")

class ReputationAssigner:
    """
    声誉分配系统
    
    管理 Agent 声誉和治理提案
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
        """初始化数据库"""
        if self._db is None:
            db_path = Path(self.data_dir) / "state" / "governance.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(str(db_path))
            self._db.row_factory = sqlite3.Row
            self._db.execute("PRAGMA journal_mode=WAL")
            
            # 声誉表
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS reputation (
                    agent_id TEXT PRIMARY KEY,
                    score REAL DEFAULT 0,
                    contributions INTEGER DEFAULT 0,
                    created_at REAL,
                    updated_at REAL
                )
            """)
            # 提案表
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS proposals (
                    proposal_id TEXT PRIMARY KEY,
                    title TEXT,
                    description TEXT,
                    proposer TEXT,
                    status TEXT DEFAULT 'open',
                    votes_for INTEGER DEFAULT 0,
                    votes_against INTEGER DEFAULT 0,
                    created_at REAL,
                    closed_at REAL
                )
            """)
            # 投票表
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS votes (
                    proposal_id TEXT,
                    agent_id TEXT,
                    vote TEXT,
                    voted_at REAL,
                    PRIMARY KEY (proposal_id, agent_id)
                )
            """)
            self._db.commit()
    
    def get_reputation(self, agent_id: str) -> Dict:
        """获取声誉"""
        self._init_db()
        cursor = self._db.cursor()
        cursor.execute("SELECT * FROM reputation WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {"agent_id": agent_id, "score": 0, "contributions": 0}
    
    def update_reputation(self, agent_id: str, delta: float) -> bool:
        """更新声誉"""
        self._init_db()
        try:
            self._db.execute(
                "INSERT OR REPLACE INTO reputation (agent_id, score, contributions, created_at, updated_at) "
                "VALUES (?, COALESCE((SELECT score FROM reputation WHERE agent_id=?), 0) + ?, "
                "COALESCE((SELECT contributions FROM reputation WHERE agent_id=?), 0) + 1, "
                "COALESCE((SELECT created_at FROM reputation WHERE agent_id=?), ?), ?)",
                (agent_id, agent_id, delta, agent_id, agent_id, time.time(), time.time())
            )
            self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Update reputation failed: {e}")
            return False
    
    def create_proposal(self, title: str, description: str, proposer: str) -> Optional[str]:
        """创建提案"""
        self._init_db()
        proposal_id = f"prop_{int(time.time())}_{hash(title) % 10000:04d}"
        
        try:
            self._db.execute(
                "INSERT INTO proposals (proposal_id, title, description, proposer, created_at) VALUES (?,?,?,?,?)",
                (proposal_id, title, description, proposer, time.time())
            )
            self._db.commit()
            logger.info(f"Proposal created: {proposal_id} by {proposer}")
            return proposal_id
        except Exception as e:
            logger.error(f"Create proposal failed: {e}")
            return None
    
    def vote(self, proposal_id: str, agent_id: str, vote: str) -> bool:
        """投票"""
        self._init_db()
        if vote not in ("for", "against"):
            return False
        
        try:
            # 记录投票
            self._db.execute(
                "INSERT OR REPLACE INTO votes (proposal_id, agent_id, vote, voted_at) VALUES (?,?,?,?)",
                (proposal_id, agent_id, vote, time.time())
            )
            # 更新计数
            if vote == "for":
                self._db.execute(
                    "UPDATE proposals SET votes_for = votes_for + 1 WHERE proposal_id = ?",
                    (proposal_id,)
                )
            else:
                self._db.execute(
                    "UPDATE proposals SET votes_against = votes_against + 1 WHERE proposal_id = ?",
                    (proposal_id,)
                )
            self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Vote failed: {e}")
            return False
    
    def get_open_proposals(self) -> List[Dict]:
        """获取开放提案"""
        self._init_db()
        cursor = self._db.cursor()
        cursor.execute(
            "SELECT * FROM proposals WHERE status = 'open' ORDER BY created_at DESC"
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def close_proposal(self, proposal_id: str) -> Dict:
        """关闭提案"""
        self._init_db()
        cursor = self._db.cursor()
        cursor.execute(
            "SELECT votes_for, votes_against FROM proposals WHERE proposal_id = ?",
            (proposal_id,)
        )
        row = cursor.fetchone()
        if not row:
            return {"error": "not_found"}
        
        result = "passed" if row[0] > row[1] else "rejected"
        self._db.execute(
            "UPDATE proposals SET status = ?, closed_at = ? WHERE proposal_id = ?",
            (result, time.time(), proposal_id)
        )
        self._db.commit()
        
        return {"proposal_id": proposal_id, "result": result, "votes_for": row[0], "votes_against": row[1]}
    
    def close(self):
        if self._db:
            self._db.close()
            self._db = None