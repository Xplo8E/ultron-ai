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

**1. INVESTIGATE**: Analyze the codebase to form a hypothesis about a vulnerability.
**2. CONSTRUCT PoC**: Use `write_to_file` to create a test script or `execute_shell_command` with an inline command (e.g., `curl`). Your PoC must target `{verification_target}`.
**3. VERIFY**: Execute your PoC and confirm the exploit against the live target. Analyze output for proof of vulnerability.
"""

STATIC_WORKFLOW_TEMPLATE = """
## WORKFLOW: STATIC ANALYSIS & PoC GENERATION (STATIC MODE)

Your primary goal is to analyze the codebase and produce a high-quality, executable Proof of Concept. You should NOT attempt to build, deploy, or run the application yourself.

**1. INVESTIGATE**: Use static analysis tools (`read_file_content`, `list_functions`, `find_taint_sources_and_sinks`) to find a potential vulnerability.
**2. HYPOTHESIZE**: Form a precise vulnerability hypothesis.
**3. CONSTRUCT PoC**: Write a complete, executable Proof of Concept (e.g., a `curl` command or a Python script) that an external user could run to exploit the vulnerability. Use the `write_to_file` tool to save this PoC.
**4. CONCLUDE**: Once you have a high-confidence PoC script, your mission is complete. Write the final report, including the PoC, and clearly state that it has not been dynamically verified.
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