from flask import Blueprint, request, redirect, session, jsonify
from datetime import datetime, timedelta

try:
    from ..core import (
        get_db_connection,
        get_support_username,
        now_str,
        MANAGER_ONLY_ACTIONS,
        MANAGER_IMPACT_ACTIONS,
        get_manager_username,
        get_user_email,
        get_alert_recipients,
        send_email_alert,
        log_action,
        send_chat_message,
        ACTION_LABELS,
        get_role_emails,
        DEFAULT_ALERT_RECIPIENTS,
        parse_dt,
    )
except ImportError:
    from core import (
        get_db_connection,
        get_support_username,
        now_str,
        MANAGER_ONLY_ACTIONS,
        MANAGER_IMPACT_ACTIONS,
        get_manager_username,
        get_user_email,
        get_alert_recipients,
        send_email_alert,
        log_action,
        send_chat_message,
        ACTION_LABELS,
        get_role_emails,
        DEFAULT_ALERT_RECIPIENTS,
        parse_dt,
    )


ticket_bp = Blueprint("ticket", __name__)


@ticket_bp.route("/raise_ticket", methods=["POST"])
def raise_ticket():
    if "username" not in session:
        return redirect("/")

    conn = get_db_connection()
    owner = get_support_username(conn)
    current_time = now_str()

    conn.execute(
        """
        INSERT INTO tickets
        (title, description, created_time, sla_hours, status, raised_by, sla_status, owner_username, next_action_text, next_action_due)
        VALUES (?, ?, ?, ?, 'OPEN', ?, 'IN PROGRESS', ?, ?, ?)
        """,
        (
            request.form["title"],
            request.form["description"],
            current_time,
            float(request.form["sla_hours"]),
            session["username"],
            owner,
            "Initial assessment by support",
            current_time,
        )
    )
    conn.commit()
    conn.close()
    return redirect("/dashboard")


@ticket_bp.route("/ticket_action", methods=["POST"])
def ticket_action():
    if "role" not in session or session["role"] not in {"support", "manager"}:
        return redirect("/")

    ticket_id = request.form.get("ticket_id")
    action_type = (request.form.get("action_type") or "").strip().upper()
    note = (request.form.get("note") or "").strip()
    next_step = (request.form.get("next_step") or "").strip()
    next_action_due = (request.form.get("next_action_due") or "").strip()
    escalated_to = (request.form.get("escalated_to") or "").strip()
    if next_action_due:
        next_action_due = next_action_due.replace("T", " ")

    if not ticket_id or not action_type:
        return "Invalid action payload", 400

    key_actions = {
        "ACK_WARNING",
        "CONTACT_CUSTOMER",
        "REPRIORITIZE",
        "ESCALATE_TO_MANAGER",
        "RECOVERY_PLAN",
        "RCA_REQUIRED",
        "RCA_COMPLETED",
        "CLOSE_WITH_NOTE",
        "CAPTURE_GOOD_PRACTICE",
        "MANAGER_REASSIGN_OWNER",
        "MANAGER_SET_PRIORITY",
        "MANAGER_SLA_EXTENSION",
        "MANAGER_PREVENTIVE_INTERVENTION",
        "MANAGER_CUSTOMER_ASSURANCE",
        "MANAGER_SIGNOFF",
    }
    if action_type in key_actions and not note:
        return "Note is required for this action", 400

    conn = get_db_connection()
    ticket = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    if not ticket:
        conn.close()
        return "Ticket not found", 404

    actor = session["username"]
    role = session["role"]
    current_time = now_str()

    if action_type in MANAGER_ONLY_ACTIONS and role != "manager":
        conn.close()
        return "Only manager can perform this action", 403

    if action_type == "ACK_WARNING":
        conn.execute("UPDATE tickets SET warning_ack_time=?, owner_username=? WHERE id=?", (current_time, actor, ticket_id))
    elif action_type == "ESCALATE_TO_MANAGER":
        if not escalated_to:
            escalated_to = get_manager_username(conn)
        conn.execute(
            "UPDATE tickets SET owner_username=?, next_action_text=?, next_action_due=? WHERE id=?",
            (escalated_to, next_step or "Manager review", next_action_due or current_time, ticket_id),
        )
    elif action_type == "RECOVERY_PLAN":
        conn.execute(
            "UPDATE tickets SET breach_action_time=?, next_action_text=?, next_action_due=? WHERE id=?",
            (current_time, next_step or "Recovery tracking", next_action_due or current_time, ticket_id),
        )
    elif action_type == "RCA_REQUIRED":
        conn.execute("UPDATE tickets SET rca_required=1 WHERE id=?", (ticket_id,))
    elif action_type == "RCA_COMPLETED":
        conn.execute("UPDATE tickets SET rca_completed=1 WHERE id=?", (ticket_id,))
    elif action_type == "CLOSE_WITH_NOTE":
        conn.execute(
            "UPDATE tickets SET next_action_text=?, next_action_due=? WHERE id=?",
            (next_step or "Closure note captured", next_action_due or current_time, ticket_id),
        )
    elif action_type == "CAPTURE_GOOD_PRACTICE":
        conn.execute(
            "UPDATE tickets SET next_action_text=?, next_action_due=? WHERE id=?",
            (next_step or "Good practice documented", next_action_due or current_time, ticket_id),
        )
    elif action_type == "MANAGER_REASSIGN_OWNER":
        if not escalated_to:
            conn.close()
            return "Owner username required in 'Escalate to' field", 400
        conn.execute(
            "UPDATE tickets SET owner_username=?, next_action_text=?, next_action_due=? WHERE id=?",
            (escalated_to, next_step or "Manager reassigned ownership", next_action_due or current_time, ticket_id),
        )
    elif action_type == "MANAGER_SET_PRIORITY":
        priority_note = next_step or "P1 - Immediate action"
        conn.execute(
            "UPDATE tickets SET next_action_text=?, next_action_due=?, priority_flag=1 WHERE id=?",
            (f"Manager Priority: {priority_note}", next_action_due or current_time, ticket_id),
        )
    elif action_type == "MANAGER_SLA_EXTENSION":
        if (ticket["extension_request_status"] or "NONE") != "NONE":
            conn.close()
            return "SLA extension workflow is already completed/requested once for this ticket", 400
        request_mins = int(ticket["sla_extension_minutes"] or 0)
        if request_mins <= 0:
            conn.close()
            return "Extension is disabled for this ticket (SLA Extension is set to 0)", 400
        user_email = get_user_email(conn, ticket["raised_by"])
        recipients = [user_email] if user_email else get_alert_recipients(conn)
        send_email_alert(
            f"SLA Extension Request for Ticket {ticket_id}",
            (
                f"Manager requested SLA extension of {request_mins} minutes for ticket {ticket_id} ({ticket['title']}).\n"
                f"Reason: {note}\n"
                "Please review and respond from your dashboard."
            ),
            recipients=recipients,
        )
        conn.execute(
            """
            UPDATE tickets
            SET extension_requested_minutes=?,
                extension_request_status='PENDING',
                extension_requested_by=?,
                extension_requested_time=?,
                extension_decision_time=NULL,
                extension_decision_note=NULL,
                extension_difficulty='CONFIGURED',
                priority_flag=1,
                next_action_text=?,
                next_action_due=?
            WHERE id=?
            """,
            (
                request_mins,
                actor,
                current_time,
                next_step or f"Waiting user approval for +{request_mins} min SLA extension",
                next_action_due or current_time,
                ticket_id,
            ),
        )
        note = f"Requested +{request_mins} min extension (Configured SLA Extension). {note}"
    elif action_type == "MANAGER_PREVENTIVE_INTERVENTION":
        intervention_due = next_action_due or (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "UPDATE tickets SET next_action_text=?, next_action_due=?, owner_username=?, priority_flag=1 WHERE id=?",
            (next_step or "Manager intervention to prevent breach", intervention_due, ticket["owner_username"] or get_support_username(conn), ticket_id),
        )
    elif action_type == "MANAGER_CUSTOMER_ASSURANCE":
        customer_email = get_user_email(conn, ticket["raised_by"])
        recipients = [customer_email] if customer_email else get_alert_recipients(conn)
        send_email_alert(
            f"Update on your ticket {ticket_id}",
            f"Manager update for ticket {ticket_id} ({ticket['title']}): {note}",
            recipients=recipients,
        )
        conn.execute(
            "UPDATE tickets SET next_action_text=?, next_action_due=? WHERE id=?",
            (next_step or "Customer assurance sent by manager", next_action_due or current_time, ticket_id),
        )
    elif action_type == "MANAGER_SIGNOFF":
        if ticket["rca_required"] and not ticket["rca_completed"]:
            conn.close()
            return "Complete RCA before manager sign-off", 400
        conn.execute(
            "UPDATE tickets SET manager_signoff=1, next_action_text=?, next_action_due=? WHERE id=?",
            (next_step or "Manager sign-off approved for closure", next_action_due or current_time, ticket_id),
        )
    else:
        conn.execute(
            "UPDATE tickets SET owner_username=?, next_action_text=?, next_action_due=? WHERE id=?",
            (actor, next_step or ticket["next_action_text"], next_action_due or ticket["next_action_due"], ticket_id),
        )

    if role == "manager" and action_type in MANAGER_IMPACT_ACTIONS:
        conn.execute("UPDATE tickets SET manager_intervened=1 WHERE id=?", (ticket_id,))

    log_action(conn, ticket_id, actor, role, action_type, note or "Action updated", next_step=next_step, escalated_to=escalated_to)

    if role == "manager":
        action_label = ACTION_LABELS.get(action_type, action_type)
        send_chat_message(
            conn,
            actor,
            role,
            ticket["raised_by"],
            ticket_id,
            (
                f"Ticket {ticket_id} update from Manager: {action_label}. "
                f"Details: {(note or 'Action recorded').strip()}."
            ),
            auto_generated=1,
        )

    if action_type == "ESCALATE_TO_MANAGER":
        manager_emails = get_role_emails(conn, "manager")
        send_email_alert(
            f"Ticket {ticket_id} escalated to manager",
            f"Ticket {ticket_id} ({ticket['title']}) escalated by {actor}. Note: {note}",
            recipients=manager_emails,
        )

    conn.commit()
    conn.close()
    return redirect("/dashboard")


@ticket_bp.route("/set_sla_extension", methods=["POST"])
@ticket_bp.route("/set_task_difficulty", methods=["POST"])  # backward-compatible alias
def set_sla_extension():
    if session.get("role") != "manager":
        return redirect("/")

    ticket_id = request.form.get("ticket_id")
    try:
        sla_extension_minutes = int((request.form.get("sla_extension_minutes") or "0").strip())
    except ValueError:
        return "Invalid SLA extension value", 400
    if sla_extension_minutes < 0:
        return "SLA extension minutes cannot be negative", 400

    conn = get_db_connection()
    ticket = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    if not ticket:
        conn.close()
        return "Ticket not found", 404

    if sla_extension_minutes == 0 and ticket["extension_request_status"] == "PENDING":
        conn.execute(
            """
            UPDATE tickets
            SET extension_request_status='REJECTED',
                extension_decision_time=?,
                extension_decision_note=?
            WHERE id=?
            """,
            (now_str(), "Extension workflow disabled by manager SLA extension setting.", ticket_id),
        )
    conn.execute("UPDATE tickets SET sla_extension_minutes=? WHERE id=?", (sla_extension_minutes, ticket_id))
    log_action(
        conn,
        ticket_id,
        session["username"],
        session["role"],
        "MANAGER_SET_SLA_EXTENSION",
        f"SLA Extension configured to {sla_extension_minutes} minutes.",
        next_step="SLA extension configured for request workflow",
    )
    conn.commit()
    conn.close()
    return redirect("/dashboard")


@ticket_bp.route("/set_sla_extension_api", methods=["POST"])
@ticket_bp.route("/set_task_difficulty_api", methods=["POST"])  # backward-compatible alias
def set_sla_extension_api():
    if session.get("role") != "manager":
        return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(silent=True) or request.form
    ticket_id = payload.get("ticket_id")
    try:
        sla_extension_minutes = int(str(payload.get("sla_extension_minutes", "0")).strip())
    except ValueError:
        return jsonify({"error": "Invalid SLA extension value"}), 400
    if sla_extension_minutes < 0:
        return jsonify({"error": "SLA extension minutes cannot be negative"}), 400

    conn = get_db_connection()
    ticket = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    if not ticket:
        conn.close()
        return jsonify({"error": "Ticket not found"}), 404

    if sla_extension_minutes == 0 and ticket["extension_request_status"] == "PENDING":
        conn.execute(
            """
            UPDATE tickets
            SET extension_request_status='REJECTED',
                extension_decision_time=?,
                extension_decision_note=?
            WHERE id=?
            """,
            (now_str(), "Extension workflow disabled by manager SLA extension setting.", ticket_id),
        )
    conn.execute("UPDATE tickets SET sla_extension_minutes=? WHERE id=?", (sla_extension_minutes, ticket_id))
    log_action(
        conn,
        ticket_id,
        session["username"],
        session["role"],
        "MANAGER_SET_SLA_EXTENSION",
        f"SLA Extension configured to {sla_extension_minutes} minutes.",
        next_step="SLA extension configured for request workflow",
    )
    conn.commit()
    conn.close()
    return jsonify({
        "ok": True,
        "ticket_id": int(ticket_id),
        "extension_minutes": sla_extension_minutes,
    })


@ticket_bp.route("/resolve_ticket", methods=["POST"])
def resolve_ticket():
    if "role" not in session or session["role"] not in {"support", "manager"}:
        return redirect("/")

    conn = get_db_connection()
    ticket = conn.execute(
        "SELECT * FROM tickets WHERE id=?",
        (request.form["ticket_id"],)
    ).fetchone()

    if not ticket:
        conn.close()
        return "Ticket not found", 404

    created = parse_dt(ticket["created_time"])
    elapsed = 0
    if created:
        elapsed = (datetime.now() - created).total_seconds() / 3600

    sla_status = "MET" if elapsed <= float(ticket["sla_hours"] or 0) else "BREACHED"

    if sla_status == "BREACHED":
        if ticket["rca_required"] and not ticket["rca_completed"]:
            conn.close()
            return "RCA must be completed before resolving a breached ticket", 400
        if not ticket["manager_signoff"]:
            conn.close()
            return "Manager sign-off is required before resolving a breached ticket", 400

    conn.execute(
        """
        UPDATE tickets
        SET status='RESOLVED', sla_status=?, resolved_time=?, next_action_text=?, next_action_due=?, priority_flag=0
        WHERE id=?
        """,
        (sla_status, now_str(), "Ticket resolved", now_str(), request.form["ticket_id"])
    )

    note = (request.form.get("resolution_note") or "").strip() or "Resolved by support"
    log_action(conn, ticket["id"], session["username"], session["role"], "RESOLVED", note)

    conn.commit()
    conn.close()
    return redirect("/dashboard")


@ticket_bp.route("/extension_decision", methods=["POST"])
def extension_decision():
    if session.get("role") != "user":
        return redirect("/")

    ticket_id = request.form.get("ticket_id")
    decision = (request.form.get("decision") or "").strip().upper()
    note = (request.form.get("note") or "").strip() or "No additional comments."
    if decision not in {"ACCEPT", "REJECT"}:
        return "Invalid decision", 400

    conn = get_db_connection()
    ticket = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    if not ticket:
        conn.close()
        return "Ticket not found", 404
    if ticket["raised_by"] != session.get("username"):
        conn.close()
        return "Not allowed", 403
    if ticket["extension_request_status"] != "PENDING":
        conn.close()
        return "No pending extension request for this ticket", 400

    current_time = now_str()
    mins = int(ticket["extension_requested_minutes"] or 0)
    if decision == "ACCEPT":
        new_sla = round(float(ticket["sla_hours"] or 0) + (mins / 60), 2)
        conn.execute(
            """
            UPDATE tickets
            SET sla_hours=?,
                extension_request_status='ACCEPTED',
                extension_decision_time=?,
                extension_decision_note=?,
                warning_mail_sent=0,
                breach_mail_sent=0,
                warning_started_time=NULL,
                warning_ack_time=NULL,
                warning_auto_escalated=0,
                breach_started_time=NULL,
                breach_action_time=NULL,
                breach_auto_escalated=0,
                priority_mail_sent=0,
                manager_signoff=0,
                next_action_text=?,
                next_action_due=?
            WHERE id=?
            """,
            (
                new_sla,
                current_time,
                note,
                f"User accepted SLA extension (+{mins} min)",
                current_time,
                ticket_id,
            ),
        )
        log_action(
            conn,
            ticket_id,
            session["username"],
            session["role"],
            "EXTENSION_ACCEPTED",
            f"Accepted +{mins} min extension. {note}",
        )
        manager_receiver = (ticket["extension_requested_by"] or get_manager_username(conn)).strip()
        send_chat_message(
            conn,
            session["username"],
            session["role"],
            manager_receiver,
            ticket_id,
            (
                f"Ticket {ticket_id}: I have approved the SLA extension request (+{mins} min). "
                f"Comment: {note}"
            ),
        )
        send_email_alert(
            f"User Accepted SLA Extension: Ticket {ticket_id}",
            (
                f"User {session['username']} approved the SLA extension request for ticket {ticket_id} "
                f"(+{mins} minutes)."
            ),
            recipients=get_role_emails(conn, "manager") or DEFAULT_ALERT_RECIPIENTS,
        )
    else:
        conn.execute(
            """
            UPDATE tickets
            SET extension_request_status='REJECTED',
                extension_decision_time=?,
                extension_decision_note=?,
                next_action_text=?,
                next_action_due=?
            WHERE id=?
            """,
            (
                current_time,
                note,
                "User rejected SLA extension request",
                current_time,
                ticket_id,
            ),
        )
        log_action(
            conn,
            ticket_id,
            session["username"],
            session["role"],
            "EXTENSION_REJECTED",
            f"Rejected extension request. {note}",
        )
        manager_receiver = (ticket["extension_requested_by"] or get_manager_username(conn)).strip()
        send_chat_message(
            conn,
            session["username"],
            session["role"],
            manager_receiver,
            ticket_id,
            f"Ticket {ticket_id}: I have rejected the SLA extension request. Comment: {note}",
        )
        send_email_alert(
            f"User Rejected SLA Extension: Ticket {ticket_id}",
            f"User {session['username']} rejected extension request on ticket {ticket_id}.",
            recipients=get_role_emails(conn, "manager") or DEFAULT_ALERT_RECIPIENTS,
        )

    conn.commit()
    conn.close()
    return redirect("/dashboard")
