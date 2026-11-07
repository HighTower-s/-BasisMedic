"""EDGE: `python -m app.cli ingest|search` — parse args, call one service, print, map
exceptions to exit codes. No business logic lives here (Constitution VI)."""

import argparse
import json
import sys

from app.config import ConfigError
from app.retrieval.ingest import build_index
from app.retrieval.runbooks import CorpusError
from app.retrieval.search import InvalidQueryError, search
from app.retrieval.store import StaleIndexError


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


def _cmd_search(args: argparse.Namespace) -> int:
    from app import config
    from app.retrieval.store import Store

    if args.file:
        query = open(args.file, encoding="utf-8").read()
    else:
        query = args.query

    mode = args.mode or config.retrieval_mode()
    k = args.k if args.k is not None else config.top_k()
    min_score = args.min_score if args.min_score is not None else config.min_score()

    try:
        store = Store.load()
        hits = search(query, mode=mode, k=k, min_score=min_score, store=store)
    except InvalidQueryError as exc:
        print(f"invalid query: {exc}", file=sys.stderr)
        return 2
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 3
    except StaleIndexError as exc:
        print(f"index error: {exc}", file=sys.stderr)
        return 5
    except Exception as exc:  # UpstreamError from dense/hybrid gateway calls
        print(f"gateway error: {exc}", file=sys.stderr)
        return 4

    if args.show_tokens:
        from app.normalize import extract_key_tokens

        print(f"key tokens  : {extract_key_tokens(query)}", file=sys.stderr)
        print(f"rare tokens : {sorted(store.rare_tokens(query.strip()))}", file=sys.stderr)

    if not hits:
        from app.retrieval.search import rank

        print("NO_RELEVANT_RUNBOOK")
        print(f"Nothing in the corpus cleared the relevance floor (min_score={min_score}).")
        if mode in ("dense", "hybrid"):
            ranked = rank(query, mode=mode, store=store)
            best = ranked[0].dense_score if ranked else None
            print(f"  best dense score : {best:.3f}" if best is not None else "  best dense score : n/a")
        print("  rare tokens seen :", sorted(store.rare_tokens(query.strip())) or "none")
        print("This incident is not covered by the runbooks.")
        return 0

    if args.json:
        print(json.dumps([h.model_dump() for h in hits], indent=2))
        return 0

    for hit in hits:
        score = hit.score_for(mode)
        print(f"{hit.rank}. {hit.chunk_id:<35} {mode} {score:.3f}")
        print(f"   {hit.text[:200]}")
    return 0


def _print_triage_result(result) -> None:
    print(f"category    : {result.category}")
    print(f"summary     : {result.summary}")
    print(f"tcodes      : {', '.join(result.tcodes) or '(none)'}")
    print("steps       :")
    for i, step in enumerate(result.steps, start=1):
        suffix = f"  [{step.tcode}]" if step.tcode else ""
        print(f"  {i}. {step.action}{suffix}")
    print(f"escalate_to : {result.escalate_to or '(none)'}")
    print(f"sources     : {', '.join(result.sources) or '(none)'}")
    print(f"confidence  : {result.confidence}")
    if result.unverified_tcodes:
        print(f"unverified  : {', '.join(result.unverified_tcodes)}", file=sys.stderr)
    if result.category == "out_of_scope":
        print("This incident is not covered by the runbooks.")


def _cmd_triage(args: argparse.Namespace) -> int:
    from app.retrieval.store import Store
    from app.triage_service import triage

    if args.file:
        log = open(args.file, encoding="utf-8").read()
    else:
        log = args.query

    try:
        store = Store.load()
        trace: list = [] if args.show_trace else None
        result = triage(log, store=store, trace=trace)
        if trace:
            for record in trace:
                print(f"tool call: {record.tool}({record.args}) -> {record.result[:200]}", file=sys.stderr)
    except InvalidQueryError as exc:
        print(f"invalid query: {exc}", file=sys.stderr)
        return 2
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 3
    except StaleIndexError as exc:
        print(f"index error: {exc}", file=sys.stderr)
        return 5
    except Exception as exc:  # UpstreamError from chat/embedding gateway calls
        print(f"gateway error: {exc}", file=sys.stderr)
        return 4

    if args.json:
        print(json.dumps(result.model_dump(), indent=2))
    else:
        _print_triage_result(result)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="build the search index from the corpus")
    ingest_parser.add_argument("--strategy", choices=("section", "fixed"), default=None)
    ingest_parser.add_argument("--no-embed", action="store_true")
    ingest_parser.add_argument("--quiet", action="store_true")
    ingest_parser.set_defaults(func=_cmd_ingest)

    search_parser = subparsers.add_parser("search", help="search the corpus with a log or query")
    search_group = search_parser.add_mutually_exclusive_group(required=True)
    search_group.add_argument("query", nargs="?", default=None)
    search_group.add_argument("--file", default=None)
    search_parser.add_argument("--mode", choices=("dense", "bm25", "hybrid"), default=None)
    search_parser.add_argument("--k", type=int, default=None)
    search_parser.add_argument("--min-score", type=float, default=None)
    search_parser.add_argument("--json", action="store_true")
    search_parser.add_argument("--show-tokens", action="store_true")
    search_parser.set_defaults(func=_cmd_search)

    triage_parser = subparsers.add_parser("triage", help="triage a log with the full agent")
    triage_group = triage_parser.add_mutually_exclusive_group(required=True)
    triage_group.add_argument("query", nargs="?", default=None)
    triage_group.add_argument("--file", default=None)
    triage_parser.add_argument("--json", action="store_true")
    triage_parser.add_argument("--show-trace", action="store_true")
    triage_parser.set_defaults(func=_cmd_triage)

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
