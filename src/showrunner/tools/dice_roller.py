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
    ability = max(characteristic, skill_ranks)
    proficiency = min(characteristic, skill_ranks)

    # Additional upgrades (Triumph talents, etc.) convert Ability → Proficiency
    extra_upgrades = min(upgrades, ability - proficiency)
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


def roll_pool(pool: dict) -> DiceResult:
    """Roll a dice pool and return the net DiceResult."""
    raise NotImplementedError("Phase 1 implementation pending")
