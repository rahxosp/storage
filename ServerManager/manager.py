"""Manager for coordinating all server workers."""
from queue import Queue
from typing import Dict, List, Optional
from models import ServerConfig, ServerState
from worker import ServerWorker
from config import load_servers, save_servers
from ssh_client import SSHClient
from logging_setup import get_app_logger
from metrics_db import init_db


class ServerManager:
    """Manages all server workers and configuration."""
    
    def __init__(self):
        self.workers: Dict[str, ServerWorker] = {}
        self.ui_queue = Queue()
        self.logger = get_app_logger()
        self.configs: List[ServerConfig] = []
    
    def load_configs(self):
        """Load server configurations and create workers."""
        self.logger.info("Loading server configurations...")
        # Ensure metrics DB is ready
        init_db()
        self.configs = load_servers()
        
        # Create workers for each config
        for config in self.configs:
            if config.name not in self.workers:
                worker = ServerWorker(config, self.ui_queue)
                self.workers[config.name] = worker
                self.logger.info(f"Created worker for {config.name}")
        
        self.logger.info(f"Loaded {len(self.configs)} servers")
    
    def start_all(self):
        """Start all enabled workers."""
        for name, worker in self.workers.items():
            if worker.config.enabled:
                worker.manual_stop_requested = False
                worker.start_worker()
        self.logger.info("Started all enabled workers")
    
    def stop_all(self):
        """Stop all workers."""
        for worker in self.workers.values():
            worker.stop_worker()
        self.logger.info("Stopped all workers")
    
    def start_server(self, name: str):
        """Start a specific server worker."""
        if name in self.workers:
            self.workers[name].manual_stop_requested = False
            self.workers[name].start_worker()
            self.logger.info(f"Started worker for {name}")
    
    def stop_server(self, name: str):
        """Stop a specific server worker."""
        if name in self.workers:
            self.workers[name].stop_worker()
            self.logger.info(f"Stopped worker for {name}")
    
    def restart_server(self, name: str):
        """Restart a specific server's process."""
        if name in self.workers:
            self.workers[name].request_restart()
            self.logger.info(f"Requested restart for {name}")
    
    def force_restart_server(self, name: str):
        """Force restart a specific server's process (even if External)."""
        if name in self.workers:
            self.workers[name].force_restart()
            self.logger.info(f"Requested force restart for {name}")
    
    def add_server(self, config: ServerConfig):
        """Add a new server configuration."""
        # Check for duplicate name
        if any(c.name == config.name for c in self.configs):
            raise ValueError(f"Server with name '{config.name}' already exists")
        
        self.configs.append(config)
        save_servers(self.configs)
        
        # Create worker
        worker = ServerWorker(config, self.ui_queue)
        self.workers[config.name] = worker
        
        self.logger.info(f"Added server: {config.name}")
    
    def edit_server(self, old_name: str, new_config: ServerConfig):
        """Edit an existing server configuration."""
        # Find and update config
        for i, config in enumerate(self.configs):
            if config.name == old_name:
                # If name changed, check for duplicate
                if new_config.name != old_name:
                    if any(c.name == new_config.name for c in self.configs):
                        raise ValueError(f"Server with name '{new_config.name}' already exists")
                
                # Stop old worker if running
                if old_name in self.workers:
                    self.workers[old_name].stop_worker()
                    del self.workers[old_name]
                
                # Update config
                self.configs[i] = new_config
                save_servers(self.configs)
                
                # Create new worker
                worker = ServerWorker(new_config, self.ui_queue)
                self.workers[new_config.name] = worker
                
                self.logger.info(f"Edited server: {old_name} -> {new_config.name}")
                return
        
        raise ValueError(f"Server '{old_name}' not found")
    
    def delete_server(self, name: str):
        """Delete a server configuration."""
        # Stop worker if running
        if name in self.workers:
            self.workers[name].stop_worker()
            del self.workers[name]
        
        # Remove from configs
        self.configs = [c for c in self.configs if c.name != name]
        save_servers(self.configs)
        
        self.logger.info(f"Deleted server: {name}")
    
    def test_connection(self, config: ServerConfig) -> tuple[bool, dict]:
        """Test SSH connection to a server without starting it."""
        try:
            ssh = SSHClient(config.host, config.port, config.username, config.auth)
            success, error = ssh.connect()
            
            if not success:
                return False, {"error": error}
            
            # Gather info
            success, info = ssh.test_connection()
            ssh.close()
            
            return success, info
        except Exception as e:
            return False, {"error": str(e)}
    
    def get_worker_state(self, name: str) -> Optional[ServerState]:
        """Get current state of a worker."""
        if name in self.workers:
            return self.workers[name].state
        return None
    
    def get_all_states(self) -> Dict[str, ServerState]:
        """Get states of all workers."""
        return {name: worker.state for name, worker in self.workers.items()}
