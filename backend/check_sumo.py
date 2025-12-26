"""
Simple SUMO-RL Environment Setup
Based on official SUMO-RL repository
"""
import os
import sys

def check_sumo_installation():
    """Check if SUMO is properly installed"""
    if 'SUMO_HOME' in os.environ:
        tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
        sys.path.append(tools)
        print(f"✅ SUMO_HOME found: {os.environ['SUMO_HOME']}")
        return True
    else:
        print("❌ SUMO_HOME environment variable not set!")
        print("\nPlease set SUMO_HOME:")
        print("Windows: set SUMO_HOME=C:\\Program Files (x86)\\Eclipse\\Sumo")
        print("Linux: export SUMO_HOME=/usr/share/sumo")
        return False

def test_sumo_binary():
    """Test if SUMO binary exists"""
    try:
        import traci
        sumo_binary = os.path.join(os.environ['SUMO_HOME'], 'bin', 'sumo')
        if os.path.exists(sumo_binary) or os.path.exists(sumo_binary + '.exe'):
            print(f"✅ SUMO binary found")
            return True
        else:
            print(f"❌ SUMO binary not found at: {sumo_binary}")
            return False
    except ImportError:
        print("❌ TraCI not installed. Install with: pip install traci")
        return False

def test_sumo_rl():
    """Test if SUMO-RL is installed"""
    try:
        import sumo_rl
        print(f"✅ SUMO-RL installed: version {sumo_rl.__version__ if hasattr(sumo_rl, '__version__') else 'unknown'}")
        return True
    except ImportError:
        print("❌ SUMO-RL not installed. Install with: pip install sumo-rl")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("SUMO Installation Check")
    print("=" * 50)
    
    checks = [
        ("SUMO Installation", check_sumo_installation()),
        ("SUMO Binary", test_sumo_binary()),
        ("SUMO-RL Library", test_sumo_rl())
    ]
    
    print("\n" + "=" * 50)
    print("Summary:")
    print("=" * 50)
    for name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")
    
    if all(passed for _, passed in checks):
        print("\n🎉 All checks passed! You're ready to run simulations!")
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
