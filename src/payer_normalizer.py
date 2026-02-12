"""Payer name normalization for cross-hospital comparisons.

Hospital MRFs encode payer names inconsistently.  This module maps raw
payer strings to a canonical ``(insurer, plan_type)`` tuple so that the
same insurer can be compared across hospitals.

Design principles:
  - **Keyword-based extraction** – does not require maintaining an
    exhaustive lookup table for every plan variant.
  - **Two-level output** – ``payer_group`` (e.g. "Aetna") for broad
    comparisons and ``payer_canonical`` (e.g. "Aetna - Commercial")
    for plan-type detail.
  - **Non-destructive** – original ``payer_name`` is preserved;
    canonical columns are added alongside it.
"""

from __future__ import annotations

import re

import pandas as pd

# ── Insurer keyword → canonical insurer name ────────────────────────
# Order matters: more-specific patterns first to avoid false positives.
_INSURER_PATTERNS: list[tuple[str, str]] = [
    (r"\bpremera\b", "Premera Blue Cross"),
    (r"\blifewise\b", "Premera Blue Cross"),
    (r"\bregence\b", "Regence BlueShield"),
    (r"\bbridgespan\b", "Regence BlueShield"),
    (r"\basuris\b", "Regence BlueShield"),
    (r"\bunitedhealth", "UnitedHealthcare"),
    (r"\buhc\b", "UnitedHealthcare"),
    (r"\bunited\s*healthcare\b", "UnitedHealthcare"),
    (r"\baetna\b", "Aetna"),
    (r"\bcigna\b", "Cigna"),
    (r"\bkaiser\b", "Kaiser Permanente"),
    (r"\bmolina\b", "Molina Healthcare"),
    (r"\bhumana\b", "Humana"),
    (r"\bamerigroup\b", "Amerigroup"),
    (r"\bcoordinated\s*care\b", "Coordinated Care"),
    (r"\bambetter\b", "Coordinated Care"),
    (r"\bfirst\s*choice\b", "First Choice Health"),
    (r"\bcommunity\s*health\s*plan\b", "Community Health Plan of WA"),
    (r"\bmultiplan\b", "MultiPlan"),
    (r"\btricare\b", "TRICARE"),
    (r"\bchampva\b", "CHAMPVA"),
    (r"\bworkers?\s*comp", "Workers Comp"),
]

# ── Plan type keyword → canonical plan type ─────────────────────────
_PLAN_TYPE_PATTERNS: list[tuple[str, str]] = [
    (r"\bmedicaid\b", "Medicaid"),
    (r"\bmanaged\s*medicaid\b", "Medicaid"),
    (r"\bmedicare\s*(?:managed\s*care|advantage|hmo|ppo)", "Medicare Advantage"),
    (r"\bmedicare\b", "Medicare"),
    (r"\bexchange\b", "Exchange"),
    (r"\bmarketplace\b", "Exchange"),
    (r"\bcommercial\b", "Commercial"),
    (r"\bhmo\b", "HMO"),
    (r"\bppo\b", "PPO"),
    (r"\bpos\b", "POS"),
    (r"\bepo\b", "EPO"),
]


def _extract_insurer(raw: str) -> str:
    """Extract canonical insurer name from a raw payer string."""
    low = raw.lower()
    for pattern, insurer in _INSURER_PATTERNS:
        if re.search(pattern, low):
            return insurer

    # Fallback heuristics
    if "discounted_cash" in low or "self_pay" in low or "self pay" in low:
        return "Self-Pay / Cash"
    if "blue cross" in low:
        return "Blue Cross"
    if "blue shield" in low:
        return "Blue Shield"

    # Last resort: use the first token before any separator as the group
    first = re.split(r"\s*[-–—|/]\s*", raw.strip())[0].strip()
    if len(first) > 2:
        return first.title()
    return "Other"


def _extract_plan_type(raw: str) -> str:
    """Extract canonical plan type from a raw payer string."""
    low = raw.lower()
    for pattern, plan_type in _PLAN_TYPE_PATTERNS:
        if re.search(pattern, low):
            return plan_type
    return "Other"


def normalize_payer_names(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``payer_group`` and ``payer_canonical`` columns to a pricing DataFrame.

    Parameters
    ----------
    df : DataFrame
        Must contain a ``payer_name`` column.

    Returns
    -------
    DataFrame
        Input frame with two new columns:
        - ``payer_group``: Canonical insurer name (e.g. "Aetna")
        - ``payer_canonical``: Insurer + plan type (e.g. "Aetna - Commercial")
    """
    if "payer_name" not in df.columns:
        df["payer_group"] = "Unknown"
        df["payer_canonical"] = "Unknown"
        return df

    raw = df["payer_name"].astype(str)
    groups = raw.map(_extract_insurer)
    types = raw.map(_extract_plan_type)
    df["payer_group"] = groups
    df["payer_canonical"] = groups + " - " + types
    return df


def fuzzy_match_payer(query: str, payer_list: list[str], top_n: int = 10) -> list[str]:
    """Return the best payer matches for a user's free-text query.

    Uses a simple scoring approach: keyword overlap + prefix bonus.
    No external fuzzy matching library needed.

    Parameters
    ----------
    query : str
        User's input (e.g. "premera ppo", "aetna", "blue cross")
    payer_list : list[str]
        Available payer names to search.
    top_n : int
        Maximum results to return.

    Returns
    -------
    list[str]
        Best matching payer names, sorted by relevance.
    """
    if not query.strip():
        return payer_list[:top_n]

    query_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    if not query_tokens:
        return payer_list[:top_n]

    scored: list[tuple[float, str]] = []
    for payer in payer_list:
        payer_lower = payer.lower()
        payer_tokens = set(re.findall(r"[a-z0-9]+", payer_lower))

        # Token overlap score
        overlap = len(query_tokens & payer_tokens)
        if overlap == 0:
            # Check substring match (e.g. "premera" in "blue cross - premera...")
            substr_score = sum(1 for qt in query_tokens if qt in payer_lower)
            if substr_score == 0:
                continue
            overlap = substr_score * 0.8

        # Normalize by query length so short queries still match well
        score = overlap / len(query_tokens)

        # Bonus for exact prefix match
        if payer_lower.startswith(query.lower().strip()):
            score += 0.5

        scored.append((score, payer))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [p for _, p in scored[:top_n]]
