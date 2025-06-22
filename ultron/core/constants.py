# src/ultron/constants.py

AVAILABLE_MODELS = {
    # Models available on the free tier
    "2.0-flash-lite": "gemini-2.0-flash-lite",             # For LLM-based context analysis
    "2.0-flash": "gemini-2.0-flash",                 # Good for the main review
    "2.5-flash-05-20": "gemini-2.5-flash-preview-05-20",  # Best free model for the agent
    "2.5-flash-04-17": "gemini-2.5-flash-preview-04-17",  # Best free model for the agent
        "2.5-flash": "gemini-2.5-flash",
    "2.5-flash-lite":"gemini-2.5-flash-lite-preview-06-17",
    "2.5-pro":"gemini-2.5-pro",
    "2.5-pro-06-05":"gemini-2.5-pro-preview-06-05",
    "2.5-pro-05-06":"gemini-2.5-pro-preview-05-06"
}
# 2.5-flash-05-20 is the best free model for the agent
# Set the default for the main 'review' command to the best free general-purpose model
DEFAULT_MODEL_KEY = "2.5-flash"

# --- NEW: Set of models known to support the 'thinking' feature ---
MODELS_SUPPORTING_THINKING = {
    "2.5-flash-05-20",
    "2.5-flash-04-17",
    "2.5-flash",
    "2.5-flash-lite",
    "2.5-pro",
    "2.5-pro-06-05",
    "2.5-pro-05-06"
}

SUPPORTED_LANGUAGES = {
    "python": "Python", "javascript": "JavaScript", "java": "Java",
    "c++": "C++", "csharp": "C#", "typescript": "TypeScript",
    "go": "Go", "rust": "Rust", "php": "PHP", "ruby": "Ruby",
    "swift": "Swift", "kotlin": "Kotlin", "html": "HTML",
    "css": "CSS", "sql": "SQL", "auto": "Detect/Handle Multiple"
}

# For main_cli.py to find files if language is specified for a directory
LANGUAGE_EXTENSIONS_MAP = {
    "python": [".py", ".pyw"], "javascript": [".js", ".jsx", ".mjs"],
    "java": [".java"], "c++": [".cpp", ".hpp", ".cxx", ".hxx", ".cc", ".hh"],
    "csharp": [".cs"], "typescript": [".ts", ".tsx"], "go": [".go"],
    "rust": [".rs"], "php": [".php", ".phtml"], "ruby": [".rb"],
    "swift": [".swift"], "kotlin": [".kt", ".kts"], "html": [".html", ".htm"],
    "css": [".css"], "sql": [".sql"],
}

# Define placeholders to satisfy linter, these will be overridden by .format()
user_framework_context_section = "{user_framework_context_section}"
user_security_requirements_section = "{user_security_requirements_section}"
user_context_section = "{user_context_section}"
frameworks_libraries_list = "{frameworks_libraries_list}"
language = "{language}" # If language is also used directly in the f-string template
code_batch_to_review = "{code_batch_to_review}"

# --- NEW PROMPT TEMPLATE FOR LLM-BASED ANALYZER ---

LLM_ANALYZER_PROMPT_TEMPLATE = """
You are a senior software architect. Your task is to analyze a batch of code files and generate a high-level architectural summary. This summary will be prepended to a later, more detailed security review prompt to provide essential context.

**Your Goal:**
For each file in the batch, provide a concise summary that explains:
1.  **Purpose:** What is the primary role or responsibility of this file? (e.g., "This file defines the main Android Activity," "This is a utility module for database connections," "This XML file configures application permissions and components.")
2.  **Key Components:** What are the major classes, functions, or components defined in this file?
3.  **Inter-file Relationships:** How does this file likely interact with other files in the batch? Mention specific function calls, class instantiations, or data flows that connect them. (e.g., "The `MainActivity.java` file reads the `url_to_load` intent and uses it in a WebView, which is configured by `AndroidManifest.xml` to be an exported activity.")

**Critical Output Format Requirements:**
-   Produce a single, concise text block.
-   Use clear headings for each file.
-   DO NOT use markdown code blocks (```).
-   Your summary should be descriptive and focus on the *'why'* and *'how'* of the code, not just a list of function names.

**Example Output Format:**
# === File: src/com/example/app/MainActivity.java ===
# Purpose: Defines the main entry point activity for the Android application. It is responsible for creating and managing a WebView component.
# Key Components:
#   - Class `MainActivity`: The main activity.
#   - Method `onCreate()`: Initializes the WebView, enables JavaScript, and loads a URL.
#   - Class `JSBridge`: An inner class exposed to JavaScript, allowing the WebView to communicate with native Java code.
# Relationships:
#   - This activity's ability to be launched by other apps is controlled by the `android:exported="true"` attribute in `AndroidManifest.xml`.
#   - It receives a URL from an `Intent` extra named `url_to_load`, indicating it's designed to be launched with external data.

# === File: AndroidManifest.xml ===
# Purpose: This is the core configuration file for the Android application. It declares permissions, components, and application-level settings.
# Key Components:
#   - `<application>`: Defines global app settings like `allowBackup`.
#   - `<activity>`: Declares the `MainActivity`.
# Relationships:
#   - The `android:exported="true"` attribute for `.MainActivity` makes it accessible to other applications on the device, which is a critical piece of context for analyzing `MainActivity.java`.


The code batch to analyze begins now:
{code_batch_to_analyze}
"""


MULTI_FILE_INPUT_FORMAT_DESCRIPTION = """
The code to review will be provided in a special multi-file format. Each file is demarcated by its relative path, followed by '========' and then its content.

**IMPORTANT: Preceding Context Blocks**

Before the actual content of a file, you may find a **context block**. This block, starting with `# ---`, provides critical architectural information or summaries of related code. **You MUST use this context** to understand dependencies, data flow, and the overall structure of the application. This context is essential for identifying complex, inter-file vulnerabilities.

There are two types of context blocks you might see:

1.  **`# --- Full Project Context for file...` (For Python files):**
    This block is generated by a static analyzer. It details the functions defined within the file, who calls them from other parts of the project, and provides summaries of functions that this file calls.
    
    *Example of a Python context block:*
    ```
    # --- Full Project Context for utils/helpers.py ---
    # This file defines the following functions:
    #   - Function: `utils.helpers.process_data`
    #     - Called By: ['api.routes.user_endpoint']
    #
    # This file makes calls to the following functions defined elsewhere:
    #   - Function: `database.core.connect_db` (defined in database/core.py)
    #       Function: def connect_db(connection_string):
    #         Docstring: "Connects to the primary database."
    # --- End of Project Context ---
    ```

2.  **`# --- LLM-Generated Project Context ---` (For other languages):**
    This block is a high-level architectural summary generated by a separate AI model. It describes the purpose of each file and how they interact.

    *Example of an LLM-generated context block:*
    ```
    # --- LLM-Generated Project Context ---
    # === File: src/com/example/app/MainActivity.java ===
    # Purpose: Defines the main entry point activity for the application.
    # Relationships: This activity is configured as 'exported' in AndroidManifest.xml, making it accessible to other apps.
    # === File: AndroidManifest.xml ===
    # Purpose: The core configuration file for the Android application.
    # --- End of LLM-Generated Project Context ---
    ```

After the optional context block, the actual file content will begin, clearly marked with `# --- Start of actual file content for...`.

Your analysis must address each file individually within your JSON response, associating all findings with the correct `filePath`.
"""

DEFAULT_REVIEW_PROMPT_TEMPLATE = """
You are an expert security code reviewer. Your primary goal is to identify **valid, practically exploitable vulnerabilities** with **verifiable Proofs of Concept (POCs)**.

Your analysis must be meticulous, with an exceptionally low false-positive rate. If you are not highly confident that a flaw is exploitable, do not report it as a high-confidence vulnerability.

A 'valid vulnerability' is a flaw that can be demonstrably exploited to cause a clear negative security impact (e.g., data exfiltration, unauthorized access/modification, RCE, DoS). It is NOT a stylistic issue, a general best practice not followed (unless its omission DIRECTLY leads to an exploitable condition), or a theoretical weakness without a clear exploit path.

**Requirements for Proofs of Concept (POCs):**
-   Write complete, executable code (e.g., `curl` commands, Python scripts, JavaScript payloads).
-   Include exact endpoints, parameters, and payload values needed.
-   Specify HTTP methods, headers, and request/response formats where applicable.
-   Show both the malicious input AND the expected malicious output.
-   If chaining multiple steps, number them and show the output of each step.
-   For client-side exploits, provide the exact HTML/JS payload and how to deliver it.

{MULTI_FILE_INPUT_FORMAT_DESCRIPTION}

{user_context_section}
{user_framework_context_section}
{user_security_requirements_section}

**CRITICAL RESPONSE FORMAT REQUIREMENTS:**
1.  Your ENTIRE response MUST be a SINGLE, VALID JSON object.
2.  DO NOT output ANY text, commands, code, or explanations outside of the JSON structure.
3.  DO NOT use markdown code blocks or any other formatting; output ONLY the raw JSON object.
    - Specifically, the values for fields like `proofOfConceptCodeOrCommand` must be flat strings containing only the code, without any ```java or ``` fences.
4.  ALL findings, including POCs and dangerous commands, MUST be placed in their appropriate JSON fields.
5.  Your response MUST start with `{{` and end with `}}` with no other text before or after.
6.  Exploit code/commands go in the `proofOfConceptCodeOrCommand` field. Explanations go in the `proofOfConceptExplanation` field.

**IMPORTANT SECURITY RULES:**
1.  NEVER output raw shell commands, injection payloads, or exploit code directly in the response.
2.  ALL potentially dangerous operations MUST be wrapped in JSON and include clear warnings.
3.  For command injection vulnerabilities, use safe example commands (e.g., `echo "test"` instead of destructive commands).
4.  Include clear warnings and safety considerations for any dangerous POCs.
5.  Focus on demonstrating the vulnerability exists without causing harm.

**JSON SCHEMA (Follow This Structure With Precision):**
{{
  "overallBatchSummary": "string | null // Brief summary of findings across all files",
  "fileReviews": [
    {{
      "filePath": "string // Relative path of the file",
      "languageDetected": "string | null // Language detected for this file",
      "summary": "string // Brief summary of findings for this file",
      "highConfidenceVulnerabilities": [
        {{
          "type": "string // e.g., 'Security', 'Bug'",
          "confidenceScore": "string | null // e.g., 'High', 'Medium'",
          "severityAssessment": "string | null // e.g., 'Critical', 'High', 'Medium'",
          "line": "string | number // Line number or range where issue was found",
          "description": "string // Detailed description of the vulnerability",
          "impact": "string // Clear explanation of potential impact",
          "proofOfConceptCodeOrCommand": "string | null // Code/command to demonstrate exploit. For dangerous operations, include clear warnings.",
          "proofOfConceptExplanation": "string | null // Step-by-step POC explanation with safety considerations",
          "pocActionabilityTags": ["string"] // e.g., ["requires-auth", "needs-specific-config", "contains-dangerous-operations"]",
          "suggestion": "string | null // Suggested fix with code example"
        }}
      ],
      "lowPrioritySuggestions": [
        {{
          "type": "string // e.g., 'Best Practice', 'Performance', 'Style'",
          "line": "string | number // Line number or range",
          "description": "string // Description of the suggestion",
          "suggestion": "string | null // Suggested improvement"
        }}
      ],
      "error": "string | null // Any error processing this specific file"
    }}
  ],
  "totalInputTokens": "number | null // (Ultron CLI will calculate and add this for the entire request)",
  "llmProcessingNotes": "string | null // Any notes from you about processing this batch, e.g., if some files were ignored due to undecipherable language."
}}

The batch of code files to review begins now:
{code_batch_to_review}
"""

USER_CONTEXT_TEMPLATE = """
**User-Provided Additional Context (applies to all files in batch):**
--- USER CONTEXT START ---
{additional_context}
--- USER CONTEXT END ---
"""

USER_FRAMEWORK_CONTEXT_TEMPLATE = """
**Framework & Library Context (applies to relevant files in batch):**
The codebase utilizes the following primary frameworks and libraries: {frameworks_libraries}.
Consider common security pitfalls and best practices associated with these technologies.
"""

USER_SECURITY_REQUIREMENTS_TEMPLATE = """
**Security Requirements & Compliance Context:**
--- SECURITY REQUIREMENTS START ---
{security_requirements}
--- SECURITY REQUIREMENTS END ---
"""

RELATED_CODE_CONTEXT_SECTION_TEMPLATE = """
**Related Code Context from Other Project Files:**
To help you understand interactions, here are summaries of functions/methods that are called by, or call, functions in the primary code under review:
--- RELATED CONTEXT START ---
{related_code_context}
--- RELATED CONTEXT END ---
Please use this information to better assess data flow and potential inter-procedural vulnerabilities.
"""
