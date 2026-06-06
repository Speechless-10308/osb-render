"""Project-level conftest — ensures the project root is on sys.path for imports."""

import sys
import os

# Add the project root directory to sys.path so that `src.*` imports work
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
