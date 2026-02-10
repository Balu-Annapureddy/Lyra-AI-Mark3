# Lyra AI Operating System - Design Decisions

This document explains key design decisions made during Lyra's development and the rationale behind them.

---

## 1. Command Schema as Central Data Structure

### Decision
Create a unified `Command` dataclass that flows through the entire system.

### Rationale
- **Single Source of Truth**: Every operation has one canonical representation
- **Explainability**: Command object contains all information needed to explain "why did you do this?"
- **Safety Integration**: Risk level and confirmation requirements are part of the command
- **Learning Foundation**: Tracking outcomes becomes straightforward
- **Debugging**: Complete command history with all metadata

### Implementation
```python
@dataclass
class Command:
    command_id: str
    raw_input: str
    intent: str
    entities: Dict[str, Any]
    confidence: float
    risk_level: RiskLevel
    requires_confirmation: bool
    execution_plan: List[Dict[str, Any]]
    context: Dict[str, Any]
    status: str
    result: Optional[Any]
    error: Optional[str]
    user_feedback: Optional[str]
    execution_time_ms: Optional[float]
```

### Benefits Realized
- Safety validation is straightforward
- Audit logging is comprehensive
- Learning from outcomes is simple
- Explainability is built-in

---

## 2. Dry-Run Mode by Default

### Decision
Simulate actions before executing them, showing users what would happen.

### Rationale
- **Safety**: Prevents accidental destructive actions
- **Trust**: Users can review before approving
- **Transparency**: Clear understanding of what Lyra will do
- **Jarvis-Level UX**: Sophisticated AI assistant behavior

### Implementation
```python
# First: dry-run simulation
result = executor.execute_command(command, dry_run=True)
# Shows: steps, side effects, estimated risk

# Then: user confirmation
response = input("Execute this command? (yes/no): ")

# Finally: actual execution
if approved:
    result = executor.execute_command(command, dry_run=False)
```

### Trade-offs
- **Pro**: Much safer, builds trust
- **Con**: Extra step for every command
- **Mitigation**: Can be disabled for trusted operations later

---

## 3. Memory Level Classification

### Decision
Tag all memories with levels: SHORT_TERM, LONG_TERM, PREFERENCE, SYSTEM_EVENT

### Rationale
- **Future-Proofing**: Prevents painful refactoring later
- **Intelligent Cleanup**: Different retention policies per level
- **Retrieval Optimization**: Filter by importance
- **Minimal Cost Now**: Just an enum tag

### Implementation
```python
class MemoryLevel(Enum):
    SHORT_TERM = "short_term"      # Current session
    LONG_TERM = "long_term"         # Persistent
    PREFERENCE = "preference"       # User settings
    SYSTEM_EVENT = "system_event"   # Audit trail
```

### Future Benefits
- Automatic cleanup of SHORT_TERM after 30 days
- LONG_TERM memories persist indefinitely
- PREFERENCES can be backed up separately
- SYSTEM_EVENTS for compliance/debugging

---

## 4. Explicit State Management

### Decision
Track Lyra's operational state explicitly (IDLE, LISTENING, THINKING, EXECUTING, WAITING_CONFIRMATION, ERROR)

### Rationale
- **Voice UX**: Users know when Lyra is listening
- **Debugging**: Clear system status at all times
- **AR Integration**: Future AR UI can show state visually
- **Error Handling**: Proper state recovery

### Implementation
```python
class LyraState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_CONFIRMATION = "waiting_confirmation"
    ERROR = "error"
```

### Benefits
- Text interface shows colored state indicator
- State history for debugging
- Thread-safe state transitions

---

## 5. Local-First Architecture

### Decision
Use SQLite for memory, JSON for preferences, local file logging. No cloud dependencies.

### Rationale
- **Privacy**: User data stays on their machine
- **Reliability**: No network dependencies
- **Speed**: Local operations are fast
- **Offline**: Works without internet
- **Ownership**: User controls their data

### Trade-offs
- **Pro**: Privacy, speed, reliability
- **Con**: No cross-device sync (yet)
- **Future**: Optional cloud sync for those who want it

---

## 6. Permission Levels (Strict, Moderate, Relaxed)

### Decision
Three configurable permission levels with different confirmation requirements.

### Rationale
- **Flexibility**: Users can choose their safety level
- **Learning Curve**: Start strict, relax as trust builds
- **Context-Aware**: Different levels for different use cases

### Implementation
```python
class PermissionLevel(Enum):
    STRICT = "strict"      # Confirm MEDIUM, HIGH, CRITICAL
    MODERATE = "moderate"  # Confirm HIGH, CRITICAL
    RELAXED = "relaxed"    # Confirm CRITICAL only
```

### Default
STRICT mode by default. Users can change after they're comfortable.

---

## 7. Pattern-Based Intent Detection (Phase 1)

### Decision
Use regex patterns for intent detection instead of ML models in Phase 1.

### Rationale
- **Simplicity**: Easy to understand and debug
- **No Training**: Works immediately
- **Extensible**: Easy to add new intents
- **Deterministic**: Predictable behavior
- **Fast**: No model loading time

### Future Enhancement
Phase 2+ can add ML-based intent detection while keeping patterns as fallback.

---

## 8. Modular Layer Architecture

### Decision
Separate concerns into distinct layers: Core, Interaction, Reasoning, Memory, Automation, Safety, Learning

### Rationale
- **Maintainability**: Each layer has clear responsibility
- **Testability**: Layers can be tested independently
- **Extensibility**: New features fit into existing layers
- **Team Scalability**: Different people can work on different layers

### Layer Responsibilities
- **Core**: Config, logging, state, exceptions
- **Interaction**: User communication
- **Reasoning**: Intent, planning, context
- **Memory**: Storage and retrieval
- **Automation**: Action execution
- **Safety**: Permissions and validation
- **Learning**: Outcome tracking

---

## 9. Cross-Platform PC Controller

### Decision
Support Windows, Linux, macOS with platform-specific implementations.

### Rationale
- **Portability**: Lyra works on any OS
- **Native Feel**: Uses OS-specific commands
- **Reliability**: Platform-specific code is more reliable

### Implementation
```python
if self.os_type == "Windows":
    os.startfile(filepath)
elif self.os_type == "Darwin":  # macOS
    subprocess.run(["open", filepath])
else:  # Linux
    subprocess.run(["xdg-open", filepath])
```

---

## 10. Phone Controller as Abstracted Interface

### Decision
Create placeholder phone controller in Phase 1, full implementation in Phase 2.

### Rationale
- **Scope Control**: Phase 1 focuses on PC automation
- **Architecture Ready**: Interfaces defined, easy to implement later
- **No Wasted Effort**: Don't build what we won't test yet

### Future Implementation
- Android: ADB integration
- iOS: Shortcuts API

---

## 11. Rich Console Output

### Decision
Use `rich` library for beautiful terminal output instead of plain print statements.

### Rationale
- **UX**: Professional, polished interface
- **Clarity**: Colors and formatting improve readability
- **State Indicators**: Colored dots show Lyra's state
- **Debugging**: Easier to spot errors and warnings

---

## 12. YAML for Configuration

### Decision
Use YAML instead of JSON or TOML for configuration files.

### Rationale
- **Human-Readable**: Easy to edit manually
- **Comments**: Supports inline documentation
- **Hierarchical**: Natural for nested config
- **Standard**: Widely used in AI/ML projects

---

## 13. SQLite for Memory

### Decision
Use SQLite instead of PostgreSQL, MongoDB, or in-memory storage.

### Rationale
- **Local-First**: No server required
- **Reliable**: Battle-tested database
- **Fast**: Good enough for personal use
- **Simple**: Single file, no setup
- **SQL**: Powerful queries when needed

---

## 14. Separate Safety Audit Log

### Decision
Maintain a separate log file specifically for safety-critical actions.

### Rationale
- **Compliance**: Easy to audit all safety-related events
- **Debugging**: Quickly find permission issues
- **Trust**: Transparent record of all actions
- **Separation**: Don't mix with general logs

---

## 15. Outcome Tracking from Day 1

### Decision
Track command outcomes even in Phase 1, before ML implementation.

### Rationale
- **Data Collection**: Start collecting data immediately
- **Foundation**: Infrastructure ready for ML later
- **Analytics**: Basic success rates available now
- **Learning**: Identify error patterns early

---

## Rejected Alternatives

### Why Not Use LangChain?
- **Complexity**: Too heavy for Phase 1
- **Control**: Want full control over pipeline
- **Learning**: Better to understand fundamentals first
- **Future**: Can integrate later if needed

### Why Not Cloud-Based?
- **Privacy**: User data should stay local
- **Reliability**: No network dependencies
- **Cost**: No cloud bills
- **Ownership**: User controls their data

### Why Not Voice-First in Phase 1?
- **Scope**: Text interface is simpler to test
- **Debugging**: Easier to debug text than voice
- **Foundation**: Get core logic right first
- **Phase 2**: Voice will be added with proper testing

---

## Lessons Learned

### What Worked Well
1. Command Schema - Excellent decision, used everywhere
2. Dry-Run Mode - Users love seeing what will happen
3. Memory Levels - No regrets, future-proof
4. State Manager - Debugging is much easier

### What We'd Do Differently
1. Could have added basic voice in Phase 1 (but scope control was good)
2. More unit tests from the start (added in testing phase)

---

**Version**: 0.1.0 (Phase 1)
**Last Updated**: 2026-02-10
