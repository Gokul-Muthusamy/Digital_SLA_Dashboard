from datetime import datetime

try:
    from .constants import (
        ACTION_LABELS,
        WARNING_THRESHOLD_PCT,
        WARNING_ACK_MINUTES,
        BREACH_ACTION_MINUTES,
        DEFAULT_ALERT_RECIPIENTS,
    )
    from .utils import now_str, parse_dt
    from .notifications import (
        get_alert_recipients,
        merge_with_default_recipients,
        get_role_emails,
        get_user_email,
        send_email_alert,
    )
    from .chat_service import send_chat_message
except ImportError:
    from constants import (
        ACTION_LABELS,
        WARNING_THRESHOLD_PCT,
        WARNING_ACK_MINUTES,
        BREACH_ACTION_MINUTES,
        DEFAULT_ALERT_RECIPIENTS,
    )
    from utils import now_str, parse_dt
    from notifications import (
        get_alert_recipients,
        merge_with_default_recipients,
        get_role_emails,
        get_user_email,
        send_email_alert,
    )
    from chat_service import send_chat_message


def get_manager_username(conn):
    row = conn.execute("SELECT username FROM users WHERE role='manager' ORDER BY id LIMIT 1").fetchone()
    return row["username"] if row else "manager1"


def get_support_username(conn):
    row = conn.execute("SELECT username FROM users WHERE role='support' ORDER BY id LIMIT 1").fetchone()
    return row["username"] if row else "support1"


def log_alert(conn, ticket_id, alert_type):
    existing = conn.execute(
        "SELECT 1 FROM alerts WHERE ticket_id=? AND alert_type=?",
        (ticket_id, alert_type)
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO alerts (ticket_id, alert_type, alert_time) VALUES (?, ?, ?)",
            (ticket_id, alert_type, now_str())
        )


def log_action(conn, ticket_id, actor_username, actor_role, action_type, note, next_step="", escalated_to=""):
    action_time = now_str()
    label = ACTION_LABELS.get(action_type, action_type.replace("_", " ").title())
    note_text = (note or "").strip() or "Action updated"
    if not note_text.lower().startswith(label.lower()):
        note_text = f"{label}: {note_text}"
    conn.execute(
        """
        INSERT INTO action_log (ticket_id, actor_username, actor_role, action_type, note, action_time, next_step, escalated_to)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ticket_id, actor_username, actor_role, action_type, note_text, action_time, next_step or None, escalated_to or None),
    )
    conn.execute("UPDATE tickets SET last_action_time=? WHERE id=?", (action_time, ticket_id))


def compute_open_ticket_state(ticket):
    created = parse_dt(ticket["created_time"])
    now = datetime.now()
    if not created:
        return {"elapsed_hours": 0, "time_left": 0, "phase": "UNKNOWN", "sla_status": "IN PROGRESS", "alert": "NONE"}

    elapsed = (now - created).total_seconds() / 3600
    time_left = round(float(ticket["sla_hours"] or 0) - elapsed, 2)
    if time_left <= 0:
        return {"elapsed_hours": elapsed, "time_left": time_left, "phase": "BREACH", "sla_status": "BREACHED", "alert": "BREACH"}
    if elapsed >= WARNING_THRESHOLD_PCT * float(ticket["sla_hours"] or 0):
        return {"elapsed_hours": elapsed, "time_left": time_left, "phase": "WARNING", "sla_status": "IN PROGRESS", "alert": "WARNING"}
    return {"elapsed_hours": elapsed, "time_left": time_left, "phase": "SAFE", "sla_status": "IN PROGRESS", "alert": "NONE"}


def process_sla_automation(conn):
    tickets = conn.execute("SELECT * FROM tickets WHERE status='OPEN'").fetchall()
    manager_username = get_manager_username(conn)
    alert_recipients = merge_with_default_recipients(get_alert_recipients(conn))
    manager_emails = get_role_emails(conn, "manager") or DEFAULT_ALERT_RECIPIENTS

    for t in tickets:
        state = compute_open_ticket_state(t)
        ticket_id = t["id"]
        raised_by = t["raised_by"] or ""
        created = parse_dt(t["created_time"])
        created_text = t["created_time"] or "-"
        sla_hours = float(t["sla_hours"] or 0)
        warning_eta = "-"
        breach_eta = "-"
        if created:
            warning_eta = datetime.fromtimestamp(created.timestamp() + (sla_hours * 0.75 * 3600)).strftime("%Y-%m-%d %H:%M:%S")
            breach_eta = datetime.fromtimestamp(created.timestamp() + (sla_hours * 3600)).strftime("%Y-%m-%d %H:%M:%S")

        warning_subject = f"SLA Warning (65%): Ticket {ticket_id}"
        warning_message = (
            f"Ticket {ticket_id} ({t['title']}) has reached 65% of its SLA window.\n"
            f"Raised by: {t['raised_by'] or '-'}\nCreated time: {created_text}\nSLA (hours): {sla_hours}\n"
            f"Warning threshold crossed at: {warning_eta}\n"
            "Required actions:\n1. Prioritize and acknowledge immediately.\n2. Contact customer and update next action.\n3. Escalate if resolution risk remains.\n"
        )
        breach_subject = f"SLA Breached (100%): Ticket {ticket_id}"
        breach_message = (
            f"Ticket {ticket_id} ({t['title']}) has breached SLA (100% elapsed).\n"
            f"Raised by: {t['raised_by'] or '-'}\nCreated time: {created_text}\nSLA (hours): {sla_hours}\nBreach time: {breach_eta}\n"
            "Required actions:\n1. Start recovery plan immediately.\n2. Escalate to manager and assign owner.\n3. Capture RCA requirement and timeline.\n"
        )

        extension_pending = t["extension_request_status"] == "PENDING" and int(t["extension_requested_minutes"] or 0) > 0
        extension_already_requested = t["extension_request_status"] in {"PENDING", "ACCEPTED", "REJECTED", "AUTO_APPROVED"}
        remaining_hours = float(state["time_left"] or 0)

        if not extension_already_requested and state["phase"] == "WARNING" and sla_hours > 0 and remaining_hours <= (0.25 * sla_hours):
            req_mins = int(t["sla_extension_minutes"] or 0)
            if req_mins > 0:
                conn.execute(
                    """
                    UPDATE tickets
                    SET extension_requested_minutes=?, extension_request_status='PENDING', extension_requested_by=?, extension_requested_time=?,
                        extension_decision_time=NULL, extension_decision_note=NULL, extension_difficulty='CONFIGURED', priority_flag=1,
                        next_action_text=?, next_action_due=?
                    WHERE id=?
                    """,
                    (req_mins, manager_username, now_str(), f"Awaiting user approval for +{req_mins} min extension", now_str(), ticket_id),
                )
                log_action(conn, ticket_id, manager_username, "manager", "MANAGER_SLA_EXTENSION",
                           f"Proactive SLA extension request ({req_mins} minutes) initiated as remaining SLA reached 25%.",
                           next_step="Await user response for extension approval")
                send_chat_message(conn, manager_username, "manager", raised_by, ticket_id,
                                  f"Ticket {ticket_id}: As SLA remaining time reached 25%, I am requesting your approval for a {req_mins}-minute extension to ensure quality resolution. Please respond from your dashboard.",
                                  auto_generated=1)
                user_email = get_user_email(conn, raised_by)
                send_email_alert(
                    f"SLA Extension Approval Request: Ticket {ticket_id}",
                    f"Dear User,\n\nTicket {ticket_id} ({t['title']}) has reached the final 25% of SLA window.\nA professional extension request for {req_mins} minutes has been raised.\nPlease accept or reject in your dashboard.\n\nThank you.",
                    recipients=[user_email] if user_email else get_alert_recipients(conn),
                )

        if state["phase"] == "WARNING":
            log_alert(conn, ticket_id, "WARNING")
            if not t["warning_started_time"]:
                conn.execute("UPDATE tickets SET warning_started_time=? WHERE id=?", (now_str(), ticket_id))
            if not t["warning_mail_sent"]:
                send_email_alert(warning_subject, warning_message, recipients=alert_recipients)
                conn.execute("UPDATE tickets SET warning_mail_sent=1, priority_mail_sent=1 WHERE id=?", (ticket_id,))
            warning_start = parse_dt(t["warning_started_time"])
            if warning_start and not t["warning_ack_time"] and not t["warning_auto_escalated"]:
                age_mins = (datetime.now() - warning_start).total_seconds() / 60
                if age_mins >= WARNING_ACK_MINUTES:
                    note = f"Auto-escalated: warning not acknowledged within {WARNING_ACK_MINUTES} minutes"
                    log_action(conn, ticket_id, "system", "system", "AUTO_ESCALATE_WARNING", note, escalated_to=manager_username)
                    conn.execute("UPDATE tickets SET owner_username=?, warning_auto_escalated=1, next_action_text=?, next_action_due=? WHERE id=?",
                                 (manager_username, "Manager review required", now_str(), ticket_id))
                    send_email_alert(f"Auto Escalation: Ticket {ticket_id}", f"{note}. Ticket title: {t['title']}", recipients=manager_emails)

        elif state["phase"] == "BREACH":
            if not t["breach_mail_sent"]:
                send_email_alert(breach_subject, breach_message, recipients=alert_recipients)
                conn.execute("UPDATE tickets SET breach_mail_sent=1 WHERE id=?", (ticket_id,))

            if extension_pending:
                mins = int(t["extension_requested_minutes"] or 0)
                new_sla = round(float(t["sla_hours"] or 0) + (mins / 60), 2)
                conn.execute(
                    """
                    UPDATE tickets
                    SET sla_hours=?, extension_request_status='AUTO_APPROVED', extension_decision_time=?, extension_decision_note=?,
                        warning_mail_sent=0, breach_mail_sent=0, warning_started_time=NULL, warning_ack_time=NULL, warning_auto_escalated=0,
                        breach_started_time=NULL, breach_action_time=NULL, breach_auto_escalated=0, priority_mail_sent=0, manager_signoff=0,
                        next_action_text=?, next_action_due=?
                    WHERE id=?
                    """,
                    (new_sla, now_str(), "Auto-approved due to no user response before SLA expiry.",
                     f"Extension auto-approved (+{mins} min); continue resolution on revised SLA.", now_str(), ticket_id),
                )
                log_action(conn, ticket_id, "system", "system", "EXTENSION_AUTO_APPROVED",
                           f"No user response before SLA expiry. +{mins} min extension applied automatically.")
                send_chat_message(conn, "system", "system", raised_by, ticket_id,
                                  f"Ticket {ticket_id}: SLA extension has been auto-approved (+{mins} min) as no response was received before expiry. Work will continue on revised SLA.",
                                  auto_generated=1)
                send_chat_message(conn, "system", "system", manager_username, ticket_id,
                                  f"Ticket {ticket_id}: Extension request auto-approved (+{mins} min) due to no user response.", auto_generated=1)
                manager_email_targets = get_role_emails(conn, "manager")
                user_email = get_user_email(conn, raised_by)
                recipient_targets = list(DEFAULT_ALERT_RECIPIENTS)
                for email in manager_email_targets + ([user_email] if user_email else []):
                    if email and email not in recipient_targets:
                        recipient_targets.append(email)
                send_email_alert(
                    f"SLA Extension Auto-Approved: Ticket {ticket_id}",
                    f"Ticket {ticket_id} ({t['title']}) reached SLA expiry without user response.\nExtension of {mins} minutes was auto-approved and SLA timer has been extended.",
                    recipients=recipient_targets,
                )
                continue

            log_alert(conn, ticket_id, "BREACH")
            if not t["breach_started_time"]:
                conn.execute("UPDATE tickets SET breach_started_time=?, manager_signoff=0 WHERE id=?", (now_str(), ticket_id))
            if not t["warning_mail_sent"]:
                send_email_alert(warning_subject, warning_message, recipients=alert_recipients)
                conn.execute("UPDATE tickets SET warning_mail_sent=1, priority_mail_sent=1 WHERE id=?", (ticket_id,))
            breach_start = parse_dt(t["breach_started_time"])
            last_action = parse_dt(t["last_action_time"])
            no_post_breach_action = not last_action or (breach_start and last_action < breach_start)
            if breach_start and no_post_breach_action and not t["breach_auto_escalated"]:
                age_mins = (datetime.now() - breach_start).total_seconds() / 60
                if age_mins >= BREACH_ACTION_MINUTES:
                    note = f"Auto-escalated: no breach action for {BREACH_ACTION_MINUTES} minutes"
                    log_action(conn, ticket_id, "system", "system", "AUTO_ESCALATE_BREACH", note, escalated_to=manager_username)
                    conn.execute(
                        """
                        UPDATE tickets
                        SET owner_username=?, breach_auto_escalated=1, next_action_text=?, next_action_due=?, rca_required=1, manager_signoff=0
                        WHERE id=?
                        """,
                        (manager_username, "Recovery plan and RCA required", now_str(), ticket_id),
                    )
                    send_email_alert(f"Critical SLA Breach Escalation: Ticket {ticket_id}",
                                     f"{note}. Immediate managerial intervention needed.", recipients=manager_emails)


def get_action_logs_by_ticket(conn, ticket_ids):
    if not ticket_ids:
        return {}
    placeholders = ",".join(["?"] * len(ticket_ids))
    rows = conn.execute(
        f"SELECT * FROM action_log WHERE ticket_id IN ({placeholders}) ORDER BY action_time DESC",
        ticket_ids,
    ).fetchall()
    grouped = {ticket_id: [] for ticket_id in ticket_ids}
    for row in rows:
        item = dict(row)
        item["action_label"] = ACTION_LABELS.get(item["action_type"], item["action_type"].replace("_", " ").title())
        grouped[row["ticket_id"]].append(item)
    return grouped


def build_live_token(conn, username=None, role=None):
    ticket_row = conn.execute(
        """
        SELECT COALESCE(MAX(id), 0) AS max_id, COALESCE(MAX(last_action_time), '') AS max_last_action,
               COALESCE(MAX(next_action_due), '') AS max_next_due, COALESCE(MAX(extension_decision_time), '') AS max_ext_decision,
               COALESCE(SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END), 0) AS open_count
        FROM tickets
        """
    ).fetchone()
    alert_row = conn.execute("SELECT COALESCE(MAX(id),0) AS max_id, COALESCE(MAX(alert_time),'') AS max_time FROM alerts").fetchone()
    action_row = conn.execute("SELECT COALESCE(MAX(id),0) AS max_id, COALESCE(MAX(action_time),'') AS max_time FROM action_log").fetchone()
    chat_row = conn.execute("SELECT COALESCE(MAX(id),0) AS max_id, COALESCE(MAX(sent_time),'') AS max_time FROM chat_messages").fetchone()

    user_scope = ""
    if username and role == "user":
        user_scope_row = conn.execute(
            "SELECT COALESCE(MAX(id), 0) AS max_ticket_id, COALESCE(MAX(extension_decision_time), '') AS max_user_ext_decision FROM tickets WHERE raised_by=?",
            (username,),
        ).fetchone()
        user_scope = f"{user_scope_row['max_ticket_id']}:{user_scope_row['max_user_ext_decision']}"

    return "|".join([
        str(ticket_row["max_id"]), ticket_row["max_last_action"], ticket_row["max_next_due"], ticket_row["max_ext_decision"],
        str(ticket_row["open_count"]), str(alert_row["max_id"]), alert_row["max_time"], str(action_row["max_id"]),
        action_row["max_time"], str(chat_row["max_id"]), chat_row["max_time"], user_scope,
    ])


def reset_operational_tables(conn):
    conn.execute("DELETE FROM tickets")
    conn.execute("DELETE FROM alerts")
    conn.execute("DELETE FROM action_log")
    conn.execute("DELETE FROM chat_messages")
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('tickets', 'alerts', 'action_log', 'chat_messages')")

