# Lyra — Local-First Personal AI Operating System

> **Status: 🟡 Active Development / Experimental**

Lyra is my long-running personal AI systems project: a **local-first, modular assistant** designed to understand user intent, reason about tasks, enforce safety policies, plan multi-step work, and execute approved actions through controlled tools.

This repository is **not presented as a finished product**. Lyra is being developed incrementally, and several subsystems remain experimental or incomplete. The project has also been designed around limited local hardware, so resource management and graceful degradation are first-class engineering concerns.

## Why Lyra?

Most personal-assistant projects stop at conversational responses. Lyra explores the harder systems problem:

**How can an AI assistant move from an instruction to a safe, explainable, controlled action?**

The project therefore focuses on the pipeline around an AI model rather than treating an LLM as the entire application.

## Current Architecture

```text
User Input
    │
    ▼
┌──────────────────────┐
│   Lyra Pipeline      │
│ normalization/session │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Semantic / Intent    │
│ Routing & Extraction │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Reasoning / Planning │
│   & Context          │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Policy & Safety      │
│     Gates            │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Execution Planner /  │
│   Task Orchestrator  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Controlled Tool      │
│      Registry        │
└──────────┬───────────┘
           ▼
      Approved Action
```

The current implementation includes dedicated modules for capabilities, context, core orchestration, execution, LLM management, memory, planning, policy, reasoning, safety, semantic routing, and metrics.

See [`PROJECT_ARCHITECTURE.md`](PROJECT_ARCHITECTURE.md) for the current technical architecture and data flow.

## Key Engineering Ideas

### Local-first execution

Lyra is designed to prefer local computation and only use external services when required. Heavy cognitive components are loaded lazily and resource-aware behavior is used to avoid unnecessarily exhausting system memory.

### Semantic intent routing

The current architecture uses an embedding-based intent router (`all-MiniLM-L6-v2`) for lightweight semantic classification, with resource checks before loading heavier components.

### Safety before execution

Actions do not go directly from natural-language input to arbitrary command execution. Lyra uses multiple governance layers, including capability/policy checks and an execution gateway that evaluates risk and can require human confirmation for dangerous operations.

### Multi-step planning

Complex goals can be decomposed into individual steps by the planning/orchestration layer. Each step is subject to safety verification rather than treating an entire generated plan as automatically trusted.

### Resource-aware AI

Lyra follows a **single-heavy-model** approach where practical: embedding and LLM components are managed to reduce memory pressure on constrained systems, with idle unloading and resource checks.

## Current Components

| Component | Purpose |
|---|---|
| `lyra/core` | Central pipeline and system coordination |
| `lyra/semantic` | Intent routing, parameter extraction and semantic validation |
| `lyra/reasoning` | Reasoning and decision support |
| `lyra/planning` | Task and execution planning |
| `lyra/orchestration` | Multi-step task execution |
| `lyra/policy` | Capability and policy enforcement |
| `lyra/safety` | Safety and risk controls |
| `lyra/execution` | Controlled execution gateway and tools |
| `lyra/capabilities` | Available assistant capabilities |
| `lyra/memory` | Persistent/session memory components |
| `lyra/context` | Context handling |
| `lyra/llm` | Local/LLM integration and resource management |
| `lyra/metrics` | Runtime/system metrics |

## Project Status

Lyra is **actively being developed**.

### Working foundations

- Modular Python architecture
- Central processing pipeline
- Semantic intent routing
- Parameter/feasibility validation
- Policy and capability checks
- Risk-aware execution gateway
- Human-in-the-loop safety controls
- Multi-step planning/orchestration foundations
- Tool registry architecture
- Session/context handling
- Resource-aware heavy-model management
- Technical architecture documentation

### Still evolving

- Broader real-world tool integrations
- More reliable autonomous workflows
- Voice interaction
- Device/application control
- Long-term memory behavior
- Learning and personalization
- More robust end-to-end testing
- Resource optimization and stability on constrained hardware

The project roadmap is intentionally iterative. A feature is not considered complete merely because a prototype works once; reliability, safety, resource usage and repeatability matter.

## Running Lyra

### Requirements

- Python 3.10+
- Windows, Linux or macOS
- Sufficient RAM for the optional embedding/LLM components

### Setup

```bash
git clone https://github.com/Balu-Annapureddy/Lyra-AI-Mark3.git
cd Lyra-AI-Mark3

python -m venv venv

# Windows
venv\\Scripts\\activate

# Linux/macOS
# source venv/bin/activate

pip install -r requirements.txt
```

The main runtime entry point is currently:

```bash
python -m lyra.main
```

> **Note:** Lyra is still under active development. Some capabilities may require additional local configuration or may not yet be stable across machines. Do not treat the current repository as a production-ready autonomous agent.

## Documentation

- [Project Architecture](PROJECT_ARCHITECTURE.md)
- [Documentation directory](documentation/)

Additional documentation is being expanded alongside the implementation so that architectural decisions and system behavior remain understandable as Lyra grows.

## Design Principles

1. **Local-first** — prefer local execution where practical.
2. **Permission-based automation** — actions should respect explicit capability boundaries.
3. **Safe by default** — risky operations should be blocked or require confirmation.
4. **Explainability** — important decisions and actions should be inspectable.
5. **Modularity** — subsystems should remain independently replaceable and testable.
6. **Resource awareness** — the assistant must account for the limitations of the machine it runs on.
7. **Incremental development** — experimental capabilities are clearly separated from reliable foundations.

## Roadmap Direction

Future development is focused on making Lyra more reliable rather than simply adding more features:

- strengthen end-to-end testing
- improve resource management and startup behavior
- expand safe tool integrations
- improve memory and context handling
- improve voice interaction
- improve application/device control
- strengthen observability and failure recovery
- evaluate autonomous workflows under strict safety constraints

## Why This Project Matters

Lyra is my first large, long-running systems project and an ongoing exploration of **AI agents, software architecture, automation, safety engineering and local AI**. The project has gone through multiple architectural iterations, and this repository represents the current Mark 3 implementation rather than a claim of a finished assistant.

## License

No open-source license has been selected yet. Until one is added, the repository should be treated as **all rights reserved**.

---

**Lyra is a work in progress — built to learn how to engineer an AI system, not just how to call an AI model.**
