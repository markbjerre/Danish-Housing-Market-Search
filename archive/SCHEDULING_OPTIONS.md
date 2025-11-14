# Scheduling Periodic Updates - Hosting Options

**Created:** October 7, 2025  
**Purpose:** Compare options for running periodic database updates

---

## 🎯 THE CHALLENGE

You need to run Python scripts daily/weekly to keep your database fresh:
- **Daily:** Discovery scan + active case refresh (~1-2 hours runtime)
- **Weekly:** Full database refresh (~3-4 hours runtime)
- **Requirements:** Access to your PostgreSQL database, stable connection

---

## ☁️ OPTION 1: FREE CLOUD HOSTING (RECOMMENDED) ✅

### GitHub Actions (FREE for public repos, 2,000 min/month for private)

**Pros:**
- ✅ Completely free for public repos
- ✅ 2,000 minutes/month free on private repos
- ✅ No server maintenance
- ✅ Built-in scheduling (cron)
- ✅ Logs and monitoring included
- ✅ Your code already in GitHub

**Cons:**
- ⚠️ Need to expose database to internet (security concern)
- ⚠️ Limited to 6 hour max runtime per job
- ⚠️ Requires secrets management

**Setup:**

```yaml
# .github/workflows/daily_update.yml

name: Daily Database Update

on:
  schedule:
    # Run at 6 AM UTC daily
    - cron: '0 6 * * *'
  workflow_dispatch:  # Allow manual trigger

jobs:
  update-database:
    runs-on: ubuntu-latest
    timeout-minutes: 120  # 2 hour timeout
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run discovery scan
        env:
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
          DB_NAME: ${{ secrets.DB_NAME }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          python housing_project/periodic_updates.py --discover
      
      - name: Refresh active cases
        env:
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
          DB_NAME: ${{ secrets.DB_NAME }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          python housing_project/periodic_updates.py --refresh
      
      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: update-logs
          path: logs/
```

**Database Access:**
- Open PostgreSQL to GitHub Actions IPs (risky)
- Or use SSH tunnel / VPN
- Or use cloud database (AWS RDS, etc.)

**Cost:** FREE (2,000 min/month = ~33 hours)

---

### Render.com Cron Jobs (FREE tier available)

**Pros:**
- ✅ Free tier with cron jobs
- ✅ Easy setup
- ✅ Built-in PostgreSQL hosting option
- ✅ Can connect to external databases

**Cons:**
- ⚠️ Free tier spins down after inactivity
- ⚠️ Limited to daily jobs on free tier

**Setup:**

```yaml
# render.yaml

services:
  - type: cron
    name: daily-update
    env: python
    schedule: "0 6 * * *"  # Daily at 6 AM
    buildCommand: "pip install -r requirements.txt"
    startCommand: "python housing_project/periodic_updates.py --daily"
    envVars:
      - key: DB_HOST
        sync: false
      - key: DB_PASSWORD
        sync: false
```

**Cost:** FREE

---

### Railway.app Cron Jobs

**Pros:**
- ✅ $5 free credit monthly
- ✅ Easy PostgreSQL integration
- ✅ Good for scheduled tasks
- ✅ Simple deployment

**Cons:**
- ⚠️ Credit runs out quickly with daily jobs
- ⚠️ Need to monitor usage

**Cost:** ~$5-10/month (after free credits)

---

### PythonAnywhere (FREE tier)

**Pros:**
- ✅ Free tier with scheduled tasks
- ✅ Built for Python
- ✅ One daily scheduled task free

**Cons:**
- ⚠️ Only ONE task per day on free tier
- ⚠️ Limited CPU time
- ⚠️ Database connection may timeout

**Setup:**
1. Upload code to PythonAnywhere
2. Set up daily task in dashboard
3. Configure database connection

**Cost:** FREE (1 task/day), $5/month for unlimited

---

## 💻 OPTION 2: LOCAL MACHINE SCHEDULING

### Windows Task Scheduler (YOUR CURRENT SETUP) ✅

**Pros:**
- ✅ Completely free
- ✅ Full control
- ✅ Direct database access (no security risks)
- ✅ No runtime limits
- ✅ Reliable if PC always on

**Cons:**
- ❌ Computer must be on 24/7
- ❌ Uses your electricity (~$10-20/month)
- ❌ No redundancy (if PC crashes, no updates)
- ❌ Internet connection dependency

**Setup Steps:**

1. **Create batch file** (`run_daily_update.bat`):
```batch
@echo off
cd /d "C:\Users\Mark BJ\Desktop\Code"
call .venv\Scripts\activate
python housing_project\periodic_updates.py --daily >> logs\daily_update.log 2>&1
```

2. **Open Task Scheduler:**
   - Press `Win + R`, type `taskschd.msc`
   - Click "Create Task" (not Basic Task)

3. **General Tab:**
   - Name: "Housing Database Daily Update"
   - Description: "Discover new properties and refresh active cases"
   - Run whether user is logged on or not
   - Run with highest privileges

4. **Triggers Tab:**
   - New → Daily
   - Start: 6:00 AM
   - Recur every: 1 day
   - Enabled: ✓

5. **Actions Tab:**
   - New → Start a program
   - Program/script: `C:\Users\Mark BJ\Desktop\Code\run_daily_update.bat`
   - Start in: `C:\Users\Mark BJ\Desktop\Code`

6. **Conditions Tab:**
   - ✓ Start only if computer is on AC power (if laptop)
   - ✓ Wake the computer to run this task
   - ✗ Start the task only if the computer is idle

7. **Settings Tab:**
   - ✓ Allow task to be run on demand
   - ✓ Run task as soon as possible after scheduled start is missed
   - If task fails, restart every: 10 minutes, 3 attempts
   - Stop task if runs longer than: 3 hours

**Weekly Task** (full refresh):
- Same setup, but trigger set to "Weekly" on Sunday at 3 AM

**Cost:** $10-20/month in electricity (24/7 PC)

---

### Linux Cron (if you have a Linux machine/server)

**Setup:**

```bash
# Edit crontab
crontab -e

# Add these lines:
# Daily at 6 AM
0 6 * * * cd /path/to/Code && .venv/bin/python housing_project/periodic_updates.py --daily >> logs/daily.log 2>&1

# Weekly on Sunday at 3 AM
0 3 * * 0 cd /path/to/Code && .venv/bin/python housing_project/periodic_updates.py --weekly >> logs/weekly.log 2>&1
```

**Cost:** FREE (if you have the machine)

---

## 🏠 OPTION 3: HYBRID APPROACH (BEST OF BOTH WORLDS) ⭐

### Keep Database Local, Run Scripts in Cloud

**Architecture:**
1. Database stays on your local machine (secure, fast)
2. Expose database through secure tunnel (ngrok, Tailscale, or CloudFlare Tunnel)
3. GitHub Actions runs the update scripts
4. Scripts connect to your local DB through tunnel

**Option A: CloudFlare Tunnel (FREE & SECURE)** ✅

**Pros:**
- ✅ Completely free
- ✅ Secure encrypted tunnel
- ✅ No port forwarding
- ✅ No firewall changes
- ✅ Works behind NAT/routers

**Setup:**

1. **Install CloudFlare Tunnel:**
```powershell
# Download cloudflared
winget install --id Cloudflare.cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create housing-db

# Configure tunnel
# C:\Users\Mark BJ\.cloudflared\config.yml
tunnel: <TUNNEL-ID>
credentials-file: C:\Users\Mark BJ\.cloudflared\<TUNNEL-ID>.json

ingress:
  - hostname: housing-db.yourdomain.com
    service: tcp://localhost:5432
  - service: http_status:404
```

2. **Run tunnel as service:**
```powershell
cloudflared service install
cloudflared service start
```

3. **Update GitHub Actions:**
```yaml
env:
  DB_HOST: housing-db.yourdomain.com
  DB_PORT: 5432
```

**Cost:** FREE

---

**Option B: Tailscale (FREE for personal use)**

**Pros:**
- ✅ Free for up to 100 devices
- ✅ Peer-to-peer VPN
- ✅ Very secure
- ✅ Easy setup

**Setup:**
1. Install Tailscale on your PC
2. Install Tailscale on GitHub Actions runner (complex)
3. Connect through private network

**Cost:** FREE

---

**Option C: ngrok (FREE tier, $8/month for persistent URLs)**

**Setup:**
```powershell
# Install ngrok
winget install --id ngrok.ngrok

# Authenticate
ngrok authtoken YOUR_TOKEN

# Expose PostgreSQL
ngrok tcp 5432
```

**Cost:** FREE (random URLs) or $8/month (persistent)

---

## 💰 COST COMPARISON

| Option | Setup Complexity | Monthly Cost | Reliability | Security |
|--------|-----------------|--------------|-------------|----------|
| **GitHub Actions + CloudFlare Tunnel** | Medium | FREE | High | Excellent |
| **Windows Task Scheduler** | Easy | $10-20 (electricity) | Medium | Excellent |
| **Render.com** | Easy | FREE | High | Good |
| **PythonAnywhere** | Easy | FREE | Medium | Good |
| **Railway.app** | Easy | $5-10 | High | Good |
| **Linux Cron** | Easy | FREE (if have server) | High | Excellent |

---

## 🎯 MY RECOMMENDATION FOR YOU

### **Option 1: Windows Task Scheduler (Immediate Solution)**

**Why:**
- ✅ Zero cost (you already have the PC)
- ✅ Zero setup complexity
- ✅ Works right now
- ✅ No security concerns (database stays local)
- ✅ No API rate limit issues

**Drawbacks:**
- Computer must stay on 24/7
- Uses some electricity
- No backup if computer fails

**Best For:** Testing and short-term use (next 1-2 months)

---

### **Option 2: GitHub Actions + CloudFlare Tunnel (Long-term Solution)**

**Why:**
- ✅ Completely free forever
- ✅ Your PC can sleep (saves electricity)
- ✅ More reliable (GitHub's infrastructure)
- ✅ Secure tunnel (no exposed ports)
- ✅ Built-in monitoring and logs
- ✅ Can run from anywhere

**Drawbacks:**
- Requires initial setup (1-2 hours)
- Need to learn GitHub Actions
- Database must be accessible during runs

**Best For:** Production use (after testing)

---

## 🚀 PHASED IMPLEMENTATION

### **Phase 1: This Week (Use Windows Task Scheduler)**

1. Create `periodic_updates.py` script
2. Test manually first
3. Set up daily task for 6 AM
4. Monitor for 1 week

**Effort:** 30 minutes  
**Cost:** $0

---

### **Phase 2: Next Month (Migrate to GitHub Actions)**

1. Set up CloudFlare Tunnel
2. Create GitHub Actions workflow
3. Test with manual triggers
4. Enable scheduled runs
5. Turn off local machine scheduling

**Effort:** 2-3 hours  
**Cost:** $0

---

### **Phase 3: Future (Optimize)**

1. Add monitoring/alerting
2. Implement smart change detection
3. Reduce API calls with incremental updates
4. Add dashboard for update status

---

## 📋 NEXT STEPS

**Immediate:**
1. ✅ Create `periodic_updates.py` script (I'll do this)
2. ✅ Test script manually
3. ✅ Set up Windows Task Scheduler
4. ✅ Monitor logs for 1 week

**This Weekend:**
- Decide if PC stays on 24/7 or if you want cloud solution
- If cloud: Set up CloudFlare Tunnel
- If local: Configure Task Scheduler with wake timers

**Want me to:**
- [ ] Create the Windows Task Scheduler setup script?
- [ ] Write the GitHub Actions workflow file?
- [ ] Set up CloudFlare Tunnel configuration?

---

## 💡 QUICK WIN: Hybrid Local + Manual

**Alternative Simple Approach:**

Keep your PC on during the day, run updates when you're using it:

```python
# In your main script, add a check
if __name__ == "__main__":
    # Check if it's time to update
    last_update = get_last_update_time()
    if datetime.now() - last_update > timedelta(hours=24):
        run_daily_update()
```

Then just keep your development environment open, and it auto-updates in the background!

**Cost:** $0  
**Effort:** 5 minutes  
**Reliability:** Depends on you opening VS Code daily 😄

---

Let me know which approach you prefer and I'll create the necessary scripts!
