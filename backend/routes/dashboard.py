from flask import Blueprint, render_template, redirect, session, jsonify

try:
    from ..core import (
        get_db_connection,
        process_sla_automation,
        get_chat_messages_for_user,
        get_manager_username,
        build_live_token,
        compute_open_ticket_state,
        get_action_logs_by_ticket,
        build_manager_metrics,
        get_role_usernames,
    )
except ImportError:
    from core import (
        get_db_connection,
        process_sla_automation,
        get_chat_messages_for_user,
        get_manager_username,
        build_live_token,
        compute_open_ticket_state,
        get_action_logs_by_ticket,
        build_manager_metrics,
        get_role_usernames,
    )


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
def dashboard():
    if "role" not in session:
        return redirect("/")

    conn = get_db_connection()
    process_sla_automation(conn)
    conn.commit()

    role = session["role"]

    if role == "user":
        tickets = conn.execute(
            "SELECT * FROM tickets WHERE raised_by=? ORDER BY id DESC",
            (session["username"],)
        ).fetchall()
        pending_extensions = conn.execute(
            """
            SELECT * FROM tickets
            WHERE raised_by=?
              AND status='OPEN'
              AND extension_request_status='PENDING'
            ORDER BY id DESC
            """,
            (session["username"],),
        ).fetchall()
        chat_messages = get_chat_messages_for_user(conn, session["username"], limit=80)
        manager_username = get_manager_username(conn)
        live_token = build_live_token(conn, session["username"], role)
        conn.close()
        return render_template(
            "user_dashboard.html",
            tickets=tickets,
            pending_extensions=pending_extensions,
            chat_messages=chat_messages,
            manager_username=manager_username,
            current_username=session["username"],
            live_token=live_token,
        )

    if role == "support":
        tickets = conn.execute(
            "SELECT * FROM tickets WHERE status='OPEN' ORDER BY id DESC"
        ).fetchall()

        ticket_dicts = []
        ids = []
        for t in tickets:
            td = dict(t)
            td.update(compute_open_ticket_state(t))
            ids.append(t["id"])
            ticket_dicts.append(td)

        priority_tickets = [
            t for t in ticket_dicts
            if (t.get("priority_flag") or 0) == 1 or t.get("extension_request_status") in {"PENDING", "ACCEPTED"}
        ]
        logs_by_ticket = get_action_logs_by_ticket(conn, ids)
        chat_messages = get_chat_messages_for_user(conn, session["username"], limit=80)
        live_token = build_live_token(conn, session["username"], role)
        conn.close()
        return render_template(
            "support_dashboard.html",
            tickets=ticket_dicts,
            action_logs=logs_by_ticket,
            priority_tickets=priority_tickets,
            chat_messages=chat_messages,
            current_username=session["username"],
            live_token=live_token,
        )

    tickets = conn.execute("SELECT * FROM tickets ORDER BY id DESC").fetchall()
    alerts = conn.execute(
        """
        SELECT
            alerts.ticket_id,
            alerts.alert_type,
            alerts.alert_time,
            tickets.title,
            tickets.status
        FROM alerts
        JOIN tickets ON alerts.ticket_id = tickets.id
        ORDER BY alerts.alert_time DESC
        """
    ).fetchall()

    ticket_list = []
    ids = []
    sla_met = sla_breached = open_tickets = 0
    closed_tickets = 0

    for t in tickets:
        td = dict(t)

        if t["status"] == "OPEN":
            open_tickets += 1
            state = compute_open_ticket_state(t)
            td.update(state)
            if state["phase"] == "BREACH":
                sla_breached += 1
        else:
            closed_tickets += 1
            td["time_left"] = "-"
            td["alert"] = "-"
            td["sla_status"] = t["sla_status"] or "IN PROGRESS"
            if td["sla_status"] == "MET":
                sla_met += 1
            elif td["sla_status"] == "BREACHED":
                sla_breached += 1

        ids.append(t["id"])
        ticket_list.append(td)

    total_tickets = open_tickets + closed_tickets
    metrics = build_manager_metrics(conn)
    logs_by_ticket = get_action_logs_by_ticket(conn, ids)
    priority_tickets = [
        t for t in ticket_list
        if t["status"] == "OPEN" and ((t.get("priority_flag") or 0) == 1 or t.get("extension_request_status") in {"PENDING", "ACCEPTED"})
    ]
    chat_messages = get_chat_messages_for_user(conn, session["username"], limit=120)
    user_usernames = get_role_usernames(conn, "user")
    live_token = build_live_token(conn, session["username"], role)

    conn.close()
    return render_template(
        "manager_dashboard.html",
        tickets=ticket_list,
        alerts=alerts,
        action_logs=logs_by_ticket,
        sla_met=sla_met,
        sla_breached=sla_breached,
        open_tickets=open_tickets,
        closed_tickets=closed_tickets,
        total_tickets=total_tickets,
        metrics=metrics,
        priority_tickets=priority_tickets,
        chat_messages=chat_messages,
        user_usernames=user_usernames,
        current_username=session["username"],
        live_token=live_token,
    )


@dashboard_bp.route("/sla_heartbeat", methods=["POST"])
def sla_heartbeat():
    if "role" not in session:
        return ("", 401)

    conn = get_db_connection()
    process_sla_automation(conn)
    conn.commit()
    conn.close()
    return ("", 204)


@dashboard_bp.route("/live_state", methods=["GET"])
def live_state():
    if "role" not in session:
        return jsonify({"error": "unauthorized"}), 401

    conn = get_db_connection()
    process_sla_automation(conn)
    conn.commit()
    token = build_live_token(conn, session.get("username"), session.get("role"))
    conn.close()
    return jsonify({"token": token})

