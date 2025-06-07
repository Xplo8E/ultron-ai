# src/ultron/constants.py

AVAILABLE_MODELS = {
    # Models available on the free tier
    "2.0-flash-lite": "gemini-2.0-flash-lite",             # For LLM-based context analysis
    "2.0-flash": "gemini-2.0-flash",                 # Good for the main review
    "2.5-flash-05-20": "gemini-2.5-flash-preview-05-20"  # Best free model for the agent
}
# 2.5-flash-05-20 is the best free model for the agent
# Set the default for the main 'review' command to the best free general-purpose model
DEFAULT_MODEL_KEY = "2.5-flash-05-20"

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
You are a high-performance, language-agnostic code analysis engine. Your sole purpose is to read a batch of code files and generate a structured summary of function/method definitions and their call sites.

**Your Task:**
1.  Analyze the provided code batch, which contains multiple files.
2.  For each file, identify all the function or method definitions.
3.  For each function/method, identify all the other functions/methods it calls.
4.  Produce a single, concise text output summarizing your findings.

**Critical Output Format Requirements:**
-   DO NOT provide any commentary, explanation, or summary.
-   DO NOT use markdown code blocks (```).
-   Follow the specified text format EXACTLY.
-   If a file contains no functions or calls, state that.

**Example Output Format:**
# === File: src/com/example/app/MainActivity.java ===
# Defines Methods:
#   - public void onCreate(Bundle savedInstanceState) (Lines: 15-32)
#   - class JSBridge.showToast(String toast) (Lines: 9-12)
# Calls:
#   - `super.onCreate()` at line 16
#   - `new WebView()` at line 17
#   - `getIntent().getStringExtra()` at line 23
#   - `webView.loadUrl()` at line 31

# === File: AndroidManifest.xml ===
# This file does not contain function definitions or calls.


The code batch to analyze begins now:
{code_batch_to_analyze}
"""


MULTI_FILE_INPUT_FORMAT_DESCRIPTION = """
The code to review will be provided in a special format, listing multiple files.
Each file will be clearly demarcated with its relative file path from the scanned root, followed by '========' and then its content.

**Important for Python files:** For some Python files, a section starting with '# Related Code Context for file:' may precede the actual file content. This section provides summaries of functions or methods that are called by, or related to, the functions in the main file content that follows. Please use this related context to better understand inter-dependencies and data flow when analyzing the main file content.

Example of a file block with related context:
path/to/main_module.py:
========
# Related Code Context for file: path/to/main_module.py
# Function: def some_function_in_main_module():
#   Calls the following functions:
#     - `utils.helper_function` (defined in `utils.py`):
#       Function: def helper_function(param1, param2):
#         Docstring: "This helper does X and Y."
# ---

# --- Start of actual file content for path/to/main_module.py ---
def some_function_in_main_module():
    # ... code ...
    utils.helper_function(a, b)
    # ... more code ...
# --- End of actual file content for path/to/main_module.py ---


another/path/file2.js:
========
console.log("World");

Your analysis should address each file individually within your JSON response, associating findings with the correct 'filePath'.
If the primary language hint is 'auto' or if files of different types are present, attempt to identify the language for each file block.
"""

DEFAULT_REVIEW_PROMPT_TEMPLATE = """
You are an expert security code reviewer. Your primary goal is to identify **valid, practically exploitable vulnerabilities** with **verifiable Proofs of Concept (POCs)**.
A 'valid vulnerability' is a flaw that can be demonstrably exploited to cause a clear negative security impact (e.g., data exfiltration, unauthorized access/modification, RCE, DoS).
It is NOT a stylistic issue, a general best practice not followed (unless its omission DIRECTLY leads to an exploitable condition), or a theoretical weakness without a clear exploit path.
Aim for an exceptionally low false-positive rate. If you are not highly confident, do not report it as a high-confidence vulnerability.

For each POC/exploit:
- Write complete, executable code (e.g., curl commands, Python scripts, JavaScript payloads)
- Include exact endpoints, parameters, and payload values needed
- Specify HTTP methods, headers, and request/response formats where applicable
- Show both the malicious input AND the expected malicious output
- If chaining multiple steps, number them and show the output of each step
- For client-side exploits, provide the exact HTML/JS payload and how to deliver it
- For race conditions, show the exact timing and concurrent request patterns
- For file-based exploits, show exact file contents and upload methods

{MULTI_FILE_INPUT_FORMAT_DESCRIPTION}

{user_context_section}
{user_framework_context_section}
{user_security_requirements_section}

**CRITICAL RESPONSE FORMAT REQUIREMENTS:**
1. Your ENTIRE response MUST be a SINGLE, VALID JSON object.
2. DO NOT output ANY text, commands, code, or explanations outside of the JSON structure.
3. DO NOT use markdown code blocks or any other formatting - output ONLY the raw JSON object.
4. ALL findings, including POCs and dangerous commands, MUST be placed in their appropriate JSON fields.
5. NEVER output raw commands or code directly - they must be part of the JSON structure.
6. If you need to show a command or POC, it MUST be inside the appropriate JSON field (e.g., "proofOfConceptCodeOrCommand").
7. Your response MUST start with '{{' and end with '}}' with no other text before or after.
8. When showing vulnerabilities or exploits:
   - Place ALL exploit code/commands in the "proofOfConceptCodeOrCommand" field
   - Place ALL exploit explanations in the "proofOfConceptExplanation" field
   - NEVER output exploits or commands directly in the response
   - ALWAYS wrap everything in proper JSON structure
   - NEVER output raw shell commands or injection payloads directly
   - ALL dangerous operations MUST be clearly marked and explained

**IMPORTANT SECURITY RULES:**
1. NEVER output raw shell commands, injection payloads, or exploit code directly in the response.
2. ALL potentially dangerous operations MUST be wrapped in JSON and include clear warnings.
3. For command injection vulnerabilities, use safe example commands (e.g., 'echo "test"' instead of destructive commands).
4. Include clear warnings and safety considerations for any dangerous POCs.
5. Focus on demonstrating the vulnerability exists without causing harm.

**JSON Schema (EXACTLY Follow This Structure):**
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