"""
conftest.py - pytest 全局配置和 fixtures
"""

import sys
import os
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

import pytest

# 将项目根目录加入 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def project_root():
    """项目根目录"""
    return PROJECT_ROOT


@pytest.fixture
def temp_db():
    """临时 SQLite 数据库 fixture"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    try:
        yield conn, path
    finally:
        conn.close()
        os.unlink(path)


@pytest.fixture
def sample_memories_db(temp_db):
    """包含示例记忆数据的临时数据库"""
    conn, path = temp_db
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            content TEXT NOT NULL,
            importance REAL DEFAULT 0.5,
            category TEXT DEFAULT 'general',
            emotion_tags TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE memory_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_agent TEXT NOT NULL,
            to_agent TEXT NOT NULL,
            memory_id INTEGER,
            permission TEXT DEFAULT 'see_content',
            shared_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # 插入示例数据
    sample_data = [
        ("agent_alpha", "今天学会了使用 GEP 进化算法", 0.85, "learning", "curiosity,excitement"),
        ("agent_alpha", "市场分析显示牛市趋势", 0.7, "market", "confidence"),
        ("agent_beta", "新技能树解锁了 3 个节点", 0.6, "skill", "satisfaction"),
        ("agent_gamma", "城邦桥接测试成功完成", 0.9, "bridge", "joy"),
        ("agent_delta", "普通记忆条目", 0.3, "general", None),
    ]

    for agent_id, content, importance, category, emotion in sample_data:
        cursor.execute(
            "INSERT INTO memories (agent_id, content, importance, category, emotion_tags) VALUES (?, ?, ?, ?, ?)",
            (agent_id, content, importance, category, emotion)
        )

    conn.commit()
    return conn, path


@pytest.fixture
def sample_session_log_db(temp_db):
    """包含会话日志的临时数据库"""
    conn, path = temp_db
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE session_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT,
            message_type TEXT,
            status TEXT DEFAULT 'completed',
            response_time_ms REAL,
            timestamp TEXT DEFAULT (datetime('now'))
        )
    """)

    base_time = datetime.now() - timedelta(days=10)
    for day in range(10):
        for i in range(20):
            ts = base_time + timedelta(days=day, minutes=i * 3)
            response_time = 500 + (day % 5) * 200 + i * 10
            status = "completed" if i < 18 else "timeout"
            cursor.execute(
                "INSERT INTO session_log (sender, receiver, message_type, status, response_time_ms, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (f"agent_{day % 3}", "receiver", "query", status, response_time, ts.isoformat())
            )

    conn.commit()
    return conn, path
