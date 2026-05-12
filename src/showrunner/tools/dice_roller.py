# ABOUTME: Genesys narrative dice roller — exact face tables from Core Rulebook Table I.1-2 (p.11).
# ABOUTME: Builds pools, rolls dice, cancels symbols, returns DiceResult with net outcomes.

# TODO(Phase 1): Implement full dice roller — this is the critical path dependency for all other work.

# Die face tables (S=Success, F=Failure, A=Advantage, T=Threat, Tr=Triumph, De=Despair)
BOOST_FACES = [
    {},
    {},
    {"S": 1},
    {"S": 1, "A": 1},
    {"A": 2},
    {"A": 1},
]

SETBACK_FACES = [
    {},
    {},
    {"F": 1},
    {"F": 1},
    {"T": 1},
    {"T": 1},
]

ABILITY_FACES = [
    {},
    {"S": 1},
    {"S": 1},
    {"S": 2},
    {"A": 1},
    {"A": 1},
    {"S": 1, "A": 1},
    {"A": 2},
]

DIFFICULTY_FACES = [
    {},
    {"F": 1},
    {"F": 2},
    {"T": 1},
    {"T": 1},
    {"T": 1},
    {"T": 2},
    {"F": 1, "T": 1},
]

PROFICIENCY_FACES = [
    {},
    {"S": 1},
    {"S": 1},
    {"S": 2},
    {"S": 2},
    {"A": 1},
    {"S": 1, "A": 1},
    {"S": 1, "A": 1},
    {"S": 1, "A": 1},
    {"A": 2},
    {"A": 2},
    {"Tr": 1},
]

CHALLENGE_FACES = [
    {},
    {"F": 1},
    {"F": 1},
    {"F": 2},
    {"F": 2},
    {"T": 1},
    {"T": 1},
    {"F": 1, "T": 1},
    {"F": 1, "T": 1},
    {"T": 2},
    {"T": 2},
    {"De": 1},
]


class DiceResult:
    """Net outcome after symbol cancellation."""

    def __init__(self, net_successes, net_advantage, triumphs, despairs):
        self.net_successes = net_successes
        self.net_advantage = net_advantage
        self.triumphs = triumphs
        self.despairs = despairs
        self.passed = net_successes > 0

    def __repr__(self):
        return (
            f"DiceResult(successes={self.net_successes}, advantage={self.net_advantage}, "
            f"triumphs={self.triumphs}, despairs={self.despairs}, passed={self.passed})"
        )


def build_pool(characteristic: int, skill_ranks: int, difficulty: int,
               boost: int = 0, setback: int = 0, upgrades: int = 0) -> dict:
    """Return die counts for a standard Genesys check.

    Pool construction: max(char, skill) Ability dice, min(char, skill) upgraded to Proficiency.
    """
    proficiency = min(characteristic, skill_ranks)
    ability = max(characteristic, skill_ranks) - proficiency

    # Additional upgrades (Triumph talents, etc.) convert Ability → Proficiency
    extra_upgrades = min(upgrades, ability)
    proficiency += extra_upgrades
    ability -= extra_upgrades

    return {
        "proficiency": proficiency,
        "ability": ability,
        "difficulty": difficulty,
        "challenge": 0,
        "boost": boost,
        "setback": setback,
    }


def cancel_symbols(raw: dict) -> DiceResult:
    """Apply Genesys cancellation rules to a raw symbol count dict.

    Tr and De each contribute +1 to their respective S/F totals before
    cancellation but are preserved independently in the result.
    """
    triumphs = raw.get("Tr", 0)
    despairs = raw.get("De", 0)
    net_successes = raw.get("S", 0) + triumphs - raw.get("F", 0) - despairs
    net_advantage = raw.get("A", 0) - raw.get("T", 0)
    return DiceResult(net_successes, net_advantage, triumphs, despairs)


_FACE_TABLES = {
    "proficiency": PROFICIENCY_FACES,
    "ability": ABILITY_FACES,
    "difficulty": DIFFICULTY_FACES,
    "challenge": CHALLENGE_FACES,
    "boost": BOOST_FACES,
    "setback": SETBACK_FACES,
}


def roll_pool(pool: dict) -> DiceResult:
    """Roll a dice pool and return the net DiceResult."""
    import random
    raw: dict[str, int] = {}
    for die_type, count in pool.items():
        faces = _FACE_TABLES[die_type]
        for _ in range(count):
            face = random.choice(faces)
            for symbol, qty in face.items():
                raw[symbol] = raw.get(symbol, 0) + qty
    return cancel_symbols(raw)


_SYMBOL_CODES = {"s": "S", "f": "F", "a": "A", "t": "T", "tr": "Tr", "de": "De"}


def parse_manual_input(text: str) -> DiceResult:
    """Parse a space-separated string of symbol tokens into a DiceResult.

    Each token is an integer followed by a symbol code (s, f, a, t, tr, de).
    Raises ValueError on unrecognised codes.
    """
    raw: dict[str, int] = {}
    for token in text.split():
        # Split numeric prefix from alphabetic suffix
        i = 0
        while i < len(token) and (token[i].isdigit() or (i == 0 and token[i] == "-")):
            i += 1
        qty_str, code = token[:i], token[i:].lower()
        if code not in _SYMBOL_CODES or not qty_str:
            raise ValueError(f"Unrecognised token: {token!r}")
        symbol = _SYMBOL_CODES[code]
        raw[symbol] = raw.get(symbol, 0) + int(qty_str)
    return cancel_symbols(raw)
