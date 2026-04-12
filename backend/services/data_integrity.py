from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def cleanup_orphan_relations(db: Session, commit: bool = True) -> dict:
    """
    Remove orphan relation rows that point to missing parent records.
    Works for both SQLite and PostgreSQL.
    """
    statements = {
        "user_event_likes": """
            DELETE FROM user_event_likes l
            WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = l.user_id)
               OR NOT EXISTS (SELECT 1 FROM events e WHERE e.id = l.event_id)
        """,
        "user_event_saves": """
            DELETE FROM user_event_saves s
            WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = s.user_id)
               OR NOT EXISTS (SELECT 1 FROM events e WHERE e.id = s.event_id)
        """,
        "user_community_follows": """
            DELETE FROM user_community_follows f
            WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = f.user_id)
               OR NOT EXISTS (SELECT 1 FROM communities c WHERE c.id = f.community_id)
        """,
        "comments": """
            DELETE FROM comments c
            WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = c.user_id)
               OR NOT EXISTS (SELECT 1 FROM events e WHERE e.id = c.event_id)
        """,
    }

    removed = {}
    for key, sql in statements.items():
        result = db.execute(text(sql))
        removed[key] = int(result.rowcount or 0)

    if commit:
        db.commit()

    removed["total_removed"] = sum(removed.values())
    return removed
