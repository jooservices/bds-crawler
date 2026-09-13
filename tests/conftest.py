import sys
from pathlib import Path

# ensure the repo root is importable (tests import `parser`, `config`)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
