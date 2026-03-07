from flask import Blueprint, request, redirect, session, jsonify

try:
    from ..core import get_db_connection, get_manager_username, send_chat_message
except ImportError:
    from core import get_db_connection, get_manager_username, send_chat_message


chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/send_message", methods=["POST"])
def send_message():
    if "username" not in session:
        return redirect("/")

    sender = session["username"]
    sender_role = session["role"]
    receiver = (request.form.get("receiver_username") or "").strip()
    message_text = (request.form.get("message_text") or "").strip()
    ticket_id = (request.form.get("ticket_id") or "").strip()

    if not message_text:
        return "Message cannot be empty", 400

    conn = get_db_connection()

    if sender_role == "user" and not receiver:
        receiver = get_manager_username(conn)

    if sender_role == "manager" and not receiver and ticket_id:
        t = conn.execute("SELECT raised_by FROM tickets WHERE id=?", (ticket_id,)).fetchone()
        if t:
            receiver = t["raised_by"]

    target = conn.execute("SELECT 1 FROM users WHERE username=?", (receiver,)).fetchone()
    if not target:
        conn.close()
        return "Receiver not found", 400

    send_chat_message(conn, sender, sender_role, receiver, ticket_id, message_text)
    conn.commit()
    conn.close()
    return redirect("/dashboard")


@chat_bp.route("/chat_messages", methods=["GET"])
def chat_messages():
    if "username" not in session:
        return jsonify({"error": "unauthorized"}), 401

    username = session["username"]
    with_user = (request.args.get("with_user") or "").strip()
    ticket_id = (request.args.get("ticket_id") or "").strip()
    try:
        limit = min(max(int(request.args.get("limit", "80")), 1), 200)
    except ValueError:
        limit = 80

    conn = get_db_connection()
    query = """
        SELECT c.*, t.title AS ticket_title
        FROM chat_messages c
        LEFT JOIN tickets t ON t.id = c.ticket_id
        WHERE (c.sender_username=? OR c.receiver_username=?)
    """
    params = [username, username]

    if with_user:
        query += """
            AND (
                (c.sender_username=? AND c.receiver_username=?)
                OR
                (c.sender_username=? AND c.receiver_username=?)
            )
        """
        params.extend([username, with_user, with_user, username])

    if ticket_id.isdigit():
        query += " AND c.ticket_id=?"
        params.append(int(ticket_id))

    query += " ORDER BY c.sent_time ASC, c.id ASC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows])


@chat_bp.route("/send_message_api", methods=["POST"])
def send_message_api():
    if "username" not in session:
        return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(silent=True) or request.form
    sender = session["username"]
    sender_role = session["role"]
    receiver = (payload.get("receiver_username") or "").strip()
    message_text = (payload.get("message_text") or "").strip()
    ticket_id_raw = (payload.get("ticket_id") or "").strip()
    ticket_id = int(ticket_id_raw) if str(ticket_id_raw).isdigit() else None

    if not message_text:
        return jsonify({"error": "Message cannot be empty"}), 400

    conn = get_db_connection()
    if sender_role == "user":
        receiver = get_manager_username(conn)

    if not receiver:
        conn.close()
        return jsonify({"error": "Receiver is required"}), 400

    exists = conn.execute("SELECT 1 FROM users WHERE username=?", (receiver,)).fetchone()
    if not exists:
        conn.close()
        return jsonify({"error": "Receiver not found"}), 400

    send_chat_message(conn, sender, sender_role, receiver, ticket_id, message_text)
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

