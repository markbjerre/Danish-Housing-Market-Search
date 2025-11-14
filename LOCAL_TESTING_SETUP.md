# Local Testing with VPS Database via SSH Tunnel

## Quick Setup (5 minutes)

### Step 1: Create SSH Tunnel to VPS Database
Open a terminal and run:

```bash
# Windows (PowerShell or CMD)
ssh -L 5432:housing-db:5432 root@72.61.179.126

# Mac/Linux
ssh -L 5432:housing-db:5432 root@72.61.179.126
```

This creates a tunnel:
- `localhost:5432` → forwards to → `housing-db:5432` (on VPS internal network)
- Keep this terminal open while testing

### Step 2: Create Local Virtual Environment

```bash
cd "Danish Housing Market Search"

# Create venv if not exists
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Create .env File for Local Testing

Create `.env` in the project root:

```
DATABASE_URL=postgresql://housing:housing_password@localhost:5432/housing
FLASK_ENV=development
FLASK_DEBUG=True
```

### Step 4: Start Flask App Locally

```bash
cd webapp
python app.py
```

Open browser: **http://localhost:5000/housing**

## Testing Workflow

1. **Keep SSH tunnel running** in one terminal
2. **Run Flask app** in another terminal
3. **Test in browser** at http://localhost:5000/housing
4. **Changes are instant** - just edit files and refresh browser
5. **No Docker rebuilds needed** - much faster iteration

## Advanced: Keep Tunnel Running in Background

### Windows (PowerShell - Run Once)
```powershell
# Create a script to maintain SSH tunnel
New-Item -Path "$env:USERPROFILE\ssh-tunnel.bat" -Force -Value @"
@echo off
:loop
ssh -N -L 5432:housing-db:5432 root@72.61.179.126
timeout /t 5
goto loop
"@ | Set-Content

# Then run it in background:
Start-Process powershell -WindowStyle Hidden -ArgumentList "-Command &{.$env:USERPROFILE\ssh-tunnel.bat}"
```

### Mac/Linux
```bash
# Create a background tunnel that auto-reconnects
nohup bash -c 'while true; do ssh -N -L 5432:housing-db:5432 root@72.61.179.126; sleep 5; done' > ~/ssh-tunnel.log 2>&1 &

# Check it's running
ps aux | grep ssh-tunnel
```

## Troubleshooting

### Connection refused on localhost:5432
- Check SSH tunnel is still running (first terminal)
- Verify no other service on port 5432

### Can't connect to housing-db
- SSH tunnel uses internal Docker network name `housing-db`
- Make sure `.env` has `localhost:5432` (not `housing-db:5432`)

### Flask app won't start
- Check `.env` DATABASE_URL is correct
- Run `pip install -r requirements.txt` again
- Check Python version: `python --version`

## Clean Shutdown
```bash
# When done testing:
# 1. Press Ctrl+C in Flask terminal
# 2. Press Ctrl+C in SSH tunnel terminal
```

## Benefits of This Approach
✅ No Docker rebuilds (instant file changes)
✅ Full database access from localhost
✅ Can debug with breakpoints
✅ Hot reload on file save
✅ Same data as production
✅ Quick iteration cycle
