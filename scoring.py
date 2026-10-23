
PENALTY = {"high": 12, "medium": 5, "low": 1}


def trust_score(findings):
    """Start at 100 and subtract points for each finding."""
    score = 100 - sum(PENALTY[f.severity] for f in findings)
    return max(score, 0)


def verdict(score, findings):
    has_high = any(f.severity == "high" for f in findings)
    if score >= 85 and not has_high:
        return "SAFE TO ANALYZE"
    if score >= 60:
        return "USE WITH CAUTION"
    return "DO NOT USE UNTIL FIXED"
