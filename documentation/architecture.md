# Lyra AI Operating System - Architecture Documentation

## Overview

Lyra is a local-first, modular personal AI operating system designed for real-world automation, device control, proactive reasoning, and human-like interaction.

**Core Philosophy**: Lyra is not a chatbot. It's an AI operating system that understands, plans, acts, learns, and explains.

## System Architecture

### Layered Design

```
┌─────────────────────────────────────────────────────────┐
│                 Interaction Layer                       │
│              (Text/Voice Interface)                     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│              Reasoning / Agent Layer                    │
│    (Intent Detection, Planning, Context Management)    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌──────────────┬──────────────┬──────────────┬────────────┐
│    Memory    │    Safety    │  Automation  │  Learning  │
│    Layer     │    Layer     │    Layer     │   Layer    │
└──────────────┴──────────────┴──────────────┴────────────┘
```

### Component Breakdown

#### 1. Core System (`lyra/core/`)

**Purpose**: Foundational utilities used across all layers

**Components**:
- `config.py` - Configuration management with YAML support
- `logger.py` - Structured logging system with rotation
- `state_manager.py` - Lyra operational state tracking (IDLE, LISTENING, THINKING, EXECUTING, WAITING_CONFIRMATION, ERROR)
- `exceptions.py` - Custom exception hierarchy

**Key Features**:
- Singleton pattern for state management
- Thread-safe state transitions
- Hierarchical configuration with dot notation access

---

#### 2. Reasoning Layer (`lyra/reasoning/`)

**Purpose**: Intent understanding, task planning, and context management

**Components**:

##### Command Schema (`command_schema.py`)
Central data structure for all Lyra operations. Every user request flows through this schema.

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
```

**Benefits**:
- Enables safety validation
- Supports comprehensive logging
- Facilitates learning from outcomes
- Provides explainability ("why did you do this?")

##### Intent Detector (`intent_detector.py`)
- Pattern-based intent classification
- Entity extraction
- Confidence scoring
- Extensible intent registry

##### Task Planner (`task_planner.py`)
- Decomposes intents into executable steps
- Handles dependencies
- Creates execution plans

##### Context Manager (`context_manager.py`)
- Tracks conversation history
- Manages active commands
- Stores user preferences
- Provides session context

---

#### 3. Memory Layer (`lyra/memory/`)

**Purpose**: Persistent storage of events, preferences, and knowledge

**Components**:

##### Memory Levels (`memory_level.py`)
Classification system for memories:
- `SHORT_TERM` - Current session, conversation context
- `LONG_TERM` - Persistent across sessions
- `PREFERENCE` - User preferences and settings
- `SYSTEM_EVENT` - System actions, errors, audit trail

##### Event Memory (`event_memory.py`)
- SQLite-based event storage
- Time-decayed retrieval
- Memory level filtering
- Automatic cleanup of old SHORT_TERM memories

##### Preference Store (`preference_store.py`)
- JSON-based preference storage
- Hierarchical preferences
- Default values

##### Memory Summarizer (`summarizer.py`)
- Event compression for long-term storage
- Key information extraction
- Foundation for future ML enhancements

---

#### 4. Automation Layer (`lyra/automation/`)

**Purpose**: Execute actions on PC and phone (future)

**Components**:

##### Task Executor (`task_executor.py`)
**Dry-Run Mode** - Simulates actions before execution:
```python
# Dry-run shows what would happen
result = executor.execute_command(command, dry_run=True)
# Shows: steps, side effects, estimated risk

# Then execute for real
result = executor.execute_command(command, dry_run=False)
```

**Benefits**:
- Prevents accidental destructive actions
- User can review before execution
- Builds trust through transparency

##### PC Controller (`pc_controller.py`)
Cross-platform PC automation:
- File operations (create, delete, open, search)
- Application control (launch, close)
- System commands (shutdown, restart)

##### Phone Controller (`phone_controller.py`)
Placeholder for future phone automation (Phase 2+)

---

#### 5. Safety Layer (`lyra/safety/`)

**Purpose**: Permission management, validation, and audit logging

**Components**:

##### Permission Manager (`permission_manager.py`)
Three permission levels:
- `STRICT` - Confirm MEDIUM, HIGH, CRITICAL actions
- `MODERATE` - Confirm HIGH, CRITICAL actions
- `RELAXED` - Confirm CRITICAL actions only

Risk-based confirmation system:
- `SAFE` - No confirmation (e.g., "what time is it?")
- `LOW` - No confirmation (e.g., "open calculator")
- `MEDIUM` - Confirm in STRICT mode (e.g., "create file")
- `HIGH` - Confirm in STRICT/MODERATE (e.g., "delete file")
- `CRITICAL` - Always confirm (e.g., "shutdown system")

##### Input Validator (`validator.py`)
- Detects dangerous patterns
- Validates filenames and paths
- Sanitizes input
- Prevents path traversal attacks

##### Safety Action Logger (`action_logger.py`)
- Comprehensive audit trail
- Separate log for safety-critical actions
- Tracks permissions, violations, executions

---

#### 6. Learning Layer (`lyra/learning/`)

**Purpose**: Track outcomes and improve over time

**Components**:

##### Outcome Tracker (`outcome_tracker.py`)
Phase 1: Basic tracking
- Records success/failure
- Tracks execution time
- Stores user feedback
- Calculates success rates
- Identifies error patterns

Future: Pattern detection, workflow optimization, preference learning

---

#### 7. Interaction Layer (`lyra/interaction/`)

**Purpose**: User communication interfaces

**Components**:

##### Text Interface (`text_interface.py`)
- Rich console output with colors
- State indicators (colored dots)
- Dry-run result display
- Error formatting

Future: Voice interface with Whisper (STT) and pyttsx3 (TTS)

---

## Data Flow

### Typical Command Flow

```
1. User Input
   ↓
2. Text Interface receives input
   ↓
3. Input Validator sanitizes and validates
   ↓
4. Intent Detector classifies intent + extracts entities
   ↓
5. Task Planner creates execution plan
   ↓
6. Context Manager adds context
   ↓
7. [DRY RUN] Task Executor simulates → shows results → asks confirmation
   ↓
8. Permission Manager checks permissions → may ask confirmation
   ↓
9. Task Executor executes command
   ↓
10. Result displayed to user
    ↓
11. Event Memory stores command
    ↓
12. Outcome Tracker records result
```

---

## Key Design Decisions

### 1. Command Schema as Central Structure
**Decision**: All operations flow through a unified `Command` object

**Rationale**:
- Single source of truth for each operation
- Enables comprehensive logging
- Supports learning from outcomes
- Facilitates explainability
- Simplifies safety validation

### 2. Dry-Run Mode by Default
**Decision**: Simulate before executing

**Rationale**:
- Prevents accidental destructive actions
- Builds user trust
- Allows review of complex operations
- Jarvis-level UX

### 3. Memory Level Classification
**Decision**: Tag memories as SHORT_TERM, LONG_TERM, PREFERENCE, SYSTEM_EVENT

**Rationale**:
- Prevents future refactoring pain
- Enables intelligent cleanup
- Supports different retention policies
- Minimal cost now, high value later

### 4. Explicit State Management
**Decision**: Track Lyra's state (IDLE, LISTENING, THINKING, EXECUTING, etc.)

**Rationale**:
- Improves voice UX
- Better debugging
- Easier AR integration later
- Clear system status

### 5. Local-First Architecture
**Decision**: SQLite for memory, JSON for preferences, local file logging

**Rationale**:
- Privacy and data ownership
- No cloud dependencies
- Fast and reliable
- Works offline

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Language | Python 3.10+ | Rich ecosystem, AI/ML libraries |
| Database | SQLite | Local, simple, no external DB |
| Config | YAML | Human-readable |
| Logging | Python logging + rotation | Built-in, reliable |
| Console UI | Rich | Beautiful terminal output |
| Voice (future) | Whisper + pyttsx3 | Local-first |

---

## Security & Safety

### Defense in Depth

1. **Input Validation** - Sanitize and validate all input
2. **Risk Classification** - Every intent has a risk level
3. **Permission System** - Configurable confirmation requirements
4. **Dry-Run Mode** - Simulate before executing
5. **Audit Logging** - Comprehensive action trail
6. **Path Validation** - Prevent traversal attacks
7. **Pattern Detection** - Block dangerous commands

### Safe by Default

- Dry-run mode enabled by default
- STRICT permission level by default
- All risky actions require confirmation
- Comprehensive logging enabled
- Input sanitization always active

---

## Extensibility

### Adding New Intents

```python
intent_detector.register_intent(
    "new_intent",
    [r"pattern1", r"pattern2"],
    RiskLevel.MEDIUM,
    {"entity_name": r"extraction_pattern"}
)
```

### Adding New Actions

1. Add action to `task_planner.py`
2. Implement in appropriate controller
3. Add to `task_executor._execute_action()`

### Adding New Memory Types

Memory levels are already defined - just use appropriate level when storing.

---

## Future Enhancements (Phase 2+)

- Voice interface with Whisper
- Phone automation via ADB
- Proactive suggestions
- Workflow optimization
- Advanced learning
- Vision capabilities
- AR visualization

---

## File Structure

```
lyra/
├── core/              # Config, logging, state, exceptions
├── interaction/       # Text/voice interfaces
├── reasoning/         # Intent, planning, context
├── memory/            # Events, preferences, summarization
├── automation/        # PC/phone controllers, executor
├── safety/            # Permissions, validation, audit
└── learning/          # Outcome tracking
```

---

**Version**: 0.1.0 (Phase 1)
**Last Updated**: 2026-02-10
