"""Make the modules of inspect_eval/ importable by the tests (dataset, solver, scorer)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
