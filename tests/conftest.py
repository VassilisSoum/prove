import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Make the harness (templates/bench) and scripts importable by the tests.
sys.path.insert(0, os.path.join(ROOT, "templates", "bench"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
