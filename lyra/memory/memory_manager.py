# -*- coding: utf-8 -*-
"""
lyra/memory/memory_manager.py
Phase 2: Structured Memory Manager v1
Coordinates Session (STM) and Persistent (LTM) layers.
"""

import json
import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from lyra.memory.memory_schema import MemoryEntry, MemorySource
from lyra.core.logger import get_logger

class MemoryManager:
    """
    Dual-layer structured memory manager.
    Phase 2 Hardening v1.1: Atomic transactions, size guards, and write protection.
    """
    
    MAX_LTM_SIZE_MB = 50

    def __init__(self, db_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = str(project_root / "data" / "memory.db")
        
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self._init_db()
        self.session_memory: List[MemoryEntry] = []  # STM
        self._write_restricted = False # Restricted during high-risk execution
        
        self.logger.info(f"MemoryManager initialized (LTM: {db_path})")

    def _init_db(self):
        """Initialize SQLite database with migration guard for v1.1 -> v1.2."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # 1. Check for legacy 'timestamp' column and migrate
        cursor.execute("PRAGMA table_info(memory_entries)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "timestamp" in columns and "created_at" not in columns:
            self.logger.info("[MEMORY-MIGRATION] Detected legacy 'timestamp' column. Renaming to 'created_at'.")
            try:
                cursor.execute("ALTER TABLE memory_entries RENAME COLUMN timestamp TO created_at")
                # Attempt to convert existing string timestamps to integers if possible, 
                # but since they were ISO strings, they might be complex. 
                # For safety, we just rename the column and rely on INTEGER type affinity.
                conn.commit()
            except Exception as e:
                self.logger.error(f"[MEMORY-MIGRATION-FAILED] Failed to rename column: {e}")
                # Fallback: recreate table if critical
        
        # 2. Ensure table exists with v1.2 schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                source TEXT,
                memory_type TEXT,
                priority INTEGER,
                content TEXT,
                created_at INTEGER,
                version INTEGER,
                tags TEXT,
                metadata TEXT,
                approval_required INTEGER
            )
        ''')
        conn.commit()
        conn.close()

    def set_write_restriction(self, restricted: bool):
        """Enable/disable write restriction (e.g., during high-risk operations)."""
        self._write_restricted = restricted
        self.logger.info(f"[MEMORY] Write restriction set to: {restricted}")

    def add_memory(self, content: Dict[str, Any], source: MemorySource, 
                  memory_type: Any = None, priority: int = 3,
                  tags: List[str] = None, persistent: bool = False,
                  trace_id: str = "") -> str:
        """
        Add a new memory entry with integrity checks and logging.
        """
        from lyra.memory.memory_schema import MemoryType
        if memory_type is None:
            memory_type = MemoryType.TASK_HISTORY

        # Hardening: Check write restriction
        if self._write_restricted and memory_type != MemoryType.TASK_HISTORY:
            self.logger.warning(f"[MEMORY-WRITE] BLOCKED: Write restricted to TASK_HISTORY. Attempted {memory_type.value}.")
            return ""

        # Phase 2.3: Poisoning Mitigation & Validation
        if not self._validate_integrity(content, memory_type):
            self.logger.warning(f"[MEMORY-INTEGRITY] BLOCKED: Malicious/Malformed content in {memory_type.value}. Trace: {trace_id}")
            return ""

        import uuid
        entry_id = str(uuid.uuid4())
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            source=source,
            memory_type=memory_type,
            priority=priority,
            tags=tags or []
        )
        
        if persistent:
            try:
                self._save_to_ltm(entry)
                self.logger.info(f"[MEMORY-WRITE] [Trace: {trace_id}] Persistent entry {entry_id} ({memory_type.value})")
                self._enforce_size_limit()
            except Exception as e:
                self.logger.error(f"[MEMORY-WRITE-ERROR] Failed to save {entry_id}: {e}")
                return ""
        else:
            self.session_memory.append(entry)
            self.logger.info(f"[MEMORY-WRITE] [Trace: {trace_id}] Session entry {entry_id} ({memory_type.value})")
            
        return entry_id

    def _validate_integrity(self, content: Dict[str, Any], memory_type: Any) -> bool:
        """
        Phase 2.3: Validate memory integrity to prevent poisoning.
        Blocks LLM-defined safety overrides or tool definitions.
        """
        from lyra.memory.memory_schema import MemoryType
        content_str = json.dumps(content).lower()
        
        # 1. Block dangerous keywords in learned data
        restricted_patterns = [
            "safety_override", "bypass_security", "ignore_risk",
            "disable_confirmation", "tool_definition", "pipeline_override"
        ]
        
        for pattern in restricted_patterns:
            if pattern in content_str:
                self.logger.error(f"[MEMORY-INTEGRITY] Restricted pattern '{pattern}' detected in {memory_type.value}")
                return False
        
        # 2. Schema enforcement for LEARNED_PROCEDURE
        if memory_type == MemoryType.LEARNED_PROCEDURE:
            required_keys = ["step_pattern", "tool_sequence", "observation"]
            # But ensure the tool_sequence isn't actually redefining tools
            if not all(k in content for k in required_keys):
                self.logger.error(f"[MEMORY-INTEGRITY] LEARNED_PROCEDURE missing required keys")
                return False
                
        return True

    def query_memory(self, criteria: Dict[str, Any], persistent: bool = True, trace_id: str = "") -> List[MemoryEntry]:
        """
        Query memory entries with structured logging and deterministic ordering.
        """
        self.logger.info(f"[MEMORY-READ] [Trace: {trace_id}] Querying criteria: {criteria}")
        results = []
        
        # Query STM
        for entry in self.session_memory:
            if self._matches_criteria(entry, criteria):
                results.append(entry)
                
        # Query LTM
        if persistent:
            results.extend(self._query_ltm(criteria))
            
        # Phase 3.1: Deterministic tie-breaker ordering (v1.2)
        # Priority DESC, created_at DESC, ID DESC
        results.sort(key=lambda x: (x.priority, x.created_at, x.id), reverse=True)
            
        return results

    def _matches_criteria(self, entry: MemoryEntry, criteria: Dict[str, Any]) -> bool:
        """Simple criteria matching logic."""
        for key, value in criteria.items():
            if key == "source" and entry.source != value:
                return False
            if key == "memory_type" and entry.memory_type != value:
                return False
            if key == "tag" and value not in entry.tags:
                return False
        return True

    def _save_to_ltm(self, entry: MemoryEntry):
        """Save a MemoryEntry atomically to SQLite."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("BEGIN TRANSACTION")
            cursor = conn.cursor()
            data = entry.to_dict()
            cursor.execute('''
                INSERT OR REPLACE INTO memory_entries 
                (id, source, memory_type, priority, content, created_at, version, tags, metadata, approval_required)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data["id"],
                data["source"],
                data["memory_type"],
                data["priority"],
                json.dumps(data["content"]),
                data["created_at"],
                data["version"],
                json.dumps(data["tags"]),
                json.dumps(data["metadata"]),
                1 if data["approval_required"] else 0
            ))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _enforce_size_limit(self):
        """Enforce LTM size cap (50MB). Archive oldest low-priority if exceeded."""
        db_size_mb = os.path.getsize(self.db_path) / (1024 * 1024)
        if db_size_mb > self.MAX_LTM_SIZE_MB:
            self.logger.warning(f"[MEMORY-ARCHIVE] Size limit exceeded ({db_size_mb:.1f}MB > {self.MAX_LTM_SIZE_MB}MB). Triggering archive.")
            self._archive_old_memories()

    def _archive_old_memories(self):
        """Archive logic: Delete oldest low-priority entries to free space.
        Uses deterministic ordering: priority ASC, timestamp ASC.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("BEGIN TRANSACTION")
            cursor = conn.cursor()
            # Find oldest entries with priority < 4, using strict ordering
            cursor.execute('''
                DELETE FROM memory_entries 
                WHERE id IN (
                    SELECT id FROM memory_entries 
                    WHERE priority < 4 
                    ORDER BY priority ASC, created_at ASC, id ASC 
                    LIMIT 50
                )
            ''')
            self.logger.info(f"[MEMORY-ARCHIVE] Deleted 50 oldest low-priority entries (Deterministic Order).")
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"[MEMORY-ARCHIVE-ERROR] Archival failed: {e}")
        finally:
            conn.close()

    def _query_ltm(self, criteria: Dict[str, Any]) -> List[MemoryEntry]:
        """Fetch matching MemoryEntries from SQLite."""
        from lyra.memory.memory_schema import MemoryType
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM memory_entries"
        params = []
        if criteria:
            wheres = []
            if "source" in criteria:
                wheres.append("source = ?")
                params.append(criteria["source"].value if isinstance(criteria["source"], MemorySource) else criteria["source"])
            if "memory_type" in criteria:
                wheres.append("memory_type = ?")
                params.append(criteria["memory_type"].value if isinstance(criteria["memory_type"], MemoryType) else criteria["memory_type"])
        if wheres:
            query += " WHERE " + " AND ".join(wheres)
            
            # Phase 3.1: Enforce deterministic ordering in SQLite
            query += " ORDER BY priority DESC, created_at DESC, id DESC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                entry = MemoryEntry(
                    id=row["id"],
                    source=MemorySource(row["source"]),
                    memory_type=MemoryType(row["memory_type"]),
                    priority=row["priority"],
                    content=json.loads(row["content"]),
                    created_at=row["created_at"],
                    version=row["version"],
                    tags=json.loads(row["tags"]),
                    metadata=json.loads(row["metadata"]),
                    approval_required=bool(row["approval_required"])
                )
                if "tag" in criteria and criteria["tag"] not in entry.tags:
                    continue
                results.append(entry)
            
        conn.close()
        return results

    def update_memory(self, entry_id: str, new_content: Dict[str, Any]):
        """Update an existing memory entry (increments version)."""
        pass # Placeholder for Phase 2 
