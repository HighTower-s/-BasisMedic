from app.retrieval.search import fuse_rrf


def test_fuse_rrf_matches_hand_computed_ranks():
    dense = ["a", "b", "c"]
    bm25 = ["b", "a", "d"]
    fused = fuse_rrf(dense, bm25, k=60)
    expected = {
        "a": 1 / 61 + 1 / 62,
        "b": 1 / 62 + 1 / 61,
        "c": 1 / 63,
        "d": 1 / 63,
    }
    for doc_id, score in expected.items():
        assert abs(fused[doc_id] - score) < 1e-9
    assert fused["a"] == fused["b"]  # symmetric: each is rank1 in one list, rank2 in the other


def test_fuse_rrf_empty_dense_list():
    fused = fuse_rrf([], ["x", "y"], k=60)
    assert fused == {"x": 1 / 61, "y": 1 / 62}


def test_fuse_rrf_empty_bm25_list():
    fused = fuse_rrf(["x", "y"], [], k=60)
    assert fused == {"x": 1 / 61, "y": 1 / 62}


def test_fuse_rrf_both_empty():
    assert fuse_rrf([], [], k=60) == {}
