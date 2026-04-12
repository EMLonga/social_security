from sqlalchemy import create_engine, text


DB_URL = "postgresql+psycopg://postgres:123456@localhost:5432/social_security"


def main() -> None:
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM user_event_likes"))
        conn.execute(text("DELETE FROM user_event_saves"))
        conn.execute(text("DELETE FROM user_community_follows"))
        conn.execute(text("DELETE FROM comments"))
        conn.execute(text("DELETE FROM events"))
        conn.execute(text("DELETE FROM communities"))
        conn.execute(text("DELETE FROM spider_tasks"))
        conn.execute(text("DELETE FROM sensitive_words"))
        conn.execute(text("DELETE FROM auth_verification_codes"))
        conn.execute(
            text("DELETE FROM users WHERE NOT (role::text IN ('ADMIN','admin') OR username='admin')")
        )

        for table in [
            "users",
            "communities",
            "events",
            "comments",
            "spider_tasks",
            "sensitive_words",
            "auth_verification_codes",
        ]:
            seq = conn.execute(text("SELECT pg_get_serial_sequence(:table, 'id')"), {"table": table}).scalar_one()
            if not seq:
                continue
            max_id = conn.execute(text(f"SELECT COALESCE(MAX(id), 0) FROM {table}")).scalar_one()
            if max_id > 0:
                conn.execute(text("SELECT setval(:seq, :val, true)"), {"seq": seq, "val": max_id})
            else:
                conn.execute(text("SELECT setval(:seq, 1, false)"), {"seq": seq})

    print("CLEAN_OK")


if __name__ == "__main__":
    main()
