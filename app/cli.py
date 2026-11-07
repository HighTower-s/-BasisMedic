"""EDGE: `python -m app.cli ingest|search` — parse args, call one service, print, map
exceptions to exit codes. No business logic lives here (Constitution VI)."""

import argparse
import sys

from app.config import ConfigError
from app.retrieval.ingest import build_index
from app.retrieval.runbooks import CorpusError


def _cmd_ingest(args: argparse.Namespace) -> int:
    try:
        manifest, n_tcodes, cache_hits, cache_misses = build_index(
            strategy=args.strategy, embed=not args.no_embed
        )
    except CorpusError as exc:
        print(f"corpus error: {exc}", file=sys.stderr)
        return 2
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 3
    except Exception as exc:  # UpstreamError or any gateway failure during embedding
        print(f"gateway error: {exc}", file=sys.stderr)
        return 4

    if not args.quiet:
        print(f"loaded {manifest.n_runbooks} runbooks, wrote {manifest.n_chunks} chunks")

    n_categories = 8
    unit = "sections" if manifest.chunk_strategy == "section" else "chunks"
    print(f"corpus      : {manifest.n_runbooks} runbooks, {n_categories} categories, {manifest.n_chunks} {unit}")
    print(f"tcodes      : {n_tcodes} allow-listed")
    print(f"strategy    : {manifest.chunk_strategy}")
    if args.no_embed:
        print("embeddings  : skipped (--no-embed); bm25 only")
    else:
        print(
            f"embeddings  : {manifest.n_vectors} vectors, dim {manifest.embed_dim}  "
            f"(cache: {cache_hits} hit, {cache_misses} miss)"
        )
    commit = manifest.git_commit or "none"
    print(f"index       : data/index/  corpus_sha={manifest.corpus_sha[:8]}...  commit={commit}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="build the search index from the corpus")
    ingest_parser.add_argument("--strategy", choices=("section", "fixed"), default=None)
    ingest_parser.add_argument("--no-embed", action="store_true")
    ingest_parser.add_argument("--quiet", action="store_true")
    ingest_parser.set_defaults(func=_cmd_ingest)

    return parser


def main(argv: list[str] | None = None) -> int:
    from app import config

    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "strategy", None) is None and args.command == "ingest":
        args.strategy = config.chunk_strategy()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
