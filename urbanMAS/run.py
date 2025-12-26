
import os
import sys
from config import SUMO_HOME

# Set SUMO_HOME environment variable
os.environ['SUMO_HOME'] = SUMO_HOME
sys.path.append(os.path.join(SUMO_HOME, 'tools'))

if __name__ == '__main__':
    try:
        # Import after SUMO_HOME is set
        from main import main
        import asyncio
        asyncio.run(main())
    except ImportError as e:
        print(f"Error importing dependencies: {e}")
        print("Please ensure all requirements are installed:")
        print("pip install -r requirements.txt")
    except Exception as e:
        print(f"Error running simulation: {e}")
