"""Configuration management for servers.json."""
import json
import os
from typing import List
from models import ServerConfig


CONFIG_FILE = "servers.json"


def get_default_config() -> dict:
    """Return default configuration with example server."""
    return {
        "servers": [
            {
                "name": "server-1",
                "host": "113.201.14.131",
                "port": 43857,
                "username": "root",
                "auth": {
                    "type": "key",
                    "key_path": "C:/Users/AJU/.ssh/vast",
                    "passphrase": None
                },
                "command": "python3 /home/v13/ultra_aggressive_worker.py",
                "working_dir": "/home/v13",
                "env": {},
                "restart_delay_seconds": 12,
                "enabled": True,
                "stop_command": "pkill -f ultra_aggressive_worker.py"
            }
        ]
    }


def load_servers() -> List[ServerConfig]:
    """Load server configurations from servers.json."""
    if not os.path.exists(CONFIG_FILE):
        # Create default config
        default = get_default_config()
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default, f, indent=2)
        print(f"Created default {CONFIG_FILE}")
    
    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)
    
    servers = []
    for server_data in data.get("servers", []):
        # Apply defaults for missing fields
        server_data.setdefault("command", "python3 /home/v13/ultra_aggressive_worker.py")
        server_data.setdefault("working_dir", "/home/v13")
        server_data.setdefault("env", {})
        server_data.setdefault("restart_delay_seconds", 12)
        server_data.setdefault("enabled", True)
        server_data.setdefault("stop_command", "pkill -f ultra_aggressive_worker.py")
        server_data.setdefault("process_match_regex", None)
        server_data.setdefault("pre_command", "")
        
        # Health check defaults (for backward compatibility)
        server_data.setdefault("health_check_enabled", False)
        server_data.setdefault("health_check_cpu_enabled", False)
        server_data.setdefault("health_check_cpu_threshold", 50.0)
        server_data.setdefault("health_check_cpu_duration", 100)
        server_data.setdefault("health_check_gpu_enabled", False)
        server_data.setdefault("health_check_gpu_threshold", 50.0)
        server_data.setdefault("health_check_gpu_duration", 100)
        
        # Validate required fields
        required = ["name", "host", "port", "username", "auth"]
        if not all(field in server_data for field in required):
            print(f"Warning: Skipping invalid server config: {server_data.get('name', 'unknown')}")
            continue
        
        if "type" not in server_data["auth"]:
            print(f"Warning: Skipping server {server_data['name']} - missing auth.type")
            continue
        
        servers.append(ServerConfig(**server_data))
    
    return servers


def save_servers(servers: List[ServerConfig]):
    """Save server configurations to servers.json."""
    data = {
        "servers": [server.to_dict() for server in servers]
    }
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved {len(servers)} servers to {CONFIG_FILE}")
