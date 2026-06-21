"""A tiny doc-search ranker — the code under test for this example.

`baseline_rank` is what the team ships today: exact keyword overlap. When nothing
matches it returns None — it ABSTAINS, and the app asks the user to clarify.

`candidate_rank` is the proposed "fuzzy" upgrade: it also gives partial credit for
substring matches. It ranks more queries (a real win on word variants like
"migrations" -> "migration"), but it NEVER abstains — so on inputs it doesn't really
understand it confidently returns a wrong doc instead of declining.

That contrast is the whole point: a confidently-wrong answer is worse than a safe
abstention, and pass-rate alone hides the difference.
"""

DOCS = {
    "auth/reset.md":     {"reset", "password", "forgot", "login"},
    "billing/refund.md": {"refund", "payment", "charge", "invoice"},
    "db/migrate.md":     {"migration", "schema", "database", "alembic"},
    "cache/ttl.md":      {"cache", "ttl", "expiry", "redis"},
}


def _tokens(query):
    return [w.strip(".,?!").lower() for w in query.split()]


def baseline_rank(query):
    """Exact keyword overlap; returns the best doc, or None when nothing matches."""
    qs = _tokens(query)
    scored = [(sum(1 for w in qs if w in kws), doc) for doc, kws in DOCS.items()]
    best_score, best_doc = max(scored)
    return best_doc if best_score > 0 else None      # abstain on no exact match


def candidate_rank(query):
    """Exact match = 1.0, substring match = 0.5. Always returns a doc (never abstains)."""
    qs = _tokens(query)
    scored = []
    for doc, kws in DOCS.items():
        score = 0.0
        for w in qs:
            if w in kws:
                score += 1.0
            elif any(w in k or k in w for k in kws):
                score += 0.5
        scored.append((score, doc))
    best_score, best_doc = max(scored)
    return best_doc                                  # never abstains — always guesses
