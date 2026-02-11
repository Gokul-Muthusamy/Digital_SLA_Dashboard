from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "secretkey"

# ================= DATABASE =================
def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

# ================= EMAIL =================
def send_email_alert(subject, message):
    sender_email = "fmdetectionbit@gmail.com"
    sender_password = "iuboltipvixyvelw"
    receiver_email = "gokulnathanm.ec23@bitsathy.ac.in"

    msg = MIMEText(message)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("Mail error:", e)

# ================= ALERT LOG =================
def log_alert(ticket_id, alert_type):
    conn = get_db_connection()

    existing = conn.execute(
        "SELECT * FROM alerts WHERE ticket_id=? AND alert_type=?",
        (ticket_id, alert_type)
    ).fetchone()

    if not existing:
        alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO alerts (ticket_id, alert_type, alert_time) VALUES (?, ?, ?)",
            (ticket_id, alert_type, alert_time)
        )
        conn.commit()

        send_email_alert(
            f"SLA {alert_type} ALERT",
            f"""
SLA ALERT NOTIFICATION

Ticket ID: {ticket_id}
Alert Type: {alert_type}
Time: {alert_time}

Immediate attention required.
"""
        )
    conn.close()

# ================= LOGIN =================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (request.form["username"], request.form["password"])
        ).fetchone()
        conn.close()

        if user:
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect("/dashboard")
        return "Invalid login"

    return render_template("login.html")

# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "role" not in session:
        return redirect("/")

    conn = get_db_connection()
    role = session["role"]

    # -------- USER --------
    if role == "user":
        tickets = conn.execute(
            "SELECT * FROM tickets WHERE raised_by=?",
            (session["username"],)
        ).fetchall()
        conn.close()
        return render_template("user_dashboard.html", tickets=tickets)

    # -------- SUPPORT --------
    if role == "support":
        tickets = conn.execute(
            "SELECT * FROM tickets WHERE status='OPEN'"
        ).fetchall()
        conn.close()
        return render_template("support_dashboard.html", tickets=tickets)

    # -------- MANAGER --------
    tickets = conn.execute("SELECT * FROM tickets").fetchall()

    alerts = conn.execute("""
        SELECT 
            alerts.ticket_id,
            alerts.alert_type,
            alerts.alert_time,
            tickets.title,
            tickets.status
        FROM alerts
        JOIN tickets ON alerts.ticket_id = tickets.id
        ORDER BY alerts.alert_time DESC
    """).fetchall()

    conn.close()

    ticket_list = []
    sla_met = sla_breached = open_tickets = 0
    closed_tickets = 0
    now = datetime.now()

    for t in tickets:
        td = dict(t)

        if t["status"] == "OPEN":
            open_tickets += 1
            created = datetime.strptime(t["created_time"], "%Y-%m-%d %H:%M:%S")
            elapsed = (now - created).total_seconds() / 3600
            time_left = round(t["sla_hours"] - elapsed, 2)

            td["time_left"] = time_left
            td["sla_status"] = "IN PROGRESS"

            if time_left <= 0:
                sla_breached += 1
                log_alert(t["id"], "BREACH")
                td["alert"] = "BREACH"
            elif elapsed >= 0.75 * t["sla_hours"]:
                log_alert(t["id"], "WARNING")
                td["alert"] = "WARNING"
            else:
                td["alert"] = "NONE"
        else:
            closed_tickets += 1
            td["time_left"] = "-"
            td["alert"] = "-"
            td["sla_status"] = t["sla_status"]
            if t["sla_status"] == "MET":
                sla_met += 1
            elif t["sla_status"] == "BREACHED":
                sla_breached += 1

        ticket_list.append(td)

    total_tickets = open_tickets + closed_tickets

    return render_template(
        "manager_dashboard.html",
        tickets=ticket_list,
        alerts=alerts,
        sla_met=sla_met,
        sla_breached=sla_breached,
        open_tickets=open_tickets,
        closed_tickets=closed_tickets,
        total_tickets=total_tickets
    )

# ================= RAISE TICKET =================
@app.route("/raise_ticket", methods=["POST"])
def raise_ticket():
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO tickets
        (title, description, created_time, sla_hours, status, raised_by)
        VALUES (?, ?, ?, ?, 'OPEN', ?)
        """,
        (
            request.form["title"],
            request.form["description"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            float(request.form["sla_hours"]),
            session["username"]
        )
    )
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ================= RESOLVE =================
@app.route("/resolve_ticket", methods=["POST"])
def resolve_ticket():
    conn = get_db_connection()
    ticket = conn.execute(
        "SELECT * FROM tickets WHERE id=?",
        (request.form["ticket_id"],)
    ).fetchone()

    created = datetime.strptime(ticket["created_time"], "%Y-%m-%d %H:%M:%S")
    elapsed = (datetime.now() - created).total_seconds() / 3600
    sla_status = "MET" if elapsed <= ticket["sla_hours"] else "BREACHED"

    conn.execute(
        """
        UPDATE tickets
        SET status='RESOLVED', sla_status=?, resolved_time=?
        WHERE id=?
        """,
        (sla_status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), request.form["ticket_id"])
    )
    conn.commit()
    conn.close()
    return redirect("/dashboard")

# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
