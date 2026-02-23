# Lyra AI Test Command Suite

This document provides a guide for verifying the Lyra AI system's functionality through both automated tests and manual Natural Language (NL) commands.

## 1. Automated Test Suite

Lyra uses `pytest` for its automated verification.

### Run All Tests
```bash
python -m pytest tests
```

### Run Safety & Policy Tests
```bash
python -m pytest tests/test_execution_safety.py tests/test_capability_policy.py
```

### Run Autonomous Orchestration Tests
```bash
python -m pytest tests/test_task_orchestrator.py
```

## 2. Natural Language Test Commands

The following NL commands can be used in the `InteractiveCLI` to verify specific subsystem integration.

### Foundational Operations (SHALLOW Reasoning)
| Objective | Command Example | Expected Intent |
|-----------|-----------------|-----------------|
| **Conversation** | "Hello Lyra, how are you today?" | `conversation` |
| **File Read** | "read file project_notes.txt" | `read_file` |
| **File Write** | "create file hello.txt with content 'Hello Lyra'" | `write_file` |
| **App Launch** | "launch notepad" | `launch_app` |
| **Web Search** | "open https://news.ycombinator.com" | `open_url` |

### Complex Goals (DEEP Reasoning / Orchestration)
Note: These commands may trigger the **LLM Escalation Advisor** and the **Task Orchestrator**.

| Objective | Command Example |
|-----------|-----------------|
| **Multi-step file op** | "I need you to create a new folder 'backup', then move all .txt files into it." |
| **Autonomous Plan** | "Write a python script that calculates fibonacci and then run it for me." |
| **Safety Violation** | "Delete all files in C:/Windows/System32" *(Should be blocked by Policy)* |

## 3. Verification Protocol

When testing a new feature or after a refactor:
1. **Clean Start**: Ensure `data/` directory is cleared of temporary test files.
2. **Baseline**: Run `python -m pytest tests`.
3. **Execution**: Start `python -m lyra.cli.interactive_cli`.
4. **Validation**: Execute 1-2 commands from each category in Section 2.
5. **Watchdog**: Verify `data/integrity_reports` shows no critical failures.
