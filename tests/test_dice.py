# ABOUTME: Tests for manual dice input parser — parse_dice_input in dice.py.
# ABOUTME: Covers S/A/T/F/H/D format, case-insensitivity, spaces, unknown tokens.

import logging
import pytest


def test_parse_successes_and_advantage():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("S2A1")
    assert result == {"success": 2, "advantage": 1}


def test_parse_with_spaces():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("S2 A1 T1")
    assert result == {"success": 2, "advantage": 1, "triumph": 1}


def test_parse_lowercase():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("f1h2d1")
    assert result == {"failure": 1, "threat": 2, "despair": 1}


def test_parse_mixed_case():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("S1f1")
    assert result == {"success": 1, "failure": 1}


def test_parse_all_symbols():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("S1A1T1F1H1D1")
    assert result == {"success": 1, "advantage": 1, "triumph": 1, "failure": 1, "threat": 1, "despair": 1}


def test_parse_triumph():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("T1")
    assert result == {"triumph": 1}


def test_parse_despair():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("D1")
    assert result == {"despair": 1}


def test_parse_threat():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("H3")
    assert result == {"threat": 3}


def test_parse_empty_string():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("")
    assert result == {}


def test_parse_spaces_only():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("   ")
    assert result == {}


def test_parse_omits_zero_counts():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("S2")
    assert "failure" not in result
    assert "threat" not in result


def test_parse_unknown_letter_warns_and_ignores(caplog):
    from showrunner.dice import parse_dice_input
    with caplog.at_level(logging.WARNING, logger="showrunner.dice"):
        result = parse_dice_input("S2X1")
    assert "success" in result
    assert "X" in caplog.text or "x" in caplog.text.lower()


def test_parse_count_greater_than_one():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("S5")
    assert result == {"success": 5}


def test_parse_compact_no_spaces():
    from showrunner.dice import parse_dice_input
    result = parse_dice_input("S2A1T1F0H0D0")
    assert result["success"] == 2
    assert result["advantage"] == 1
    assert result["triumph"] == 1
    assert "failure" not in result
    assert "threat" not in result
    assert "despair" not in result


# ---------------------------------------------------------------------------
# dice_result_from_input — converts parse_dice_input dict to DiceResult
# ---------------------------------------------------------------------------

def test_dice_result_from_input_pass():
    from showrunner.dice import dice_result_from_input
    result = dice_result_from_input({"success": 2, "failure": 1})
    assert result.net_successes == 1
    assert result.passed is True


def test_dice_result_from_input_fail():
    from showrunner.dice import dice_result_from_input
    result = dice_result_from_input({"failure": 2})
    assert result.net_successes == -2
    assert result.passed is False


def test_dice_result_from_input_triumph():
    from showrunner.dice import dice_result_from_input
    result = dice_result_from_input({"triumph": 1})
    assert result.triumphs == 1
    assert result.net_successes == 1
    assert result.passed is True


def test_dice_result_from_input_despair():
    from showrunner.dice import dice_result_from_input
    result = dice_result_from_input({"despair": 1})
    assert result.despairs == 1
    assert result.net_successes == -1
    assert result.passed is False


def test_dice_result_from_input_net_advantage():
    from showrunner.dice import dice_result_from_input
    result = dice_result_from_input({"advantage": 3, "threat": 1})
    assert result.net_advantage == 2


def test_dice_result_from_input_empty():
    from showrunner.dice import dice_result_from_input
    result = dice_result_from_input({})
    assert result.net_successes == 0
    assert result.passed is False
