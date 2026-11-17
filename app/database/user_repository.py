from uuid import UUID

from app.database.connection import get_connection


def create_user(email, password_hash):
    with get_connection() as conn:
        return conn.execute(
            """INSERT INTO app_users (email, password_hash)
               VALUES (%s, %s) RETURNING id, email, created_at""",
            (email, password_hash),
        ).fetchone()


def get_user_by_email(email):
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, email, password_hash, created_at FROM app_users WHERE email=%s",
            (email,),
        ).fetchone()


def get_user_by_id(user_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, email, created_at FROM app_users WHERE id=%s",
            (UUID(str(user_id)),),
        ).fetchone()
