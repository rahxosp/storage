# Server Manager

A Python + Tkinter application for managing and monitoring remote server processes via SSH. Automatically restarts processes when they crash or when servers reboot.

## Features

- **Remote Process Management**: Start, stop, and restart processes on multiple servers via SSH
- **Auto-Restart**: Automatically restart processes when they crash or exit (configurable delay: default 12 seconds)
- **Connection Recovery**: Automatically reconnect when servers reboot or network is restored
- **Live Monitoring**: Real-time status, PID, uptime, and error tracking
- **Log Viewing**: View and search through process logs with syntax highlighting
- **Flexible Authentication**: Support for SSH key-based and password authentication
- **Custom Commands**: Configure any command to run per server (e.g., Python scripts, Docker containers)
- **GUI Management**: Easy-to-use Tkinter interface with server list, actions, and log viewer

## Prerequisites

- **Python 3.7+** installed on Windows
- **SSH access** to your remote servers
- **Private SSH keys** (optional but recommended) stored locally

## Installation

### 1. Navigate to the ServerManager directory

```powershell
cd D:\xampp3\htdocs\storage\ServerManager
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

If you get an execution policy error, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

## Configuration

The application uses `servers.json` for configuration. On first run, a default configuration file will be created with an example server.

### Example `servers.json`:

```json
{
  "servers": [
    {
      "name": "server-1",
      "host": "113.201.14.131",
      "port": 43857,
      "username": "root",
      "auth": {
        "type": "key",
        "key_path": "C:/Users/AJU/.ssh/vast",
        "passphrase": null
      },
      "command": "python3 /home/v13/ultra_aggressive_worker.py",
      "working_dir": "/home/v13",
      "env": {},
      "restart_delay_seconds": 12,
      "enabled": true,
      "stop_command": "pkill -f ultra_aggressive_worker.py"
    }
  ]
}
```

### Configuration Fields

- **name**: Unique identifier for the server
- **host**: Server IP address or hostname
- **port**: SSH port (usually 22 or custom)
- **username**: SSH username
- **auth**: Authentication details
  - **type**: `"key"` for private key or `"password"` for password
  - **key_path**: Path to private SSH key file (for key auth)
  - **passphrase**: Optional passphrase for encrypted keys
  - **password**: Password (for password auth)
- **command**: Command to execute (e.g., `python3 /home/v13/ultra_aggressive_worker.py`)
- **working_dir**: Directory to run the command in
- **env**: Environment variables (key-value pairs)
- **restart_delay_seconds**: Seconds to wait before restarting after crash (default: 12)
- **enabled**: Whether this server is enabled
- **stop_command**: Command to kill the process (default uses `pkill`)

### Docker Support

To run commands inside Docker containers, set the command like:

```json
"command": "docker exec -i my_container python3 /home/v13/ultra_aggressive_worker.py"
```

## Usage

### Start the Application

```powershell
python main.py
```

### Main Window

The main window shows a table with all configured servers and their status:

- **Name**: Server identifier
- **Host:Port**: Connection details
- **Status**: Current status (Disconnected, Connecting, Running, Stopped, Error, External)
- **PID**: Process ID (if running)
- **Uptime**: How long the process has been running
- **Restarts**: Number of times the process has restarted
- **Last Restart**: Timestamp of last restart
- **Last Error**: Most recent error message

### Toolbar Actions

- **Add Server**: Add a new server configuration
- **Edit**: Edit selected server
- **Delete**: Delete selected server
- **Test Connection**: Test SSH connection without starting the process
- **Start**: Start monitoring and running the process
- **Stop**: Stop the process and worker
- **Restart**: Restart the process after the configured delay
- **Force Restart**: Kill and restart even if an external process is detected
- **View Logs**: Open log viewer for selected server
- **Open Logs Folder**: Open the logs directory
- **Start All**: Start all enabled servers
- **Stop All**: Stop all servers

### Right-Click Context Menu

Right-click any server in the list for quick access to actions.

## Monitoring Behavior

### Process States

- **Disconnected**: Not connected to server; will retry with exponential backoff (5, 10, 20, 40, 60 seconds)
- **Connecting**: Connection attempt in progress
- **Running**: Process is running and being monitored
- **Stopped**: Process exited normally; will restart after delay
- **Error**: Process crashed or error occurred; will restart after delay
- **External**: A matching process is already running but not started by this app

### Auto-Restart Logic

1. When a process exits (any reason), wait `restart_delay_seconds` (default: 12)
2. Restart the process automatically
3. Repeat indefinitely unless manually stopped

### Connection Recovery

- If SSH connection drops (network issue, server reboot), the worker enters **Disconnected** state
- Automatic reconnection with backoff: 5s → 10s → 20s → 40s → 60s (capped at 60s)
- On reconnect, checks if process is already running (External state) or starts a new one

### Duplicate Process Detection

- On connect/reconnect, the app checks if a process matching your command is already running
- If found, it marks the server as **External** and doesn't start a duplicate
- Use **Force Restart** to kill the external process and start a fresh one under monitoring

## Logs

- Logs are stored in the `logs/` directory
- Each server gets its own log file: `logs/{server-name}-YYYYMMDD.log`
- Logs rotate at 10 MB with 5 backups
- Combined stdout and stderr from the remote process
- Includes lifecycle events (connect, start, stop, errors)

### Log Viewer

- Click **View Logs** to open a live log viewer
- Features:
  - Last 500 lines displayed
  - Refresh and Clear buttons
  - Search with highlighting
  - Auto-scroll toggle
  - Syntax highlighting (errors in red, warnings in orange)

## Troubleshooting

### SSH Key Issues

**Error: "Private key not found"**
- Ensure the `key_path` in `servers.json` uses forward slashes: `C:/Users/AJU/.ssh/vast`
- Verify the key file exists at that path

**Error: "Failed to load private key"**
- If your key has a passphrase, add it to the config: `"passphrase": "your_passphrase"`
- Try converting key format if needed: `ssh-keygen -p -m PEM -f ~/.ssh/vast`

### Connection Issues

**Status stays "Disconnected"**
- Check that the host and port are correct
- Verify SSH service is running on the remote server: `ssh -i key_path -p port user@host`
- Check firewall rules

**Authentication fails**
- Verify username is correct
- For key auth, ensure the public key is in `~/.ssh/authorized_keys` on the server
- For password auth, double-check the password

### Process Issues

**Process shows "External" status**
- A process matching your command is already running
- Use **Force Restart** to kill it and start fresh
- Or manually SSH and kill it: `pkill -f ultra_aggressive_worker.py`

**Process keeps crashing immediately**
- Check logs for errors
- Verify the script path is correct on the server
- Ensure Python and dependencies are installed on the server
- Check working directory and permissions

**Script not found error**
- Verify `command` and `working_dir` are correct
- SSH manually and check: `test -f /home/v13/ultra_aggressive_worker.py && echo exists`

### Windows-Specific

**Virtual environment activation fails**
- Run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**Can't open logs folder**
- Manually navigate to `D:\xampp3\htdocs\storage\ServerManager\logs\`

## Tips

- **Test Connection** before starting to catch configuration errors early
- Use **Force Restart** if you manually killed a process and it shows "External"
- Adjust `restart_delay_seconds` per server (10-15 seconds recommended)
- For Docker environments, ensure the container is running before starting the worker
- Keep your SSH keys secure; avoid storing passphrases if possible

## Architecture

- **main.py**: Tkinter GUI and event loop
- **manager.py**: Coordinates all workers and configuration
- **worker.py**: Per-server thread that monitors and restarts processes
- **ssh_client.py**: Paramiko wrapper for SSH operations
- **models.py**: Data classes for configuration and state
- **config.py**: Load/save servers.json
- **logging_setup.py**: Per-server rotating log files
- **ui/server_form.py**: Add/Edit dialog
- **ui/log_viewer.py**: Log viewing dialog

## Support

For issues or questions:
1. Check the logs in `logs/app.log` and `logs/{server-name}-YYYYMMDD.log`
2. Verify SSH access manually: `ssh -i key_path -p port user@host`
3. Check that the command works when run manually on the server

## License

MIT License - feel free to modify and use as needed.
