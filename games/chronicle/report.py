"""Chronicle -- the report-a-problem payload. UI only in this pass: nothing here touches a network.

A player who thinks a claim is wrong builds a report; the page shows it, saves a draft on this device and
says "reporting opens soon". When the backend table exists (planning/TODO.md CH-6, the same pattern as Le
Champ de Mots' answer reports), the page can post exactly this payload. Nothing is ever posted from here.
"""

REASONS = (
    ("wrong_fact", "The fact looks wrong"),
    ("wrong_date", "The date looks wrong"),
    ("source_mismatch", "A source does not support the claim"),
    ("broken_link", "A source link is broken"),
    ("unbalanced", "The wording is unbalanced or unfair"),
    ("other", "Something else"),
)
REASON_IDS = [r[0] for r in REASONS]
MAX_NOTE = 500


def build(cset, claim_id, reason, note):
    """Return (payload, error). Never raises on bad input."""
    claim = cset.claims.get(claim_id) if isinstance(claim_id, str) else None
    if claim is None:
        return None, "That claim does not exist in this set."
    if reason not in REASON_IDS:
        return None, "Pick a reason first."
    note = (note or "").strip() if isinstance(note, str) else ""
    if len(note) > MAX_NOTE:
        return None, "Keep the note under %d characters." % MAX_NOTE
    payload = {
        "kind": "chronicle-claim-report",
        "set_id": cset.id,
        "set_version": cset.version,
        "set_status": cset.status,
        "claim_id": claim["id"],
        "claim_text": claim["text"],
        "confidence": claim["confidence"],
        "source_urls": [cset.sources[ref["source"]]["url"] for ref in claim["sources"]],
        "reason": reason,
        "note": note,
    }
    return payload, None
