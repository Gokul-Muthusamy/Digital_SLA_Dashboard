from flask import Blueprint, redirect, session

try:
    from ..core import get_db_connection, reset_operational_tables
except ImportError:
    from core import get_db_connection, reset_operational_tables


admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/reset_database", methods=["POST"])
def reset_database():
    if session.get("role") != "manager":
        return redirect("/")

    conn = get_db_connection()
    reset_operational_tables(conn)
    conn.commit()
    conn.close()
    return redirect("/dashboard")

