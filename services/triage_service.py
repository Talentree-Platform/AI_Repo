"""Support ticket triage service — auto-categorize and prioritize."""


CATEGORY_KEYWORDS = {
    "Technical": ["error", "bug", "crash", "loading", "page", "app", "login", "upload", "display", "search"],
    "Payment": ["payment", "refund", "charge", "payout", "bank", "transfer", "invoice", "money", "amount"],
    "Account": ["password", "reset", "email", "verify", "profile", "account", "suspend", "settings"],
    "Other": [],
}

PRIORITY_KEYWORDS = {
    "Urgent": ["urgent", "emergency", "immediately", "critical", "asap", "down", "cannot access"],
    "High": ["important", "serious", "broken", "failed", "error", "lost", "missing"],
    "Medium": ["help", "issue", "problem", "question", "need", "please"],
    "Low": ["how to", "wondering", "general", "info", "suggestion", "feedback"],
}


def triage_ticket(cursor, ticket_id: int) -> dict:
    """Auto-categorize and prioritize a support ticket."""
    cursor.execute("SELECT Id, Subject, Category, Priority FROM SupportTickets WHERE Id = ?", (ticket_id,))
    row = cursor.fetchone()
    if not row:
        return {"error": "Ticket not found"}

    tid, subject, current_cat, current_pri = row
    text = (subject or "").lower()

    # Auto-categorize
    best_cat = "Other"
    best_score = 0
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_cat = cat

    # Auto-prioritize
    priority_score = 0.3  # default medium
    auto_priority = "Medium"
    for pri, keywords in PRIORITY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            auto_priority = pri
            break
    priority_scores = {"Low": 0.2, "Medium": 0.45, "High": 0.7, "Urgent": 0.9}
    priority_score = priority_scores.get(auto_priority, 0.3)

    # Get message count for priority boost
    cursor.execute("SELECT COUNT(*) FROM TicketMessages WHERE TicketId = ?", (ticket_id,))
    msg_count = (cursor.fetchone() or [0])[0]
    if msg_count >= 5:
        priority_score = min(0.99, priority_score + 0.1)

    cursor.execute("""
        UPDATE SupportTickets
        SET AutoCategory = ?, PriorityScore = ?
        WHERE Id = ?
    """, (best_cat, round(priority_score, 2), ticket_id))


    return {
        "ticket_id": ticket_id,
        "auto_category": best_cat,
        "priority_score": round(priority_score, 2),
    }


def triage_all_tickets(cursor) -> list:
    """Triage all tickets."""
    cursor.execute("SELECT Id FROM SupportTickets")
    ids = [r[0] for r in cursor.fetchall()]
    results = []
    for tid in ids:
        try:
            results.append(triage_ticket(cursor, tid))
        except Exception as e:
            results.append({"ticket_id": tid, "error": str(e)})
    return results
