"""Server worker thread that monitors and auto-restarts remote processes."""
import threading
import time
import select
from datetime import datetime
from queue import Queue
from typing import Optional
from models import ServerConfig, ServerState, ServerStatus
from ssh_client import SSHClient
from logging_setup import get_server_logger


class ServerWorker:
    """Worker thread that manages a single server's process lifecycle."""
    
    def __init__(self, config: ServerConfig, ui_queue: Queue):
        self.config = config
        self.state = ServerState()
        self.ui_queue = ui_queue
        self.logger = get_server_logger(config.name)
        
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.ssh: Optional[SSHClient] = None
        self.channel = None
        self.process_start_time: Optional[float] = None
        
        self.manual_stop_requested = False  # Track if user requested stop
        self._last_liveness_check: float = 0.0  # For periodic external liveness checks
        # Metrics sampling state
        self._last_metrics_time: float = 0.0
        self._prev_cpu_total: Optional[int] = None
        self._prev_cpu_idle: Optional[int] = None
        
        # Health check tracking
        self._cpu_below_threshold_start: Optional[float] = None
        self._gpu_below_threshold_start: Optional[float] = None
        self._last_cpu_value: Optional[float] = None
        self._last_gpu_value: Optional[float] = None
    
    def start_worker(self):
        """Start the worker thread."""
        if self.thread and self.thread.is_alive():
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()
        self.logger.info(f"Worker thread started for {self.config.name}")
    
    def stop_worker(self):
        """Stop the worker thread gracefully."""
        self.running = False
        self.manual_stop_requested = True
        
        # Kill remote process if running
        if self.ssh and self.ssh.is_connected():
            self.logger.info("Stopping remote process...")
            self.ssh.kill_process(self.config.stop_command)
        
        if self.channel:
            try:
                self.channel.close()
            except:
                pass
        
        if self.ssh:
            self.ssh.close()
        
        self._update_state(ServerStatus.STOPPED, pid=None, error="Manually stopped")
        self.logger.info(f"Worker stopped for {self.config.name}")
    
    def request_restart(self):
        """Request a restart of the remote process."""
        self.logger.info("Restart requested")
        self.manual_stop_requested = False
        
        # Kill current process
        if self.ssh and self.ssh.is_connected():
            self.ssh.kill_process(self.config.stop_command)
        
        if self.channel:
            try:
                self.channel.close()
            except:
                pass
        
        self._update_state(ServerStatus.STOPPED, error="Restarting...")
    
    def force_restart(self):
        """Force restart even if process is External."""
        self.logger.info("Force restart requested")
        self.manual_stop_requested = False
        
        if self.ssh and self.ssh.is_connected():
            self.ssh.kill_process(self.config.stop_command)
            time.sleep(2)  # Give it time to die
        
        self._update_state(ServerStatus.STOPPED, pid=None, error="Force restarting...")
    
    def _worker_loop(self):
        """Main worker loop - runs in background thread."""
        self.logger.info("Worker loop started")
        
        while self.running:
            try:
                # Check if server is enabled
                if not self.config.enabled:
                    self._update_state(ServerStatus.STOPPED, error="Disabled")
                    time.sleep(5)
                    continue
                
                # State machine
                if self.state.status == ServerStatus.DISCONNECTED:
                    self._handle_disconnected()
                elif self.state.status == ServerStatus.CONNECTING:
                    self._handle_connecting()
                elif self.state.status == ServerStatus.RUNNING:
                    self._handle_running()
                elif self.state.status in [ServerStatus.STOPPED, ServerStatus.ERROR]:
                    if not self.manual_stop_requested:
                        self._handle_restart_delay()
                    else:
                        time.sleep(1)
                elif self.state.status == ServerStatus.EXTERNAL:
                    # External process detected - poll for liveness and take over when it stops
                    self._handle_external()
                
            except Exception as e:
                self.logger.error(f"Worker loop error: {e}")
                self._update_state(ServerStatus.ERROR, error=str(e))
                time.sleep(self.state.backoff_seconds)
        
        self.logger.info("Worker loop ended")
    
    def _handle_disconnected(self):
        """Handle disconnected state - attempt to connect."""
        self.logger.info(f"Attempting to connect (backoff: {self.state.backoff_seconds}s)...")
        self._update_state(ServerStatus.CONNECTING)
        
        time.sleep(self.state.backoff_seconds)
        
        # Create SSH client and attempt connection
        self.ssh = SSHClient(
            self.config.host,
            self.config.port,
            self.config.username,
            self.config.auth
        )
        
        success, error = self.ssh.connect()
        
        if success:
            self.logger.info("SSH connection established")
            self.state.reset_backoff()
            
            # Check if process is already running
            pid, cmd = self.ssh.detect_running_process(self.config.process_match_regex)
            
            if pid:
                self.logger.warning(f"Process already running (PID: {pid}): {cmd}")
                self._update_state(ServerStatus.EXTERNAL, pid=pid, error="Process already running (not started by us)")
            else:
                # Start the process
                self._start_process()
        else:
            self.logger.error(f"Connection failed: {error}")
            self._update_state(ServerStatus.DISCONNECTED, error=error)
            self.state.increase_backoff()
            
            if self.ssh:
                self.ssh.close()
                self.ssh = None
    
    def _handle_connecting(self):
        """Handle connecting state (transitional)."""
        time.sleep(0.5)
    
    def _handle_running(self):
        """Handle running state - monitor process output."""
        if not self.channel or not self.ssh or not self.ssh.is_connected():
            self.logger.warning("Lost connection while running")
            self._update_state(ServerStatus.DISCONNECTED, pid=None, error="Connection lost")
            if self.ssh:
                self.ssh.close()
                self.ssh = None
            return
        
        # Update uptime
        if self.process_start_time:
            self.state.uptime_seconds = int(time.time() - self.process_start_time)
            self._push_update()
        
        # Periodic PID refresh (do not treat as fatal if not found)
        now = time.time()
        if now - self._last_liveness_check > 5:
            self._last_liveness_check = now
            if self.state.pid is None and self.ssh and self.ssh.is_connected():
                pid, _ = self.ssh.detect_running_process(self.config.process_match_regex)
                if pid:
                    self.logger.info(f"Captured PID via pgrep: {pid}")
                    self._update_state(ServerStatus.RUNNING, pid=pid)
        
        # Check if channel has data or closed
        try:
            # Non-blocking check for data
            if self.channel.recv_ready():
                data = self.channel.recv(4096)
                if data:
                    text = data.decode('utf-8', errors='replace')
                    for line in text.splitlines():
                        if line.strip():
                            self.logger.info(f"[STDOUT] {line}")
                            self._push_log_line(line, "stdout")
            
            if self.channel.recv_stderr_ready():
                data = self.channel.recv_stderr(4096)
                if data:
                    text = data.decode('utf-8', errors='replace')
                    for line in text.splitlines():
                        if line.strip():
                            self.logger.warning(f"[STDERR] {line}")
                            self._push_log_line(line, "stderr")
            
            # Check if process exited
            if self.channel.exit_status_ready():
                exit_code = self.channel.recv_exit_status()
                self.logger.info(f"Process exited with code {exit_code}")
                
                if exit_code == 0:
                    self._update_state(ServerStatus.STOPPED, pid=None, error=f"Exited with code {exit_code}")
                else:
                    self._update_state(ServerStatus.ERROR, pid=None, error=f"Exited with code {exit_code}")
                
                self.channel.close()
                self.channel = None
                return
            
            # Small delay to avoid busy-waiting
            time.sleep(0.1)
        
        except Exception as e:
            self.logger.error(f"Error reading process output: {e}")
            self._update_state(ServerStatus.ERROR, pid=None, error=str(e))
            if self.channel:
                try:
                    self.channel.close()
                except:
                    pass
                self.channel = None
        
        # Metrics sampling (1s cadence) when connected
        self._maybe_sample_metrics()
    
    def _handle_external(self):
        """Poll external process; when it stops, start managed process."""
        if not self.ssh or not self.ssh.is_connected():
            # Connection lost; transition to disconnected
            self._update_state(ServerStatus.DISCONNECTED, error="Connection lost")
            if self.ssh:
                try:
                    self.ssh.close()
                except:
                    pass
                self.ssh = None
            time.sleep(1)
            return
        
        # Poll every 2 seconds for the presence of the external process
        pid, _ = self.ssh.detect_running_process(self.config.process_match_regex)
        if pid:
            # Still running externally; keep status and sleep
            if self.state.pid != pid:
                # Update PID if it changed (e.g., external restart)
                self._update_state(ServerStatus.EXTERNAL, pid=pid)
            time.sleep(2)
            return
        
        # External process is gone - take over after the configured delay
        self.logger.info("External process ended - taking over and starting managed process")
        self._update_state(ServerStatus.STOPPED, pid=None, error="External process ended")
        self._handle_restart_delay()
        
        # Also sample metrics while external is running/when connected
        self._maybe_sample_metrics()
    
    def _handle_restart_delay(self):
        """Handle restart delay before restarting process."""
        delay = self.config.restart_delay_seconds
        self.logger.info(f"Waiting {delay} seconds before restart...")
        
        for i in range(delay):
            if not self.running or self.manual_stop_requested:
                return
            time.sleep(1)
        
        # Attempt restart
        if self.ssh and self.ssh.is_connected():
            self._start_process()
        else:
            self._update_state(ServerStatus.DISCONNECTED, error="Connection lost, reconnecting...")
    
    def _start_process(self):
        """Start the remote process."""
        if not self.ssh or not self.ssh.is_connected():
            self.logger.error("Cannot start process - not connected")
            self._update_state(ServerStatus.DISCONNECTED, error="Not connected")
            return
        
        self.logger.info(f"Starting process: {self.config.command}")
        
        # Verify script exists (optional but helpful)
        script_parts = self.config.command.split()
        if len(script_parts) >= 2 and script_parts[-1].endswith('.py'):
            script_path = script_parts[-1]
            if not script_path.startswith('/'):
                script_path = f"{self.config.working_dir}/{script_path}"
            
            if not self.ssh.verify_script_exists(script_path):
                error_msg = f"Script not found: {script_path}"
                self.logger.error(error_msg)
                self._update_state(ServerStatus.ERROR, error=error_msg)
                return
        
        # Execute command
        # Prepend pre_command if provided (activate env, etc.)
        cmd_to_run = self.config.command
        
        success, channel, error = self.ssh.exec_command(
            cmd_to_run,
            self.config.working_dir,
            self.config.env,
            pre_command=self.config.pre_command
        )
        
        if not success:
            self.logger.error(f"Failed to start process: {error}")
            self._update_state(ServerStatus.ERROR, error=error)
            return
        
        self.channel = channel
        self.process_start_time = time.time()
        self._last_liveness_check = time.time()
        
        # Try to get PID
        time.sleep(1)  # Give process time to start
        pid, cmd = self.ssh.detect_running_process(self.config.process_match_regex)
        
        self.state.restarts_count += 1
        self.state.last_restart_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.logger.info(f"Process started (PID: {pid if pid else 'unknown'})")
        self._update_state(ServerStatus.RUNNING, pid=pid, error=None)
        # Reset CPU baseline so first sample computes correctly
        self._prev_cpu_total = None
        self._prev_cpu_idle = None
    
    def _update_state(self, status: ServerStatus, pid: Optional[int] = None, error: Optional[str] = None):
        """Update internal state and notify UI."""
        self.state.status = status
        
        if pid is not None:
            self.state.pid = pid
        
        if error is not None:
            self.state.last_error = error
        
        if status == ServerStatus.RUNNING:
            self.state.last_error = None
        elif status in [ServerStatus.STOPPED, ServerStatus.ERROR]:
            self.state.pid = None
            self.state.uptime_seconds = 0
        
        self._push_update()
    
    def _push_update(self):
        """Push state update to UI queue."""
        try:
            self.ui_queue.put({
                'type': 'state_update',
                'server': self.config.name,
                'state': self.state
            })
        except:
            pass
    
    def _push_log_line(self, line: str, stream: str):
        """Push log line to UI queue."""
        try:
            self.ui_queue.put({
                'type': 'log_line',
                'server': self.config.name,
                'line': line,
                'stream': stream,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        except:
            pass
    
    # ------------------------------ Metrics ------------------------------
    def _maybe_sample_metrics(self):
        now = time.time()
        if not self.ssh or not self.ssh.is_connected():
            return
        # 1-second cadence
        if now - self._last_metrics_time < 1.0:
            return
        self._last_metrics_time = now
        
        cpu = self._sample_cpu()
        ram_used_mb, ram_total_mb = self._sample_ram()
        gpu_util, gpu_mem_used_mb, gpu_mem_total_mb = self._sample_gpu()
        
        # Store for health checks
        self._last_cpu_value = cpu
        self._last_gpu_value = gpu_util
        
        # Evaluate health checks
        self._evaluate_health_checks(cpu, gpu_util)
        
        # Persist
        try:
            from metrics_db import insert_metric
            insert_metric(
                self.config.name,
                int(time.time()),
                cpu,
                ram_used_mb,
                ram_total_mb,
                gpu_util,
                gpu_mem_used_mb,
                gpu_mem_total_mb
            )
        except Exception as e:
            # Swallow DB errors to not impact worker
            self.logger.warning(f"Metrics DB insert failed: {e}")
        
        # Push to UI
        try:
            self.ui_queue.put({
                'type': 'metrics_update',
                'server': self.config.name,
                'metrics': {
                    'cpu': cpu,
                    'ram_used_mb': ram_used_mb,
                    'ram_total_mb': ram_total_mb,
                    'gpu_util': gpu_util,
                    'gpu_mem_used_mb': gpu_mem_used_mb,
                    'gpu_mem_total_mb': gpu_mem_total_mb
                }
            })
        except:
            pass
    
    def _sample_cpu(self):
        # Read /proc/stat and compute CPU usage delta
        try:
            ok, out, err = self.ssh.run_simple("cat /proc/stat | head -n1", timeout=3)
            if not ok or not out:
                return None
            parts = out.strip().split()
            if parts[0] != 'cpu':
                return None
            nums = list(map(int, parts[1:]))
            # Total time is sum of all fields
            total = sum(nums)
            # idle = idle + iowait (fields 4 and 5)
            idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
            if self._prev_cpu_total is None:
                self._prev_cpu_total = total
                self._prev_cpu_idle = idle
                return None
            dt_total = total - self._prev_cpu_total
            dt_idle = idle - self._prev_cpu_idle
            self._prev_cpu_total = total
            self._prev_cpu_idle = idle
            if dt_total <= 0:
                return None
            usage = 100.0 * (1.0 - (dt_idle / dt_total))
            return max(0.0, min(100.0, usage))
        except Exception:
            return None
    
    def _sample_ram(self):
        try:
            ok, out, err = self.ssh.run_simple("cat /proc/meminfo", timeout=3)
            if not ok or not out:
                return None, None
            meminfo = {}
            for line in out.splitlines():
                if ':' in line:
                    k, v = line.split(':', 1)
                    meminfo[k.strip()] = v.strip()
            def parse_kb(key):
                val = meminfo.get(key)
                if not val:
                    return None
                num = ''.join(ch for ch in val if ch.isdigit())
                return int(num) if num else None
            total_kb = parse_kb('MemTotal')
            avail_kb = parse_kb('MemAvailable')
            if total_kb is None or avail_kb is None:
                return None, None
            used_mb = (total_kb - avail_kb) / 1024.0
            total_mb = total_kb / 1024.0
            return round(used_mb, 1), round(total_mb, 1)
        except Exception:
            return None, None
    
    def _sample_gpu(self):
        try:
            ok, out, err = self.ssh.run_simple(
                "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits",
                timeout=4
            )
            if not ok or not out:
                return None, None, None
            # If multiple GPUs, take the first line
            line = out.strip().splitlines()[0]
            parts = [p.strip() for p in line.split(',')]
            util = float(parts[0]) if parts and parts[0] else None
            mem_used = float(parts[1]) if len(parts) > 1 and parts[1] else None
            mem_total = float(parts[2]) if len(parts) > 2 and parts[2] else None
            return util, mem_used, mem_total
        except Exception:
            return None, None, None
    
    def _evaluate_health_checks(self, cpu: Optional[float], gpu_util: Optional[float]):
        """Evaluate health check rules and trigger restart if conditions met."""
        if not self.config.health_check_enabled:
            return
        
        # Only check when process is RUNNING
        if self.state.status != ServerStatus.RUNNING:
            # Reset timers if not running
            self._cpu_below_threshold_start = None
            self._gpu_below_threshold_start = None
            return
        
        now = time.time()
        
        # CPU health check
        if self.config.health_check_cpu_enabled and cpu is not None:
            if cpu < self.config.health_check_cpu_threshold:
                # CPU below threshold
                if self._cpu_below_threshold_start is None:
                    self._cpu_below_threshold_start = now
                    self.logger.info(f"CPU below threshold ({cpu:.1f}% < {self.config.health_check_cpu_threshold}%) - monitoring started")
                else:
                    duration = now - self._cpu_below_threshold_start
                    if duration >= self.config.health_check_cpu_duration:
                        # Threshold exceeded - trigger restart
                        self.logger.warning(f"Health check failed: CPU below {self.config.health_check_cpu_threshold}% for {duration:.0f}s - restarting process")
                        self._trigger_health_restart("CPU usage too low")
                        return
            else:
                # CPU back above threshold - reset
                if self._cpu_below_threshold_start is not None:
                    self.logger.info(f"CPU back above threshold ({cpu:.1f}% >= {self.config.health_check_cpu_threshold}%)")
                self._cpu_below_threshold_start = None
        
        # GPU health check
        if self.config.health_check_gpu_enabled and gpu_util is not None:
            if gpu_util < self.config.health_check_gpu_threshold:
                # GPU below threshold
                if self._gpu_below_threshold_start is None:
                    self._gpu_below_threshold_start = now
                    self.logger.info(f"GPU below threshold ({gpu_util:.1f}% < {self.config.health_check_gpu_threshold}%) - monitoring started")
                else:
                    duration = now - self._gpu_below_threshold_start
                    if duration >= self.config.health_check_gpu_duration:
                        # Threshold exceeded - trigger restart
                        self.logger.warning(f"Health check failed: GPU below {self.config.health_check_gpu_threshold}% for {duration:.0f}s - restarting process")
                        self._trigger_health_restart("GPU usage too low")
                        return
            else:
                # GPU back above threshold - reset
                if self._gpu_below_threshold_start is not None:
                    self.logger.info(f"GPU back above threshold ({gpu_util:.1f}% >= {self.config.health_check_gpu_threshold}%)")
                self._gpu_below_threshold_start = None
    
    def _trigger_health_restart(self, reason: str):
        """Trigger a restart due to health check failure."""
        self.logger.info(f"Health check triggered restart: {reason}")
        
        # Kill current process
        if self.ssh and self.ssh.is_connected():
            self.ssh.kill_process(self.config.stop_command)
        
        if self.channel:
            try:
                self.channel.close()
            except:
                pass
            self.channel = None
        
        # Reset health check timers
        self._cpu_below_threshold_start = None
        self._gpu_below_threshold_start = None
        
        self._update_state(ServerStatus.STOPPED, pid=None, error=f"Health check: {reason}")
