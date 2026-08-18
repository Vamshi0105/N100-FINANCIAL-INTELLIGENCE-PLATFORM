from src.analytics.cagr import calculate_cagr


def test_normal_cagr():
    value, flag = calculate_cagr(
        100,
        121,
        2
    )

    assert round(value, 2) == 10.0
    assert flag is None


def test_turnaround():
    value, flag = calculate_cagr(
        -100,
        100,
        5
    )

    assert value is None
    assert flag == "TURNAROUND"


def test_decline_to_loss():
    value, flag = calculate_cagr(
        100,
        -50,
        5
    )

    assert value is None
    assert flag == "DECLINE_TO_LOSS"


def test_both_negative():
    value, flag = calculate_cagr(
        -100,
        -50,
        5
    )

    assert value is None
    assert flag == "BOTH_NEGATIVE"


def test_zero_base():
    value, flag = calculate_cagr(
        0,
        100,
        5
    )

    assert value is None
    assert flag == "ZERO_BASE"


def test_insufficient_data():
    value, flag = calculate_cagr(
        None,
        100,
        5
    )

    assert value is None
    assert flag == "INSUFFICIENT"