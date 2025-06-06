# ⚡ ULTRON-AI: Perfection Protocol ⚡
_Advanced AI-powered code analysis with no strings attached._

**ULTRON-AI** is a command-line interface (CLI) that leverages Google's Gemini models to perform deep, context-aware security code reviews. It's designed to go beyond simple pattern matching by building a rich understanding of the codebase before sending it for AI analysis, dramatically improving the quality and accuracy of the results.

### Core Features
- **Hybrid Analysis Engine:** Uses a fast, precise AST parser for Python and a flexible LLM-powered analyzer for other languages to build call graphs and context.
- **Advanced AI Reasoning:** Employs **Chain of Thought (CoT)** and the **ReAct (Reasoning and Acting)** framework to perform multi-step investigations into complex vulnerabilities.
- **Rich, Actionable Output:** Provides results in multiple formats, including a human-readable pretty print, JSON for scripting, and SARIF for CI/CD integration.
- **Intelligent Caching:** Caches results to save time and API costs on repeated scans of unchanged code.
- **Flexible and Configurable:** Offers fine-grained control over the analysis through various command-line options, including file exclusions and finding ignores.

---

## 🚀 How to Use

### 1. Prerequisites
- **Python 3.10+**
- **Google Gemini API Key:** You must have a Gemini API key.
- Create a `.env` file in the root of the `ultron-ai` project directory:
```
GEMINI_API_KEY="YOUR_API_KEY_HERE"
```
Ultron will automatically load this key.

### 2. Installation
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/ultron-ai.git
    cd ultron-ai
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
3.  **Install dependencies:**
    *(Assuming you have a `requirements.txt` file)*
    ```bash
    pip install -r requirements.txt
    ```
    *(If not, install them manually: `pip install click rich python-dotenv google-genai`)*

### 3. Usage & Scenarios
All commands are run through the `main_cli.py` module.

#### Scenario 1: Basic Scan of a Single File
To quickly review a single file and see the output in the terminal.
```bash
python -m ultron.main_cli review -p path/to/your/file.js -l javascript
```
- `-p`: Specifies the path to the file.
- `-l`: Provides the language hint.

#### Scenario 2: Recursive Scan of a Directory
To scan an entire Java project, excluding test files, and output to a SARIF file.

```bash
python -m ultron.main_cli review -p path/to/java/project -l java -r -e "**/test/*" -o sarif > results.sarif
```

- `-r`: Enables recursive scanning.
- `-e`: Excludes files matching the glob pattern.
- `-o sarif`: Sets the output format to SARIF.

#### Scenario 3: Deep Dive Agent on a Python Project
To perform a standard review and then activate the ReAct agent to investigate complex findings. This uses the fast AST-based context analyzer.

```bash
python -m ultron.main_cli review -p path/to/python/project -l python --deep-dive
```

- `--deep-dive`: Activates the DeepDiveAgent after the initial scan. You will see the agent's "Thought" and "Action" process live in the terminal.

#### Scenario 4: LLM-Powered Context for Decompiled Code
When scanning non-Python code (like decompiled Java or .NET), the AST analyzer cannot be used. This command tells Ultron to use a preliminary LLM call to build the code context first.

```bash
python -m ultron.main_cli review -p path/to/decompiled/code -l java --llm-context
```

- `--llm-context`: Triggers the LLMCodeAnalyzer to perform a pre-analysis pass, which is then fed into the main review prompt.

#### Scenario 5: Full Verbose Mode for Debugging
To see the exact prompt sent to the model, the raw JSON response, and the step-by-step agent workflow.

```bash
python -m ultron.main_cli review -p path/to/project -l auto -r --deep-dive -v
```

- `-v`: Enables verbose mode.

## 🛠️ Technical Concepts
Ultron's power comes from how it prepares context before asking an LLM for a security review.

### Hybrid Analysis Engine
Ultron intelligently chooses the best way to understand your code.

- **Static AST Analysis (ProjectCodeAnalyzer):** For Python code, Ultron uses a built-in Abstract Syntax Tree (AST) parser. It walks the code's structure just like a compiler would, creating a highly accurate and fast map of all function definitions and calls. This process is free and happens locally.
- **LLM-Powered Context (LLMCodeAnalyzer):** For all other languages (or when the AST parser fails), you can use the `--llm-context` flag. This triggers a special, low-cost LLM call that is prompted to act as a code parser and return a text-based summary of functions and calls. This provides crucial context for languages where a static analyzer is not available.

### The ReAct Agent (DeepDiveAgent)
The `--deep-dive` flag activates a powerful agent built on two key principles: Chain of Thought (CoT) and the ReAct (Reasoning and Acting) framework.

#### 1. Chain of Thought (CoT)
This is the agent's "internal monologue." Instead of just outputting a final answer, the model is prompted to think step-by-step. This dramatically improves its ability to solve complex problems logically. You see this in the terminal as the agent's "Thought" process, where it plans its next move.

#### 2. ReAct Framework
This framework combines the agent's Reasoning (the CoT) with Acting (using tools). The agent works in a continuous loop:

- **Thought (CoT):** The agent analyzes the initial finding and its current knowledge and thinks, "What do I need to know to confirm this? I should read the configuration file."
- **Action:** The agent decides to use a tool, like `read_file_content('web.config')`.
- **Observation:** The tool's output (the file content) is fed back to the agent as new information.
- **Repeat:** The agent loops back to the Thought step, now with more information, and decides its next action. "Okay, the config file shows this is exposed. Now I need to check the function's source code."

This allows the agent to perform complex, multi-step research, just like a human security analyst.

## 📦 Module Breakdown

| Directory | Technical Purpose | Practical Role (What it does) |
|-----------|-------------------|-------------------------------|
| `ultron/` | The root package. | Contains the main entrypoint (`main_cli.py`) and the sub-packages. |
| `ultron/core/` | Cross-cutting concerns. | Holds the project's constants, caching logic, and the finding ignorer. |
| `ultron/engine/` | The "brain" of the application. | Contains the code for the initial AI review, the ReAct agent, and the code analyzers. |
| `ultron/models/` | Pydantic data models. | Defines the data structures for review findings (`data_models.py`) and SARIF (`sarif_models.py`). |
| `ultron/reporting/` | The "mouthpiece" of the application. | Contains the code for generating all user-facing output (pretty terminal or SARIF file). |

## ✅ Current Support
- **Languages for Review:** Python, JavaScript, Java, C++, C#, TypeScript, Go, Rust, PHP, Ruby, Swift, Kotlin, HTML, CSS, SQL.
- **Languages for Static Context Analysis:** Python
- **Languages for LLM-based Context Analysis:** All supported languages.
- **Output Formats:** Pretty Terminal, JSON, SARIF 2.1.0.

## ⚠️ Limitations
- **Cost & Speed:** Using `--llm-context` or `--deep-dive` involves multiple LLM API calls, which increases the time and monetary cost of a scan.
- **LLM Reliability:** The quality of the analysis is dependent on the performance of the underlying Gemini model. The tool includes a robust JSON repairer, but extremely malformed responses from the API can still cause failures.
- **Context Window:** Very large files or projects may exceed the LLM's context window, leading to incomplete analysis.

## 🔮 Future Improvements (TODO)
- **Integrate Tree-sitter:** Implement additional static analyzers for other major languages (like JavaScript/TypeScript and Java) to provide fast, free context without an LLM call.
- **Cache LLM-Generated Context:** Save the output of the `--llm-context` pass to avoid re-calculating it on subsequent runs.
- **Expand Agent Tooling:** Give the DeepDiveAgent more tools, such as the ability to run safe, sandboxed commands or perform web lookups for CVEs.
- **Configuration File:** Allow users to define settings like default models, ignore rules, and other options in a `.ultron.toml` file.