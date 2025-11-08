#!/usr/bin/env python3
"""
Scheduled Import Runner for Danish Housing Properties
Runs periodic imports from Boligsiden API with logging and error handling

Usage:
  python scheduler.py --frequency daily --time 02:00
  python scheduler.py --frequency weekly --day monday --time 02:00
  python scheduler.py --once  # Run once and exit
  
For production deployment with cron, see SCHEDULER_SETUP.md
"""

import argparse
import subprocess
import sys
import os
import logging
from datetime import datetime, time
from pathlib import Path
import json

# Setup logging
log_dir = Path(__file__).parent.parent / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"scheduler_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ImportScheduler:
    """Manages scheduled imports of housing data"""
    
    def __init__(self, script_path=None, log_output=True):
        """
        Initialize scheduler
        
        Args:
            script_path: Path to import_copenhagen_area.py (auto-detected if None)
            log_output: Whether to log import script output
        """
        if script_path is None:
            script_path = Path(__file__).parent / "import_copenhagen_area.py"
        
        self.script_path = Path(script_path).resolve()
        self.log_output = log_output
        
        if not self.script_path.exists():
            raise FileNotFoundError(f"Import script not found: {self.script_path}")
        
        logger.info(f"Scheduler initialized with script: {self.script_path}")
    
    def run_import(self, dry_run=False, workers=20, batch_size=50):
        """
        Run the import script once
        
        Args:
            dry_run: If True, don't actually import to database
            workers: Number of parallel workers for API requests
            batch_size: Number of properties per batch
            
        Returns:
            bool: True if import succeeded, False if failed
        """
        try:
            logger.info("=" * 80)
            logger.info(f"Starting import at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)
            
            cmd = [
                sys.executable,
                str(self.script_path),
                f"--workers={workers}",
                f"--batch_size={batch_size}"
            ]
            
            if dry_run:
                cmd.append("--dry_run")
                logger.warning("DRY RUN MODE - No database changes will be made")
            
            # Run import script
            result = subprocess.run(cmd, cwd=self.script_path.parent)
            
            if result.returncode == 0:
                logger.info("✅ Import completed successfully")
                return True
            else:
                logger.error(f"❌ Import failed with return code {result.returncode}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error running import: {e}", exc_info=True)
            return False
        finally:
            logger.info("=" * 80)
            logger.info(f"Import finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 80)
    
    def run_once(self, args):
        """Run import once and exit"""
        logger.info("Running import once...")
        success = self.run_import(
            dry_run=args.dry_run,
            workers=args.workers,
            batch_size=args.batch_size
        )
        sys.exit(0 if success else 1)
    
    def run_continuous(self, args):
        """Run import on a schedule (for use with cron or systemd)"""
        import time
        import signal
        
        def signal_handler(sig, frame):
            logger.info("Received interrupt signal, exiting...")
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info(f"Starting continuous scheduler (frequency: {args.frequency})")
        
        while True:
            try:
                now = datetime.now()
                should_run = False
                
                # Check if it's time to run
                if args.frequency == "daily":
                    target_time = datetime.strptime(args.time, "%H:%M").time()
                    if now.time().hour == target_time.hour and now.time().minute == target_time.minute:
                        should_run = True
                
                elif args.frequency == "weekly":
                    day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                    target_day = day_names.index(args.day.lower())
                    target_time = datetime.strptime(args.time, "%H:%M").time()
                    
                    if now.weekday() == target_day and now.time().hour == target_time.hour and now.time().minute == target_time.minute:
                        should_run = True
                
                elif args.frequency == "hourly":
                    if now.minute == 0:
                        should_run = True
                
                if should_run:
                    self.run_import(
                        dry_run=args.dry_run,
                        workers=args.workers,
                        batch_size=args.batch_size
                    )
                    # Wait a minute to avoid running again immediately
                    time.sleep(60)
                
                # Check every 10 seconds
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                time.sleep(60)


def main():
    parser = argparse.ArgumentParser(
        description="Schedule housing property imports from Boligsiden API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run import once immediately
  python scheduler.py --once
  
  # Run daily at 2 AM
  python scheduler.py --frequency daily --time 02:00
  
  # Run weekly on Monday at 2 AM
  python scheduler.py --frequency weekly --day monday --time 02:00
  
  # Run every hour
  python scheduler.py --frequency hourly
  
  # Dry run (no database changes)
  python scheduler.py --once --dry-run
        """
    )
    
    # Main mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--once', action='store_true',
                           help='Run import once and exit')
    mode_group.add_argument('--frequency', choices=['daily', 'weekly', 'hourly'],
                           help='Run import on a schedule')
    
    # Schedule options
    parser.add_argument('--time', default='02:00', metavar='HH:MM',
                       help='Time to run (HH:MM format, default: 02:00)')
    parser.add_argument('--day', default='monday',
                       choices=['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'],
                       help='Day for weekly frequency (default: monday)')
    
    # Import options
    parser.add_argument('--workers', type=int, default=20,
                       help='Number of parallel workers (default: 20)')
    parser.add_argument('--batch_size', type=int, default=50,
                       help='Batch size for database inserts (default: 50)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run - no database changes')
    
    args = parser.parse_args()
    
    try:
        scheduler = ImportScheduler()
        
        if args.once:
            scheduler.run_once(args)
        else:
            scheduler.run_continuous(args)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
