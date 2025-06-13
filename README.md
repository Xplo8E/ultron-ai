# Ultron AI

*Advanced AI-powered security code analysis with no strings attached.*

Ultron is a sophisticated, command-line static analysis tool that leverages Large Language Models (LLMs) to identify security vulnerabilities, bugs, and architectural issues in your codebase. It combines traditional static analysis techniques with advanced AI agent capabilities to deliver deep, context-aware insights.

## Core Features

*   **Dual-Mode Analysis**: Choose between a quick, comprehensive scan (`review`) or a deep, mission-driven investigation (`autonomous-review`).
*   **Autonomous Agent with Tools**: The `autonomous-review` mode unleashes a ReAct-based agent equipped with tools to read files, search the codebase, and execute shell commands to dynamically validate its findings.
*   **Advanced Context Generation**: Before analysis, Ultron pre-processes your code. For Python, it builds an Abstract Syntax Tree (AST) to understand cross-file function calls. For other languages, it uses a high-speed LLM to generate an architectural summary. This gives the primary AI core the context it needs to find complex, inter-file vulnerabilities.
*   **Structured, Verifiable Output**: The `review` mode enforces a strict JSON output, validated by Pydantic models. This ensures reliable, machine-readable results and supports conversion to the industry-standard **SARIF** format for CI/CD integration.
*   **Deep Dive Verification**: The optional `--deep-dive` flag spawns a focused sub-agent to take an initial, low-confidence finding and attempt to build a verifiable, high-quality Proof of Concept.
*   **Caching & Filtering**: Caches results to speed up repeated analyses and allows for fine-grained filtering of findings with `.ultronignore`-style rules.

## Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/ultron-ai.git
    cd ultron-ai
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure API Key:**
    Ultron requires a Google Gemini API key. Create a `.env` file in the project root:
    ```
    # .env
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    ```
    Alternatively, export it as an environment variable.

## How to Use

Ultron is operated via the command line.

### Mode 1: Comprehensive Review

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

### Mode 2: Autonomous Mission

Use the `autonomous-review` command to give the agent a specific, high-level goal. It's best for investigating a complex feature or hunting for a specific type of vulnerability.

**Example Mission: Find and prove an RCE vulnerability.**
```bash
python -m ultron.main_cli autonomous-review \
  -p ./vulnerable-app/ \
  -m "2.5-flash-05-20" \
  --mission "My primary goal is to find a remote code execution (RCE) vulnerability. I must trace all user-controlled input to dangerous sinks like 'eval', 'exec', or 'subprocess.run'. My final report must include a working Proof of Concept."
```
The agent will log its entire thought process to a file in the `logs/` directory.

### Understanding the Codebase: Architecture and Concepts

The Ultron AI project is an advanced static analysis security tool built on a sophisticated, multi-layered architecture. It goes beyond simple prompt-and-response by employing AI agents, traditional code analysis techniques, and structured data handling to deliver high-quality security reviews.

At its core, the project is divided into two main operational modes, accessible via the CLI: `review` and `autonomous-review`.

#### Key Concepts & Architectural Patterns

1.  **Agent-based Architecture**: The system utilizes AI agents as the primary drivers of analysis.
    *   **Orchestrator Agent (`review` command)**: This is a high-level agent that follows a structured, one-shot process. It gathers context, builds a comprehensive prompt, and expects a single, detailed JSON response.
    *   **Deep Dive Agent (`--deep-dive` flag)**: A specialized, focused sub-agent spawned by the `review` command. Its purpose is to take a single, unverified vulnerability and use a ReAct-style loop to confirm its exploitability and generate a better Proof-of-Concept.
    *   **Autonomous Agent (`autonomous-review` command)**: This is a true autonomous agent that operates in a multi-turn loop. It is given a high-level "mission" and uses a set of tools to explore the codebase, form hypotheses, and test them until it achieves its goal.

2.  **ReAct Framework (Reason + Act)**: The `autonomous-review` mode is a clear implementation of the ReAct pattern. The agent's "constitution" (`system_prompt.md`) explicitly instructs it to:
    *   **Think/Reason**: Analyze the current situation and form a hypothesis.
    *   **Act**: Choose and execute a single tool to test the hypothesis.
    *   **Observe**: Process the tool's output to inform the next cycle.
    This loop allows it to tackle complex, multi-step problems that a single prompt cannot solve.

3.  **Advanced Context Generation**: A key innovation of this tool is its ability to provide the LLM with rich, pre-analyzed context, which drastically improves the quality of its findings.
    *   **Static AST Analysis (`engine/code_analyzer.py`)**: For Python code, it uses the built-in `ast` library to parse the entire project, building a map of function definitions, calls, and inter-file relationships. This context is prepended to the code, allowing the LLM to "see" the call graph.
    *   **LLM-based Analysis (`engine/llm_code_analyzer.py`)**: For non-Python code, it uses a smaller, faster LLM in a pre-analysis step to generate a high-level architectural summary, serving a similar purpose to the AST analysis.

4.  **Tools on an LLM (Function Calling)**: Both the Deep Dive and Autonomous agents are provided with a "toolbox" via the Gemini API's function calling feature. The `autonomous/tool_handler.py` acts as a crucial safety and abstraction layer, defining the tools, validating their inputs (e.g., preventing path traversal), and executing the underlying functions.

5.  **Structured Data & Validation (Pydantic)**: The `review` mode does not rely on parsing unstructured markdown. It forces the LLM to return a strict JSON object, which is immediately validated against Pydantic models (`models/data_models.py`). This ensures the output is reliable, predictable, and can be programmatically processed. The `clean_json_response` function adds robustness by fixing common LLM syntax errors.

6.  **Standardized Reporting (SARIF)**: The tool can convert its native JSON output into the industry-standard SARIF format (`reporting/sarif_converter.py`). This allows Ultron's results to be seamlessly integrated into CI/CD pipelines and security dashboards (like GitHub's code scanning).

7.  **Modularity and Separation of Concerns**: The codebase is well-organized:
    *   `main_cli.py`: Handles user interaction and orchestrates the different modes.
    *   `engine/`: Contains the core logic for the one-shot `review` mode and the focused `DeepDiveAgent`.
    *   `autonomous/`: Contains the logic for the general-purpose, mission-driven `AutonomousAgent` and its tools.
    *   `core/`: Holds shared components like constants, caching, and result filtering.
    *   `models/`: Defines the data schemas (Pydantic).
    *   `reporting/`: Handles all user-facing output, from pretty terminal printing to SARIF generation.

---

### How It Works: A Flow Diagram

**`review` command:**
`CLI Input` -> `Gather Files` -> `Generate Context (AST/LLM)` -> `Build Master Prompt` -> `engine.reviewer` -> `LLM (Gemini)` -> `JSON Response` -> `Pydantic Validation` -> `(Optional) engine.agent (Deep Dive)` -> `Filter Results` -> `Display/SARIF Output`

**`autonomous-review` command:**
`CLI Input` -> `autonomous.agent` -> `[Loop Start]` -> `Think (Reason)` -> `Choose Tool (Act)` -> `tool_handler` -> `Execute Tool` -> `Get Observation` -> `LLM (Gemini)` -> `[Loop End]` -> `Generate Final Report`

---
