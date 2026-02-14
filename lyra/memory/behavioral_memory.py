"""
Behavioral Memory Layer - Phase 3A
Long-term behavioral pattern storage separate from execution logs
Tracks workflow frequency, task clusters, risk tolerance, and suggestion effectiveness
"""

import sqlite3
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from lyra.core.logger import get_logger


@dataclass
class WorkflowPattern:
    """Workflow usage pattern"""
    pattern_id: str
    workflow_id: str
    workflow_name: str
    frequency: int
    last_used: str
    time_of_day_distribution: Dict[int, int]  # {hour: count}
    day_of_week_distribution: Dict[int, int]  # {0-6: count}
    avg_execution_time: float


@dataclass
class TaskCluster:
    """Cluster of related tasks"""
    cluster_id: str
    task_sequence: List[str]  # [intent1, intent2, ...]
    occurrence_count: int
    avg_time_gap: float  # Average seconds between tasks
    context_similarity: Dict[str, Any]


@dataclass
class RiskToleranceRecord:
    """Risk tolerance history"""
    record_id: str
    timestamp: str
    risk_level: str
    operation: str
    user_action: str  # accepted, rejected, overridden
    trust_score_at_time: float


class BehavioralMemory:
    """
    Long-term behavioral pattern storage
    Separate from execution logs for focused pattern analysis
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.logger = get_logger(__name__)
        
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = str(project_root / "data" / "behavioral_memory.db")
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        self.logger.info(f"Behavioral memory initialized: {db_path}")
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Workflow patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_patterns (
                pattern_id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                workflow_name TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                last_used TIMESTAMP NOT NULL,
                time_of_day_distribution TEXT,  -- JSON
                day_of_week_distribution TEXT,  -- JSON
                avg_execution_time REAL DEFAULT 0.0
            )
        """)
        
        # Task clusters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_clusters (
                cluster_id TEXT PRIMARY KEY,
                task_sequence TEXT NOT NULL,  -- JSON array
                occurrence_count INTEGER DEFAULT 1,
                avg_time_gap REAL DEFAULT 0.0,
                context_similarity TEXT,  -- JSON
                last_occurrence TIMESTAMP
            )
        """)
        
        # Risk tolerance history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_tolerance_history (
                record_id TEXT PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                risk_level TEXT NOT NULL,
                operation TEXT NOT NULL,
                user_action TEXT NOT NULL,
                trust_score_at_time REAL NOT NULL
            )
        """)
        
        # Suggestion effectiveness
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suggestion_effectiveness (
                suggestion_type TEXT PRIMARY KEY,
                total_suggestions INTEGER DEFAULT 0,
                accepted_count INTEGER DEFAULT 0,
                rejected_count INTEGER DEFAULT 0,
                acceptance_rate REAL DEFAULT 0.0,
                last_suggested TIMESTAMP,
                time_of_day_acceptance TEXT,  -- JSON {hour: acceptance_rate}
                context_acceptance TEXT  -- JSON {context: acceptance_rate}
            )
        """)
        
        conn.commit()
        conn.close()
    
    # Workflow Pattern Methods
    
    def record_workflow_execution(self, workflow_id: str, workflow_name: str, 
                                   execution_time: float = 0.0):
        """Record a workflow execution"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()
        
        # Check if pattern exists
        cursor.execute(
            "SELECT pattern_id, frequency, time_of_day_distribution, day_of_week_distribution, avg_execution_time "
            "FROM workflow_patterns WHERE workflow_id = ?",
            (workflow_id,)
        )
        result = cursor.fetchone()
        
        if result:
            # Update existing pattern
            pattern_id, freq, tod_json, dow_json, avg_time = result
            
            tod_dist = json.loads(tod_json) if tod_json else {}
            dow_dist = json.loads(dow_json) if dow_json else {}
            
            tod_dist[str(hour)] = tod_dist.get(str(hour), 0) + 1
            dow_dist[str(day_of_week)] = dow_dist.get(str(day_of_week), 0) + 1
            
            new_freq = freq + 1
            new_avg_time = ((avg_time * freq) + execution_time) / new_freq
            
            cursor.execute("""
                UPDATE workflow_patterns
                SET frequency = ?, last_used = ?, time_of_day_distribution = ?,
                    day_of_week_distribution = ?, avg_execution_time = ?
                WHERE pattern_id = ?
            """, (new_freq, now.isoformat(), json.dumps(tod_dist), 
                  json.dumps(dow_dist), new_avg_time, pattern_id))
        else:
            # Create new pattern
            pattern_id = str(uuid.uuid4())
            tod_dist = {str(hour): 1}
            dow_dist = {str(day_of_week): 1}
            
            cursor.execute("""
                INSERT INTO workflow_patterns 
                (pattern_id, workflow_id, workflow_name, frequency, last_used,
                 time_of_day_distribution, day_of_week_distribution, avg_execution_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (pattern_id, workflow_id, workflow_name, 1, now.isoformat(),
                  json.dumps(tod_dist), json.dumps(dow_dist), execution_time))
        
        conn.commit()
        conn.close()
    
    def get_workflow_patterns(self, min_frequency: int = 1) -> List[WorkflowPattern]:
        """Get workflow patterns above minimum frequency"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pattern_id, workflow_id, workflow_name, frequency, last_used,
                   time_of_day_distribution, day_of_week_distribution, avg_execution_time
            FROM workflow_patterns
            WHERE frequency >= ?
            ORDER BY frequency DESC
        """, (min_frequency,))
        
        patterns = []
        for row in cursor.fetchall():
            pattern = WorkflowPattern(
                pattern_id=row[0],
                workflow_id=row[1],
                workflow_name=row[2],
                frequency=row[3],
                last_used=row[4],
                time_of_day_distribution=json.loads(row[5]) if row[5] else {},
                day_of_week_distribution=json.loads(row[6]) if row[6] else {},
                avg_execution_time=row[7]
            )
            patterns.append(pattern)
        
        conn.close()
        return patterns
    
    def get_time_patterns(self, workflow_id: str) -> Dict[str, Any]:
        """Get time-based patterns for a workflow"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT time_of_day_distribution, day_of_week_distribution
            FROM workflow_patterns
            WHERE workflow_id = ?
        """, (workflow_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            tod_dist = json.loads(result[0]) if result[0] else {}
            dow_dist = json.loads(result[1]) if result[1] else {}
            
            # Find peak hours and days
            peak_hours = sorted(tod_dist.items(), key=lambda x: x[1], reverse=True)[:3]
            peak_days = sorted(dow_dist.items(), key=lambda x: x[1], reverse=True)[:3]
            
            return {
                "peak_hours": [int(h) for h, _ in peak_hours],
                "peak_days": [int(d) for d, _ in peak_days],
                "time_distribution": tod_dist,
                "day_distribution": dow_dist
            }
        
        return {}
    
    # Risk Tolerance Methods
    
    def record_risk_action(self, risk_level: str, operation: str, 
                           user_action: str, trust_score: float):
        """Record a risk-related user action"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        record_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO risk_tolerance_history
            (record_id, timestamp, risk_level, operation, user_action, trust_score_at_time)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (record_id, timestamp, risk_level, operation, user_action, trust_score))
        
        conn.commit()
        conn.close()
    
    def get_risk_tolerance_trend(self, days_back: int = 30) -> Dict[str, Any]:
        """Analyze risk tolerance trend"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        cursor.execute("""
            SELECT risk_level, user_action, COUNT(*) as count
            FROM risk_tolerance_history
            WHERE timestamp >= ?
            GROUP BY risk_level, user_action
        """, (cutoff,))
        
        results = cursor.fetchall()
        conn.close()
        
        trend = {}
        for risk_level, action, count in results:
            if risk_level not in trend:
                trend[risk_level] = {"accepted": 0, "rejected": 0, "overridden": 0}
            trend[risk_level][action] = count
        
        return trend
    
    # Suggestion Effectiveness Methods
    
    def record_suggestion_outcome(self, suggestion_type: str, accepted: bool,
                                   context: Dict[str, Any] = None):
        """Record suggestion outcome"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        hour = now.hour
        context_key = context.get("project", "default") if context else "default"
        
        # Get existing record
        cursor.execute("""
            SELECT total_suggestions, accepted_count, rejected_count,
                   time_of_day_acceptance, context_acceptance
            FROM suggestion_effectiveness
            WHERE suggestion_type = ?
        """, (suggestion_type,))
        
        result = cursor.fetchone()
        
        if result:
            total, acc_count, rej_count, tod_json, ctx_json = result
            
            tod_acc = json.loads(tod_json) if tod_json else {}
            ctx_acc = json.loads(ctx_json) if ctx_json else {}
            
            # Update counts
            total += 1
            if accepted:
                acc_count += 1
            else:
                rej_count += 1
            
            acceptance_rate = acc_count / total if total > 0 else 0.0
            
            # Update time-of-day acceptance
            hour_key = str(hour)
            if hour_key not in tod_acc:
                tod_acc[hour_key] = {"total": 0, "accepted": 0}
            tod_acc[hour_key]["total"] += 1
            if accepted:
                tod_acc[hour_key]["accepted"] += 1
            
            # Update context acceptance
            if context_key not in ctx_acc:
                ctx_acc[context_key] = {"total": 0, "accepted": 0}
            ctx_acc[context_key]["total"] += 1
            if accepted:
                ctx_acc[context_key]["accepted"] += 1
            
            cursor.execute("""
                UPDATE suggestion_effectiveness
                SET total_suggestions = ?, accepted_count = ?, rejected_count = ?,
                    acceptance_rate = ?, last_suggested = ?,
                    time_of_day_acceptance = ?, context_acceptance = ?
                WHERE suggestion_type = ?
            """, (total, acc_count, rej_count, acceptance_rate, now.isoformat(),
                  json.dumps(tod_acc), json.dumps(ctx_acc), suggestion_type))
        else:
            # Create new record
            tod_acc = {str(hour): {"total": 1, "accepted": 1 if accepted else 0}}
            ctx_acc = {context_key: {"total": 1, "accepted": 1 if accepted else 0}}
            
            cursor.execute("""
                INSERT INTO suggestion_effectiveness
                (suggestion_type, total_suggestions, accepted_count, rejected_count,
                 acceptance_rate, last_suggested, time_of_day_acceptance, context_acceptance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (suggestion_type, 1, 1 if accepted else 0, 0 if accepted else 1,
                  1.0 if accepted else 0.0, now.isoformat(),
                  json.dumps(tod_acc), json.dumps(ctx_acc)))
        
        conn.commit()
        conn.close()
    
    def get_suggestion_effectiveness(self, suggestion_type: str) -> Dict[str, Any]:
        """Get effectiveness metrics for a suggestion type"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT total_suggestions, accepted_count, rejected_count, acceptance_rate,
                   time_of_day_acceptance, context_acceptance
            FROM suggestion_effectiveness
            WHERE suggestion_type = ?
        """, (suggestion_type,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "total": result[0],
                "accepted": result[1],
                "rejected": result[2],
                "acceptance_rate": result[3],
                "time_patterns": json.loads(result[4]) if result[4] else {},
                "context_patterns": json.loads(result[5]) if result[5] else {}
            }
        
        return {"total": 0, "accepted": 0, "rejected": 0, "acceptance_rate": 0.5}
