# Quick Start Guide

## Installation (30 seconds)

1. **Open PowerShell** in the ServerManager directory
2. **Run the setup script:**
   ```powershell
   .\setup.ps1
   ```
   
   If you get an execution policy error, run this first:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

## Launch

**Option 1: Use the run script (easiest)**
```powershell
.\run.ps1
```

**Option 2: Manual launch**
```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

## First Steps

### 1. Your server is already configured!

The app created a default `servers.json` with your server:
- **Name**: server-1
- **Host**: 113.201.14.131:43857
- **Auth**: SSH key at C:/Users/AJU/.ssh/vast
- **Command**: `python3 /home/v13/ultra_aggressive_worker.py`

### 2. Test the connection

1. Select "server-1" in the list
2. Click **Test Connection**
3. Verify it connects successfully

### 3. Start monitoring

1. Click **Start** button
2. Watch the status change: Disconnected → Connecting → Running
3. The PID and Uptime will appear once running

### 4. View live logs

1. Click **View Logs**
2. Watch the script output stream in real-time
3. Leave it open to see live updates

### 5. Test auto-restart

**Option A: Kill from terminal**
```bash
ssh -i "C:\Users\AJU\.ssh\vast" -p 43857 root@113.201.14.131 "pkill -f ultra_aggressive_worker.py"
```

**Option B: Use the Restart button**
- Click **Restart** to gracefully restart after 12 seconds

**Watch it restart:**
- Status changes to "Stopped" or "Error"
- After ~12 seconds, it automatically restarts
- Status returns to "Running"
- Restart count increases

## Adding More Servers

1. Click **Add Server**
2. Fill in the form:
   - Name: `server-2`
   - Host: Your server IP
   - Port: Your SSH port
   - Username: Usually `root`
   - Auth Type: Choose "Private Key" or "Password"
   - Key Path: Browse to your SSH key file
   - Command: Keep default or customize
   - Restart Delay: 12 seconds (recommended)
3. Click **Save**
4. Click **Test Connection** to verify
5. Click **Start** to begin monitoring

## Customizing Commands

### Different script path
```json
"command": "python3 /home/myapp/worker.py"
```

### Using environment variables
```json
"command": "python3 /home/v13/ultra_aggressive_worker.py",
"env": {
  "API_KEY": "your_key_here",
  "DEBUG": "true"
}
```

### Docker containers
```json
"command": "docker exec -i my_container python3 /home/v13/ultra_aggressive_worker.py"
```

### Different working directory
```json
"working_dir": "/home/myapp"
```

## Status Meanings

- **Disconnected**: Can't connect to server; retrying with backoff (5s, 10s, 20s, 40s, 60s)
- **Connecting**: Attempting to establish SSH connection
- **Running**: Process is running and being monitored ✓
- **Stopped**: Process exited normally; will restart in 12 seconds
- **Error**: Process crashed; will restart in 12 seconds
- **External**: A matching process is already running (not started by this app)
  - Use **Force Restart** to take control

## Common Actions

### Start All Servers
Click **Start All** to monitor all enabled servers at once

### Stop a Server
Click **Stop** → Confirm → Process killed and monitoring stopped

### Force Restart
If status shows "External":
1. Click **Force Restart**
2. This kills any existing process and starts fresh

### Edit Server Settings
1. Select server
2. Click **Edit**
3. Change settings (command, restart delay, etc.)
4. Click **Save**
5. The worker restarts with new settings

## Logs Location

All logs are saved to:
```
D:\xampp3\htdocs\storage\ServerManager\logs\
```

- **Per-server logs**: `logs/server-1-20251026.log`
- **App log**: `logs/app.log`

## Troubleshooting

### Can't connect?
- Verify server is online: `ping 113.201.14.131`
- Test SSH manually: `ssh -i "C:\Users\AJU\.ssh\vast" -p 43857 root@113.201.14.131`
- Check firewall/network

### Authentication failed?
- Verify key path: `C:/Users/AJU/.ssh/vast` (use forward slashes)
- Check key permissions
- Try password auth instead

### Process keeps crashing?
1. Click **View Logs**
2. Look for error messages (in red)
3. Verify script exists: `test -f /home/v13/ultra_aggressive_worker.py`
4. Check Python version: `python3 --version`

### Status stuck on "External"?
- Another process with the same name is running
- Click **Force Restart** to kill it and start fresh

## Tips

✓ Use **Test Connection** before starting to catch issues early  
✓ Keep **View Logs** open to monitor script output  
✓ Adjust **Restart Delay** per server (10-15 seconds recommended)  
✓ Use **Start All** to quickly start all servers after reboot  
✓ Check logs folder if something goes wrong  

## Next Steps

- Add your other 9 servers using **Add Server**
- Customize restart delays per server
- Set up different commands for different servers
- Keep the app running to ensure 24/7 monitoring

---

**Need help?** Check the full `README.md` for detailed documentation.
