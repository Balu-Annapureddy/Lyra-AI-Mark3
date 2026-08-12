# Lyra — Local-First Personal AI Operating System

> **Status**: 🟡 Active Development / Experimental  
> **Target Identity**: Lyra  
> **License**: MIT License  

Lyra is a local-first personal AI operating system designed around semantic intent routing, safe automation, planning, context memory, and resource-aware model execution.

---

## Overview

Most AI assistant projects stop at calling an LLM endpoint and streaming natural language text back to the user. **Lyra** addresses the harder systems engineering problem: **How can an AI assistant translate intent into explainable, controlled, and safe actions on local hardware without exhausting system memory?**

Lyra implements an offline-first pipeline around the model rather than treating the LLM as the entire application. It integrates semantic routing, capability registration, policy engines, execution gateways, dry-run simulation, and multi-tier memory management.

---

## Why I Built It

Lyra is my first large, long-running systems project. I built it to explore local AI execution, systems architecture, security policy enforcement, and autonomous agent orchestration. Developing Lyra on a resource-constrained hardware setup (8GB RAM) forced resource management, lazy model loading, and idle unloading to be designed as first-class architectural concerns.

---

## Architecture & Data Flow

```mermaid
flowchart TD
    User([User Natural Language Input]) --> CLI[Interactive CLI / Entry Point]
    CLI --> Pipeline[Lyra Execution Pipeline]
    
    subgraph Cognitive Layer
        Pipeline --> IntentRouter[Embedding Intent Router]
        Pipeline --> SemanticEngine[Local Semantic Engine]
        Pipeline --> Escalation[LLM Escalation Advisor]
    end

    subgraph Governance & Safety
        IntentRouter --> PolicyEngine[Policy Engine & Capability Registry]
        PolicyEngine --> SafetyGate[Execution Gateway / Risk Scorer]
        SafetyGate --> DryRun{Simulation Mode?}
        DryRun -- Yes --> Sandbox[Sandbox Dry-Run Output]
        DryRun -- No --> ExecutionPlanner[Execution Planner & Orchestrator]
    end

    subgraph Execution & Monitoring
        ExecutionPlanner --> Tools[Controlled Tool Registry]
        Tools --> Memory[Session & Behavioral Memory]
        Tools --> Watchdog[Integrity Watchdog & Audit Ledger]
    end
```

For comprehensive technical specifications, see [`PROJECT_ARCHITECTURE.md`](PROJECT_ARCHITECTURE.md) and [`documentation/`](documentation/).

---

## Key Features & Systems Design

- **Local-First & Offline Intent Routing**: Uses `sentence-transformers` (`all-MiniLM-L6-v2`) and regex fallback rules for sub-millisecond intent extraction before attempting cloud escalation.
- **Resource-Aware Heavy Model Management**: Implements a strict single-heavy-model constraint (`memory_guard_min_free_gb: 0.8`, `max_ram_usage_gb: 4.0`), lazy component loading, and automatic idle model unloading to preserve memory.
- **Safety Policy & Capability Governance**: Enforces single-ownership intent mapping in `CapabilityRegistry`, pre-execution policy checks, risk scoring (`SAFE`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), and human confirmation gates.
- **Dry-Run Simulation Gateway**: Supports simulated dry-run execution (`simulate <command>`) allowing users to preview planned side effects before granting permission.
- **Autonomous Task Orchestration**: Decomposes complex multi-step goals into validated atomic steps managed by `ExecutionPlanner` and `TaskOrchestrator` with `RollbackManager` capabilities.

---

## Technical Stack

| Domain | Technologies |
|---|---|
| **Core & Runtime** | Python 3.10+, PyYAML, `psutil` |
| **Semantic & ML** | `sentence-transformers`, `numpy`, `scikit-learn` |
| **Cloud Escalation & LLM** | Google Generative AI (`gemini-1.5-flash`), Ollama API (`qwen2.5:3b`) |
| **Storage & Memory** | SQLite (`data/lyra_memory.db`), JSONL outcome logging |
| **Testing & Quality** | Python `unittest`, `logging` module |

---

## Repository Structure

```
Lyra/
├── config/
│   └── default_config.yaml    # System configuration & RAM guard thresholds
├── data/
│   └── tool_registry.json     # Declarative tool definitions
├── documentation/
│   ├── architecture.md        # Technical architecture specs
│   ├── design_decisions.md    # Architectural decision records (ADRs)
│   └── task_roadmap.md        # System roadmap and task progress
├── lyra/
│   ├── capabilities/          # Capability mapping & permission definitions
│   ├── cli/                   # Interactive CLI interface
│   ├── context/               # Context normalization & clarification service
│   ├── core/                  # Main execution pipeline & integrity watchdog
│   ├── execution/             # Execution gateway, rollback, & permissions
│   ├── llm/                   # Ollama & Gemini adapters, escalation router
│   ├── memory/                # Session memory & context compression
│   ├── orchestration/         # Autonomous task orchestrator
│   ├── planning/              # Step decomposition & execution planner
│   ├── policy/                # Policy engine & governance rules
│   ├── reasoning/             # Intent detection & command schemas
│   ├── safety/                # Risk scoring, simulation, & audit ledger
│   ├── semantic/              # Intent router & local semantic engine
│   └── tools/                 # Tool implementations (file, system, web)
├── tests/
│   └── test_pipeline.py       # Automated unit test suite
├── requirements.txt           # Dependency requirements
└── setup.py                   # Package setup & console scripts
```

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- 8GB RAM minimum (4GB available for Lyra runtime)

### Setup Virtual Environment

```bash
# Clone repository
git clone https://github.com/Balu-Annapureddy/Lyra.git
cd Lyra

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

---

## Usage

Start the interactive CLI loop:

```bash
# Using installed console script
lyra

# Or directly via module entry point
python -m lyra.main
```

### CLI Commands

```text
Commands:
  - Type your command naturally (e.g. create file notes.txt with content "Meeting notes")
  - Type 'simulate <command>' for dry-run simulation
  - Type 'history' to view recent command history
  - Type 'logs' to inspect execution audit logs
  - Type 'metrics' to view runtime performance statistics
  - Type 'help' for available command examples
  - Type 'exit' to quit
```

---

## Testing

Run the automated unit test suite using Python's standard `unittest` framework:

```bash
.\.venv\Scripts\python.exe -m unittest discover tests
```

---

## Current Limitations

- **Experimental Subsystems**: Task orchestration and multi-step reasoning are currently experimental and actively under development.
- **Resource Constraints**: High-capacity local LLMs (e.g. 7B+ models) are avoided on 8GB hardware in favor of lightweight 3B quantization or cloud escalation.
- **Tool Sandbox Boundaries**: File operations and system calls run under process-level permission checks rather than full hypervisor containerization.

---

## Roadmap

- [x] **Phase 1: Core Architecture & Safety** — Pipeline design, intent detection, capability registry, policy gate, dry-run simulation, unit testing.
- [ ] **Phase 2: Advanced Context & Memory** — Deep context compression, proactive memory retrieval, behavioral adaptation.
- [ ] **Phase 3: Robust Multi-Agent Orchestration** — Parallel subtask delegation with automated rollback verification.

---

## License

This project is licensed under the MIT License — see `setup.py` for metadata details.
