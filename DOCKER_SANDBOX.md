# Ultron Docker Sandbox Guide

This guide explains how to use Ultron's Docker sandbox feature for secure autonomous security analysis.

## Overview

The Docker sandbox provides a **secure, isolated environment** for running Ultron's autonomous agent on potentially dangerous code. Key benefits:

- 🔒 **Complete Isolation**: Agent runs in a separate container with restricted capabilities
- 🚫 **No Host Access**: Cannot modify or access files outside the mounted target directory  
- ⚡ **Resource Limits**: Memory and CPU usage are constrained
- 🛡️ **Security Hardened**: Read-only filesystem, dropped capabilities, optional network isolation

## Quick Start

### 1. Prerequisites

- Docker installed and running
- `GEMINI_API_KEY` environment variable set
- Be in the ultron-ai project root directory

### 2. Prepare Your Target

Create a directory with your code and any pre-compiled binaries:

```bash
# Example C project
mkdir vulnerable_app
cd vulnerable_app
echo '#include <stdio.h>
#include <string.h>
int main() {
    char buf[10];
    gets(buf);  // Vulnerable!
    printf("Hello %s\n", buf);
    return 0;
}' > main.c

# Compile the binary yourself
gcc -o bin/app main.c -fno-stack-protector
cd ..
```

### 3. Launch the Agent

```bash
python run_autonomous.py \
    --target ./vulnerable_app \
    --mission "Find buffer overflow vulnerabilities in the compiled binary and create a working PoC"
```

## Usage Examples

### C/C++ Binary Analysis
```bash
python run_autonomous.py \
    --target ./my_c_project \
    --mission "Analyze the compiled binary for memory corruption vulnerabilities. Create exploit PoCs and test them."
```

### Python Web Application
```bash
python run_autonomous.py \
    --target ./flask_app \
    --mission "Find SQL injection and XSS vulnerabilities in this Flask application"
```

### Node.js Project
```bash
python run_autonomous.py \
    --target ./node_app \
    --mission "Identify prototype pollution and command injection vulnerabilities"
```

### Advanced Usage with Custom Model
```bash
python run_autonomous.py \
    --target ./complex_app \
    --mission "Comprehensive security audit focusing on authentication bypass" \
    --model-key 2.5-pro \
    --verbose \
    --max-turns 75
```

## Command Reference

### Required Arguments

- `--target PATH`: Directory containing your code and binaries
- `--mission "DESCRIPTION"`: Clear mission objective for the agent

### Optional Arguments

- `--model-key MODEL`: Gemini model to use (default: 2.5-flash-05-20)
  - Options: `flash-8b`, `2.5-flash-05-20`, `2.5-pro`
- `--verbose`: Show detailed agent reasoning and tool calls
- `--max-turns N`: Maximum analysis turns (default: 50)
- `--no-build`: Skip Docker image build (for subsequent runs)
- `--network-isolation`: Disable network access for max security
- `--image-name NAME`: Custom Docker image name

## Security Features

### Container Hardening
- **Read-only filesystem**: Container cannot modify its own files
- **Dropped capabilities**: No root-level system access
- **Resource limits**: 2GB memory, 2 CPU cores maximum
- **Temporary filesystems**: Only /tmp and workspace temp dirs are writable

### Network Controls
- Default: Internet access for API calls and downloads
- `--network-isolation`: Complete network isolation (blocks everything)

### File System Access
- Agent can only access files in the mounted target directory
- Cannot access host filesystem outside the target
- Cannot persist changes outside the workspace

## Target Directory Structure

### Recommended Layout
```
your_project/
├── src/                    # Source code
│   ├── main.c
│   └── utils.c
├── bin/                    # Pre-compiled binaries
│   └── app
├── test_inputs/           # Test data files
│   └── sample.txt
├── Makefile              # Build instructions (for reference)
└── README.md             # Project documentation
```

### What to Include
- **Source code**: All relevant source files
- **Compiled binaries**: Pre-compile any executables
- **Test data**: Sample inputs, config files
- **Build scripts**: Makefiles, build.sh (for reference)

### What NOT to Include
- Build artifacts (*.o files, build/ directories)
- Large datasets or media files
- Sensitive credentials or API keys

## Agent Capabilities in Sandbox

The autonomous agent has access to:

### High-Level Analysis Tools
- `list_functions()`: AST-based Python function parsing
- `find_taint_sources_and_sinks()`: Data flow analysis
- `search_codebase()`: Structured recursive search
- `read_file_content()`: Enhanced file reading

### System-Level Tools
- `execute_shell_command()`: Full shell access within container
- `write_to_file()`: Create PoCs, test scripts, patches

### Available System Tools
- Development: `gcc`, `make`, `cmake`, `git`
- Analysis: `gdb`, `strace`, `ltrace`, `valgrind`
- Network: `curl`, `netcat`, `nmap`, `socat`
- Utilities: `file`, `xxd`, `binutils`

## Example Workflow

The agent follows this general pattern:

1. **Reconnaissance**: Explore the codebase structure
   ```bash
   ls -la /workspace
   find /workspace -name "*.c" -o -name "*.py"
   ```

2. **Static Analysis**: Examine source code for vulnerabilities
   ```python
   list_functions('src/main.c')
   find_taint_sources_and_sinks('src/app.py', ['input', 'request'], ['eval', 'system'])
   ```

3. **Dynamic Testing**: Create and test exploits
   ```bash
   # Create PoC payload
   write_to_file('exploit.txt', 'A' * 100)
   
   # Test the binary
   execute_shell_command('./bin/app < exploit.txt')
   ```

4. **Verification**: Confirm vulnerabilities and document findings

## Troubleshooting

### Docker Build Fails
```bash
# Clean build without cache
docker system prune -f
python run_autonomous.py --target ./myapp --mission "test" --no-build false
```

### Permission Denied Errors
```bash
# Ensure target directory is readable
chmod -R 755 your_target_directory
```

### Agent Can't Find Binaries
- Ensure binaries are executable: `chmod +x bin/your_app`
- Use absolute paths: `./bin/app` instead of just `app`
- Check if binary architecture matches (x86_64 Linux)

### Network Issues
- Default setup allows internet access for API calls
- Use `--network-isolation` only if you don't need external dependencies
- Check your firewall/proxy settings if API calls fail

### Out of Memory/Resources
- Reduce `--max-turns` for complex analysis
- Use `flash-8b` model for lower resource usage
- Check `docker stats` to monitor resource usage

## Best Practices

### Target Preparation
- ✅ Compile binaries on Linux (preferably Ubuntu)
- ✅ Include debug symbols when possible (`-g` flag)
- ✅ Disable protections during testing (`-fno-stack-protector`)
- ✅ Provide clear, specific mission objectives

### Mission Crafting
- ✅ Be specific about vulnerability types to find
- ✅ Mention if you want PoC creation and testing
- ✅ Include context about the application's purpose
- ❌ Don't use vague goals like "find bugs"

### Performance Optimization
- Use `--no-build` for subsequent runs
- Start with `flash-8b` model for faster analysis
- Upgrade to `2.5-pro` for complex codebases only

## Limitations

- Container runs on Linux; Windows binaries won't execute
- No GUI applications (terminal/CLI only)
- Network isolation blocks all external connectivity
- Resource limits may constrain analysis of very large codebases
- Agent cannot modify host system or other containers

## Safety Notes

⚠️ **Important**: This sandbox provides strong isolation, but:
- Always use on non-critical systems
- Don't mount sensitive directories as targets
- Monitor resource usage during long analyses
- The agent will attempt to exploit vulnerabilities it finds

The sandbox is designed to contain any malicious code or exploits the agent discovers and tests. 