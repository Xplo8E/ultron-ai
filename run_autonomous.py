#!/usr/bin/env python3
"""
Ultron Autonomous Agent Docker Launcher

This script provides a secure, sandboxed way to run Ultron's autonomous security analysis
using Docker containers. It builds the necessary Docker image and launches the agent
with your target codebase mounted in a controlled environment.

Usage:
    python run_autonomous.py --target ./my_project --mission "Find buffer overflows"
"""

import subprocess
import argparse
import os
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(
        description="Launch the Ultron autonomous agent in a secure Docker sandbox.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  # Analyze a C project with pre-compiled binary
  python run_autonomous.py --target ./vulnerable_app --mission "Find buffer overflow in the compiled binary"
  
  # Analyze a Python web application
  python run_autonomous.py --target ./flask_app --mission "Find SQL injection vulnerabilities"
  
  # Use a specific model with verbose output
  python run_autonomous.py --target ./my_code --mission "Security audit" --model-key flash-8b --verbose
        """
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Path to the target directory on your host machine.\n"
             "This directory should contain the source code and any manually\n"
             "compiled binaries you want the agent to use (e.g., in a 'bin' subfolder)."
    )
    parser.add_argument(
        "--mission",
        required=True,
        help="A clear, high-level mission objective for the agent.\n"
             "Be specific about what vulnerabilities to look for and what to test."
    )
    parser.add_argument(
        "--model-key",
        default="2.5-flash-05-20",
        help="The Gemini model key for the agent's reasoning (default: 2.5-flash-05-20).\n"
             "Other options: flash-8b, 2.5-pro"
    )
    parser.add_argument(
        "--image-name",
        default="ultron-autonomous-agent:latest",
        help="The name for the Docker image (default: ultron-autonomous-agent:latest)."
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Skip the Docker image build step and use the existing image.\n"
             "Useful for subsequent runs after the first build."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose mode for the agent inside the container.\n"
             "Shows detailed tool calls and reasoning."
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=50,
        help="Maximum number of analysis turns for the agent (default: 50)."
    )
    parser.add_argument(
        "--network-isolation",
        action="store_true",
        help="Enable complete network isolation for maximum security.\n"
             "WARNING: This will prevent the agent from downloading dependencies."
    )
    args = parser.parse_args()

    # Validate environment
    if not check_prerequisites():
        return 1

    # --- 1. Build the Docker Image (if not skipped) ---
    if not args.no_build:
        print(f"🐳 Building Docker image '{args.image_name}'...")
        print("    This may take a few minutes on first run...")
        
        build_command = ["docker", "build", "-t", args.image_name, "."]
        try:
            result = subprocess.run(build_command, check=True, capture_output=True, text=True)
            print("✅ Docker image built successfully.")
            if args.verbose:
                print(f"Build output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Docker build failed. Aborting.")
            print(f"--- STDERR ---\n{e.stderr}")
            if e.stdout:
                print(f"--- STDOUT ---\n{e.stdout}")
            return 1
    else:
        print(f"⏭️  Skipping Docker build, using existing image '{args.image_name}'")

    # --- 2. Validate Target Directory ---
    host_target_path = Path(args.target).resolve()
    if not host_target_path.is_dir():
        print(f"❌ Error: The target path '{host_target_path}' is not a valid directory.")
        return 1

    # --- 3. Prepare Docker Run Command ---
    print("\n🚀 Preparing to launch the agent in a sandboxed container...")
    
    # Define the fixed workspace path inside the container
    container_workspace_path = "/workspace"
    
    # Construct the `docker run` command
    docker_command = [
        "docker", "run",
        "--rm",                 # Automatically remove the container when it exits
        "--interactive",        # Keep STDIN open
        "--tty",               # Allocate a pseudo-TTY for colored output
        "--cap-drop=ALL",       # Crucial security: drop all Linux capabilities
        "--read-only",          # Make the container filesystem read-only
        "--tmpfs", "/tmp",      # Allow temporary files in /tmp
        "--tmpfs", "/workspace/.ultron_temp",  # Temp space for agent
        
        # Mount the user's target directory into the container's workspace
        "-v", f"{host_target_path}:{container_workspace_path}",
        
        # Pass the Gemini API key securely from the host environment
        "-e", f"GEMINI_API_KEY={os.getenv('GEMINI_API_KEY', '')}",
        
        # Set resource limits for additional safety
        "--memory=2g",          # Limit memory usage
        "--cpus=2.0",           # Limit CPU usage
        
        args.image_name,        # The Docker image to use
        
        # --- Arguments for the 'ultron' entrypoint ---
        "autonomous-review",
        "--path", container_workspace_path,
        "--mission", args.mission,
        "--model-key", args.model_key,
        "--max-turns", str(args.max_turns),
    ]
    
    # Add network isolation if requested
    if args.network_isolation:
        docker_command.extend(["--network", "none"])
        print("🔒 Network isolation enabled - container will have no internet access")
    
    # Add verbose flag if requested
    if args.verbose:
        docker_command.append("--verbose")
    
    # Display launch information
    print(f"\n📁 Target Analysis:")
    print(f"    HOST PATH:      {host_target_path}")
    print(f"    CONTAINER PATH: {container_workspace_path}")
    print(f"\n🎯 Mission: '{args.mission}'")
    print(f"🤖 Model: {args.model_key}")
    print(f"🔄 Max Turns: {args.max_turns}")
    
    # Check if target contains obvious files
    common_files = ["main.c", "app.py", "index.js", "Makefile", "requirements.txt"]
    found_files = [f for f in common_files if (host_target_path / f).exists()]
    if found_files:
        print(f"📋 Detected files: {', '.join(found_files)}")
    
    print(f"\n{'='*60}")
    print("🔥 LAUNCHING ULTRON AUTONOMOUS AGENT")
    print(f"{'='*60}")

    # --- 4. Execute the Command ---
    try:
        # Run the container and capture the exit code
        result = subprocess.run(docker_command, check=False)
        exit_code = result.returncode
        
        print(f"\n{'='*60}")
        if exit_code == 0:
            print("✅ AGENT COMPLETED SUCCESSFULLY")
        else:
            print(f"⚠️  AGENT FINISHED WITH EXIT CODE: {exit_code}")
        print(f"{'='*60}")
        
        return exit_code
        
    except FileNotFoundError:
        print("❌ Error: 'docker' command not found. Is Docker installed and running?")
        return 1
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user. Container will be automatically cleaned up.")
        return 130
    except Exception as e:
        print(f"❌ An error occurred while trying to run the container: {e}")
        return 1

def check_prerequisites():
    """Check that all prerequisites are met before launching."""
    
    # Check Docker
    try:
        result = subprocess.run(["docker", "--version"], 
                              capture_output=True, text=True, check=True)
        print(f"✅ Docker detected: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker is not installed or not running.")
        print("   Please install Docker and ensure the Docker daemon is running.")
        return False
    
    # Check API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "PLACE-HOLDER":
        print("❌ GEMINI_API_KEY environment variable is not set or is a placeholder.")
        print("   Please set your API key:")
        print("   export GEMINI_API_KEY='your-actual-api-key'")
        return False
    else:
        print("✅ GEMINI_API_KEY is configured")
    
    # Check if we're in the right directory
    if not Path("setup.py").exists() or not Path("ultron").is_dir():
        print("❌ This script must be run from the ultron-ai project root directory.")
        print("   Make sure you're in the directory containing setup.py and the ultron/ folder.")
        return False
    
    print("✅ All prerequisites met")
    return True

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(130) 