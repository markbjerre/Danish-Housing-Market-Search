#!/usr/bin/env python3
"""
Deployment Package Creator for Danish Housing Market Search (Portable Version)

Creates a clean package ready for deployment to work laptop or other computers.
"""

import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def create_deployment_package():
    """Create a deployment package for the portable version"""
    
    print("🚀 Creating deployment package for Danish Housing Market Search")
    print("=" * 60)
    
    # Create deployment directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    package_name = f"Danish-Housing-Market-Search-Portable_{timestamp}"
    package_dir = Path(f"deployment/{package_name}")
    
    print(f"📁 Creating package: {package_name}")
    package_dir.mkdir(parents=True, exist_ok=True)
    
    # Files and directories to include
    items_to_copy = [
        # Core application files
        ("webapp/app_portable.py", "webapp/app_portable.py"),
        ("webapp/templates/", "webapp/templates/"),
        ("src/file_database.py", "src/file_database.py"),
        
        # Data (find the most recent full export)
        ("data/backups/", "data/backups/"),
        
        # Documentation and setup
        ("requirements_portable.txt", "requirements_portable.txt"),
        ("README_PORTABLE.md", "README_PORTABLE.md"),
    ]
    
    # Copy files
    total_size = 0
    files_copied = 0
    
    for src, dst in items_to_copy:
        src_path = Path(src)
        dst_path = package_dir / dst
        
        if src_path.exists():
            if src_path.is_file():
                # Copy single file
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                size = src_path.stat().st_size
                total_size += size
                files_copied += 1
                print(f"   ✅ {src} ({size/1024/1024:.1f} MB)")
                
            elif src_path.is_dir():
                # Copy directory
                if dst_path.exists():
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
                
                # Calculate directory size
                dir_size = sum(f.stat().st_size for f in dst_path.rglob('*') if f.is_file())
                file_count = len(list(dst_path.rglob('*')))
                total_size += dir_size
                files_copied += file_count
                print(f"   ✅ {src}/ ({dir_size/1024/1024:.1f} MB, {file_count} files)")
        else:
            print(f"   ⚠️  Not found: {src}")
    
    # Create startup script for Windows
    startup_script = package_dir / "start_website.bat"
    with open(startup_script, 'w') as f:
        f.write("""@echo off
echo Starting Danish Housing Market Search (Portable)
echo ================================================
echo.
echo Installing dependencies...
pip install -r requirements_portable.txt

echo.
echo Starting web server...
cd webapp
python app_portable.py

pause
""")
    
    # Create startup script for Mac/Linux
    startup_script_unix = package_dir / "start_website.sh"
    with open(startup_script_unix, 'w') as f:
        f.write("""#!/bin/bash
echo "Starting Danish Housing Market Search (Portable)"
echo "================================================"
echo ""
echo "Installing dependencies..."
pip install -r requirements_portable.txt

echo ""
echo "Starting web server..."
cd webapp
python app_portable.py
""")
    
    # Make shell script executable
    os.chmod(startup_script_unix, 0o755)
    
    print(f"\n📦 Package created successfully!")
    print(f"📊 Total size: {total_size/1024/1024:.1f} MB")
    print(f"📁 Files: {files_copied}")
    print(f"🎯 Location: {package_dir.absolute()}")
    
    # Create ZIP file for easy transfer
    zip_path = package_dir.parent / f"{package_name}.zip"
    print(f"\n🗜️  Creating ZIP file: {zip_path.name}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in package_dir.rglob('*'):
            if file_path.is_file():
                arc_name = file_path.relative_to(package_dir.parent)
                zipf.write(file_path, arc_name)
    
    zip_size = zip_path.stat().st_size / 1024 / 1024
    print(f"   ✅ ZIP created: {zip_size:.1f} MB")
    
    print(f"\n🎉 Deployment package ready!")
    print(f"📁 Directory: {package_dir.absolute()}")
    print(f"📦 ZIP file: {zip_path.absolute()}")
    
    print(f"\n📋 To deploy on work laptop:")
    print(f"1. Copy {zip_path.name} to work laptop")
    print(f"2. Extract the ZIP file")
    print(f"3. Run start_website.bat (Windows) or start_website.sh (Mac/Linux)")
    print(f"4. Open http://127.0.0.1:5000 in browser")
    
    return package_dir, zip_path

if __name__ == '__main__':
    create_deployment_package()