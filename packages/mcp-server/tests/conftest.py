import sys
from pathlib import Path

# Ensure tests import local package code from this workspace, not another editable install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
