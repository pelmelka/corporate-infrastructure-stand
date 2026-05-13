import html
import logging
import os
import re
import time
from datetime import datetime, timezone

import httpx
from prometheus_client import Counter, Gauge, Histogram, start_http_server, disable_created_metrics
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update

disable_created_metrics()
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest


SERVICE_NAME = "misis-digital-support-bot"
SERVICE_VERSION = "1.0.0"
LOG_FILE = "/var/log/bot/support-bot.log"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "").strip()

SUPPORTDESK_API_URL = os.environ.get(
    "SUPPORTDESK_API_URL",
    "http://supportdesk-api:8080",
).rstrip("/")

TELEGRAM_PROXY_URL = (
    os.environ.get("HTTPS_PROXY")
    or os.environ.get("HTTP_PROXY")
    or ""
).strip()

ALLOWED_TELEGRAM_USER_IDS_RAW = os.environ.get(
    "ALLOWED_TELEGRAM_USER_IDS",
    "",
).strip()

METRICS_PORT = int(os.environ.get("METRICS_PORT", "8090"))

SOURCE_NAME = "telegram"

MAX_DESCRIPTION_LEN = 1500
TICKETS_PER_PAGE = 8


os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s service=misis-digital-support-bot %(message)s",
)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)


SUPPORT_BOT_INFO = Gauge(
    "support_bot_info",
    "Static information about MISIS Digital Support Telegram bot",
    ["service", "version"],
)

SUPPORT_BOT_START_TIME_SECONDS = Gauge(
    "support_bot_start_time_seconds",
    "Unix timestamp when MISIS Digital Support Telegram bot started",
)

SUPPORT_BOT_ACTIONS_TOTAL = Counter(
    "support_bot_actions_total",
    "Total Telegram bot user actions by normalized action name",
    ["action"],
)

SUPPORT_BOT_API_REQUESTS_TOTAL = Counter(
    "support_bot_api_requests_total",
    "Total backend API requests made by Telegram bot",
    ["method", "endpoint", "status_code"],
)

SUPPORT_BOT_API_REQUEST_DURATION_SECONDS = Histogram(
    "support_bot_api_request_duration_seconds",
    "Backend API request duration in seconds for Telegram bot",
    ["method", "endpoint", "status_code"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

SUPPORT_BOT_ERRORS_TOTAL = Counter(
    "support_bot_errors_total",
    "Total Telegram bot errors by type",
    ["type"],
)


class SecretRedactingFilter(logging.Filter):
    def filter(self, record):
        if TELEGRAM_BOT_TOKEN:
            if isinstance(record.msg, str):
                record.msg = record.msg.replace(TELEGRAM_BOT_TOKEN, "[redacted-token]")

            if record.args:
                record.args = tuple(
                    str(arg).replace(TELEGRAM_BOT_TOKEN, "[redacted-token]")
                    for arg in record.args
                )

        return True


for handler in logging.getLogger().handlers:
    handler.addFilter(SecretRedactingFilter())


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def mask_secret(value):
    text = "" if value is None else str(value)

    if TELEGRAM_BOT_TOKEN:
        text = text.replace(TELEGRAM_BOT_TOKEN, "[redacted-token]")

    return text


def clean_log_value(value):
    text = mask_secret(value)

    if text == "":
        return "-"

    return (
        text.replace("\\", "\\\\")
        .replace("\n", "_")
        .replace("\r", "_")
        .replace("\t", "_")
        .replace(" ", "_")
    )


def log_event(event, **fields):
    parts = [f"event={clean_log_value(event)}"]

    for key, value in fields.items():
        parts.append(f"{key}={clean_log_value(value)}")

    logging.info(" ".join(parts))


def h(value):
    return html.escape("" if value is None else str(value), quote=False)


def code(value):
    return f"<code>{h(value)}</code>"


def truncate(value, limit=160):
    text = "" if value is None else str(value)

    if len(text) <= limit:
        return text

    return text[: limit - 1] + "…"


def allowed_user_ids():
    if not ALLOWED_TELEGRAM_USER_IDS_RAW:
        return set()

    result = set()

    for item in ALLOWED_TELEGRAM_USER_IDS_RAW.split(","):
        item = item.strip()
        if item.isdigit():
            result.add(int(item))

    return result


def user_meta(update: Update):
    user = update.effective_user

    if not user:
        return {
            "telegram_user_id": "-",
            "telegram_username": "-",
            "telegram_full_name": "-",
        }

    return {
        "telegram_user_id": user.id,
        "telegram_username": user.username or "-",
        "telegram_full_name": user.full_name or "-",
    }


def is_allowed(update: Update):
    allowed = allowed_user_ids()

    if not allowed:
        return True

    user = update.effective_user
    return bool(user and user.id in allowed)


def normalize_bot_action(action):
    if not action:
        return "unknown"

    if action.startswith("category:"):
        return "category_selected"

    if action.startswith("resource:"):
        return "resource_selected"

    if action.startswith("priority:"):
        return "priority_selected"

    if action.startswith("resolve_page:"):
        return "resolve_page"

    if action.startswith("active_page:"):
        return "active_page"

    if action.startswith("resolve:"):
        return "resolve_ticket"

    return action


def normalize_api_endpoint(path):
    if re.fullmatch(r"/v1/tickets/\d+/status", path):
        return "/v1/tickets/{id}/status"

    if re.fullmatch(r"/v1/tickets/\d+", path):
        return "/v1/tickets/{id}"

    return path


def record_action(action):
    SUPPORT_BOT_ACTIONS_TOTAL.labels(action=normalize_bot_action(action)).inc()


def record_error(error_type):
    SUPPORT_BOT_ERRORS_TOTAL.labels(type=error_type).inc()


async def deny_if_needed(update: Update):
    if is_allowed(update):
        return False

    meta = user_meta(update)

    log_event(
        "access_denied",
        **meta,
    )

    text = (
        "⛔ <b>Access denied</b>\n\n"
        "Ваш Telegram user_id:\n"
        f"{code(meta['telegram_user_id'])}\n\n"
        "Попросите администратора добавить этот id в "
        f"{code('ALLOWED_TELEGRAM_USER_IDS')}."
    )

    if update.callback_query:
        await update.callback_query.answer("Access denied", show_alert=True)
        await update.callback_query.edit_message_text(
            text,
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.HTML,
        )

    return True


def main_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Создать заявку", callback_data="new_ticket")],
            [InlineKeyboardButton("📋 Активные заявки", callback_data="active_tickets")],
            [InlineKeyboardButton("✅ Закрыть заявку", callback_data="resolve_menu")],
            [InlineKeyboardButton("🔎 Проверить backend", callback_data="check_backend")],
            [InlineKeyboardButton("ℹ️ Помощь", callback_data="help")],
        ]
    )


def back_to_menu_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ В главное меню", callback_data="main_menu")]]
    )


def cancel_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Отмена", callback_data="cancel")]]
    )


def after_create_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("➕ Создать еще заявку", callback_data="new_ticket")],
            [InlineKeyboardButton("📋 Активные заявки", callback_data="active_tickets")],
            [InlineKeyboardButton("⬅️ В главное меню", callback_data="main_menu")],
        ]
    )


def after_resolve_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📋 Активные заявки", callback_data="active_tickets")],
            [InlineKeyboardButton("✅ Закрыть другую заявку", callback_data="resolve_menu")],
            [InlineKeyboardButton("⬅️ В главное меню", callback_data="main_menu")],
        ]
    )


async def send_or_edit(update: Update, text, reply_markup=None):
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    elif update.message:
        await update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )


async def api_request(method, path, json_body=None):
    endpoint = normalize_api_endpoint(path)
    start_time = time.perf_counter()
    status_code = "error"

    try:
        url = f"{SUPPORTDESK_API_URL}{path}"

        async with httpx.AsyncClient(timeout=10.0, trust_env=True) as client:
            response = await client.request(method, url, json=json_body)

        status_code = str(response.status_code)

        try:
            data = response.json()
        except Exception:
            data = {
                "raw": response.text[:500],
            }

        if response.status_code >= 400:
            error_value = data.get("error") if isinstance(data, dict) else response.text
            record_error("backend_error")
            raise RuntimeError(
                f"{method} {path} failed: HTTP {response.status_code}: {error_value}"
            )

        return data

    except Exception:
        if status_code == "error":
            record_error("backend_error")
        raise

    finally:
        duration = time.perf_counter() - start_time

        SUPPORT_BOT_API_REQUESTS_TOTAL.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).inc()

        SUPPORT_BOT_API_REQUEST_DURATION_SECONDS.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code,
        ).observe(duration)


async def get_support_model(context: ContextTypes.DEFAULT_TYPE, force=False):
    if not force and context.bot_data.get("support_model"):
        return context.bot_data["support_model"]

    model = await api_request("GET", "/v1/support-model")
    context.bot_data["support_model"] = model

    log_event(
        "support_model_loaded",
        categories_count=len(model.get("categories", [])),
    )

    return model


def find_category(model, category_value):
    for category in model.get("categories", []):
        if category.get("value") == category_value:
            return category

    return None


def find_resource(category, resource_value):
    for resource in category.get("resources", []):
        if resource.get("value") == resource_value:
            return resource

    return None


def category_keyboard(model):
    rows = []

    for category in model.get("categories", []):
        rows.append(
            [
                InlineKeyboardButton(
                    category.get("label", category.get("value")),
                    callback_data=f"category:{category.get('value')}",
                )
            ]
        )

    rows.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


def resource_keyboard(category):
    rows = []

    for resource in category.get("resources", []):
        rows.append(
            [
                InlineKeyboardButton(
                    resource.get("label", resource.get("value")),
                    callback_data=f"resource:{resource.get('value')}",
                )
            ]
        )

    rows.append([InlineKeyboardButton("⬅️ Назад к сервисам", callback_data="new_ticket")])
    rows.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


def priority_keyboard(model):
    priorities = model.get("priorities", ["low", "normal", "high", "critical"])

    rows = []
    row = []

    for priority in priorities:
        row.append(
            InlineKeyboardButton(
                priority,
                callback_data=f"priority:{priority}",
            )
        )

        if len(row) == 2:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


def confirmation_keyboard():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Создать заявку", callback_data="confirm_create")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
        ]
    )


def active_tickets_keyboard(tickets, page=0):
    total = len(tickets)
    total_pages = max(1, (total + TICKETS_PER_PAGE - 1) // TICKETS_PER_PAGE)

    page = max(0, min(page, total_pages - 1))

    rows = []
    navigation_row = []

    if page > 0:
        navigation_row.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"active_page:{page - 1}")
        )

    if page < total_pages - 1:
        navigation_row.append(
            InlineKeyboardButton("➡️ Следующая", callback_data=f"active_page:{page + 1}")
        )

    if navigation_row:
        rows.append(navigation_row)

    rows.append([InlineKeyboardButton("⬅️ В главное меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(rows)


def resolve_keyboard(tickets, page=0):
    total = len(tickets)
    total_pages = max(1, (total + TICKETS_PER_PAGE - 1) // TICKETS_PER_PAGE)

    page = max(0, min(page, total_pages - 1))

    start = page * TICKETS_PER_PAGE
    end = start + TICKETS_PER_PAGE
    visible_tickets = tickets[start:end]

    rows = []

    for ticket in visible_tickets:
        ticket_id = ticket.get("id")
        category_label = ticket.get("category_label") or ticket.get("category")
        resource_label = ticket.get("resource_label") or ticket.get("resource")

        button_text = f"✅ #{ticket_id} {category_label} / {resource_label}"
        rows.append(
            [
                InlineKeyboardButton(
                    truncate(button_text, 60),
                    callback_data=f"resolve:{ticket_id}",
                )
            ]
        )

    navigation_row = []

    if page > 0:
        navigation_row.append(
            InlineKeyboardButton("⬅️ Назад", callback_data=f"resolve_page:{page - 1}")
        )

    if page < total_pages - 1:
        navigation_row.append(
            InlineKeyboardButton("➡️ Следующая", callback_data=f"resolve_page:{page + 1}")
        )

    if navigation_row:
        rows.append(navigation_row)

    rows.append([InlineKeyboardButton("⬅️ В главное меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(rows)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meta = user_meta(update)

    context.user_data.pop("state", None)
    context.user_data.pop("draft", None)

    log_event(
        "main_menu_opened",
        **meta,
    )

    text = (
        "🎓 <b>MISIS Digital Support</b>\n\n"
        "Я помогу создать заявку по цифровым сервисам университета.\n\n"
        "Выберите действие:"
    )

    await send_or_edit(
        update,
        text,
        reply_markup=main_menu_keyboard(),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await deny_if_needed(update):
        return

    record_action("command_start")
    meta = user_meta(update)

    log_event(
        "start_command",
        bot_username=TELEGRAM_BOT_USERNAME,
        **meta,
    )

    await show_main_menu(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await deny_if_needed(update):
        return

    record_action("command_help")
    meta = user_meta(update)

    log_event(
        "help_requested",
        **meta,
    )

    text = (
        "ℹ️ <b>Помощь</b>\n\n"
        "Этот бот — Telegram-клиент для "
        "<b>MISIS_Digital Student Support</b>.\n\n"
        "Что можно сделать:\n\n"
        "📝 Создать заявку через кнопки\n"
        "📋 Посмотреть активные заявки\n"
        "✅ Закрыть активную заявку\n"
        "🔎 Проверить доступность backend API\n\n"
        "Ваш Telegram user_id:\n"
        f"{code(meta['telegram_user_id'])}"
    )

    await send_or_edit(
        update,
        text,
        reply_markup=back_to_menu_keyboard(),
    )


async def check_backend_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meta = user_meta(update)

    try:
        data = await api_request("GET", "/v1/health")

        text = (
            "✅ <b>Backend доступен</b>\n\n"
            f"Product: {code(data.get('product'))}\n"
            f"Service: {code(data.get('service'))}\n"
            f"Version: {code(data.get('version'))}\n"
            f"Environment: {code(data.get('environment'))}\n"
            f"API version: {code(data.get('api_version'))}\n"
            f"Time: {code(data.get('time'))}"
        )

        log_event(
            "backend_health_ok",
            status=data.get("status"),
            service=data.get("service"),
            **meta,
        )

    except Exception as error:
        text = (
            "❌ <b>Backend недоступен</b>\n\n"
            f"Ошибка: {code(mask_secret(error))}"
        )

        log_event(
            "backend_health_failed",
            error=error,
            **meta,
        )

    await send_or_edit(
        update,
        text,
        reply_markup=back_to_menu_keyboard(),
    )


async def start_new_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meta = user_meta(update)

    try:
        model = await get_support_model(context)
    except Exception as error:
        log_event(
            "support_model_load_failed",
            error=error,
            **meta,
        )

        await send_or_edit(
            update,
            "❌ Не удалось получить модель сервисов от backend API.\n\n"
            f"Ошибка: {code(mask_secret(error))}",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    context.user_data["state"] = "selecting_category"
    context.user_data["draft"] = {}

    log_event(
        "new_ticket_started",
        **meta,
    )

    text = (
        "➕ <b>Создание заявки</b>\n\n"
        "Шаг 1 из 4.\n"
        "Выберите цифровой сервис, где возникла проблема:"
    )

    await send_or_edit(
        update,
        text,
        reply_markup=category_keyboard(model),
    )


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category_value):
    meta = user_meta(update)
    model = await get_support_model(context)
    category = find_category(model, category_value)

    if not category:
        log_event(
            "category_not_found",
            category=category_value,
            **meta,
        )

        await send_or_edit(
            update,
            "❌ Такой цифровой сервис не найден. Начните создание заявки заново.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    draft = context.user_data.setdefault("draft", {})
    draft["category"] = category.get("value")
    draft["category_label"] = category.get("label")
    context.user_data["state"] = "selecting_resource"

    log_event(
        "ticket_category_selected",
        category=draft["category"],
        **meta,
    )

    text = (
        "➕ <b>Создание заявки</b>\n\n"
        "Шаг 2 из 4.\n"
        f"Сервис: <b>{h(draft['category_label'])}</b>\n\n"
        "Выберите раздел или функцию, где возникла проблема:"
    )

    await send_or_edit(
        update,
        text,
        reply_markup=resource_keyboard(category),
    )


async def select_resource(update: Update, context: ContextTypes.DEFAULT_TYPE, resource_value):
    meta = user_meta(update)
    model = await get_support_model(context)

    draft = context.user_data.setdefault("draft", {})
    category_value = draft.get("category")
    category = find_category(model, category_value)

    if not category:
        await send_or_edit(
            update,
            "❌ Не найден выбранный сервис. Начните создание заявки заново.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    resource = find_resource(category, resource_value)

    if not resource:
        log_event(
            "resource_not_found",
            category=category_value,
            resource=resource_value,
            **meta,
        )

        await send_or_edit(
            update,
            "❌ Такой раздел не найден для выбранного сервиса.",
            reply_markup=resource_keyboard(category),
        )
        return

    draft["resource"] = resource.get("value")
    draft["resource_label"] = resource.get("label")
    context.user_data["state"] = "selecting_priority"

    log_event(
        "ticket_resource_selected",
        category=draft.get("category"),
        resource=draft.get("resource"),
        **meta,
    )

    text = (
        "➕ <b>Создание заявки</b>\n\n"
        "Шаг 3 из 4.\n"
        f"Сервис: <b>{h(draft.get('category_label'))}</b>\n"
        f"Раздел: <b>{h(draft.get('resource_label'))}</b>\n\n"
        "Выберите приоритет:"
    )

    await send_or_edit(
        update,
        text,
        reply_markup=priority_keyboard(model),
    )


async def select_priority(update: Update, context: ContextTypes.DEFAULT_TYPE, priority):
    meta = user_meta(update)
    model = await get_support_model(context)
    priorities = model.get("priorities", ["low", "normal", "high", "critical"])

    if priority not in priorities:
        await send_or_edit(
            update,
            "❌ Некорректный приоритет.",
            reply_markup=priority_keyboard(model),
        )
        return

    draft = context.user_data.setdefault("draft", {})
    draft["priority"] = priority
    context.user_data["state"] = "awaiting_description"

    log_event(
        "ticket_priority_selected",
        category=draft.get("category"),
        resource=draft.get("resource"),
        priority=priority,
        **meta,
    )

    text = (
        "➕ <b>Создание заявки</b>\n\n"
        "Шаг 4 из 4.\n"
        f"Сервис: <b>{h(draft.get('category_label'))}</b>\n"
        f"Раздел: <b>{h(draft.get('resource_label'))}</b>\n"
        f"Приоритет: <b>{h(priority)}</b>\n\n"
        "Теперь напишите описание проблемы одним сообщением.\n\n"
        "Пример:\n"
        f"{code('В электронной зачетке не отображается оценка по дисциплине')}"
    )

    await send_or_edit(
        update,
        text,
        reply_markup=cancel_keyboard(),
    )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await deny_if_needed(update):
        return

    meta = user_meta(update)
    state = context.user_data.get("state")

    if state != "awaiting_description":
        log_event(
            "unexpected_text_message",
            **meta,
        )

        await update.message.reply_text(
            "Я не понял это сообщение в текущем контексте.\n\n"
            "Выберите действие в меню:",
            reply_markup=main_menu_keyboard(),
        )
        return

    description = update.message.text.strip()

    if len(description) < 3:
        await update.message.reply_text(
            "Описание слишком короткое. Напишите, пожалуйста, чуть подробнее.",
            reply_markup=cancel_keyboard(),
        )
        return

    if len(description) > MAX_DESCRIPTION_LEN:
        await update.message.reply_text(
            f"Описание слишком длинное. Максимум: {MAX_DESCRIPTION_LEN} символов.",
            reply_markup=cancel_keyboard(),
        )
        return

    draft = context.user_data.setdefault("draft", {})
    draft["description"] = description
    context.user_data["state"] = "confirming_ticket"

    log_event(
        "ticket_description_received",
        category=draft.get("category"),
        resource=draft.get("resource"),
        priority=draft.get("priority"),
        description_length=len(description),
        **meta,
    )

    text = (
        "🧾 <b>Проверьте заявку перед созданием</b>\n\n"
        f"Сервис: <b>{h(draft.get('category_label'))}</b>\n"
        f"Раздел: <b>{h(draft.get('resource_label'))}</b>\n"
        f"Приоритет: <b>{h(draft.get('priority'))}</b>\n\n"
        "<b>Описание:</b>\n"
        f"{h(description)}\n\n"
        "Создать заявку?"
    )

    await update.message.reply_text(
        text,
        reply_markup=confirmation_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def confirm_create_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meta = user_meta(update)
    draft = context.user_data.get("draft") or {}

    required_fields = ["category", "resource", "priority", "description"]
    missing_fields = [field for field in required_fields if not draft.get(field)]

    if missing_fields:
        log_event(
            "ticket_create_missing_draft_fields",
            missing_fields=",".join(missing_fields),
            **meta,
        )

        await send_or_edit(
            update,
            "❌ Не хватает данных для создания заявки. Начните заново.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    payload = {
        "category": draft["category"],
        "resource": draft["resource"],
        "priority": draft["priority"],
        "description": draft["description"],
        "source": SOURCE_NAME,
    }

    try:
        created_ticket = await api_request("POST", "/v1/tickets", json_body=payload)

        ticket_id = created_ticket.get("id")

        log_event(
            "ticket_created_via_bot",
            ticket_id=ticket_id,
            category=created_ticket.get("category"),
            resource=created_ticket.get("resource"),
            priority=created_ticket.get("priority"),
            source=SOURCE_NAME,
            **meta,
        )

        context.user_data.pop("state", None)
        context.user_data.pop("draft", None)

        text = (
            "✅ <b>Заявка создана</b>\n\n"
            f"Номер: {code(ticket_id)}\n"
            f"Статус: {code(created_ticket.get('status'))}\n"
            f"Сервис: <b>{h(created_ticket.get('category_label'))}</b>\n"
            f"Раздел: <b>{h(created_ticket.get('resource_label'))}</b>\n"
            f"Приоритет: <b>{h(created_ticket.get('priority'))}</b>\n"
            f"Создана через: {code(SOURCE_NAME)}"
        )

        await send_or_edit(
            update,
            text,
            reply_markup=after_create_keyboard(),
        )

    except Exception as error:
        log_event(
            "ticket_create_failed",
            category=draft.get("category"),
            resource=draft.get("resource"),
            priority=draft.get("priority"),
            error=error,
            **meta,
        )

        await send_or_edit(
            update,
            "❌ <b>Не удалось создать заявку</b>\n\n"
            f"Ошибка: {code(mask_secret(error))}",
            reply_markup=back_to_menu_keyboard(),
        )


def format_ticket_line(ticket):
    ticket_id = ticket.get("id")
    status = ticket.get("status")
    priority = ticket.get("priority")
    category_label = ticket.get("category_label") or ticket.get("category")
    resource_label = ticket.get("resource_label") or ticket.get("resource")
    description = truncate(ticket.get("description", ""), 120)

    return (
        f"#{h(ticket_id)} | {h(status)} | {h(priority)}\n"
        f"<b>{h(category_label)}</b> / {h(resource_label)}\n"
        f"{h(description)}"
    )


async def show_active_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    meta = user_meta(update)

    try:
        data = await api_request("GET", "/v1/tickets")
        tickets = data.get("tickets", [])

        log_event(
            "active_tickets_requested",
            count=len(tickets),
            page=page,
            **meta,
        )

        if not tickets:
            await send_or_edit(
                update,
                "📋 <b>Активные заявки</b>\n\n"
                "Сейчас активных заявок нет.",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        total = len(tickets)
        total_pages = max(1, (total + TICKETS_PER_PAGE - 1) // TICKETS_PER_PAGE)

        page = max(0, min(page, total_pages - 1))

        start_index = page * TICKETS_PER_PAGE
        end_index = min(start_index + TICKETS_PER_PAGE, total)
        visible_tickets = tickets[start_index:end_index]

        lines = [format_ticket_line(ticket) for ticket in visible_tickets]

        text = (
            "📋 <b>Активные заявки</b>\n\n"
            f"Всего активных: <b>{h(data.get('active_count', total))}</b>\n"
            f"Показаны заявки <b>{start_index + 1}–{end_index}</b> из <b>{total}</b>.\n"
            f"Страница <b>{page + 1}</b> из <b>{total_pages}</b>.\n\n"
            + "\n\n".join(lines)
        )

        await send_or_edit(
            update,
            text,
            reply_markup=active_tickets_keyboard(tickets, page),
        )

    except Exception as error:
        log_event(
            "active_tickets_request_failed",
            error=error,
            **meta,
        )

        await send_or_edit(
            update,
            "❌ <b>Не удалось получить активные заявки</b>\n\n"
            f"Ошибка: {code(mask_secret(error))}",
            reply_markup=back_to_menu_keyboard(),
        )


async def show_resolve_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    meta = user_meta(update)

    try:
        data = await api_request("GET", "/v1/tickets")
        tickets = data.get("tickets", [])

        log_event(
            "resolve_menu_requested",
            count=len(tickets),
            page=page,
            **meta,
        )

        if not tickets:
            await send_or_edit(
                update,
                "✅ <b>Закрыть заявку</b>\n\n"
                "Сейчас нет активных заявок, которые можно закрыть.",
                reply_markup=back_to_menu_keyboard(),
            )
            return

        total = len(tickets)
        total_pages = max(1, (total + TICKETS_PER_PAGE - 1) // TICKETS_PER_PAGE)

        page = max(0, min(page, total_pages - 1))

        start = page * TICKETS_PER_PAGE + 1
        end = min((page + 1) * TICKETS_PER_PAGE, total)

        text = (
            "✅ <b>Закрыть заявку</b>\n\n"
            "Выберите активную заявку, которую нужно перевести в "
            f"{code('resolved')}.\n\n"
            f"Показаны заявки <b>{start}–{end}</b> из <b>{total}</b>.\n"
            f"Страница <b>{page + 1}</b> из <b>{total_pages}</b>."
        )

        await send_or_edit(
            update,
            text,
            reply_markup=resolve_keyboard(tickets, page),
        )

    except Exception as error:
        log_event(
            "resolve_menu_failed",
            error=error,
            **meta,
        )

        await send_or_edit(
            update,
            "❌ <b>Не удалось получить список активных заявок</b>\n\n"
            f"Ошибка: {code(mask_secret(error))}",
            reply_markup=back_to_menu_keyboard(),
        )


async def resolve_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE, ticket_id):
    meta = user_meta(update)

    payload = {
        "status": "resolved",
        "source": SOURCE_NAME,
    }

    try:
        updated_ticket = await api_request(
            "PATCH",
            f"/v1/tickets/{ticket_id}/status",
            json_body=payload,
        )

        created_source = updated_ticket.get("source")

        log_event(
            "ticket_resolved_via_bot",
            ticket_id=updated_ticket.get("id"),
            category=updated_ticket.get("category"),
            resource=updated_ticket.get("resource"),
            old_status="-",
            new_status=updated_ticket.get("status"),
            created_source=created_source,
            action_source=SOURCE_NAME,
            source=SOURCE_NAME,
            **meta,
        )

        text = (
            "✅ <b>Заявка закрыта</b>\n\n"
            f"Номер: {code(updated_ticket.get('id'))}\n"
            f"Статус: {code(updated_ticket.get('status'))}\n"
            f"Сервис: <b>{h(updated_ticket.get('category_label'))}</b>\n"
            f"Раздел: <b>{h(updated_ticket.get('resource_label'))}</b>\n"
            f"Создана через: {code(created_source)}\n"
            f"Закрыта через: {code(SOURCE_NAME)}"
        )

        await send_or_edit(
            update,
            text,
            reply_markup=after_resolve_keyboard(),
        )

    except Exception as error:
        log_event(
            "ticket_resolve_failed",
            ticket_id=ticket_id,
            error=error,
            **meta,
        )

        await send_or_edit(
            update,
            "❌ <b>Не удалось закрыть заявку</b>\n\n"
            f"Ticket id: {code(ticket_id)}\n"
            f"Ошибка: {code(mask_secret(error))}",
            reply_markup=back_to_menu_keyboard(),
        )


async def cancel_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    meta = user_meta(update)

    context.user_data.pop("state", None)
    context.user_data.pop("draft", None)

    log_event(
        "flow_cancelled",
        **meta,
    )

    await send_or_edit(
        update,
        "❌ Действие отменено.\n\n"
        "Выберите новое действие:",
        reply_markup=main_menu_keyboard(),
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if await deny_if_needed(update):
        return

    action = query.data
    record_action(action)

    meta = user_meta(update)

    log_event(
        "button_pressed",
        action=action,
        normalized_action=normalize_bot_action(action),
        **meta,
    )

    if action == "main_menu":
        await show_main_menu(update, context)
        return

    if action == "help":
        await help_command(update, context)
        return

    if action == "cancel":
        await cancel_flow(update, context)
        return

    if action == "check_backend":
        await check_backend_handler(update, context)
        return

    if action == "new_ticket":
        await start_new_ticket(update, context)
        return

    if action == "active_tickets":
        await show_active_tickets(update, context, 0)
        return

    if action.startswith("active_page:"):
        page_raw = action.split(":", 1)[1]

        if page_raw.isdigit():
            await show_active_tickets(update, context, int(page_raw))
        else:
            await show_active_tickets(update, context, 0)

        return

    if action == "resolve_menu":
        await show_resolve_menu(update, context, 0)
        return

    if action.startswith("resolve_page:"):
        page_raw = action.split(":", 1)[1]

        if page_raw.isdigit():
            await show_resolve_menu(update, context, int(page_raw))
        else:
            await show_resolve_menu(update, context, 0)

        return

    if action.startswith("category:"):
        category_value = action.split(":", 1)[1]
        await select_category(update, context, category_value)
        return

    if action.startswith("resource:"):
        resource_value = action.split(":", 1)[1]
        await select_resource(update, context, resource_value)
        return

    if action.startswith("priority:"):
        priority = action.split(":", 1)[1]
        await select_priority(update, context, priority)
        return

    if action == "confirm_create":
        await confirm_create_ticket(update, context)
        return

    if action.startswith("resolve:"):
        ticket_id = action.split(":", 1)[1]
        await resolve_ticket(update, context, ticket_id)
        return

    record_error("unexpected_error")

    await send_or_edit(
        update,
        "Неизвестное действие.",
        reply_markup=back_to_menu_keyboard(),
    )


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await deny_if_needed(update):
        return

    record_action("command_new")
    await start_new_ticket(update, context)


async def tickets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await deny_if_needed(update):
        return

    record_action("command_tickets")
    await show_active_tickets(update, context, 0)


async def resolve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await deny_if_needed(update):
        return

    record_action("command_resolve")

    if context.args:
        ticket_id = context.args[0].strip()

        if ticket_id.isdigit():
            await resolve_ticket(update, context, ticket_id)
            return

    await show_resolve_menu(update, context, 0)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    error = context.error

    error_type = "telegram_error" if isinstance(error, TelegramError) else "handler_error"
    record_error(error_type)

    log_event(
        "handler_error",
        error_type=error_type,
        error=mask_secret(error),
    )

    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Произошла внутренняя ошибка бота.\n\n"
                "Попробуйте открыть главное меню через /start.",
                reply_markup=main_menu_keyboard(),
            )
    except Exception as notify_error:
        record_error("unexpected_error")
        log_event(
            "handler_error_notify_failed",
            error=mask_secret(notify_error),
        )


def build_application():
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    builder = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN)

    if TELEGRAM_PROXY_URL:
        request = HTTPXRequest(
            proxy=TELEGRAM_PROXY_URL,
            connect_timeout=10.0,
            read_timeout=30.0,
        )
        updates_request = HTTPXRequest(
            proxy=TELEGRAM_PROXY_URL,
            connect_timeout=10.0,
            read_timeout=30.0,
        )

        builder = builder.request(request).get_updates_request(updates_request)

    application = builder.build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new", new_command))
    application.add_handler(CommandHandler("tickets", tickets_command))
    application.add_handler(CommandHandler("resolve", resolve_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_error_handler(error_handler)

    return application


def init_metrics():
    SUPPORT_BOT_INFO.labels(
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
    ).set(1)

    SUPPORT_BOT_START_TIME_SECONDS.set(time.time())

    start_http_server(METRICS_PORT)

    log_event(
        "metrics_server_started",
        port=METRICS_PORT,
    )


def main():
    log_event(
        "bot_starting",
        bot_username=TELEGRAM_BOT_USERNAME,
        api_url=SUPPORTDESK_API_URL,
        proxy_enabled=bool(TELEGRAM_PROXY_URL),
        whitelist_enabled=bool(allowed_user_ids()),
        metrics_port=METRICS_PORT,
        started_at=now_iso(),
    )

    init_metrics()

    application = build_application()

    log_event("bot_started")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
