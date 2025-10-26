# Health Check Feature

## Overview
The health check feature monitors CPU and GPU usage and automatically restarts processes that appear to be stuck or idle.

## Features

### 1. Configurable Thresholds
- **CPU Monitoring**: Restart if CPU usage stays below a threshold for a specified duration
- **GPU Monitoring**: Restart if GPU usage stays below a threshold for a specified duration

### 2. Per-Server Configuration
Each server can have its own health check rules configured independently.

### 3. Smart Detection
- Only monitors when process status is RUNNING
- Tracks duration continuously (resets when usage goes above threshold)
- Logs when monitoring starts and when thresholds are exceeded

## Configuration

### UI Settings
In the Add/Edit Server dialog, you'll find a "Health Checks" section with:

1. **Enable Health Checks** - Master toggle for health monitoring
2. **Monitor CPU Usage** - Enable CPU-based health checks
   - Threshold: CPU percentage (0-100%)
   - Duration: Time in seconds below threshold before restart
3. **Monitor GPU Usage** - Enable GPU-based health checks
   - Threshold: GPU percentage (0-100%)
   - Duration: Time in seconds below threshold before restart

### Example Configuration
**Use Case**: GPU worker that should always be processing
- Enable Health Checks: ✓
- Monitor GPU Usage: ✓
- Restart if GPU < 5% for 100 seconds

This will restart the process if GPU usage drops below 5% and stays there for 100 consecutive seconds.

## How It Works

### Monitoring Loop
1. Every second, the worker samples CPU and GPU metrics
2. If health checks are enabled and process is RUNNING:
   - Compare current usage against thresholds
   - Track how long usage has been below threshold
   - Trigger restart if duration exceeded

### Restart Process
When health check fails:
1. Log warning with reason (CPU/GPU too low)
2. Kill the remote process using stop_command
3. Close SSH channel
4. Update status to STOPPED with health check error
5. Normal restart cycle begins after restart_delay_seconds

### Reset Conditions
Timers reset when:
- Usage goes back above threshold (process recovers)
- Process stops or disconnects
- Server is manually stopped

## Logs

Health check events are logged:
```
[INFO] GPU below threshold (2.0% < 5.0%) - monitoring started
[WARNING] Health check failed: GPU below 5.0% for 100s - restarting process
```

## Best Practices

1. **Set realistic thresholds**: Don't set too high or processes will restart unnecessarily
2. **Allow sufficient duration**: Give processes time to legitimately idle (e.g., waiting for tasks)
3. **Start conservative**: Begin with longer durations (100-300s) and adjust based on behavior
4. **Monitor logs**: Watch restart reasons to tune settings

## Example Scenarios

### Scenario 1: GPU Worker (Redis-based)
Problem: Worker silently stops processing when Redis connection fails
Solution:
- Monitor GPU Usage: ✓
- Threshold: 10%
- Duration: 100 seconds
- Rationale: GPU should be active if tasks are processing

### Scenario 2: CPU-intensive Worker
Problem: Worker hangs on network calls
Solution:
- Monitor CPU Usage: ✓
- Threshold: 30%
- Duration: 120 seconds
- Rationale: Should maintain reasonable CPU if working

### Scenario 3: Mixed Workload
Solution: Enable both CPU and GPU monitoring with appropriate thresholds for your workload

## Notes

- Health checks only run when metrics are successfully sampled
- If SSH connection fails, health checks are paused
- Health check restarts count toward total restart count
- Works with the existing backoff and retry logic
