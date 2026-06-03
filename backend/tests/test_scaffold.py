from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


def test_backend_scaffold_matches_foundation_contract():
    required_paths = [
        BACKEND_ROOT / "app" / "main.py",
        BACKEND_ROOT / "app" / "api" / "v1" / "routers" / "health.py",
        BACKEND_ROOT / "app" / "core" / "database.py",
        BACKEND_ROOT / "app" / "core" / "logging.py",
        BACKEND_ROOT / "app" / "core" / "observability.py",
        BACKEND_ROOT / "app" / "workers" / "main.py",
        BACKEND_ROOT / "alembic" / "env.py",
        BACKEND_ROOT / "Dockerfile",
        REPO_ROOT / "docker-compose.yml",
    ]

    for path in required_paths:
        assert path.exists(), f"Missing scaffold file: {path.relative_to(REPO_ROOT)}"


def test_python_scaffold_files_stay_under_500_loc():
    for path in BACKEND_ROOT.rglob("*.py"):
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        assert line_count <= 500, f"{path.relative_to(REPO_ROOT)} exceeds 500 LOC"
