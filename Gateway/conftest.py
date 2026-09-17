import sys
import os

# Ensure Gateway root directory is in sys.path
gateway_root = os.path.dirname(os.path.abspath(__file__))
if gateway_root not in sys.path:
    sys.path.insert(0, gateway_root)
