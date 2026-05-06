from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import json
import logging
import os
import re
import time

import psycopg2
from psycopg2.extras import Json, RealDictCursor
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest


try:
    from prometheus_client import disable_created_metrics

    disable_created_metrics()
except ImportError:
    pass


HOST = "0.0.0.0"
PORT = 8080

PRODUCT_NAME = "MISIS_Digital Student Support"
SERVICE_NAME = "misis-digital-student-support-api"
SERVICE_VERSION = "1.1.0"
ENVIRONMENT = "lab"

LOG_FILE = "/var/log/app/app.log"

DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "supportdesk")
DB_USER = os.environ.get("DB_USER", "supportdesk_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

MAX_BODY_BYTES = 64 * 1024

STATUS_VALUES = ["open", "in_progress", "resolved"]
ACTIVE_STATUSES = ["open", "in_progress"]
PRIORITY_VALUES = ["low", "normal", "high", "critical"]

CATEGORY_LABELS = {
    "newlms-misis": "newlms.misis.ru",
    "lk-misis": "lk.misis.ru",
    "gornyak-misis": "gornyak.misis.ru",
    "folio-misis": "folio.misis.ru",
    "pulse-misis": "pulse.misis.ru",
    "vector-misis": "vector.misis.ru",
    "pay-misis": "pay.misis.ru",
}

RESOURCE_LABELS = {
    "login": "Login",
    "courses": "Courses",
    "schedule": "Schedule",
    "assignments": "Assignments",
    "tests": "Tests",
    "grades": "Grades",
    "files": "Files",
    "notifications": "Notifications",
    "video-lessons": "Video lessons",
    "gradebook": "Electronic gradebook",
    "attendance": "Attendance journal",
    "service-requests": "Service requests",
    "study-certificate": "Study certificate",
    "academic-leave": "Academic leave",
    "diploma-documents": "Diploma documents",
    "personal-data": "Personal data",
    "dorm-payment": "Dormitory payment",
    "cleaning-request": "Cleaning request",
    "plumber-request": "Plumber request",
    "electrician-request": "Electrician request",
    "commandant-appointment": "Commandant appointment",
    "room-info": "Room information",
    "documents": "Documents",
    "book-search": "Book search",
    "digital-books": "Digital books",
    "article-access": "Article access",
    "book-reservation": "Book reservation",
    "return-deadline": "Return deadline",
    "reader-profile": "Reader profile",
    "event-list": "Event list",
    "event-registration": "Event registration",
    "qr-ticket": "QR ticket",
    "event-reminders": "Event reminders",
    "attendance-check": "Attendance check",
    "certificates": "Certificates",
    "event-feedback": "Event feedback",
    "internships": "Internships",
    "vacancies": "Vacancies",
    "practice-documents": "Practice documents",
    "company-events": "Company events",
    "resume-upload": "Resume upload",
    "application-status": "Application status",
    "career-consultation": "Career consultation",
    "tuition-payment": "Tuition payment",
    "invoice": "Invoice",
    "payment-status": "Payment status",
    "refund": "Refund",
    "receipt": "Receipt",
}

CATEGORY_TO_RESOURCES = {
    "newlms-misis": [
        "login",
        "courses",
        "schedule",
        "assignments",
        "tests",
        "grades",
        "files",
        "notifications",
        "video-lessons",
    ],
    "lk-misis": [
        "login",
        "gradebook",
        "attendance",
        "service-requests",
        "study-certificate",
        "academic-leave",
        "diploma-documents",
        "personal-data",
        "notifications",
    ],
    "gornyak-misis": [
        "login",
        "dorm-payment",
        "cleaning-request",
        "plumber-request",
        "electrician-request",
        "commandant-appointment",
        "room-info",
        "documents",
    ],
    "folio-misis": [
        "login",
        "book-search",
        "digital-books",
        "article-access",
        "book-reservation",
        "return-deadline",
        "reader-profile",
    ],
    "pulse-misis": [
        "event-list",
        "event-registration",
        "qr-ticket",
        "event-reminders",
        "attendance-check",
        "certificates",
        "event-feedback",
    ],
    "vector-misis": [
        "internships",
        "vacancies",
        "practice-documents",
        "company-events",
        "resume-upload",
        "application-status",
        "career-consultation",
    ],
    "pay-misis": [
        "tuition-payment",
        "dorm-payment",
        "invoice",
        "payment-status",
        "refund",
        "receipt",
    ],
}

TICKET_COLUMNS = """
    id,
    schema_version,
    title,
    category,
    category_label,
    resource,
    resource_label,
    description,
    priority,
    status,
    source,
    created_at,
    updated_at,
    resolved_at
"""

TICKET_SELECT_SQL = f"""
    SELECT
        {TICKET_COLUMNS}
    FROM tickets
"""

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s service=misis-digital-student-support-api %(message)s",
)


HTTP_METRICS_REGISTRY = CollectorRegistry()

HTTP_REQUESTS_TOTAL = Counter(
    "supportdesk_http_requests_total",
    "Total HTTP requests handled by MISIS Digital Student Support API",
    ["method", "route", "status_code"],
    registry=HTTP_METRICS_REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "supportdesk_http_request_duration_seconds",
    "HTTP request duration in seconds for MISIS Digital Student Support API",
    ["method", "route", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=HTTP_METRICS_REGISTRY,
)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def as_text(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def normalize_slug(value, default=""):
    text = as_text(value, default).lower()
    text = text.replace("_", "-").replace(" ", "-")
    text = re.sub(r"[^a-z0-9-]", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or default


def normalize_status(value, default=""):
    text = as_text(value, default).lower()
    text = text.replace("-", "_").replace(" ", "_")
    text = re.sub(r"[^a-z0-9_]", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or default


def clean_log_value(value):
    if value is None or value == "":
        return "-"

    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\n", "_")
        .replace("\r", "_")
        .replace("\t", "_")
        .replace(" ", "_")
    )


def prometheus_label_value(value):
    return clean_log_value(value).replace("\\", "\\\\").replace('"', '\\"')


def prometheus_labels(**labels):
    return ",".join(
        f'{key}="{prometheus_label_value(value)}"'
        for key, value in labels.items()
    )


def category_label(category):
    return CATEGORY_LABELS.get(category, category)


def resource_label(resource):
    return RESOURCE_LABELS.get(resource, resource.replace("-", " ").title())


def build_title(category, resource):
    return f"{resource_label(resource)} issue on {category_label(category)}"


def validate_category_resource(category_value, resource_value):
    category = normalize_slug(category_value)
    resource = normalize_slug(resource_value)

    if not category:
        return None, None, "missing_category"

    if not resource:
        return None, None, "missing_resource"

    if category not in CATEGORY_TO_RESOURCES:
        return None, None, f"invalid_category:{category}"

    if resource not in CATEGORY_TO_RESOURCES[category]:
        return None, None, f"invalid_resource_for_category:{category}:{resource}"

    return category, resource, None


def validate_ticket(ticket):
    if not isinstance(ticket, dict):
        raise ValueError("ticket_must_be_object")

    category, resource, error = validate_category_resource(
        ticket.get("category"),
        ticket.get("resource"),
    )

    if error:
        raise ValueError(error)

    status = normalize_status(ticket.get("status"), "open")
    if status not in STATUS_VALUES:
        raise ValueError(f"invalid_status:{status}")

    priority = normalize_slug(ticket.get("priority"), "normal")
    if priority not in PRIORITY_VALUES:
        raise ValueError(f"invalid_priority:{priority}")

    normalized = dict(ticket)
    normalized["schema_version"] = 2
    normalized["category"] = category
    normalized["category_label"] = category_label(category)
    normalized["resource"] = resource
    normalized["resource_label"] = resource_label(resource)
    normalized["status"] = status
    normalized["priority"] = priority
    normalized["source"] = normalize_slug(ticket.get("source"), "unknown")
    normalized["title"] = as_text(ticket.get("title")) or build_title(category, resource)
    normalized["description"] = as_text(ticket.get("description"))

    if not normalized.get("created_at"):
        normalized["created_at"] = now_iso()

    if not normalized.get("updated_at"):
        normalized["updated_at"] = normalized["created_at"]

    if status == "resolved":
        if not normalized.get("resolved_at"):
            normalized["resolved_at"] = normalized["updated_at"]
    else:
        normalized["resolved_at"] = None

    return normalized


def service_model():
    return {
        "product": PRODUCT_NAME,
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "categories": [
            {
                "value": category,
                "label": category_label(category),
                "resources": [
                    {
                        "value": resource,
                        "label": resource_label(resource),
                    }
                    for resource in resources
                ],
            }
            for category, resources in CATEGORY_TO_RESOURCES.items()
        ],
        "priorities": PRIORITY_VALUES,
        "statuses": STATUS_VALUES,
    }


def db_connect():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def row_to_ticket(row):
    ticket = dict(row)

    for field in ("created_at", "updated_at", "resolved_at"):
        value = ticket.get(field)
        if value is not None and hasattr(value, "isoformat"):
            ticket[field] = value.isoformat()

    return ticket


def db_ticket_counts():
    with db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    count(*) AS total,
                    count(*) FILTER (WHERE status = 'open') AS open_count,
                    count(*) FILTER (WHERE status = 'in_progress') AS in_progress_count,
                    count(*) FILTER (WHERE status = 'resolved') AS resolved_count
                FROM tickets;
                """
            )
            row = cur.fetchone()

    open_count = int(row["open_count"])
    in_progress_count = int(row["in_progress_count"])
    resolved_count = int(row["resolved_count"])

    return {
        "total": int(row["total"]),
        "active": open_count + in_progress_count,
        "open": open_count,
        "in_progress": in_progress_count,
        "resolved": resolved_count,
    }


def db_list_tickets(selected_filter):
    if selected_filter == "active":
        where_clause = "WHERE status IN (%s, %s)"
        params = ACTIVE_STATUSES
    elif selected_filter == "all":
        where_clause = ""
        params = []
    elif selected_filter in STATUS_VALUES:
        where_clause = "WHERE status = %s"
        params = [selected_filter]
    else:
        raise ValueError(f"invalid_status_filter:{selected_filter}")

    query = f"{TICKET_SELECT_SQL} {where_clause} ORDER BY id;"

    with db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            return [row_to_ticket(row) for row in cur.fetchall()]


def db_get_ticket(ticket_id):
    with db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"{TICKET_SELECT_SQL} WHERE id = %s;",
                (ticket_id,),
            )
            row = cur.fetchone()

    if row is None:
        return None

    return row_to_ticket(row)


def make_list_payload_from_db(selected_tickets, selected_filter):
    counts = db_ticket_counts()

    return {
        "tickets": selected_tickets,
        "count": len(selected_tickets),
        "filter": selected_filter,
        "total": counts["total"],
        "active_count": counts["active"],
        "open_count": counts["open"],
        "in_progress_count": counts["in_progress"],
        "resolved_count": counts["resolved"],
    }


def build_product_metrics_body_from_db():
    counts = db_ticket_counts()

    with db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    status,
                    category,
                    resource,
                    priority,
                    count(*) AS count
                FROM tickets
                GROUP BY status, category, resource, priority
                ORDER BY status, category, resource, priority;
                """
            )
            current_rows = cur.fetchall()

            cur.execute(
                """
                SELECT
                    category,
                    resource,
                    priority,
                    GREATEST(
                        0,
                        FLOOR(EXTRACT(EPOCH FROM (now() - MIN(created_at))))::bigint
                    ) AS age_seconds
                FROM tickets
                WHERE status IN ('open', 'in_progress')
                GROUP BY category, resource, priority
                ORDER BY category, resource, priority;
                """
            )
            oldest_active_rows = cur.fetchall()

    lines = [
        "# HELP supportdesk_tickets_total Total number of support desk tickets",
        "# TYPE supportdesk_tickets_total gauge",
        f"supportdesk_tickets_total {counts['total']}",
        "# HELP supportdesk_tickets_open Number of open support desk tickets",
        "# TYPE supportdesk_tickets_open gauge",
        f"supportdesk_tickets_open {counts['open']}",
        "# HELP supportdesk_tickets_in_progress Number of in-progress support desk tickets",
        "# TYPE supportdesk_tickets_in_progress gauge",
        f"supportdesk_tickets_in_progress {counts['in_progress']}",
        "# HELP supportdesk_tickets_resolved Number of resolved support desk tickets",
        "# TYPE supportdesk_tickets_resolved gauge",
        f"supportdesk_tickets_resolved {counts['resolved']}",
        "# HELP supportdesk_tickets_active Number of active support desk tickets",
        "# TYPE supportdesk_tickets_active gauge",
        f"supportdesk_tickets_active {counts['active']}",
        "# HELP supportdesk_tickets_current Current support desk tickets by status, category, resource and priority",
        "# TYPE supportdesk_tickets_current gauge",
    ]

    for row in current_rows:
        labels = prometheus_labels(
            status=row["status"],
            category=row["category"],
            resource=row["resource"],
            priority=row["priority"],
        )
        lines.append(f"supportdesk_tickets_current{{{labels}}} {int(row['count'])}")

    lines.extend(
        [
            "# HELP supportdesk_active_ticket_age_seconds_max Oldest active support desk ticket age in seconds by category, resource and priority",
            "# TYPE supportdesk_active_ticket_age_seconds_max gauge",
        ]
    )

    for row in oldest_active_rows:
        labels = prometheus_labels(
            category=row["category"],
            resource=row["resource"],
            priority=row["priority"],
        )
        lines.append(
            f"supportdesk_active_ticket_age_seconds_max{{{labels}}} {int(row['age_seconds'])}"
        )

    lines.append("")
    return "\n".join(lines).encode("utf-8")


def create_ticket_in_db(title, category, resource, description, priority, source):
    created_at = now_iso()

    ticket = validate_ticket(
        {
            "schema_version": 2,
            "title": title,
            "category": category,
            "category_label": category_label(category),
            "resource": resource,
            "resource_label": resource_label(resource),
            "description": description,
            "priority": priority,
            "status": "open",
            "source": source,
            "created_at": created_at,
            "updated_at": created_at,
            "resolved_at": None,
        }
    )

    with db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                INSERT INTO tickets (
                    schema_version,
                    title,
                    category,
                    category_label,
                    resource,
                    resource_label,
                    description,
                    priority,
                    status,
                    source,
                    created_at,
                    updated_at,
                    resolved_at
                )
                VALUES (
                    %(schema_version)s,
                    %(title)s,
                    %(category)s,
                    %(category_label)s,
                    %(resource)s,
                    %(resource_label)s,
                    %(description)s,
                    %(priority)s,
                    %(status)s,
                    %(source)s,
                    %(created_at)s,
                    %(updated_at)s,
                    %(resolved_at)s
                )
                RETURNING {TICKET_COLUMNS};
                """,
                ticket,
            )
            created_ticket = row_to_ticket(cur.fetchone())

            cur.execute(
                """
                INSERT INTO ticket_events (
                    ticket_id,
                    event,
                    old_status,
                    new_status,
                    source,
                    metadata_json
                )
                VALUES (
                    %(ticket_id)s,
                    'ticket_created',
                    NULL,
                    %(new_status)s,
                    %(source)s,
                    %(metadata_json)s
                );
                """,
                {
                    "ticket_id": created_ticket["id"],
                    "new_status": created_ticket["status"],
                    "source": source,
                    "metadata_json": Json(
                        {
                            "storage_backend": "postgresql",
                            "write_path": "sql_native",
                        }
                    ),
                },
            )

    return created_ticket


def update_ticket_status_in_db(ticket_id, new_status, source):
    changed_at = now_iso()

    with db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"{TICKET_SELECT_SQL} WHERE id = %s FOR UPDATE;",
                (ticket_id,),
            )
            old_row = cur.fetchone()

            if old_row is None:
                return None, None, False

            old_ticket = row_to_ticket(old_row)
            old_status = old_ticket["status"]

            if old_status == new_status:
                return old_ticket, old_status, False

            resolved_at = changed_at if new_status == "resolved" else None

            cur.execute(
                f"""
                UPDATE tickets
                SET
                    schema_version = 2,
                    status = %(new_status)s,
                    updated_at = %(updated_at)s,
                    resolved_at = %(resolved_at)s
                WHERE id = %(ticket_id)s
                RETURNING {TICKET_COLUMNS};
                """,
                {
                    "ticket_id": ticket_id,
                    "new_status": new_status,
                    "updated_at": changed_at,
                    "resolved_at": resolved_at,
                },
            )
            updated_ticket = row_to_ticket(cur.fetchone())

            cur.execute(
                """
                INSERT INTO ticket_events (
                    ticket_id,
                    event,
                    old_status,
                    new_status,
                    source,
                    metadata_json
                )
                VALUES (
                    %(ticket_id)s,
                    'ticket_status_changed',
                    %(old_status)s,
                    %(new_status)s,
                    %(source)s,
                    %(metadata_json)s
                );
                """,
                {
                    "ticket_id": ticket_id,
                    "old_status": old_status,
                    "new_status": new_status,
                    "source": source,
                    "metadata_json": Json(
                        {
                            "storage_backend": "postgresql",
                            "write_path": "sql_native",
                        }
                    ),
                },
            )

    return updated_ticket, old_status, True


def normalize_path(path):
    normalized = path.rstrip("/")
    return normalized or "/"


def strip_version_prefix(path):
    if path == "/v1":
        return "/"

    if path.startswith("/v1/"):
        return path[3:]

    return path


def api_version(path):
    if path == "/v1" or path.startswith("/v1/"):
        return "v1"

    return "legacy"


def metrics_route(raw_path):
    try:
        path = normalize_path(urlparse(raw_path).path)
    except Exception:
        return "unmatched"

    exact_routes = {
        "/health",
        "/v1/health",
        "/support-model",
        "/v1/support-model",
        "/model",
        "/v1/model",
        "/tickets",
        "/v1/tickets",
        "/tickets/all",
        "/v1/tickets/all",
        "/metrics",
    }

    if path in exact_routes:
        return path

    if re.fullmatch(r"/tickets/\d+", path):
        return "/tickets/{id}"

    if re.fullmatch(r"/v1/tickets/\d+", path):
        return "/v1/tickets/{id}"

    if re.fullmatch(r"/tickets/\d+/status", path):
        return "/tickets/{id}/status"

    if re.fullmatch(r"/v1/tickets/\d+/status", path):
        return "/v1/tickets/{id}/status"

    return "unmatched"


class SupportDeskHandler(BaseHTTPRequestHandler):
    def handle_one_request(self):
        self._request_started_at = time.monotonic()
        self._response_status_code = 0

        try:
            super().handle_one_request()
        finally:
            self.record_request_metrics()

    def record_request_metrics(self):
        raw_path = getattr(self, "path", "")
        method = getattr(self, "command", "UNKNOWN")

        if not raw_path:
            return

        route = metrics_route(raw_path)

        if route == "/metrics":
            return

        status_code = str(getattr(self, "_response_status_code", 0) or 0)
        duration = time.monotonic() - self._request_started_at

        try:
            HTTP_REQUESTS_TOTAL.labels(
                method=method,
                route=route,
                status_code=status_code,
            ).inc()

            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=method,
                route=route,
                status_code=status_code,
            ).observe(duration)
        except Exception:
            pass

    def send_response(self, code, message=None):
        self._response_status_code = int(code)
        super().send_response(code, message)

    def send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_plain(self, status_code, body, content_type):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_api_error(self, status_code, error, **fields):
        payload = {"error": error}
        payload.update(fields)
        self.send_json(status_code, payload)

    def read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            raise ValueError("invalid_content_length")

        if length == 0:
            return {}

        if length > MAX_BODY_BYTES:
            raise ValueError("request_body_too_large")

        raw_body = self.rfile.read(length)
        data = json.loads(raw_body.decode("utf-8"))

        if not isinstance(data, dict):
            raise ValueError("json_body_must_be_object")

        return data

    def log_event(self, level, event, status_code, **fields):
        client_ip = self.client_address[0]
        x_forwarded_for = self.headers.get("X-Forwarded-For", "-")
        x_forwarded_proto = self.headers.get("X-Forwarded-Proto", "-")

        parts = [
            f"event={event}",
            f"method={self.command}",
            f"path={clean_log_value(self.path)}",
            f"status={status_code}",
            f"client_ip={clean_log_value(client_ip)}",
            f"x_forwarded_for={clean_log_value(x_forwarded_for)}",
            f"x_forwarded_proto={clean_log_value(x_forwarded_proto)}",
        ]

        for key, value in fields.items():
            parts.append(f"{key}={clean_log_value(value)}")

        logging.log(level, " ".join(parts))

    def handle_internal_error(self, exc):
        self.send_api_error(500, "internal_server_error")
        self.log_event(logging.ERROR, "internal_error", 500, error=type(exc).__name__)

    def do_GET(self):
        parsed = urlparse(self.path)
        raw_path = normalize_path(parsed.path)
        path = strip_version_prefix(raw_path)
        version = api_version(raw_path)
        query = parse_qs(parsed.query)

        try:
            if path == "/health":
                self.handle_health(version)
                return

            if path in ["/support-model", "/model"]:
                self.handle_support_model(version)
                return

            if path == "/tickets":
                self.handle_ticket_list(query, version)
                return

            if path == "/tickets/all":
                self.handle_ticket_list_all(version)
                return

            ticket_id = self.match_ticket_detail(path)
            if ticket_id is not None:
                self.handle_ticket_detail(ticket_id, version)
                return

            if path == "/metrics":
                self.handle_metrics(version)
                return

            self.send_api_error(404, "not_found")
            self.log_event(logging.WARNING, "endpoint_not_found", 404, api_version=version)

        except Exception as exc:
            self.handle_internal_error(exc)

    def handle_health(self, version):
        payload = {
            "status": "ok",
            "product": PRODUCT_NAME,
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
            "environment": ENVIRONMENT,
            "api_version": version,
            "supported_api_versions": ["legacy", "v1"],
            "time": now_iso(),
        }

        self.send_json(200, payload)
        self.log_event(logging.INFO, "health_check", 200, api_version=version)

    def handle_support_model(self, version):
        self.send_json(200, service_model())
        self.log_event(logging.INFO, "support_model_requested", 200, api_version=version)

    def handle_ticket_list(self, query, version):
        status_filter = normalize_status(query.get("status", ["active"])[0], "active")

        if status_filter == "active":
            selected_filter = "active"
        elif status_filter == "all":
            selected_filter = "all"
        elif status_filter in STATUS_VALUES:
            selected_filter = status_filter
        else:
            self.send_api_error(
                400,
                "invalid_status_filter",
                allowed=["active", "all"] + STATUS_VALUES,
            )
            self.log_event(
                logging.WARNING,
                "ticket_validation_failed",
                400,
                reason="invalid_status_filter",
            )
            return

        selected_tickets = db_list_tickets(selected_filter)
        payload = make_list_payload_from_db(selected_tickets, selected_filter)

        self.send_json(200, payload)
        self.log_event(
            logging.INFO,
            "ticket_list_requested",
            200,
            api_version=version,
            filter=selected_filter,
            count=len(selected_tickets),
        )

    def handle_ticket_list_all(self, version):
        selected_tickets = db_list_tickets("all")
        payload = make_list_payload_from_db(selected_tickets, "all")

        self.send_json(200, payload)
        self.log_event(
            logging.INFO,
            "ticket_list_requested",
            200,
            api_version=version,
            filter="all",
            count=len(selected_tickets),
        )

    def match_ticket_detail(self, path):
        match = re.fullmatch(r"/tickets/(\d+)", path)
        if not match:
            return None

        return int(match.group(1))

    def handle_ticket_detail(self, ticket_id, version):
        ticket = db_get_ticket(ticket_id)

        if ticket is None:
            self.send_api_error(404, "ticket_not_found")
            self.log_event(
                logging.WARNING,
                "ticket_not_found",
                404,
                ticket_id=ticket_id,
            )
            return

        self.send_json(200, ticket)
        self.log_event(
            logging.INFO,
            "ticket_detail_requested",
            200,
            api_version=version,
            ticket_id=ticket_id,
            category=ticket.get("category"),
            resource=ticket.get("resource"),
        )

    def handle_metrics(self, version):
        product_metrics_body = build_product_metrics_body_from_db()
        http_metrics_body = generate_latest(HTTP_METRICS_REGISTRY)
        body = product_metrics_body + http_metrics_body

        self.send_plain(
            200,
            body,
            "text/plain; version=0.0.4; charset=utf-8",
        )
        self.log_event(logging.INFO, "metrics_requested", 200, api_version=version)

    def do_POST(self):
        parsed = urlparse(self.path)
        raw_path = normalize_path(parsed.path)
        path = strip_version_prefix(raw_path)
        version = api_version(raw_path)

        try:
            if path != "/tickets":
                self.send_api_error(404, "not_found")
                self.log_event(logging.WARNING, "endpoint_not_found", 404, api_version=version)
                return

            self.handle_ticket_create(version)

        except Exception as exc:
            self.handle_internal_error(exc)

    def handle_ticket_create(self, version):
        data = self.safe_read_json_body()
        if data is None:
            return

        category, resource, error = validate_category_resource(
            data.get("category"),
            data.get("resource"),
        )

        if error:
            self.send_api_error(400, error)
            self.log_event(logging.WARNING, "ticket_validation_failed", 400, reason=error)
            return

        priority = normalize_slug(data.get("priority", "normal"), "normal")
        if priority not in PRIORITY_VALUES:
            self.send_api_error(400, "invalid_priority", allowed=PRIORITY_VALUES)
            self.log_event(logging.WARNING, "ticket_validation_failed", 400, reason="invalid_priority")
            return

        title = as_text(data.get("title")) or build_title(category, resource)
        description = as_text(data.get("description"))
        source = normalize_slug(data.get("source", "web"), "web")

        ticket = create_ticket_in_db(
            title=title,
            category=category,
            resource=resource,
            description=description,
            priority=priority,
            source=source,
        )

        self.send_json(201, ticket)
        self.log_event(
            logging.INFO,
            "ticket_created",
            201,
            api_version=version,
            ticket_id=ticket["id"],
            category=category,
            resource=resource,
            priority=priority,
            source=source,
        )

    def do_PATCH(self):
        parsed = urlparse(self.path)
        raw_path = normalize_path(parsed.path)
        path = strip_version_prefix(raw_path)
        version = api_version(raw_path)

        try:
            match = re.fullmatch(r"/tickets/(\d+)/status", path)
            if not match:
                self.send_api_error(404, "not_found")
                self.log_event(logging.WARNING, "endpoint_not_found", 404, api_version=version)
                return

            self.handle_ticket_status_update(int(match.group(1)), version)

        except Exception as exc:
            self.handle_internal_error(exc)

    def handle_ticket_status_update(self, ticket_id, version):
        data = self.safe_read_json_body(ticket_id=ticket_id)
        if data is None:
            return

        new_status = normalize_status(data.get("status"), "")
        source = normalize_slug(data.get("source", "web"), "web")

        if new_status not in STATUS_VALUES:
            self.send_api_error(400, "invalid_status", allowed=STATUS_VALUES)
            self.log_event(
                logging.WARNING,
                "ticket_validation_failed",
                400,
                reason="invalid_status",
                ticket_id=ticket_id,
                source=source,
            )
            return

        ticket, old_status, changed = update_ticket_status_in_db(
            ticket_id=ticket_id,
            new_status=new_status,
            source=source,
        )

        if ticket is None:
            self.send_api_error(404, "ticket_not_found")
            self.log_event(
                logging.WARNING,
                "ticket_not_found",
                404,
                ticket_id=ticket_id,
                source=source,
            )
            return

        if not changed:
            self.send_json(200, ticket)
            self.log_event(
                logging.INFO,
                "ticket_status_unchanged",
                200,
                api_version=version,
                ticket_id=ticket_id,
                old_status=old_status,
                new_status=new_status,
                category=ticket.get("category"),
                resource=ticket.get("resource"),
                source=source,
            )
            return

        self.send_json(200, ticket)
        self.log_event(
            logging.INFO,
            "ticket_status_changed",
            200,
            api_version=version,
            ticket_id=ticket_id,
            old_status=old_status,
            new_status=new_status,
            category=ticket.get("category"),
            resource=ticket.get("resource"),
            source=source,
            resolved_at=ticket.get("resolved_at"),
        )

    def safe_read_json_body(self, ticket_id=None):
        try:
            return self.read_json_body()
        except json.JSONDecodeError:
            self.send_api_error(400, "invalid_json")
            self.log_event(
                logging.WARNING,
                "ticket_validation_failed",
                400,
                reason="invalid_json",
                ticket_id=ticket_id,
            )
            return None
        except ValueError as exc:
            self.send_api_error(400, str(exc))
            self.log_event(
                logging.WARNING,
                "ticket_validation_failed",
                400,
                reason=str(exc),
                ticket_id=ticket_id,
            )
            return None

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), SupportDeskHandler)
    server.serve_forever()
