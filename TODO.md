
# TODO


1. Advanced Context Management for the LLM
When analyzing a file, its interaction with other parts of the codebase is crucial for accuracy.

- [] A. Call Graph & Dependency Analysis (Lightweight Static Analysis First):

Concept: Before sending code to the LLM, perform a lightweight static analysis pass on the codebase to build a call graph and understand basic dependencies between functions and classes.
Implementation:
Use language-specific libraries (e.g., Python's ast module, radon for complexity, or tools like pyan for call graphs; similar tools exist for other languages).
When analyzing a specific function in file_A.py that calls a function in file_B.py, extract the signature and a brief summary (or even the full body if small) of the called function from file_B.py and include it as context for the LLM.
Benefit: Provides the LLM with relevant cross-file context without overwhelming it with entire unrelated files.

- [] B. Smart Chunking for Large Files:

Concept: If a single file exceeds the practical context window or desired token limit for cost/latency, break it into smaller, logical chunks.
Implementation:
Chunk by classes or functions rather than arbitrary line numbers.
Each chunk should include necessary imports and relevant class/global variable definitions from the same file.
Consider providing overlapping context between chunks if a vulnerability might span chunk boundaries.
The LLM's summary for each chunk might need to be aggregated.
Benefit: Allows analysis of very large files that would otherwise be impossible.

B. Token Usage Monitoring & Limits:

Concept: Before sending a request, use model.count_tokens() to estimate the size. If it's too large (even for chunking strategies, the total context might be an issue), implement a strategy.
Implementation:
Warn the user if a file/chunk is too large.
Implement more aggressive context summarization or truncation if limits are approached.
Allow users to set a "max tokens per file" budget.
Benefit: Prevents errors and unexpected costs.



- [x] Folder support
- [x] Restructure neatly
- [x] adavnced/dynamic  prompt engineering to focus on user specified vulnerabilities


- [x] Explicit Exploitability & Impact Assessment:
```
Ask the LLM to rate its confidence in the exploitability of each identified vulnerability (e.g., High, Medium, Low).
Request a brief justification for why it's considered exploitable.
Ask for an estimation of potential impact if exploited, using a simple scale or referencing STRIDE/DREAD if applicable.
Modify the JSON output in models.py to include these fields: exploitabilityConfidence: str, impactAssessment: str.
```

- [x] Refined POC Generation Instructions:
```
Actionability: Stress that POCs should be conceptually actionable and clearly demonstrate the flaw with minimal setup. Reiterate "NO narrative" in the proofOfConceptCodeOrCommand field.
Expected Outcome: Emphasize that the proofOfConceptExplanation must state the specific, observable outcome if the POC were (conceptually) executed. This is key for verification.
Safety: Remind the AI that POCs should be conceptually safe and illustrative, not destructive.
```

- [x] Stronger Negative Constraints (What NOT to Report):
```
Be even more explicit in the prompt about avoiding purely stylistic issues, minor deviations from best practices that don't pose a security risk, or overly theoretical vulnerabilities without a clear path to exploitation.
Example: "CRITICAL: Do NOT report on code formatting, variable naming conventions, or lack of comments unless these directly contribute to a demonstrable security vulnerability with a plausible exploit path. Focus solely on issues that present a tangible security risk."
```

- [x] Data Flow & Taint Analysis Emphasis (Reinforce):
```
While already present, you can add more weight: "Your analysis MUST meticulously trace untrusted data from its source (e.g., user input, external API response) to any sink (e.g., database query, HTML output, command execution). Clearly describe this data flow path when explaining injection vulnerabilities."
```

- [x] "Attacker Mindset" Priming:
```
Before the code review section, you could add: "Adopt the mindset of a skilled attacker. How would you subvert this code? What are the weakest points? Consider edge cases, unexpected inputs, and race conditions."
```

- [x] Tooling & workflow improvements:

- [x] Configurable Severity/Confidence Thresholds:
```
If the LLM provides confidence scores for vulnerabilities, allow users to set a threshold in the CLI (e.g., --min-confidence medium) to filter out less certain findings.
```

- [x] Ignore Mechanism:
```
Allow users to ignore specific vulnerabilities or lines/files:
Inline comments: // ultron-ignore: CWE-79 "Reason: Handled by sanitizer"
.ultronignore file: Similar to .gitignore, listing file paths, directory patterns, or specific rule IDs/CWEs to ignore. Your script would parse this and skip reporting.
```

- [x] Pre-computation of Code Structure (Advanced):
```
For supported languages, you could use libraries like ast (for Python) or tree-sitter bindings to parse the code into an Abstract Syntax Tree (AST).
A simplified, textual representation of the AST, key function signatures, or call graphs could be passed as additional context to Gemini to aid its understanding of the code structure, especially for larger files.
```

