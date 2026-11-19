from uuid import UUID

from psycopg.types.json import Jsonb

from app.database.connection import get_connection


def create_session(user_id, title="New chat"):
    with get_connection() as conn:
        conn.execute("SELECT id FROM app_users WHERE id=%s FOR UPDATE", (user_id,)).fetchone()
        conn.execute(
            "UPDATE conversation_sessions SET status='archived', updated_at=NOW() "
            "WHERE user_id=%s AND status='active'",
            (user_id,),
        )
        row = conn.execute(
            """INSERT INTO conversation_sessions (user_id, title, status)
               VALUES (%s, %s, 'active')
               RETURNING id, user_id, title, status, created_at, updated_at""",
            (user_id, title),
        ).fetchone()
    return row


def list_sessions(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT s.id, s.user_id, s.title, s.status, s.created_at,
                      s.updated_at, COUNT(m.id) AS message_count
               FROM conversation_sessions s
               LEFT JOIN conversation_messages m ON m.session_id=s.id
               WHERE s.user_id=%s
               GROUP BY s.id
               ORDER BY s.updated_at DESC""",
            (user_id,),
        ).fetchall()
    return rows


def get_session(session_id, user_id):
    with get_connection() as conn:
        return conn.execute(
            """SELECT id, user_id, title, status, created_at, updated_at
               FROM conversation_sessions WHERE id=%s AND user_id=%s""",
            (UUID(str(session_id)), user_id),
        ).fetchone()


def activate_session(session_id, user_id):
    session_id = UUID(str(session_id))
    with get_connection() as conn:
        conn.execute("SELECT id FROM app_users WHERE id=%s FOR UPDATE", (user_id,)).fetchone()
        target = conn.execute(
            "SELECT id FROM conversation_sessions WHERE id=%s AND user_id=%s",
            (session_id, user_id),
        ).fetchone()
        if target is None:
            return None
        conn.execute(
            "UPDATE conversation_sessions SET status='archived', updated_at=NOW() "
            "WHERE user_id=%s AND status='active'",
            (user_id,),
        )
        return conn.execute(
            """UPDATE conversation_sessions SET status='active', updated_at=NOW()
               WHERE id=%s AND user_id=%s
               RETURNING id, user_id, title, status, created_at, updated_at""",
            (session_id, user_id),
        ).fetchone()


def get_messages(session_id, user_id, limit=None):
    session_id = UUID(str(session_id))
    with get_connection() as conn:
        if limit is None:
            rows = conn.execute(
                """SELECT m.id, m.session_id, m.role, m.content, m.citations,
                          m.abstained, m.metadata, m.created_at
                   FROM conversation_messages m
                   JOIN conversation_sessions s ON s.id=m.session_id
                   WHERE m.session_id=%s AND s.user_id=%s
                   ORDER BY m.created_at, m.id""",
                (session_id, user_id),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT id, session_id, role, content, citations, abstained,
                          metadata, created_at
                   FROM (
                       SELECT m.id, m.session_id, m.role, m.content, m.citations,
                              m.abstained, m.metadata, m.created_at
                       FROM conversation_messages m
                       JOIN conversation_sessions s ON s.id=m.session_id
                       WHERE m.session_id=%s AND s.user_id=%s
                       ORDER BY m.created_at DESC, m.id DESC
                       LIMIT %s
                   ) recent
                   ORDER BY created_at, id""",
                (session_id, user_id, limit),
            ).fetchall()
    return rows


def append_message(session_id, user_id, role, content, *, citations=None, abstained=False, metadata=None):
    session_id = UUID(str(session_id))
    with get_connection() as conn:
        row = conn.execute(
            """INSERT INTO conversation_messages
               (session_id, role, content, citations, abstained, metadata)
               SELECT s.id, %s, %s, %s, %s, %s
               FROM conversation_sessions s
               WHERE s.id=%s AND s.user_id=%s
               RETURNING id, session_id, role, content, citations,
                         abstained, metadata, created_at""",
            (
                role,
                content,
                Jsonb(citations or []),
                abstained,
                Jsonb(metadata or {}),
                session_id,
                user_id,
            ),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            """UPDATE conversation_sessions
               SET updated_at=NOW(),
                   title=CASE WHEN title='New chat' AND %s='user'
                              THEN LEFT(%s, 80) ELSE title END
               WHERE id=%s AND user_id=%s""",
            (role, content.strip(), session_id, user_id),
        )
    return row
