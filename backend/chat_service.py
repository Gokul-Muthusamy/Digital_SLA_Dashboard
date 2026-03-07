try:
    from .utils import now_str
except ImportError:
    from utils import now_str


def send_chat_message(conn, sender_username, sender_role, receiver_username, ticket_id, message_text, auto_generated=0):
    if not message_text or not receiver_username:
        return
    conn.execute(
        """
        INSERT INTO chat_messages
        (sender_username, sender_role, receiver_username, ticket_id, message_text, sent_time, auto_generated)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sender_username,
            sender_role,
            receiver_username,
            int(ticket_id) if ticket_id else None,
            message_text.strip(),
            now_str(),
            int(auto_generated),
        ),
    )


def get_chat_messages_for_user(conn, username, limit=120):
    rows = conn.execute(
        """
        SELECT c.*, t.title AS ticket_title
        FROM chat_messages c
        LEFT JOIN tickets t ON t.id = c.ticket_id
        WHERE c.sender_username=? OR c.receiver_username=?
        ORDER BY c.sent_time DESC, c.id DESC
        LIMIT ?
        """,
        (username, username, limit),
    ).fetchall()
    return [dict(row) for row in rows]

