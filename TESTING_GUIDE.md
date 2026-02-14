# Lyra AI - Testing Guide

## Quick Start

Run the interactive demo:
```bash
.\venv\Scripts\activate
python demo.py
```

---

## Phase 2A: Infrastructure & Voice

### 1. Test Centralized State Manager
```bash
python -c "
from lyra.core.system_state import SystemStateManager
mgr = SystemStateManager()
mgr.set_active_project('TestProject')
print(f'Project: {mgr.get_active_project()}')
print(f'Trust: {mgr.get_trust_score():.2f}')
"
```

### 2. Test User Trust Modeling
```bash
python -c "
from lyra.core.user_profile import UserProfileManager
pm = UserProfileManager()
print(f'Trust Score: {pm.get_trust_score():.2f}')
print(f'Confirmation Threshold: {pm.get_confirmation_threshold():.2f}')
"
```

### 3. Test Voice Interface (TTS)
```bash
python tests/test_tts_simple.py
```

### 4. Test Enhanced Event Logging
```bash
python tests/test_phase2a_infrastructure.py
```

---

## Phase 2B: Workflow Engine

### 1. Test Workflow Storage
```bash
python tests/test_workflow_engine.py
```

### 2. Create a Workflow Manually
```python
from lyra.memory.workflow_store import WorkflowStore, Workflow, WorkflowStep
import uuid

store = WorkflowStore()
steps = [
    WorkflowStep(
        step_id=str(uuid.uuid4()),
        command={"intent": "open_app", "app": "notepad"},
        order=0,
        description="Open Notepad"
    )
]

workflow = Workflow(
    workflow_id=str(uuid.uuid4()),
    name="My Workflow",
    description="Test workflow",
    steps=steps
)

store.save_workflow(workflow)
print("Workflow saved!")

# List all workflows
workflows = store.list_workflows()
for wf in workflows:
    print(f"{wf['name']}: {wf['steps']} steps")
```

### 3. Test Workflow Risk Assessment
```python
from lyra.safety.workflow_risk_aggregator import WorkflowRiskAggregator
from lyra.memory.workflow_store import WorkflowStore

store = WorkflowStore()
aggregator = WorkflowRiskAggregator()

workflows = store.list_workflows()
if workflows:
    wf = store.load_workflow(workflows[0]['workflow_id'])
    risk = aggregator.calculate_workflow_risk(wf, user_trust_score=0.7)
    print(f"Risk: {risk.level} ({risk.score:.2f})")
    print(f"Requires confirmation: {risk.requires_confirmation}")
```

---

## Phase 2C: Risk & Safety

### 1. Test Risk Scoring
```bash
python tests/test_phase2cd.py
```

### 2. Test Different Risk Levels
```python
from lyra.safety.risk_scorer import RiskScorer
from lyra.reasoning.command_schema import Command

scorer = RiskScorer()

commands = [
    Command(intent="get_time", raw_input="what time is it", confidence=0.9),
    Command(intent="delete_file", raw_input="delete file", confidence=0.9),
    Command(intent="shutdown_system", raw_input="shutdown", confidence=0.9)
]

for cmd in commands:
    assessment = scorer.calculate_risk(cmd)
    print(f"{cmd.intent}: {assessment.risk_level.value} ({assessment.risk_score:.2f})")
```

### 3. Test Execution Logger
```python
from lyra.safety.execution_logger import ExecutionLogger
from lyra.reasoning.command_schema import Command

logger = ExecutionLogger()
cmd = Command(intent="create_file", raw_input="create test.txt", confidence=0.9)

before = logger.capture_before_state(cmd)
# ... simulate execution ...
after = logger.capture_after_state(cmd, "Success")

record = logger.log_execution(cmd, before, after, success=True)
print(f"Logged: {record.record_id}")
print(f"Rollback instructions: {record.rollback_instructions}")
```

---

## Phase 2D: Proactive Intelligence

### 1. Test Pattern Detection
```python
from lyra.reasoning.pattern_detector import PatternDetector

detector = PatternDetector()
patterns = detector.get_all_patterns()

print(f"Time patterns: {len(patterns['time_patterns'])}")
print(f"Sequence patterns: {len(patterns['sequence_patterns'])}")
print(f"Context patterns: {len(patterns['context_patterns'])}")
```

### 2. Test Proactive Suggestions
```python
from lyra.reasoning.proactive_agent import ProactiveAgent

agent = ProactiveAgent()

# Check if should be proactive
print(f"Proactive: {agent.should_be_proactive()}")

# Get suggestions
suggestions = agent.get_suggestions()
print(f"Suggestions: {len(suggestions)}")

# Get summary
summary = agent.get_suggestion_summary()
print(f"Acceptance rate: {summary['acceptance_rate']:.1%}")
```

### 3. Test Suggestion Cooldown
```python
from lyra.reasoning.proactive_agent import ProactiveAgent

agent = ProactiveAgent()

# Record rejection (increases cooldown)
agent.record_suggestion_response("test_suggestion", accepted=False)

# Record acceptance (decreases cooldown)
agent.record_suggestion_response("test_suggestion", accepted=True)

summary = agent.get_suggestion_summary()
print(summary)
```

---

## Integration Tests

### Run All Tests
```bash
# Phase 2A
python tests/test_phase2a_infrastructure.py

# Phase 2B
python tests/test_workflow_engine.py

# Phase 2C & 2D
python tests/test_phase2cd.py

# Voice (TTS only)
python tests/test_tts_simple.py
```

---

## Feature Verification Checklist

### Phase 2A ✅
- [ ] Centralized state manager working
- [ ] User trust score updating
- [ ] Event logging with confidence scores
- [ ] TTS speaking successfully

### Phase 2B ✅
- [ ] Workflows can be created
- [ ] Workflows can be saved/loaded
- [ ] Workflow risk assessment working
- [ ] Risk multiplies (not averages)

### Phase 2C ✅
- [ ] Risk scoring adapts to trust
- [ ] Confirmation thresholds dynamic
- [ ] Execution logging captures state
- [ ] Rollback instructions generated

### Phase 2D ✅
- [ ] Patterns detected from events
- [ ] Suggestions generated
- [ ] Cooldown prevents spam
- [ ] Trust gates proactivity

---

## Troubleshooting

### Voice Interface Issues
If TTS fails:
- Check audio devices are available
- Try different voice index
- Voice interface is optional for other features

### Database Issues
If event memory fails:
- Delete `lyra_memory.db` to reset
- Database will be recreated automatically

### Import Errors
Make sure virtual environment is activated:
```bash
.\venv\Scripts\activate
```

---

## Next Steps

After testing all features:
1. Review the walkthrough: `brain/.../walkthrough.md`
2. Check implementation plan: `brain/.../implementation_plan.md`
3. Review task completion: `brain/.../task.md`

**Phase 2 Status**: ✅ COMPLETE  
**All Features**: ✅ OPERATIONAL
