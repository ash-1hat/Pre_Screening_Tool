"""
Script to install the correct Supabase version and test connection
"""

import subprocess
import sys
import os

def install_supabase():
    """Install the correct Supabase version"""
    try:
        print("🔄 Uninstalling current Supabase version...")
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "supabase", "-y"], check=True)
        
        print("📦 Installing Supabase v1.0.4...")
        subprocess.run([sys.executable, "-m", "pip", "install", "supabase==1.0.4"], check=True)
        
        print("✅ Supabase v1.0.4 installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Supabase: {e}")
        return False

if __name__ == "__main__":
    success = install_supabase()
    if success:
        print("\n🧪 Now you can run: python test_supabase_connection.py")
    else:
        print("\n❌ Installation failed. Please install manually: pip install supabase==1.0.4")
