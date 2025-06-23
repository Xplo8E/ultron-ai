# Ultron AI

> *Advanced AI-powered security code analysis with no strings attached.*

Ultron is a sophisticated, command-line static analysis tool that leverages Gemini models to identify security vulnerabilities in your codebase. It combines traditional static analysis techniques with advanced AI agent capabilities to deliver deep, context-aware insights.

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)


## 📋 Requirements

- Python 3.10 or higher
- Gemini API key
- Required Python packages (see `requirements.txt`)

## 🚀 Quick Start

### For Users (Recommended)

1.  **Install from PyPI:**
    ```bash
    pip install ultron-ai
    ```

2.  **Configure API Key:**
    Ultron requires a Google Gemini API key. Create a `.env` file in your project directory:
    ```
    # .env
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    ```
    Alternatively, export it as an environment variable (`export GEMINI_API_KEY="..."`).

### For Developers (Contributing)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/ultron-ai.git
    cd ultron-ai
    ```

2.  **Install in editable mode:**
    This will install the package and its dependencies, allowing you to edit the code directly.
    ```bash
    pip install -e .
    ```

3.  **Configure API Key:**
    Follow the same instructions as for users by creating a `.env` file in the cloned project's root.

## ✨ Features

*   **Dual-Mode Analysis**: Choose between a quick, comprehensive scan (`review`) or a deep, mission-driven investigation (`autonomous-review`).
*   **Autonomous Agent with Tools**: The `autonomous-review` mode unleashes a ReAct-based agent equipped with tools to read files, search the codebase, and execute shell commands to dynamically validate its findings.
*   **Structured, Verifiable Output**: The `review` mode enforces a strict JSON output, validated by Pydantic models. This ensures reliable, machine-readable results and supports conversion to the industry-standard **SARIF** format for CI/CD integration.

## How to Use

Ultron is operated via the command line.

### Mode 1: Comprehensive Review (will be deprecated)

Use the `review` command for a fast, comprehensive analysis of a file or project. It's ideal for getting a full picture of the codebase's health.

**Basic Review of a single file:**
```bash
python -m ultron.main_cli review -p path/to/your/file.py -l python
```

**Review an entire directory recursively:**
```bash
python -m ultron.main_cli review -p ./my-project/ -l javascript -r
```

**Advanced Review with Deep Dive and SARIF Output:**
This command will perform the standard review, then use a specialized agent to try and improve the PoCs for findings, and finally output the results to a SARIF file for CI/CD integration.

```bash
python -m ultron.main_cli review -p ./app/ --deep-dive -o sarif > results.sarif
```

### Mode 2: Autonomous Review (Power house of ultron)

Use the `autonomous-review` command to give the agent a specific, high-level goal. It's best for investigating a complex feature or hunting for a specific type of vulnerability.

**Example Mission: Find and prove an RCE vulnerability.**
```bash
python -m ultron.main_cli autonomous-review \
  -p ./vulnerable-app/ \
  -m "2.5-flash-05-20" \
  --mission "Your primary goal is to find a remote code execution (RCE) vulnerability. You must trace all user-controlled input to dangerous sinks like 'eval', 'exec', or 'subprocess.run'. You final report must include a working Proof of Concept."
```
The agent will log its entire thought process to a file in the `logs/` directory.

---

### How It Works: A Flow Diagram

**`review` command:**
`CLI Input` -> `Gather Files` -> `Generate Context (AST/LLM)` -> `Build Master Prompt` -> `engine.reviewer` -> `LLM (Gemini)` -> `JSON Response` -> `Pydantic Validation` -> `(Optional) engine.agent (Deep Dive)` -> `Filter Results` -> `Display/SARIF Output`

**`autonomous-review`:**

```
                   ┌────────────────────────────┐
                   │ Start: Receive Code & Task │
                   └────────────┬───────────────┘
                                ▼
                   ┌────────────────────────────┐
                   │ Understand Code & Strategy │
                   └────────────┬───────────────┘
                                ▼
                   ┌────────────────────────────┐
                   │  More Analysis Needed?     │
                   └───────┬────────────┬───────┘
                           │            │
                          Yes           No
                           │            │
                           ▼            ▼
                   ┌────────────┐   ┌──────────────┐
                   │ Use Tools  │   │ Consolidate  │
                   └────┬───────┘   └────┬─────────┘
                        ▼                ▼
              ┌─────────────────┐   ┌───────────────┐
              │ Vulnerability?  │   │ Final Report  │
              └──────┬──────┬───┘   └──────┬────────┘
                     │      │              ▼
                     |      |            ┌────┐
                     |    No             │ End│
                     |     |             └────┘
                    Yes    ▼             
                     |    More Analysis 
                     |
                     |
                     |
                     |
                     ▼
        ┌────────────────────────┐
        │ Create & Verify PoC    │
        └────────┬───────────────┘
                 ▼
         ┌───────────────┐
         │ Confirmed?    │
         └─────┬────┬────┘
               │    │
               |    |
               │    └─────> More Analysis
              Yes
               ▼
     ┌────────────────────────────┐
     │ Save & Continue or Go to   │
     │ Final Report if Max Turns  │
     └────────────────────────────┘
```
---
## 📋 TODOs

- [ ] Add support for Other Models
- [ ] Improve code navigation for large codebases
- [ ] Implement multi-step planning and reasoning
- [ ] Test against a large open source codebase
- [x] ~~Add basic documentation and examples~~ 

## 🤝 Contributing

We welcome contributions from the security community! To contribute:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request


## 📜 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

Ultron is intended for **educational and research purposes only**. Always obtain proper authorization before testing any system for vulnerabilities. The authors are not responsible for any misuse of this tool.

<p align="center">Made with ❤️ by Vinay</p>