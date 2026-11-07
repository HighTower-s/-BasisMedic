from app.normalize import cap_length, extract_key_tokens, strip_noise


def test_strip_noise_removes_timestamps():
    text = "2026-11-07 10:15:03 Job started\n10:15:04 User locked"
    stripped = strip_noise(text)
    assert "2026-11-07" not in stripped
    assert "10:15:03" not in stripped
    assert "10:15:04" not in stripped


def test_strip_noise_removes_memory_addresses():
    text = "Short dump at address 0x7FFA2B3C during allocation"
    assert "0x7FFA2B3C" not in strip_noise(text)


def test_strip_noise_collapses_repeated_blank_lines():
    text = "line one\n\n\n\n\nline two"
    assert "\n\n\n" not in strip_noise(text)


def test_cap_length_within_limit_is_unchanged_and_not_truncated():
    text = "short query"
    result, truncated = cap_length(text, limit=2000)
    assert result == text
    assert truncated is False


def test_cap_length_over_limit_truncates_rather_than_raising():
    text = "x" * 2500
    result, truncated = cap_length(text, limit=2000)
    assert len(result) == 2000
    assert truncated is True


def test_extract_key_tokens_runtime_error_name():
    tokens = extract_key_tokens("Runtime Errors TSV_TNEW_PAGE_ALLOC_FAILED occurred")
    assert "TSV_TNEW_PAGE_ALLOC_FAILED" in tokens


def test_extract_key_tokens_rc_code():
    tokens = extract_key_tokens("Transport returned RC=8 during import")
    assert "RC=8" in tokens


def test_extract_key_tokens_tcode():
    tokens = extract_key_tokens("Open ST22 to see the dump analysis")
    assert "ST22" in tokens


def test_extract_key_tokens_job_name():
    tokens = extract_key_tokens("Job log overview for job ZSD_BILLING_DAILY / 02150300")
    assert "ZSD_BILLING_DAILY" in tokens
