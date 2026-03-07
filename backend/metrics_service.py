try:
    from .constants import WARNING_ACK_MINUTES
    from .utils import parse_dt
except ImportError:
    from constants import WARNING_ACK_MINUTES
    from utils import parse_dt


def build_manager_metrics(conn):
    warnings = conn.execute("SELECT warning_started_time, warning_ack_time FROM tickets WHERE warning_started_time IS NOT NULL").fetchall()
    warnings_ack_15 = 0
    for w in warnings:
        start = parse_dt(w["warning_started_time"])
        ack = parse_dt(w["warning_ack_time"])
        if start and ack and (ack - start).total_seconds() <= WARNING_ACK_MINUTES * 60:
            warnings_ack_15 += 1

    breaches_no_recovery = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM tickets t
        WHERE t.status='OPEN'
          AND t.breach_started_time IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM action_log a
            WHERE a.ticket_id=t.id AND a.action_type='RECOVERY_PLAN'
          )
        """
    ).fetchone()["cnt"]

    rca_stats = conn.execute(
        "SELECT COUNT(*) AS total_required, SUM(CASE WHEN rca_completed=1 THEN 1 ELSE 0 END) AS done FROM tickets WHERE rca_required=1"
    ).fetchone()

    required = rca_stats["total_required"] or 0
    done = rca_stats["done"] or 0
    rca_completion_pct = round((done / required) * 100, 1) if required else 0

    escalations = conn.execute(
        """
        SELECT id, ticket_id, action_time
        FROM action_log
        WHERE action_type IN ('ESCALATE_TO_MANAGER', 'AUTO_ESCALATE_WARNING', 'AUTO_ESCALATE_BREACH')
        ORDER BY action_time ASC
        """
    ).fetchall()

    response_deltas = []
    for e in escalations:
        response = conn.execute(
            """
            SELECT action_time
            FROM action_log
            WHERE ticket_id=?
              AND actor_role='manager'
              AND action_time > ?
            ORDER BY action_time ASC
            LIMIT 1
            """,
            (e["ticket_id"], e["action_time"]),
        ).fetchone()
        if response:
            start = parse_dt(e["action_time"])
            end = parse_dt(response["action_time"])
            if start and end:
                response_deltas.append((end - start).total_seconds() / 60)

    avg_response = round(sum(response_deltas) / len(response_deltas), 1) if response_deltas else 0

    proactive_actions = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM action_log
        WHERE actor_role='manager'
          AND action_type IN (
            'MANAGER_REASSIGN_OWNER',
            'MANAGER_SET_PRIORITY',
            'MANAGER_SLA_EXTENSION',
            'MANAGER_PREVENTIVE_INTERVENTION',
            'MANAGER_CUSTOMER_ASSURANCE',
            'MANAGER_SIGNOFF',
            'RECOVERY_PLAN',
            'RCA_REQUIRED',
            'RCA_COMPLETED'
          )
        """
    ).fetchone()["cnt"]

    prevented_breaches = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM tickets
        WHERE status='RESOLVED'
          AND sla_status='MET'
          AND warning_started_time IS NOT NULL
          AND manager_intervened=1
        """
    ).fetchone()["cnt"]

    signoff_pending = conn.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM tickets
        WHERE status='OPEN'
          AND breach_started_time IS NOT NULL
          AND manager_signoff=0
        """
    ).fetchone()["cnt"]

    ext_stats = conn.execute(
        """
        SELECT
            SUM(CASE WHEN extension_request_status IN ('PENDING','ACCEPTED','AUTO_APPROVED','REJECTED') THEN extension_requested_minutes ELSE 0 END) AS requested_mins,
            SUM(CASE WHEN extension_request_status='ACCEPTED' THEN extension_requested_minutes ELSE 0 END) AS approved_mins,
            SUM(CASE WHEN extension_request_status='AUTO_APPROVED' THEN extension_requested_minutes ELSE 0 END) AS auto_approved_mins
        FROM tickets
        """
    ).fetchone()

    return {
        "warnings_ack_15": warnings_ack_15,
        "warnings_total": len(warnings),
        "breaches_no_recovery": breaches_no_recovery,
        "rca_completion_pct": rca_completion_pct,
        "avg_escalation_response": avg_response,
        "proactive_actions": proactive_actions,
        "prevented_breaches": prevented_breaches,
        "signoff_pending": signoff_pending,
        "extension_requested_mins": int(ext_stats["requested_mins"] or 0),
        "extension_approved_mins": int(ext_stats["approved_mins"] or 0),
        "extension_auto_approved_mins": int(ext_stats["auto_approved_mins"] or 0),
    }

