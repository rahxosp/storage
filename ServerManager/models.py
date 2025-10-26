"""Data models for server configuration and runtime state."""
from dataclasses import dataclass, field
from typing import Optional, Dict
from enum import Enum
import re


class ServerStatus(Enum):
    """Server connection and process status."""
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    RUNNING = "Running"
    STOPPED = "Stopped"
    ERROR = "Error"
    EXTERNAL = "External"  # Process running but not started by us


@dataclass
class ServerConfig:
    """Configuration for a remote server."""
    name: str
    host: str
    port: int
    username: str
    auth: Dict[str, Optional[str]]  # {"type": "key"/"password", "key_path": "...", "passphrase": None, "password": None}
    command: str = "python3 /home/v13/ultra_aggressive_worker.py"
    working_dir: str = "/home/v13"
    env: Dict[str, str] = field(default_factory=dict)
    restart_delay_seconds: int = 12
    enabled: bool = True
    stop_command: str = "pkill -f ultra_aggressive_worker.py"
    process_match_regex: Optional[str] = None
    pre_command: str = ""  # e.g., "source ~/.bashrc && conda activate main" or "source /home/v13/.venv/bin/activate"
    
    # Health check settings
    health_check_enabled: bool = False
    health_check_cpu_enabled: bool = False
    health_check_cpu_threshold: float = 50.0  # Restart if CPU below this % for duration
    health_check_cpu_duration: int = 100  # Seconds
    health_check_gpu_enabled: bool = False
    health_check_gpu_threshold: float = 50.0  # Restart if GPU below this % for duration
    health_check_gpu_duration: int = 100  # Seconds
    
    def __post_init__(self):
        """Apply defaults and generate process regex if needed."""
        if not self.process_match_regex:
            # Derive from command - escape special chars and match key parts
            cmd_parts = self.command.split()
            if len(cmd_parts) >= 2:
                # Match against script name (last significant part)
                script = cmd_parts[-1]
                self.process_match_regex = re.escape(script)
            else:
                self.process_match_regex = re.escape(self.command)
    
    def get_display_address(self) -> str:
        """Return formatted host:port for display."""
        return f"{self.host}:{self.port}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "auth": self.auth,
            "command": self.command,
            "working_dir": self.working_dir,
            "env": self.env,
            "restart_delay_seconds": self.restart_delay_seconds,
            "enabled": self.enabled,
            "stop_command": self.stop_command,
            "process_match_regex": self.process_match_regex,
            "pre_command": self.pre_command,
            "health_check_enabled": self.health_check_enabled,
            "health_check_cpu_enabled": self.health_check_cpu_enabled,
            "health_check_cpu_threshold": self.health_check_cpu_threshold,
            "health_check_cpu_duration": self.health_check_cpu_duration,
            "health_check_gpu_enabled": self.health_check_gpu_enabled,
            "health_check_gpu_threshold": self.health_check_gpu_threshold,
            "health_check_gpu_duration": self.health_check_gpu_duration
        }


@dataclass
class ServerState:
    """Runtime state for a server worker."""
    status: ServerStatus = ServerStatus.DISCONNECTED
    pid: Optional[int] = None
    uptime_seconds: int = 0
    restarts_count: int = 0
    last_restart_time: Optional[str] = None
    last_error: Optional[str] = None
    backoff_seconds: int = 5
    
    def reset_backoff(self):
        """Reset backoff to initial value."""
        self.backoff_seconds = 5
    
    def increase_backoff(self):
        """Increase backoff with exponential strategy, cap at 60 seconds."""
        self.backoff_seconds = min(self.backoff_seconds * 2, 60)
