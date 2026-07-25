"""Root conftest.py -- ensures both 'src.module' and bare 'module' import styles resolve,
since some earlier-sprint test/source files use one convention and later ones use another.
Fixes collection errors when running the full tests/ tree together (Day 42 finding)."""
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"

for path in (str(ROOT), str(SRC)):
    if path not in sys.path:
        sys.path.insert(0, path)