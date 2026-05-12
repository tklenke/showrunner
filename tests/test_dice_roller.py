# ABOUTME: Tests for the Genesys narrative dice roller.
# ABOUTME: Covers face table accuracy, pool construction, symbol cancellation, and manual input parsing.

import pytest
from showrunner.tools.dice_roller import (
    BOOST_FACES,
    SETBACK_FACES,
    ABILITY_FACES,
    DIFFICULTY_FACES,
    PROFICIENCY_FACES,
    CHALLENGE_FACES,
    DiceResult,
    build_pool,
    cancel_symbols,
    parse_manual_input,
)


# ---------------------------------------------------------------------------
# 1.1 Face Table Coverage
# ---------------------------------------------------------------------------

def test_boost_has_6_faces():
    assert len(BOOST_FACES) == 6

def test_setback_has_6_faces():
    assert len(SETBACK_FACES) == 6

def test_ability_has_8_faces():
    assert len(ABILITY_FACES) == 8

def test_difficulty_has_8_faces():
    assert len(DIFFICULTY_FACES) == 8

def test_proficiency_has_12_faces():
    assert len(PROFICIENCY_FACES) == 12

def test_challenge_has_12_faces():
    assert len(CHALLENGE_FACES) == 12

def test_boost_face_distribution():
    # 2 blank, 1 S, 1 SA, 1 AA, 1 A
    blanks = sum(1 for f in BOOST_FACES if not f)
    assert blanks == 2
    assert {"S": 1} in BOOST_FACES
    assert {"S": 1, "A": 1} in BOOST_FACES
    assert {"A": 2} in BOOST_FACES
    assert {"A": 1} in BOOST_FACES

def test_ability_face_distribution():
    # 1 blank, 2 S, 1 SS, 2 A, 1 SA, 1 AA
    blanks = sum(1 for f in ABILITY_FACES if not f)
    assert blanks == 1
    assert sum(1 for f in ABILITY_FACES if f == {"S": 1}) == 2
    assert {"S": 2} in ABILITY_FACES
    assert sum(1 for f in ABILITY_FACES if f == {"A": 1}) == 2
    assert {"S": 1, "A": 1} in ABILITY_FACES
    assert {"A": 2} in ABILITY_FACES

def test_proficiency_face_distribution():
    # 1 blank, 2 S, 2 SS, 1 A, 3 SA, 2 AA, 1 Tr
    blanks = sum(1 for f in PROFICIENCY_FACES if not f)
    assert blanks == 1
    assert sum(1 for f in PROFICIENCY_FACES if f == {"S": 1}) == 2
    assert sum(1 for f in PROFICIENCY_FACES if f == {"S": 2}) == 2
    assert sum(1 for f in PROFICIENCY_FACES if f == {"A": 1}) == 1
    assert sum(1 for f in PROFICIENCY_FACES if f == {"S": 1, "A": 1}) == 3
    assert sum(1 for f in PROFICIENCY_FACES if f == {"A": 2}) == 2
    assert {"Tr": 1} in PROFICIENCY_FACES

def test_challenge_face_distribution():
    # 1 blank, 2 F, 2 FF, 2 T, 2 FT, 2 TT, 1 De
    blanks = sum(1 for f in CHALLENGE_FACES if not f)
    assert blanks == 1
    assert sum(1 for f in CHALLENGE_FACES if f == {"F": 1}) == 2
    assert sum(1 for f in CHALLENGE_FACES if f == {"F": 2}) == 2
    assert sum(1 for f in CHALLENGE_FACES if f == {"T": 1}) == 2
    assert sum(1 for f in CHALLENGE_FACES if f == {"F": 1, "T": 1}) == 2
    assert sum(1 for f in CHALLENGE_FACES if f == {"T": 2}) == 2
    assert {"De": 1} in CHALLENGE_FACES


# ---------------------------------------------------------------------------
# 1.2 Pool Construction
# ---------------------------------------------------------------------------

def test_pool_untrained_skill():
    pool = build_pool(characteristic=3, skill_ranks=0, difficulty=2)
    assert pool["ability"] == 3
    assert pool["proficiency"] == 0

def test_pool_equal_char_and_skill():
    pool = build_pool(characteristic=2, skill_ranks=2, difficulty=2)
    assert pool["ability"] == 0
    assert pool["proficiency"] == 2

def test_pool_skill_exceeds_char():
    pool = build_pool(characteristic=2, skill_ranks=4, difficulty=2)
    assert pool["ability"] == 2
    assert pool["proficiency"] == 2

def test_pool_char_exceeds_skill():
    pool = build_pool(characteristic=4, skill_ranks=2, difficulty=2)
    assert pool["ability"] == 2
    assert pool["proficiency"] == 2

def test_pool_difficulty_passthrough():
    pool = build_pool(characteristic=3, skill_ranks=1, difficulty=3)
    assert pool["difficulty"] == 3

def test_pool_boost_and_setback():
    pool = build_pool(characteristic=3, skill_ranks=1, difficulty=2, boost=2, setback=1)
    assert pool["boost"] == 2
    assert pool["setback"] == 1

def test_pool_upgrades_convert_ability_to_proficiency():
    # char=3, skill=1 → 2 ability, 1 proficiency; 1 upgrade → 1 ability, 2 proficiency
    pool = build_pool(characteristic=3, skill_ranks=1, difficulty=2, upgrades=1)
    assert pool["proficiency"] == 2
    assert pool["ability"] == 1

def test_pool_upgrades_cannot_exceed_available_ability_dice():
    # char=2, skill=2 → 0 ability, 2 proficiency; upgrades have nothing to convert
    pool = build_pool(characteristic=2, skill_ranks=2, difficulty=2, upgrades=3)
    assert pool["ability"] == 0
    assert pool["proficiency"] == 2


# ---------------------------------------------------------------------------
# 1.3 DiceResult and Symbol Cancellation
# ---------------------------------------------------------------------------

def test_net_successes_positive_is_pass():
    result = cancel_symbols({"S": 2, "F": 1})
    assert result.passed is True
    assert result.net_successes == 1

def test_net_successes_zero_is_fail():
    result = cancel_symbols({"S": 1, "F": 1})
    assert result.passed is False
    assert result.net_successes == 0

def test_net_successes_negative_is_fail():
    result = cancel_symbols({"S": 1, "F": 3})
    assert result.passed is False
    assert result.net_successes == -2

def test_advantage_threat_cancellation():
    result = cancel_symbols({"A": 3, "T": 2})
    assert result.net_advantage == 1

def test_triumph_counts_as_success():
    # 1 Tr = 1 success; 2 F cancels it → net -1 successes, fail, Triumph preserved
    result = cancel_symbols({"Tr": 1, "F": 2})
    assert result.net_successes == -1
    assert result.passed is False
    assert result.triumphs == 1

def test_despair_counts_as_failure():
    # 2 S, 1 De = 2S vs 1F (De) → net +1 success, pass, Despair preserved
    result = cancel_symbols({"S": 2, "De": 1})
    assert result.net_successes == 1
    assert result.passed is True
    assert result.despairs == 1

def test_triumph_does_not_cancel_despair():
    result = cancel_symbols({"Tr": 1, "De": 1})
    assert result.triumphs == 1
    assert result.despairs == 1

def test_despair_does_not_cancel_triumph():
    result = cancel_symbols({"De": 1, "Tr": 1})
    assert result.triumphs == 1
    assert result.despairs == 1

def test_all_cancel_to_zero():
    result = cancel_symbols({"S": 2, "F": 2, "A": 1, "T": 1})
    assert result.passed is False
    assert result.net_successes == 0
    assert result.net_advantage == 0


# ---------------------------------------------------------------------------
# 1.5 Manual Dice Input Parser
# ---------------------------------------------------------------------------

def test_parse_simple_successes():
    result = parse_manual_input("2s 1a")
    assert result.net_successes == 2
    assert result.net_advantage == 1
    assert result.passed is True

def test_parse_triumph():
    result = parse_manual_input("1tr")
    assert result.triumphs == 1
    assert result.net_successes == 1
    assert result.passed is True

def test_parse_despair():
    result = parse_manual_input("1de")
    assert result.despairs == 1
    assert result.net_successes == -1
    assert result.passed is False

def test_parse_mixed_symbols():
    # 1tr 2a 1f → Tr(+1S) vs 1F → net 0S, fail; 2A net; Tr preserved
    result = parse_manual_input("1tr 2a 1f")
    assert result.net_successes == 0
    assert result.passed is False
    assert result.triumphs == 1
    assert result.net_advantage == 2

def test_parse_cancels_correctly():
    result = parse_manual_input("3s 2f")
    assert result.net_successes == 1
    assert result.passed is True

def test_parse_invalid_token_raises():
    with pytest.raises(ValueError):
        parse_manual_input("2x")

def test_parse_empty_string():
    result = parse_manual_input("")
    assert result.net_successes == 0
    assert result.net_advantage == 0
    assert result.triumphs == 0
    assert result.despairs == 0
    assert result.passed is False
