# ABOUTME: Manual dice input parser for Genesys narrative dice.
# ABOUTME: Parses compact symbol strings (S2A1T1) into symbol count dicts.

import logging
import re

_log = logging.getLogger(__name__)

# Single-letter key → canonical symbol name
_KEY_MAP = {
    "s": "success",
    "a": "advantage",
    "t": "triumph",
    "f": "failure",
    "h": "threat",
    "d": "despair",
}

# Matches one letter followed by one or more digits
_TOKEN_RE = re.compile(r"([A-Za-z])(\d+)")


def dice_result_from_input(parsed: dict[str, int]):
    """Convert a parse_dice_input result dict to a DiceResult.

    Bridges the full-name dict (success, advantage, …) to the cancel_symbols
    format expected by dice_roller.
    """
    from showrunner.tools.dice_roller import cancel_symbols

    _NAME_TO_SYMBOL = {
        "success": "S",
        "failure": "F",
        "advantage": "A",
        "threat": "T",
        "triumph": "Tr",
        "despair": "De",
    }
    raw = {_NAME_TO_SYMBOL[k]: v for k, v in parsed.items() if k in _NAME_TO_SYMBOL}
    return cancel_symbols(raw)


def parse_dice_input(text: str) -> dict[str, int]:
    """Parse a compact symbol string into a {symbol: count} dict.

    Format: single-letter key + integer count, spaces tolerated, case-insensitive.
    Valid keys: S=Success, A=Advantage, T=Triumph, F=Failure, H=Threat, D=Despair.
    Unknown letters are logged as warnings and skipped. Zero counts are omitted.
    """
    result: dict[str, int] = {}
    for match in _TOKEN_RE.finditer(text):
        letter, count_str = match.group(1).lower(), match.group(2)
        if letter not in _KEY_MAP:
            _log.warning("Unknown dice symbol %r — ignored", match.group(1))
            continue
        count = int(count_str)
        if count:
            result[_KEY_MAP[letter]] = result.get(_KEY_MAP[letter], 0) + count
    return result
