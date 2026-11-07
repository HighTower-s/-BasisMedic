"""Constitution VI: the core (app/retrieval/) and eval/ never depend on the CLI edge."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _source_files(*dirs: str) -> list[Path]:
    files = []
    for d in dirs:
        files.extend((ROOT / d).rglob("*.py"))
    return files


def test_no_core_or_eval_module_imports_app_cli():
    offenders = []
    for path in _source_files("app/retrieval", "eval"):
        if path.name == "__pycache__":
            continue
        text = path.read_text(encoding="utf-8")
        if "import app.cli" in text or "from app.cli" in text or "from app import cli" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
