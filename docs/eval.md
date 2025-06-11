Here's a comprehensive guide on how to evaluate Ultron:

---

### **Phase 1: Define Your Evaluation Goals**

Before you start, clarify what you want to achieve with this evaluation:

1.  **Functional Correctness**: Does Ultron successfully identify known vulnerabilities and generate correct PoCs?
2.  **Accuracy (True Positives/False Positives)**: How often does it correctly find vulnerabilities (True Positives) versus raising false alarms (False Positives)?
3.  **Completeness (True Negatives/False Negatives)**: How often does it correctly identify clean codebases (True Negatives) versus missing known vulnerabilities (False Negatives)?
4.  **Quality of Output**: Are the generated PoCs executable and clear? Are the reports well-structured, accurate, and comprehensive?
5.  **Adherence to Principles**: Does the agent follow the `CORE OPERATING PRINCIPLE: PHASE-BASED ANALYSIS` and `ONE ACTION PER TURN` as defined in `system_prompt.md`? Does it correctly use its reasoning modes?
6.  **Efficiency**: How many tokens/turns does it take to complete a mission? How long does it run?
7.  **Robustness & Safety**: Does it handle errors gracefully? Does it attempt to violate sandbox constraints?

---

### **Phase 2: Prepare Your Test Environment & Data**

To ensure consistent and fair evaluation, set up your environment properly.

1.  **Dedicated Environment**: Use a consistent environment (e.g., a specific Docker container or VM) to run Ultron. This prevents variations due to host system changes.
2.  **Codebase Repository**:
    *   **Vulnerable Codebases**: Curate a collection of small-to-medium-sized codebases with **known, documented vulnerabilities**.
        *   **Diversity**: Include different languages (Python, Node.js, C/C++, Java), different vulnerability types (SQLi, XSS, RCE, insecure deserialization, path traversal, broken authentication), and different project types (web app, CLI tool, library, mobile app).
        *   **Complexity**: Start with simple, obvious vulnerabilities and gradually introduce more complex, multi-step flaws.
        *   **Ground Truth**: For each, clearly define the vulnerability, its location, the exact PoC, and the expected outcome.
    *   **Clean Codebases**: Include some codebases that are known to be free of significant security vulnerabilities (or at least free of the types you're testing for). This helps assess its True Negative rate.
    *   **Edge Cases**:
        *   Empty directories.
        *   Directories with only excluded files (`.git`, `node_modules`).
        *   Extremely large files or codebases (to test performance and timeout handling).
        *   Malformed code files (e.g., Python files with syntax errors).
3.  **Static/Dynamic Setup**:
    *   If evaluating **dynamic analysis**, ensure the `verification_target` (e.g., a vulnerable web service) is actually running and accessible *from the perspective of Ultron's sandbox* (though the sandbox initially restricts network access, you're simulating a scenario where it *would* have access if configured for dynamic mode). For robust dynamic testing, you might need to set up a test environment where the target application is accessible via a local network from Ultron's container.
    *   If evaluating **static analysis**, no external targets are needed.
4.  **Version Control**: Pin specific versions of Ultron's code, the LLM model, and test codebases for reproducibility.

---

### **Phase 3: Execution Strategy**

1.  **Run Multiple Times**: LLMs can be non-deterministic. Run Ultron on the same test case multiple times (e.g., 3-5 times) to observe consistency.
2.  **Automated Test Harness (Recommended)**:
    *   Write a script that iterates through your test cases.
    *   For each test case:
        *   Set up the environment (e.g., copy codebase to a temp directory).
        *   Call `AutonomousAgent.run()` with the appropriate `codebase_path`, `mission`, and `verification_target` (if applicable).
        *   Capture the `final_report` and the `log_file_path`.
        *   Store these results in a structured way (e.g., JSON file, database).
3.  **Manual Observation (for qualitative insights)**: For initial runs, or particularly tricky cases, actively watch the console output. This gives you insight into the agent's real-time reasoning (`💭 Thought:`, `🧠 Reasoning:`) and tool usage (`🛠️ Calling Tool:`, `🔬 Observation:`).

---

### **Phase 4: Evaluation Metrics & Criteria**

#### **A. Quantitative Metrics (Automated or Semi-Automated)**

1.  **Vulnerability Detection Accuracy**:
    *   For each vulnerable codebase:
        *   **True Positive (TP)**: Ultron correctly identifies the vulnerability AND provides a working PoC.
        *   **False Positive (FP)**: Ultron claims a vulnerability exists but it doesn't (or the PoC fails against a known clean version).
        *   **False Negative (FN)**: Ultron fails to identify a known vulnerability.
    *   For each clean codebase:
        *   **True Negative (TN)**: Ultron correctly states no vulnerability found.
    *   **Calculations**:
        *   **Accuracy**: (TP + TN) / (TP + TN + FP + FN)
        *   **Precision**: TP / (TP + FP) (How many of its reported findings are actually correct?)
        *   **Recall (Sensitivity)**: TP / (TP + FN) (How many of the actual vulnerabilities did it find?)
        *   **F1-Score**: 2 * (Precision * Recall) / (Precision + Recall) (Harmonic mean of precision and recall)
2.  **PoC Executability**:
    *   For each TP, attempt to execute the generated PoC manually or via automation.
    *   **Metric**: Percentage of working PoCs among TPs.
3.  **Resource Usage**:
    *   **Token Count**: Parse `log_file_path` to sum `prompt_token_count` and `candidates_token_count` for each run. This directly relates to LLM costs.
    *   **Execution Time**: Measure `start_time` to `end_time` for each `AutonomousAgent.run()` call.
    *   **Turns Taken**: Count the number of turns (`🤖 ULTRON TURN X`) in the log.
4.  **Sandbox Violation Attempts**:
    *   Search `log_file_path` for `Security violation. Attempted to access a path outside of the designated workspace.` or `Path traversal or absolute paths are not allowed.` This indicates the `ToolHandler` successfully prevented an attempted breach.
    *   **Metric**: Number of prevention events (higher is better, assuming the agent *tried* to do something bad).

#### **B. Qualitative Metrics (Manual Review is Essential)**

1.  **Report Quality**:
    *   **Adherence to Template**: Does the final report strictly follow the `Vulnerability Found` or `No Vulnerability Found` markdown template? (Automated regex checks can help here).
    *   **Clarity and Conciseness**: Is the description easy to understand? Is it verbose or to the point?
    *   **Accuracy of Description**: Does the description precisely match the vulnerability?
    *   **Completeness**: Does it include all required sections (Severity, CWE, Confidence, Attack Chain, Remediation)?
    *   **Confidence Statement**: Is the `Confidence` level (High/Medium) appropriately justified by the `Verification Status`?
2.  **PoC Quality**:
    *   **Clarity of Instructions**: Are the PoC instructions easy to follow?
    *   **Completeness of PoC**: Is the PoC fully provided and ready to use without further modification?
    *   **Relevance**: Does the PoC directly demonstrate the claimed vulnerability?
    *   **Efficiency**: Is the PoC concise and effective?
3.  **Analysis Depth & Reasoning Quality**:
    *   **Phase 1 Adherence**: Did the agent correctly identify the project type and tech stack in Phase 1? Did it articulate a logical PoC strategy *before* diving into vulnerability analysis?
    *   **Reasoning Mode Usage**: Did it switch between `ANALYTICAL REASONING MODE` and `REACTIVE REASONING MODE` appropriately?
    *   **Vulnerability Analysis Framework (Analytical Mode)**: When analyzing code, did it systematically go through Code Comprehension, Threat Modeling, Data Flow Tracing, Security Control Analysis, and Vulnerability Hypothesis?
    *   **Socratic Loop (Reactive Mode)**: When reacting to tool output, did it effectively use Observation, Self-Questioning, Hypothesis, and Plan & Sandbox Check?
    *   **Tool Selection Strategy**: Did it choose the most appropriate tool for the task (e.g., `list_functions` for Python functions instead of `grep` where `list_functions` is better)?
    *   **Problem-Solving**: When encountering errors (e.g., file not found, command failed), how effectively did it diagnose and recover? Did it use the recovery guidelines from `system_prompt.md`?
    *   **Sandbox Awareness**: Did its `Plan & Sandbox Check` correctly identify safe operations and adhere to sandbox constraints?

---

### **Phase 5: Analysis and Iteration**

1.  **Consolidate Results**: Collect all quantitative metrics and qualitative assessments for each test run.
2.  **Identify Patterns**:
    *   Are there certain types of vulnerabilities Ultron struggles with?
    *   Does it consistently make the same mistakes (e.g., wrong tool usage, poor error recovery)?
    *   Are its PoCs for a specific language consistently good or bad?
    *   Is it adhering to its internal "rules" (phases, reasoning modes, one action per turn)?
3.  **Debug & Improve**:
    *   **Review Logs**: The `ultron_run_*.log` files are your best friend. Trace the agent's thought process turn by turn. Compare its "Hypothesis" with the "Observation" from the tool output. Where did it go wrong? Did it misinterpret output? Did it try an invalid command?
    *   **Prompt Engineering**: If the agent consistently fails to adhere to its principles or makes logical errors, refine the `system_prompt.md`. Make instructions clearer, add more examples, or refine the reasoning frameworks.
    *   **Tool Enhancements**: If a tool repeatedly fails or doesn't provide enough useful information, consider enhancing it (e.g., `read_file_content` now provides parent directory contents on file not found).
    *   **Model Tuning**: If available, experiment with different model parameters (temperature, top_k, top_p) or even different LLM models.
4.  **Repeat**: After making improvements, run the evaluation again to see if the changes had the desired effect.

---

By systematically following these steps, you'll gain a deep understanding of Ultron's capabilities, limitations, and areas for improvement, allowing you to iterate and enhance its performance as a security analyst.