"""Repository layer: parse and validate the runbook corpus and the T-code allow-list."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from app import config
from app.schemas import CATEGORIES, SECTION_ORDER, TCODE_RE, Runbook

# A bare T-code as it appears at the start of a numbered Check step.
_CHECK_TCODE_RE = re.compile(r"^\s*\d+\.\s*([A-Z][A-Z0-9_/]{1,19})\b", re.MULTILINE)
_FRONT_MATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
_SECTION_RE = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)


class CorpusError(Exception):
    """A runbook or the allow-list is malformed. Message names the file and the value."""


def load_tcodes(path: Path | None = None) -> dict[str, str]:
    path = path or config.TCODES_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CorpusError(f"{path} not found") from exc
    except json.JSONDecodeError as exc:
        raise CorpusError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise CorpusError(f"{path} must be a flat object of code -> description")
    for code, description in data.items():
        if not re.fullmatch(TCODE_RE, code):
            raise CorpusError(f"{path}: T-code {code!r} does not match {TCODE_RE}")
        if not isinstance(description, str) or not 5 <= len(description) <= 120:
            raise CorpusError(f"{path}: description for {code} must be a 5-120 char string")
        if "\n" in description:
            raise CorpusError(f"{path}: description for {code} must be a single line")
    return data


def _parse_front_matter(raw: str, path: Path) -> tuple[dict[str, object], str]:
    """Minimal YAML subset: scalars, inline [a, b] lists, and '  - item' block lists."""
    match = _FRONT_MATTER_RE.match(raw)
    if not match:
        raise CorpusError(f"{path}: missing --- front matter block")

    meta: dict[str, object] = {}
    key: str | None = None
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and key:
            meta.setdefault(key, [])
            if not isinstance(meta[key], list):
                raise CorpusError(f"{path}: {key} has both a value and list items")
            meta[key].append(item.group(1).strip())  # type: ignore[union-attr]
            continue
        field = re.match(r"^([A-Za-z_][\w]*):\s*(.*)$", line)
        if not field:
            raise CorpusError(f"{path}: cannot parse front-matter line {line!r}")
        key, value = field.group(1), field.group(2).strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            meta[key] = [v.strip() for v in inner.split(",") if v.strip()] if inner else []
        elif value:
            meta[key] = value
        else:
            meta[key] = []
    return meta, raw[match.end() :]


def _parse_sections(body: str, path: Path) -> dict[str, str]:
    headings = list(_SECTION_RE.finditer(body))
    if not headings:
        raise CorpusError(f"{path}: no '## ' sections found")
    sections: dict[str, str] = {}
    for i, heading in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        name = heading.group(1).strip()
        if name in sections:
            raise CorpusError(f"{path}: duplicate section {name!r}")
        sections[name] = body[heading.end() : end].strip()
    if tuple(sections) != SECTION_ORDER:
        raise CorpusError(
            f"{path}: sections must be exactly {list(SECTION_ORDER)} in that order, "
            f"got {list(sections)}"
        )
    return sections


def parse_runbook(path: Path, tcodes: dict[str, str]) -> Runbook:
    raw = path.read_text(encoding="utf-8")
    meta, body = _parse_front_matter(raw, path)
    sections = _parse_sections(body, path)

    try:
        runbook = Runbook(**meta, sections=sections, source_path=path)  # type: ignore[arg-type]
    except Exception as exc:
        raise CorpusError(f"{path}: {exc}") from exc

    if runbook.doc_id != path.stem:
        raise CorpusError(f"{path}: doc_id {runbook.doc_id!r} must equal the filename stem")

    named = set(runbook.tcodes) | set(_CHECK_TCODE_RE.findall(sections["Check"]))
    for code in sorted(named):
        if code not in tcodes:
            raise CorpusError(f"{path}: T-code {code!r} is not in data/tcodes.json")
    if not sections["References"].count("http"):
        raise CorpusError(f"{path}: the References section must list at least one URL")
    return runbook


def load_corpus(
    runbook_dir: Path | None = None, tcodes_path: Path | None = None
) -> tuple[list[Runbook], dict[str, str]]:
    runbook_dir = runbook_dir or config.RUNBOOK_DIR
    tcodes = load_tcodes(tcodes_path)
    paths = sorted(runbook_dir.glob("*.md"))
    if not paths:
        raise CorpusError(f"no runbooks found in {runbook_dir}")

    runbooks = [parse_runbook(p, tcodes) for p in paths]

    ids = Counter(r.doc_id for r in runbooks)
    duplicates = [doc_id for doc_id, n in ids.items() if n > 1]
    if duplicates:
        raise CorpusError(f"duplicate doc_id(s): {duplicates}")
    if len(runbooks) != 16:
        raise CorpusError(f"expected 16 runbooks, found {len(runbooks)}")
    per_category = Counter(r.category for r in runbooks)
    wrong = {c: per_category.get(c, 0) for c in CATEGORIES if per_category.get(c, 0) != 2}
    if wrong:
        raise CorpusError(f"expected exactly 2 runbooks per category, got {wrong}")
    return runbooks, tcodes


def corpus_sha(runbook_dir: Path | None = None, tcodes_path: Path | None = None) -> str:
    """Identity of the corpus: changes whenever any runbook or the allow-list changes.

    Hashes text content with line endings normalised to '\\n', not raw bytes — git's
    core.autocrlf rewrites CRLF/LF on checkout depending on OS and config, which would
    otherwise make this hash differ across machines (or even across a checkout on the
    same machine) for byte-identical logical content, silently breaking the
    reproducibility guarantee (SC-004, R-06) and causing false StaleIndexError."""
    runbook_dir = runbook_dir or config.RUNBOOK_DIR
    tcodes_path = tcodes_path or config.TCODES_PATH
    digest = hashlib.sha256()
    for path in sorted(runbook_dir.glob("*.md")) + [tcodes_path]:
        digest.update(path.read_text(encoding="utf-8").encode("utf-8"))
    return digest.hexdigest()
