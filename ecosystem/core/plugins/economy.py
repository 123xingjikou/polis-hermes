# ecosystem/core/plugins/economy.py
"""
经济匹配插件 - 管理 Agent 间的经济交互

设计理念：
- 复用 environment 的资源系统
- 支持交易匹配和钱包操作
"""

import json
import time
import sqlite3
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger("polis.economy")

class EconomicMatching:
    """
    经济匹配系统
    
    管理 Agent 钱包和交易
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
            db_path = Path(self.data_dir) / "state" / "polis.db"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(str(db_path))
            self._db.row_factory = sqlite3.Row
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA busy_timeout=30000")
            
            # 创建表
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    agent_id TEXT PRIMARY KEY,
                    balance REAL DEFAULT 0,
                    created_at REAL,
                    updated_at REAL
                )
            """)
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS obol_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    buyer TEXT,
                    seller TEXT,
                    amount REAL,
                    reason TEXT,
                    created_at REAL
                )
            """)
            self._db.commit()
    
    def get_wallet(self, agent_id: str) -> Dict:
        """获取 Agent 钱包"""
        self._init_db()
        cursor = self._db.cursor()
        cursor.execute("SELECT * FROM wallets WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {"agent_id": agent_id, "balance": 0}
    
    def create_wallet(self, agent_id: str, initial_balance: float = 0) -> bool:
        """创建钱包"""
        self._init_db()
        try:
            self._db.execute(
                "INSERT OR IGNORE INTO wallets (agent_id, balance, created_at, updated_at) VALUES (?,?,?,?)",
                (agent_id, initial_balance, time.time(), time.time())
            )
            self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Create wallet failed: {e}")
            return False
    
    def transfer(self, buyer: str, seller: str, amount: float, reason: str = "") -> bool:
        """转账"""
        self._init_db()
        try:
            # 检查余额
            buyer_wallet = self.get_wallet(buyer)
            if buyer_wallet.get("balance", 0) < amount:
                logger.warning(f"Insufficient balance: {buyer} has {buyer_wallet.get('balance', 0)}")
                return False
            
            # 执行转账
            self._db.execute(
                "UPDATE wallets SET balance = balance - ?, updated_at = ? WHERE agent_id = ?",
                (amount, time.time(), buyer)
            )
            self._db.execute(
                "UPDATE wallets SET balance = balance + ?, updated_at = ? WHERE agent_id = ?",
                (amount, time.time(), seller)
            )
            self._db.execute(
                "INSERT INTO obol_transactions (buyer, seller, amount, reason, created_at) VALUES (?,?,?,?,?)",
                (buyer, seller, amount, reason, time.time())
            )
            self._db.commit()
            
            logger.info(f"Transfer: {buyer} -> {seller} ({amount} obol)")
            return True
        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            return False
    
    def mint(self, agent_id: str, amount: float) -> bool:
        """发放津贴"""
        self._init_db()
        try:
            self._db.execute(
                "UPDATE wallets SET balance = balance + ?, updated_at = ? WHERE agent_id = ?",
                (amount, time.time(), agent_id)
            )
            self._db.commit()
            return True
        except Exception as e:
            logger.error(f"Mint failed: {e}")
            return False
    
    def mint_all(self, amount: float) -> int:
        """向所有钱包发放津贴"""
        self._init_db()
        cursor = self._db.cursor()
        cursor.execute("SELECT agent_id FROM wallets")
        agents = [row[0] for row in cursor.fetchall()]
        
        count = 0
        for agent_id in agents:
            if self.mint(agent_id, amount):
                count += 1
        
        return count
    
    def get_stats(self) -> Dict:
        """获取统计"""
        self._init_db()
        cursor = self._db.cursor()
        
        cursor.execute("SELECT COUNT(*), SUM(balance) FROM wallets")
        row = cursor.fetchone()
        wallet_count = row[0] or 0
        total_balance = row[1] or 0
        
        cursor.execute("SELECT COUNT(*) FROM obol_transactions")
        tx_count = cursor.fetchone()[0] or 0
        
        return {
            "wallet_count": wallet_count,
            "total_balance": total_balance,
            "avg_balance": total_balance / wallet_count if wallet_count > 0 else 0,
            "transaction_count": tx_count,
        }
    
    def close(self):
        if self._db:
            self._db.close()
            self._db = None