"""
Configuration management for Ultron autonomous agent.
"""

from dataclasses import dataclass
from pathlib import Path

@dataclass
class AgentConfig:
    """
    Holds all configuration for an agent run.
    This centralizes configuration management and makes it easy to
    pass around agent settings without having many individual parameters.
    """
    codebase_path: Path
    model_key: str
    mission: str
    log_file_path: Path
    verification_target: str | None = None
    sandbox_mode: bool = False
    verbose: bool = False
    max_turns: int = 50
    
    def __str__(self) -> str:
        """String representation for logging purposes."""
        return (
            f"AgentConfig(\n"
            f"  codebase_path={self.codebase_path}\n"
            f"  model_key={self.model_key}\n"
            f"  mission={self.mission}\n"
            f"  verification_target={self.verification_target}\n"
            f"  sandbox_mode={self.sandbox_mode}\n" # NEW
            f"  log_file_path={self.log_file_path}\n"
            f"  verbose={self.verbose}\n"
            f"  max_turns={self.max_turns}\n"
            f")"
        ) 