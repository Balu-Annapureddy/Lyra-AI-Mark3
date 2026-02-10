# Lyra AI Operating System

A local-first, modular personal AI assistant focused on real-world automation, device control, proactive reasoning, and human-like interaction.

## 🎯 What is Lyra?

Lyra is **not a chatbot**. It's a personal AI operating system that can:
- ✅ Understand intent
- ✅ Plan tasks
- ✅ Act across devices
- ✅ Learn from outcomes
- ✅ Improve over time
- ✅ Explain its decisions

## 🏗️ Architecture

Lyra follows a **modular, layered architecture**:

```
┌─────────────────────────────────────┐
│      Interaction Layer              │  Voice/Text Interface
├─────────────────────────────────────┤
│      Reasoning/Agent Layer          │  Intent, Planning, Context
├─────────────────────────────────────┤
│  ┌─────────┬─────────┬───────────┐ │
│  │ Memory  │ Safety  │ Learning  │ │  Support Layers
│  └─────────┴─────────┴───────────┘ │
├─────────────────────────────────────┤
│      Automation Layer               │  PC/Phone Control
└─────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Windows/Linux/macOS

### Installation

```bash
# Clone the repository
git clone https://github.com/Balu-Annapureddy/Lyra-AI-Mark3.git
cd LyraAI-Mark3

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Lyra
python -m lyra.main
```

## 📚 Documentation

Comprehensive documentation is available in the `/documentation` folder:
- [Architecture Overview](documentation/architecture.md)
- [Design Decisions](documentation/design_decisions.md)
- [API Reference](documentation/api_reference.md)
- [Progress Log](documentation/progress_log.md)

## 🔐 Core Principles

1. **Local-first execution** - Cloud only where unavoidable
2. **Modular architecture** - No monolithic design
3. **Permission-based automation** - User control and safety
4. **Explainable actions** - Transparency in decision-making
5. **Safe-by-default behavior** - Security first
6. **Designed for expansion** - Future-ready

## 🎯 Current Phase: Phase 1 (v1)

**Status**: In Development

### Completed
- ✅ Architecture design
- ✅ Project structure
- 🔄 Core modules implementation

### In Progress
- Text interface
- Basic voice interface
- Intent detection
- PC automation
- Memory system
- Permission system

## 🛣️ Roadmap

- **Phase 1**: Core Foundation (Current)
- **Phase 2**: Agent & Learning
- **Phase 3**: Vision & Environment
- **Phase 4**: Personality & Growth

## 📝 License

[Add your license here]

## 🤝 Contributing

This is a personal project. Contributions guidelines will be added in future phases.

## 📧 Contact

[Add your contact information]

---

**Built with ❤️ for the future of personal AI**
