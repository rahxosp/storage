"""SSH client wrapper using Paramiko."""
import paramiko
import os
from typing import Optional, Tuple
import time


class SSHClient:
    """Wrapper around paramiko.SSHClient with keepalive and convenience methods."""
    
    def __init__(self, host: str, port: int, username: str, auth: dict):
        self.host = host
        self.port = port
        self.username = username
        self.auth = auth
        self.client: Optional[paramiko.SSHClient] = None
        self.transport: Optional[paramiko.Transport] = None
    
    def connect(self) -> Tuple[bool, Optional[str]]:
        """Connect to the remote server. Returns (success, error_message)."""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': self.host,
                'port': self.port,
                'username': self.username,
                'timeout': 15,
                'banner_timeout': 30
            }
            
            # Handle authentication
            if self.auth.get('type') == 'key':
                key_path = self.auth.get('key_path', '')
                # Normalize Windows path
                key_path = key_path.replace('\\', '/')
                
                if not os.path.exists(key_path):
                    return False, f"Private key not found: {key_path}"
                
                passphrase = self.auth.get('passphrase')
                
                # Try to load the key
                try:
                    if key_path.endswith('.pem') or 'rsa' in key_path.lower():
                        pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
                    else:
                        # Auto-detect key type
                        try:
                            pkey = paramiko.RSAKey.from_private_key_file(key_path, password=passphrase)
                        except:
                            try:
                                pkey = paramiko.Ed25519Key.from_private_key_file(key_path, password=passphrase)
                            except:
                                pkey = paramiko.ECDSAKey.from_private_key_file(key_path, password=passphrase)
                    
                    connect_kwargs['pkey'] = pkey
                except Exception as e:
                    return False, f"Failed to load private key: {str(e)}"
            
            elif self.auth.get('type') == 'password':
                password = self.auth.get('password')
                if not password:
                    return False, "Password is required but not provided"
                connect_kwargs['password'] = password
            else:
                return False, f"Unknown auth type: {self.auth.get('type')}"
            
            # Connect
            self.client.connect(**connect_kwargs)
            
            # Enable keepalive
            self.transport = self.client.get_transport()
            if self.transport:
                self.transport.set_keepalive(30)
            
            return True, None
        
        except paramiko.AuthenticationException as e:
            return False, f"Authentication failed: {str(e)}"
        except paramiko.SSHException as e:
            return False, f"SSH error: {str(e)}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def is_connected(self) -> bool:
        """Check if connection is still alive."""
        if not self.client or not self.transport:
            return False
        return self.transport.is_active()
    
    def close(self):
        """Close the SSH connection."""
        if self.client:
            try:
                self.client.close()
            except:
                pass
            self.client = None
            self.transport = None
    
    def run_simple(self, command: str, timeout: int = 10) -> Tuple[bool, str, str]:
        """
        Run a simple command and return (success, stdout, stderr).
        For quick checks and status commands.
        """
        if not self.is_connected():
            return False, "", "Not connected"
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            stdout_text = stdout.read().decode('utf-8', errors='replace')
            stderr_text = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()
            
            return exit_code == 0, stdout_text, stderr_text
        except Exception as e:
            return False, "", str(e)
    
    def exec_command(self, command: str, working_dir: str, env: dict, pre_command: str = ""):
        """
        Execute a command and return the channel for streaming output.
        Command is run via bash -lc to ensure login environment.
        Returns (success, channel, error_message).
        """
        if not self.is_connected():
            return False, None, "Not connected"
        
        try:
            # Build environment variables string
            env_str = " ".join([f"{k}={v}" for k, v in env.items()])
            
            # Pre-command (e.g., activate venv/conda) should run before env and python
            pre = f"{pre_command} && " if pre_command.strip() else ""
            
            # Build full command with login shell, working dir, pre, env, and unbuffered Python
            full_command = f"bash -lc 'cd {working_dir} && {pre}{env_str} PYTHONUNBUFFERED=1 {command}'"
            
            # Execute without pseudo-terminal (no pty)
            stdin, stdout, stderr = self.client.exec_command(full_command, get_pty=False)
            
            # Return the channel for streaming reads
            channel = stdout.channel
            return True, channel, None
        
        except Exception as e:
            return False, None, str(e)
    
    def test_connection(self) -> Tuple[bool, dict]:
        """
        Test connection and gather system info.
        Returns (success, info_dict).
        """
        if not self.is_connected():
            return False, {"error": "Not connected"}
        
        info = {}
        
        # Get OS info
        success, stdout, stderr = self.run_simple("uname -a")
        if success:
            info["os"] = stdout.strip()
        else:
            info["os"] = "Unknown"
        
        # Check for Python
        success, stdout, stderr = self.run_simple("which python3 || which python")
        if success and stdout.strip():
            info["python"] = stdout.strip()
            # Get Python version
            python_cmd = stdout.strip()
            success, stdout, stderr = self.run_simple(f"{python_cmd} --version")
            if success:
                info["python_version"] = stdout.strip() or stderr.strip()
        else:
            info["python"] = "Not found"
        
        # Check working directory
        success, stdout, stderr = self.run_simple("pwd")
        if success:
            info["current_dir"] = stdout.strip()
        
        return True, info
    
    def detect_running_process(self, process_regex: str) -> Tuple[Optional[int], Optional[str]]:
        """
        Detect if a process matching the regex is running.
        Returns (pid, command_line) or (None, None).
        """
        if not self.is_connected():
            return None, None
        
        try:
            # Prefer pgrep if available
            command = f"pgrep -af '{process_regex}' 2>/dev/null || true"
            success, stdout, stderr = self.run_simple(command, timeout=5)
            
            if stdout.strip():
                # Parse output: "PID command line"
                lines = stdout.strip().split('\n')
                for line in lines:
                    parts = line.split(None, 1)
                    if len(parts) >= 1:
                        try:
                            pid = int(parts[0])
                            cmd = parts[1] if len(parts) > 1 else ""
                            if 'pgrep' not in cmd:
                                return pid, cmd
                        except ValueError:
                            continue
            
            # Fallback to ps + grep if pgrep yielded nothing
            fallback_cmd = (
                "ps -eo pid,command 2>/dev/null | "
                f"grep -E -i '{process_regex}' | grep -v grep | head -n 1"
            )
            success2, stdout2, stderr2 = self.run_simple(fallback_cmd, timeout=6)
            if stdout2.strip():
                parts = stdout2.strip().split(None, 1)
                if parts:
                    try:
                        pid = int(parts[0])
                        cmd = parts[1] if len(parts) > 1 else ""
                        return pid, cmd
                    except ValueError:
                        pass
            
            return None, None
        except Exception:
            return None, None
    
    def kill_process(self, stop_command: str) -> bool:
        """Execute the stop command to kill the process."""
        if not self.is_connected():
            return False
        
        try:
            success, stdout, stderr = self.run_simple(stop_command, timeout=10)
            # Give it a moment
            time.sleep(1)
            return True
        except:
            return False
    
    def verify_script_exists(self, script_path: str) -> bool:
        """Check if the script file exists on the remote server."""
        if not self.is_connected():
            return False
        
        success, stdout, stderr = self.run_simple(f"test -f {script_path} && echo 'exists'")
        return success and 'exists' in stdout
