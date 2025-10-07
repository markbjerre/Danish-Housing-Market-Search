# Manual Update Commands & GitHub Actions Setup

**Created:** October 7, 2025  
**Purpose:** Manual update procedures and GitHub Actions configuration

---

## 📋 RECOMMENDED UPDATE SCHEDULE

### **1. Daily Active Case Refresh** ⏰
**Frequency:** Once per day (recommended: 6 AM or 2 PM)  
**Duration:** ~30-45 minutes (3,662 properties)  
**Purpose:** 
- Update prices for active listings
- Catch price reductions/increases
- Update days on market
- Refresh images if changed
- Update descriptions

**Command:**
```bash
python housing_project/periodic_updates.py --refresh-active
```

**What it does:**
- Fetches all properties with `status='open'` cases
- Re-imports case data (prices, images, descriptions)
- Updates ~3,662 properties
- Rate limited to 10 requests/second

---

### **2. New Property Discovery** 🔍
**Frequency:** Once per day (recommended: 6 AM)  
**Duration:** ~15-30 minutes  
**Purpose:**
- Find new properties that entered the market
- Import completely new properties into database

**Command:**
```bash
python housing_project/periodic_updates.py --discover-new
```

**What it does:**
- Scans 36 municipalities in target area
- Finds properties not yet in database
- Imports full property data (buildings, registrations, cases)

---

### **3. Weekly Full Refresh** 🔄
**Frequency:** Once per week (recommended: Sunday 3 AM)  
**Duration:** ~2-3 hours (all properties with cases)  
**Purpose:**
- Deep refresh of all data
- Catch edge cases missed by daily updates
- Update sold properties
- Refresh historical data

**Command:**
```bash
python housing_project/periodic_updates.py --refresh-all
```

**What it does:**
- Re-imports ALL properties that have cases (not just active)
- Updates sold properties, withdrawn listings
- Full data refresh
- ~3,662 properties total

---

### **4. Monthly Database Cleanup** 🧹
**Frequency:** Once per month (recommended: 1st of month)  
**Duration:** ~10 minutes  
**Purpose:**
- Remove stale data
- Optimize database
- Generate statistics report

**Command:**
```bash
python housing_project/periodic_updates.py --cleanup
```

**What it does:**
- Vacuum database
- Update statistics
- Archive old logs
- Generate health report

---

## 🚀 MANUAL EXECUTION (For Now)

### Run Individual Updates

```powershell
# Activate virtual environment
cd "C:\Users\Mark BJ\Desktop\Code"
.\.venv\Scripts\Activate.ps1

# Daily: Refresh active cases
python housing_project\periodic_updates.py --refresh-active

# Daily: Discover new properties  
python housing_project\periodic_updates.py --discover-new

# Weekly: Full refresh
python housing_project\periodic_updates.py --refresh-all

# Monthly: Cleanup
python housing_project\periodic_updates.py --cleanup

# Or run combined daily update
python housing_project\periodic_updates.py --daily
```

---

## ⚙️ GITHUB ACTIONS CONFIGURATION

When you're ready to automate, here are the workflows:

### Workflow 1: Daily Active Refresh

**File:** `.github/workflows/daily_active_refresh.yml`

```yaml
name: Daily Active Case Refresh

on:
  schedule:
    # Run at 6:00 AM UTC (7 AM CET / 8 AM CEST)
    - cron: '0 6 * * *'
  
  # Allow manual trigger
  workflow_dispatch:

jobs:
  refresh-active:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Refresh active cases
        env:
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
          DB_NAME: ${{ secrets.DB_NAME }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          python housing_project/periodic_updates.py --refresh-active
      
      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: active-refresh-logs-${{ github.run_number }}
          path: logs/
          retention-days: 30
```

**Schedule:** Daily at 6 AM UTC  
**Duration:** ~30-45 minutes  
**GitHub Actions Cost:** ~45 minutes/day = 1,350 min/month (within free 2,000 min limit) ✅

---

### Workflow 2: Daily New Property Discovery

**File:** `.github/workflows/daily_discovery.yml`

```yaml
name: Daily New Property Discovery

on:
  schedule:
    # Run at 7:00 AM UTC (after active refresh)
    - cron: '0 7 * * *'
  
  workflow_dispatch:

jobs:
  discover-new:
    runs-on: ubuntu-latest
    timeout-minutes: 45
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Discover new properties
        env:
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
          DB_NAME: ${{ secrets.DB_NAME }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          python housing_project/periodic_updates.py --discover-new
      
      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: discovery-logs-${{ github.run_number }}
          path: logs/
          retention-days: 30
```

**Schedule:** Daily at 7 AM UTC  
**Duration:** ~15-30 minutes  
**GitHub Actions Cost:** ~30 minutes/day = 900 min/month ✅

---

### Workflow 3: Weekly Full Refresh

**File:** `.github/workflows/weekly_full_refresh.yml`

```yaml
name: Weekly Full Database Refresh

on:
  schedule:
    # Run every Sunday at 3:00 AM UTC
    - cron: '0 3 * * 0'
  
  workflow_dispatch:

jobs:
  full-refresh:
    runs-on: ubuntu-latest
    timeout-minutes: 180  # 3 hours
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Full database refresh
        env:
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
          DB_NAME: ${{ secrets.DB_NAME }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          python housing_project/periodic_updates.py --refresh-all
      
      - name: Upload logs
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: weekly-refresh-logs-${{ github.run_number }}
          path: logs/
          retention-days: 90
      
      - name: Send notification
        if: failure()
        run: |
          echo "Weekly refresh failed! Check logs."
          # Add email/slack notification here
```

**Schedule:** Weekly on Sunday at 3 AM UTC  
**Duration:** ~2-3 hours  
**GitHub Actions Cost:** ~180 minutes/week = 720 min/month ✅

---

### Workflow 4: Monthly Cleanup

**File:** `.github/workflows/monthly_cleanup.yml`

```yaml
name: Monthly Database Cleanup

on:
  schedule:
    # Run on the 1st of each month at 2:00 AM UTC
    - cron: '0 2 1 * *'
  
  workflow_dispatch:

jobs:
  cleanup:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python 3.13
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Database cleanup
        env:
          DB_HOST: ${{ secrets.DB_HOST }}
          DB_PORT: ${{ secrets.DB_PORT }}
          DB_NAME: ${{ secrets.DB_NAME }}
          DB_USER: ${{ secrets.DB_USER }}
          DB_PASSWORD: ${{ secrets.DB_PASSWORD }}
        run: |
          python housing_project/periodic_updates.py --cleanup
      
      - name: Generate health report
        run: |
          python housing_project/periodic_updates.py --health-report
      
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: monthly-health-report-${{ github.run_number }}
          path: reports/
          retention-days: 365
```

**Schedule:** Monthly on the 1st at 2 AM UTC  
**Duration:** ~10-15 minutes  
**GitHub Actions Cost:** ~15 minutes/month ✅

---

## 📊 TOTAL GITHUB ACTIONS USAGE

| Workflow | Frequency | Duration | Monthly Minutes |
|----------|-----------|----------|-----------------|
| Active Refresh | Daily | 45 min | 1,350 min |
| New Discovery | Daily | 30 min | 900 min |
| Full Refresh | Weekly | 180 min | 720 min |
| Cleanup | Monthly | 15 min | 15 min |
| **TOTAL** | | | **2,985 min/month** |

**Note:** This exceeds the free 2,000 min/month limit by ~985 minutes (~$8/month)

### 💡 To Stay Within Free Tier:

**Option A:** Run daily updates every other day (saves 1,125 min/month)
```yaml
# Change cron to every 2 days
- cron: '0 6 */2 * *'
```

**Option B:** Reduce active refresh to 3x per week (saves 900 min/month)
```yaml
# Monday, Wednesday, Friday only
- cron: '0 6 * * 1,3,5'
```

**Option C:** Use public repository (unlimited minutes!) ✅

---

## 🎯 RECOMMENDED STARTING SCHEDULE (Manual)

For the next few weeks while running manually:

### **Daily (Choose One Time Slot):**

**Morning Routine (6-7 AM):**
```bash
python housing_project/periodic_updates.py --daily
```
- Discovers new properties
- Refreshes active cases
- ~60-75 minutes total

**OR Evening Routine (6-7 PM):**
```bash
python housing_project/periodic_updates.py --daily
```

### **Weekly (Sunday Morning):**
```bash
python housing_project/periodic_updates.py --refresh-all
```
- Full refresh of all properties
- ~2-3 hours
- Run while you're doing other things

### **Monthly (First Sunday):**
```bash
python housing_project/periodic_updates.py --cleanup
python housing_project/periodic_updates.py --health-report
```
- Database optimization
- Health check
- ~15 minutes

---

## 📝 SUMMARY

**You need to run:**

1. **Daily:** `--refresh-active` + `--discover-new` (or combined `--daily`)
   - **Time:** ~60-75 minutes
   - **When:** Once per day at consistent time
   - **Purpose:** Keep active listings fresh

2. **Weekly:** `--refresh-all`
   - **Time:** ~2-3 hours  
   - **When:** Sunday morning
   - **Purpose:** Deep refresh of everything

3. **Monthly:** `--cleanup`
   - **Time:** ~15 minutes
   - **When:** First of month
   - **Purpose:** Database maintenance

**Total time commitment:** ~9-11 hours per month for manual updates

---

## 🚀 NEXT STEPS

1. **I'll create** the `periodic_updates.py` script with these commands
2. **You run** manually for 1-2 weeks to test
3. **When ready**, we'll set up GitHub Actions workflows
4. **Then automate** and forget about it! ✅

Want me to create the `periodic_updates.py` script now?
