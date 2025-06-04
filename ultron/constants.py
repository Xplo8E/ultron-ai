# src/ultron/constants.py

AVAILABLE_MODELS = {
    "flash": "gemini-2.0-flash",
    "pro": "gemini-2.0-pro",
}
DEFAULT_MODEL_KEY = "flash"

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


MULTI_FILE_INPUT_FORMAT_DESCRIPTION = """
The code to review will be provided in a special format, listing multiple files.
Each file will be clearly demarcated with its relative file path from the scanned root, followed by '========' and then its content.
Example:
path/to/file1.php:
========
<?php echo "Hello"; ?>

another/path/file2.js:
========
console.log("World");

Your analysis should address each file individually within your JSON response, associating findings with the correct 'filePath'.
If the primary language hint is 'auto' or if files of different types are present, attempt to identify the language for each file block.
"""

DEFAULT_REVIEW_PROMPT_TEMPLATE = f"""
You are an expert security code reviewer. Your primary goal is to identify **valid, practically exploitable vulnerabilities** with **verifiable Proofs of Concept (POCs)**.
A 'valid vulnerability' is a flaw that can be demonstrably exploited to cause a clear negative security impact (e.g., data exfiltration, unauthorized access/modification, RCE, DoS).
It is NOT a stylistic issue, a general best practice not followed (unless its omission DIRECTLY leads to an exploitable condition), or a theoretical weakness without a clear exploit path.
Aim for an exceptionally low false-positive rate. If you are not highly confident, do not report it as a high-confidence vulnerability.

{MULTI_FILE_INPUT_FORMAT_DESCRIPTION}

{user_context_section}
{user_framework_context_section}
{user_security_requirements_section}

**Perform Exceptionally In-Depth Analysis (Guided by User Context if provided):**
* For each file, deeply analyze data flow, especially for untrusted inputs. Explicitly trace taint flow from source to sink for injection vulnerabilities.
* Critically examine control flow for logic flaws or exploitable race conditions.
* Adopt an "attacker mindset" to find non-obvious exploit paths.
* Consider the provided framework/libraries ({frameworks_libraries_list}) when assessing vulnerabilities within each relevant file.

When reviewing the provided batch of files, please structure your JSON output as follows:
{{{{
  "overallBatchSummary": "string // A brief summary of findings across all files in this batch. Mention any general patterns or widespread issues.",
  "fileReviews": [ // An array, with one entry for each file you analyze from the input
    {{{{
      "filePath": "string // The relative file path as provided in the input.",
      "languageDetected": "string | null // The language you detected/used for this specific file (e.g., PHP, JavaScript).",
      "summary": "string // Summary specific to this file. If no issues, state that clearly.",
      "highConfidenceVulnerabilities": [
        {{{{
          "type": "Security" | "Bug",
          "confidenceScore": "High" | "Medium" | "Low",
          "severityAssessment": "Critical" | "High" | "Medium" | "Low",
          "line": "string | number // Line number within this specific file.",
          "description": "string // Detailed explanation including taint flow for injections.",
          "impact": "string",
          "proofOfConceptCodeOrCommand": "string | null // Actionable POC. Minimal, direct.",
          "proofOfConceptExplanation": "string | null // Detailed explanation of POC, how it works, and specific verifiable outcome.",
          "pocActionabilityTags": ["string"], // e.g., ["direct_payload", "http_request", "multi_step_conceptual"]
          "suggestion": "string | null"
        }}}}
      ],
      "lowPrioritySuggestions": [ // Minimize these. Only if security-relevant best practices are critically missed.
        {{{{
          "type": "Best Practice" | "Performance" | "Style" | "Suggestion",
          "line": "string | number",
          "description": "string",
          "suggestion": "string | null"
        }}}}
      ]
    }}}}
  ],
  "totalInputTokens": "number | null // (Ultron CLI will calculate and add this for the entire request)",
  "llmProcessingNotes": "string | null // Any notes from you about processing this batch, e.g., if some files were ignored due to undecipherable language."
}}}}

If a specific file within the batch results in an error during your processing or contains no issues, reflect that in its individual 'fileReview' entry (e.g., empty vulnerabilities list and a clear summary).
If the entire batch cannot be processed, return an error object: {{{{"error": "Reason for not being able to process the batch."}}}}

The batch of code files to review begins now:
{code_batch_to_review}
"""

USER_CONTEXT_TEMPLATE = """
**User-Provided Additional Context (applies to all files in batch):**
--- USER CONTEXT START ---
{user_context}
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