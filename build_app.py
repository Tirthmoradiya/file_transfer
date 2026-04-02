import os
import sys
import subprocess
import shutil

def build():
    print("🚀 Starting build process...")
    
    # 1. Configuration
    APP_NAME = "Transfer"
    ENTRY_POINT = "main_gui.py"
    ASSETS = [
        ("templates", "templates"),
        ("static", "static"),
    ]
    
    # 2. Prepare PyInstaller command
    # On Windows, the delimiter for --add-data is ';', on Mac/Linux it's ':'
    sep = ';' if os.name == 'nt' else ':'
    
    cmd = [
        "pyinstaller",
        "--name", APP_NAME,
        "--windowed",          # No console window
        "--onefile",           # Bundle into a single executable
        "--clean",
        "--noconfirm",
    ]
    
    # Add assets
    for src, dest in ASSETS:
        cmd.extend(["--add-data", f"{src}{sep}{dest}"])
    
    cmd.append(ENTRY_POINT)
    
    # 3. Run build
    venv_python = os.path.join("venv", "bin", "python")
    if os.name == 'nt':
        venv_python = os.path.join("venv", "Scripts", "python")
        
    print(f"Executing: {' '.join(cmd)}")
    
    # Use the venv's pyinstaller if possible
    venv_pyinstaller = os.path.join("venv", "bin", "pyinstaller")
    if os.name == 'nt':
        venv_pyinstaller = os.path.join("venv", "Scripts", "pyinstaller")
        
    if os.path.exists(venv_pyinstaller):
        subprocess.run([venv_pyinstaller] + cmd[1:])
    else:
        # Fallback to system pyinstaller
        subprocess.run(cmd)

    print("\n✅ Build complete! Check the 'dist/' folder for your application.")

if __name__ == "__main__":
    build()
