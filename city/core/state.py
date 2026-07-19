import sqlite3
import json
from typing import Optional, Type, List

from .resident import CityResident, MemoryItem


class CityState:
    def __init__(self, db_path: str = "city_state.db"):
        self.conn = sqlite3.connect(db_path)
        self._init_tables()

    def _init_tables(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS residents (
                name TEXT PRIMARY KEY,
                personality TEXT,
                skills TEXT,
                role TEXT,
                coins INTEGER,
                needs TEXT,
                relationships TEXT,
                memory_short TEXT,
                memory_long TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tick INTEGER,
                description TEXT
            )
        """)
        self.conn.commit()

    def save_resident(self, resident: CityResident) -> None:
        data = (
            resident.name,
            json.dumps(resident.personality),
            json.dumps(resident.skills),
            resident.role,
            resident.coins,
            json.dumps(resident.needs),
            json.dumps(resident.relationships),
            json.dumps([(m.content, m.timestamp, m.importance) for m in resident.memory.short_term]),
            json.dumps([(m.content, m.timestamp, m.importance) for m in resident.memory.long_term]),
        )
        self.conn.execute("REPLACE INTO residents VALUES (?,?,?,?,?,?,?,?,?)", data)
        self.conn.commit()

    def load_resident(self, name: str, resident_cls: Type[CityResident]) -> Optional[CityResident]:
        cur = self.conn.execute("SELECT * FROM residents WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            return None
        pers = json.loads(row[1])
        skills = json.loads(row[2])
        r = resident_cls(name, pers, skills, role=row[3], coins=row[4])
        r.needs = json.loads(row[5])
        r.relationships = json.loads(row[6])
        short = json.loads(row[7])
        long = json.loads(row[8])
        r.memory.short_term = [MemoryItem(c, t, imp) for c, t, imp in short]
        r.memory.long_term = [MemoryItem(c, t, imp) for c, t, imp in long]
        return r

    def list_resident_names(self) -> List[str]:
        cur = self.conn.execute("SELECT name FROM residents")
        return [row[0] for row in cur.fetchall()]

    def add_event(self, tick: int, description: str) -> None:
        self.conn.execute("INSERT INTO events (tick, description) VALUES (?, ?)", (tick, description))
        self.conn.commit()

    def get_events(self, tick: Optional[int] = None) -> List[tuple]:
        if tick is not None:
            cur = self.conn.execute("SELECT id, tick, description FROM events WHERE tick = ?", (tick,))
        else:
            cur = self.conn.execute("SELECT id, tick, description FROM events ORDER BY id")
        return cur.fetchall()

    def close(self) -> None:
        self.conn.close()
