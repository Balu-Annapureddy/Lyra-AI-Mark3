"""
Event Memory System
Stores user interactions and system events with time-decay retrieval
"""

import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from lyra.memory.memory_level import MemoryLevel
from lyra.reasoning.command_schema import Command
from lyra.core.logger import get_logger
from lyra.core.exceptions import MemoryError


class EventMemory:
    """
    Event-based memory storage with SQLite backend
    Supports time-decayed retrieval and memory level classification
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = str(project_root / "data" / "lyra_memory.db")
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT UNIQUE NOT NULL,
                        timestamp TEXT NOT NULL,
                        memory_level TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        data TEXT NOT NULL,
                        importance REAL DEFAULT 0.5,
                        created_at TEXT NOT NULL
                    )
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_memory_level ON events(memory_level)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_event_type ON events(event_type)
                """)
                
                conn.commit()
                self.logger.info("Event memory database initialized")
        
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to initialize database: {e}")
    
    def store_command(self, command: Command, memory_level: MemoryLevel = MemoryLevel.SHORT_TERM):
        """
        Store command in memory
        
        Args:
            command: Command to store
            memory_level: Memory level classification
        """
        self.store_event(
            event_id=command.command_id,
            event_type="command",
            data=command.to_dict(),
            memory_level=memory_level,
            importance=command.confidence
        )
    
    def store_event(self, event_id: str, event_type: str, data: Dict[str, Any],
                   memory_level: MemoryLevel = MemoryLevel.SHORT_TERM,
                   importance: float = 0.5):
        """
        Store an event in memory
        
        Args:
            event_id: Unique event identifier
            event_type: Type of event (command, system_event, etc.)
            data: Event data dictionary
            memory_level: Memory level classification
            importance: Importance score (0.0 to 1.0)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO events 
                    (event_id, timestamp, memory_level, event_type, data, importance, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    datetime.now().isoformat(),
                    memory_level.value,
                    event_type,
                    json.dumps(data),
                    importance,
                    datetime.now().isoformat()
                ))
                
                conn.commit()
                self.logger.debug(f"Stored event: {event_id} ({memory_level.value})")
        
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to store event: {e}")
    
    def retrieve_recent(self, limit: int = 10, 
                       memory_level: Optional[MemoryLevel] = None,
                       event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve recent events
        
        Args:
            limit: Maximum number of events to retrieve
            memory_level: Optional filter by memory level
            event_type: Optional filter by event type
        
        Returns:
            List of events
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM events WHERE 1=1"
                params = []
                
                if memory_level:
                    query += " AND memory_level = ?"
                    params.append(memory_level.value)
                
                if event_type:
                    query += " AND event_type = ?"
                    params.append(event_type)
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                events = []
                for row in rows:
                    events.append({
                        "id": row[0],
                        "event_id": row[1],
                        "timestamp": row[2],
                        "memory_level": row[3],
                        "event_type": row[4],
                        "data": json.loads(row[5]),
                        "importance": row[6],
                        "created_at": row[7]
                    })
                
                return events
        
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to retrieve events: {e}")
    
    def search_events(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search events by text query
        
        Args:
            query: Search query
            limit: Maximum results
        
        Returns:
            List of matching events
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM events 
                    WHERE data LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (f"%{query}%", limit))
                
                rows = cursor.fetchall()
                
                events = []
                for row in rows:
                    events.append({
                        "id": row[0],
                        "event_id": row[1],
                        "timestamp": row[2],
                        "memory_level": row[3],
                        "event_type": row[4],
                        "data": json.loads(row[5]),
                        "importance": row[6],
                        "created_at": row[7]
                    })
                
                return events
        
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to search events: {e}")
    
    def cleanup_old_events(self, days: int = 30):
        """
        Clean up old SHORT_TERM events
        
        Args:
            days: Delete events older than this many days
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM events 
                    WHERE memory_level = ? AND timestamp < ?
                """, (MemoryLevel.SHORT_TERM.value, cutoff_date))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"Cleaned up {deleted_count} old events")
        
        except sqlite3.Error as e:
            raise MemoryError(f"Failed to cleanup events: {e}")
