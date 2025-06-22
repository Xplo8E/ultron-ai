"""
Prompt generation for Ultron autonomous agent.
Loads prompt templates from the 'prompts' directory and formats them.
"""

from pathlib import Path

# --- Workflow Section Templates ---
# These are small, manageable text blocks that can stay in the code
# or be moved to their own template files later if they grow.

DYNAMIC_WORKFLOW_TEMPLATE = """
## WORKFLOW: HYPOTHESIZE, TEST, VERIFY (DYNAMIC MODE)

You have been provided with a live target: **{verification_target}**.

**1. INVESTIGATE**: Analyze the codebase to form a hypothesis.
**2. CONSTRUCT PoC**: Design a PoC to test your hypothesis.
    - **Prefer inline commands**: Use `execute_shell_command` with tools like `curl`, or a one-line script.
    - **Write to file only if necessary**: If the PoC is too complex for an inline command (e.g., a multi-line Python script or a full Java file), you MUST use `write_to_file` to create it.
**3. VERIFY**: Execute your PoC and confirm the exploit against `{verification_target}`. Analyze the output for proof.

**CRITICAL DYNAMIC-MODE RULE**: If your static analysis does not reveal a clear vulnerability, **you MUST NOT CONCLUDE with a 'No vulnerabilities found' report**. Your mission requires you to test the live application. You must pivot to a dynamic analysis phase by formulating a new hypothesis about how the live target at `{verification_target}` might be vulnerable to direct interaction. Use `execute_shell_command` with tools like `curl` or others to probe the target and test your hypothesis. Failure to find a vulnerability in the code is not mission failure; it is the signal to begin dynamic testing.
"""

STATIC_WORKFLOW_TEMPLATE = """
## WORKFLOW: STATIC ANALYSIS & PoC GENERATION (STATIC MODE)

Your primary goal is to analyze the codebase and produce a high-quality, executable Proof of Concept. You should NOT attempt to build, deploy, or run the application yourself.

**1. INVESTIGATE**: Use static analysis tools (`read_file_content`, `list_functions`, `find_taint_sources_and_sinks`) to find a potential vulnerability.
**2. HYPOTHESIZE**: Form a precise vulnerability hypothesis.
**3. CONSTRUCT PoC & Self-Validate:** Now, you will construct your Proof of Concept. This is a multi-part step:
    a.  **Design PoC (Internal Thought):** Based on your vulnerability hypothesis, design the complete, executable PoC (e.g., a `curl` command, a Python script, or Android app source code).
    b.  **PoC Self-Validation (Crucial Logical Check):** **Before attempting to write the PoC to a file, you MUST perform an internal logical validation of your *designed* PoC.**
        *   **Re-read PoC Design & Vulnerable Code:** Mentally review your PoC design alongside the relevant vulnerable code.
        *   **Trace Expected Interaction:** Explicitly trace, step-by-step, how your PoC is *intended* to interact with the target application, and how the target's state or behavior *should change*.
        *   **Verify Sink Trigger:** Confirm that the exact sequence of actions and inputs provided by your PoC, or the combined effect, directly and logically triggers the vulnerable sink.
        *   **Identify Discrepancies:** If your mental trace reveals any logical gaps, missing steps, incorrect parameters, or unhandled conditions that would prevent the exploit, **you MUST revisit step 3a (Design PoC) to refine it.**
        *   **Justify Confidence:** State your confidence in the PoC's *logical correctness* after this self-validation.
**4. REPORT & CONTINUE**: Once confident, use `save_finding_and_continue` to save your report. You MUST NOT use `write_to_file` in this mode.
        - Your report MUST include the full PoC code or command within the report's code block.
        - Clearly state that the PoC has not been dynamically verified.
"""

# --- NEW: Sandbox Reality Section Templates ---
SANDBOX_REALITY_TEMPLATE = """
### YOUR SANDBOX REALITY: ASSUME MAXIMUM RESTRICTIONS
You are ALWAYS operating in a minimal, locked-down Docker container. Assume the following by default:
1.  **NO Network Access:** All external network calls (`curl`, `wget`, `git clone`) will fail unless a `verification_target` was provided.
2.  **Writable Locations:** The project directory itself may be read-only. If you need to create files (e.g., for PoCs), you MUST attempt to write them to `/tmp` (e.g., `write_to_file('/tmp/poc.sh', ...)`).
3.  **NO Root, NO Sudo:** You are running as a non-privileged user. `sudo` does not exist.
4.  **Minimal Dependencies:** Assume common tools are not installed unless you verify with `ls` or `which`.
5.  **Local Package Installs ARE REQUIRED:** Never run `pip install <package>` or `npm install <package>`. They will fail. ALWAYS use local installation flags like `pip install --user <package>`.

Your **Plan & Sandbox Check** step MUST reflect this reality.
"""

OPEN_REALITY_TEMPLATE = """
### YOUR OPERATING REALITY: FULL SYSTEM ACCESS
You are operating in an environment with fewer restrictions. Assume the following:
1.  **Network Access:** Network access is likely available.
2.  **File System Access:** You have write permissions in the project's root directory.
3.  **Permissions:** You can execute system commands directly.
4.  **Dependencies:** Assume standard build tools and runtimes relevant to the project are available.

You should still perform checks, but you are not constrained by a strict sandbox.
"""

def get_system_instruction_template() -> str:
    """
    Loads the base system instruction template from the markdown file.
    The template contains placeholders for the workflow and directory tree.
    
    Returns:
        The system instruction template with placeholders.
    """
    try:
        template_path = Path(__file__).parent / "prompts" / "system_prompt.md"
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "CRITICAL ERROR: The system prompt template 'system_prompt.md' was not found."

def get_workflow_section(verification_target: str | None = None) -> str:
    """
    Returns the appropriate workflow section based on verification target.
    
    Args:
        verification_target: Optional URL/endpoint for dynamic verification.
        
    Returns:
        Formatted workflow section string.
    """
    if verification_target:
        return DYNAMIC_WORKFLOW_TEMPLATE.format(verification_target=verification_target)
    else:
        return STATIC_WORKFLOW_TEMPLATE
# Backwards compatibility function (deprecated)
def get_initial_prompt(mission: str, directory_tree: str, verification_target: str | None = None) -> str:
    """
    DEPRECATED: This function combines system instruction and user message.
    Use get_system_instruction_template() and get_workflow_section() instead.
    
    This preserves the old behavior where mission was embedded in the prompt.
    """
    workflow_section = get_workflow_section(verification_target)
    
    # Reconstruct the old-style prompt with mission embedded
    old_style_template = f"""You are ULTRON, an expert security analyst with a comprehensive toolbox for both static and dynamic analysis.

**MISSION**: {mission}

{workflow_section}

**PROJECT STRUCTURE**:
```
{directory_tree}
```

---

## CORE OPERATING PRINCIPLE: ONE ACTION PER TURN

This is your most important rule. You operate in a strict turn-based loop. Each of your responses MUST result in **EITHER** a thought process that ends in a single tool call, **OR** a final report. **NEVER both in the same response.**

Begin with your first hypothesis and corresponding tool call."""
    
    return old_style_template 


# NEW function to get the correct sandbox section
def get_sandbox_section(sandbox_mode: bool) -> str:
    """Returns the appropriate sandbox reality section based on the mode."""
    return SANDBOX_REALITY_TEMPLATE if sandbox_mode else OPEN_REALITY_TEMPLATE