"""Pure retrieval metrics. recall/mrr operate at doc_id level (data-model.md 8)."""


def recall_at_k(ranked_docs: list[str], relevant_docs: list[str]) -> float:
    if not relevant_docs:
        raise ValueError("relevant_docs must be non-empty")
    hit = set(ranked_docs) & set(relevant_docs)
    return len(hit) / len(relevant_docs)


def mrr(ranked_docs: list[str], relevant_docs: list[str]) -> float:
    relevant = set(relevant_docs)
    for i, doc in enumerate(ranked_docs, start=1):
        if doc in relevant:
            return 1.0 / i
    return 0.0


def gate_accuracy(gated_out_flags: list[bool]) -> float:
    """Fraction of out-of-scope cases correctly rejected (flag True means [] was returned)."""
    if not gated_out_flags:
        return 0.0
    return sum(gated_out_flags) / len(gated_out_flags)


def false_refusal_rate(gated_out_flags: list[bool]) -> float:
    """Fraction of in-scope cases wrongly rejected (flag True means [] was returned)."""
    if not gated_out_flags:
        return 0.0
    return sum(gated_out_flags) / len(gated_out_flags)
