# Danus-AI

P1-1 engineering foundation only: installable empty package, static import checks and local CI entry point. No scientific business objects, database, model calls or upstream code are included.

Use Ubuntu/WSL, uv 0.13.7 and CPython 3.12.16. From this checkout run:

    bash scripts/verify.sh

The script checks the lock, installs locked development tools, builds and installs this project non-editably, runs Ruff/mypy/import checks/pytest and builds an sdist and wheel. The setuptools build backend is pinned and included in the lock; the project build uses the already locked environment with build isolation disabled. Upstream paths are never injected.

GitHub Actions is manual-only pending confirmation of free runner eligibility; do not dispatch until that is confirmed. See docs/implementation/p1-1-delivery.md for rules, evidence and remaining R01 requirements.
