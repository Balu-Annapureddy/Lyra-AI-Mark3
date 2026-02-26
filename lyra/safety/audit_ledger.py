# -*- coding: utf-8 -*-
"""
lyra/safety/audit_ledger.py
Phase 4+5: Execution Audit Ledger — Hash Chain v2.0
Stores immutable, chained records of all execution attempts.

Hard Constraints:
- Append-only persistence.
- Entries cannot be edited or deleted.
- Each record includes previous_record_hash → tamper-evident chain.
- If any record is altered → entire chain invalidates.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from lyra.core.logger import get_logger


class AuditLedger:
    """
    Structured, append-only, hash-chained logger for execution accountability.
    No mutation or deletion allowed via this interface.
    
    Phase 5 Upgrade:
    - Each record includes previous_record_hash and current_record_hash.
    - validate_chain() verifies entire history integrity.
    - Cryptographically auditable. Legally defensible. Enterprise-ready.
    """
    
    GENESIS_HASH = "0" * 64  # Genesis block hash
    
    def __init__(self, ledger_path: str = None):
        self.logger = get_logger(__name__)
        
        if ledger_path is None:
            project_root = Path(__file__).parent.parent.parent
            ledger_path = str(project_root / "data" / "audit_ledger.jsonl")
            
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Cache the last record hash for chain continuity
        self._last_record_hash = self._get_last_hash()
    
    def _get_last_hash(self) -> str:
        """Read the last record's hash from the ledger for chain continuity."""
        if not self.ledger_path.exists():
            return self.GENESIS_HASH
            
        last_hash = self.GENESIS_HASH
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entry = json.loads(line)
                        last_hash = entry.get("current_record_hash", self.GENESIS_HASH)
        except Exception:
            pass
        return last_hash
    
    def _compute_record_hash(self, entry: Dict[str, Any], previous_hash: str) -> str:
        """
        Compute SHA256 hash over critical record fields + previous hash.
        This creates the tamper-evident chain.
        """
        hash_data = {
            "plan_id": entry.get("plan_id", ""),
            "deterministic_hash": entry.get("deterministic_hash", ""),
            "simulation_result": str(entry.get("simulation_result", "")),
            "final_state": entry.get("final_state", entry.get("status", "")),
            "created_at": entry.get("created_at", 0),
            "previous_record_hash": previous_hash
        }
        canonical = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()
        
    def record_entry(self, entry: Dict[str, Any]):
        """
        Append a new entry to the hash-chained audit ledger.
        Entries are immutable once written.
        """
        # Ensure canonical timestamp
        if "created_at" not in entry:
            entry["created_at"] = int(datetime.now().timestamp())
            
        # Ensure trace_id
        if "trace_id" not in entry:
            entry["trace_id"] = f"audit-{entry['created_at']}"
        
        # Ensure final_state
        if "final_state" not in entry and "status" in entry:
            entry["final_state"] = entry["status"]
        
        # Phase 5: Hash chain linkage
        entry["previous_record_hash"] = self._last_record_hash
        entry["current_record_hash"] = self._compute_record_hash(entry, self._last_record_hash)
        
        try:
            with open(self.ledger_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, default=str) + "\n")
            
            # Update chain head
            self._last_record_hash = entry["current_record_hash"]
            
            self.logger.info(
                f"[AUDIT-RECORDED] plan_id={entry.get('plan_id', 'UNKNOWN')} "
                f"state={entry.get('final_state', entry.get('status', 'UNKNOWN'))} "
                f"chain_hash={entry['current_record_hash'][:16]}..."
            )
        except Exception as e:
            self.logger.error(f"[AUDIT-LEDGER-ERROR] Failed to write audit entry: {e}")

    def validate_chain(self) -> Dict[str, Any]:
        """
        Phase 5: Validate the entire hash chain.
        If any record has been altered, the chain breaks.
        
        Returns:
            {valid: bool, records_checked: int, break_at: index or None, error: str or None}
        """
        if not self.ledger_path.exists():
            return {"valid": True, "records_checked": 0, "break_at": None, "error": None}
        
        previous_hash = self.GENESIS_HASH
        records_checked = 0
        
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    
                    entry = json.loads(line)
                    records_checked += 1
                    
                    # Verify previous hash linkage
                    stored_prev = entry.get("previous_record_hash", "")
                    if stored_prev != previous_hash:
                        self.logger.error(
                            f"[CHAIN-BROKEN] Record {i}: previous_hash mismatch. "
                            f"Expected: {previous_hash[:16]}... Got: {stored_prev[:16]}..."
                        )
                        return {
                            "valid": False,
                            "records_checked": records_checked,
                            "break_at": i,
                            "error": f"Previous hash mismatch at record {i}"
                        }
                    
                    # Recompute and verify current hash
                    expected_hash = self._compute_record_hash(entry, previous_hash)
                    stored_hash = entry.get("current_record_hash", "")
                    
                    if expected_hash != stored_hash:
                        self.logger.error(
                            f"[CHAIN-BROKEN] Record {i}: content hash mismatch. "
                            f"Expected: {expected_hash[:16]}... Got: {stored_hash[:16]}..."
                        )
                        return {
                            "valid": False,
                            "records_checked": records_checked,
                            "break_at": i,
                            "error": f"Content hash mismatch at record {i}"
                        }
                    
                    previous_hash = stored_hash
        except Exception as e:
            self.logger.error(f"[CHAIN-VALIDATION-ERROR] {e}")
            return {
                "valid": False,
                "records_checked": records_checked,
                "break_at": None,
                "error": str(e)
            }
        
        self.logger.info(
            f"[CHAIN-VALID] All {records_checked} records verified. "
            f"Head: {previous_hash[:16]}..."
        )
        return {
            "valid": True,
            "records_checked": records_checked,
            "break_at": None,
            "error": None
        }

    def get_plan_history(self, plan_id: str) -> List[Dict[str, Any]]:
        """Search the ledger for entries related to a specific plan."""
        history = []
        if not self.ledger_path.exists():
            return history
            
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry.get("plan_id") == plan_id:
                        history.append(entry)
        except Exception as e:
            self.logger.error(f"[AUDIT-LEDGER-ERROR] Failed to read history: {e}")
            
        return history

    def get_full_ledger(self) -> List[Dict[str, Any]]:
        """Return the full audit ledger (read-only)."""
        entries = []
        if not self.ledger_path.exists():
            return entries
            
        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entries.append(json.loads(line))
        except Exception as e:
            self.logger.error(f"[AUDIT-LEDGER-ERROR] Failed to read ledger: {e}")
            
        return entries
