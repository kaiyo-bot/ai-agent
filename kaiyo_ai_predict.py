# -*- coding: utf-8 -*-
"""
Kaiyo AI Predict - Python standalone hosting version
Converted from the uploaded bot.js project.

Required modules:
    pip install requests pyTelegramBotAPI

IMPORTANT:
The uploaded bot.js does not contain the real .env values.
Put your real values in the CONFIG section below, or use environment
variables if the hosting service supports them.
"""

import os
import re
import json
import time
import hashlib
import threading
from datetime import datetime, timezone

import requests
import telebot
from telebot import types


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_BOT_TOKEN_HERE")
ADMIN_CHAT_ID = str(os.getenv("ADMIN_CHAT_ID", "PUT_ADMIN_TELEGRAM_ID_HERE"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@kaiyo1111")

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://6lotteryapi.com/api/webapi/"
).rstrip("/") + "/"

WINGO_LIMIT = max(1, int(os.getenv("WINGO_HISTORY_LIMIT", "1700")))
TRX_LIMIT = max(1, int(os.getenv("TRX_HISTORY_LIMIT", "1700")))
LANGUAGE = int(os.getenv("LANGUAGE", "7"))
DEVICE_ID = os.getenv(
    "DEVICE_ID",
    "5dcab3e06db88a206975e91ea6ac7c87"
)
DATA_PHONE = os.getenv("DATA_PHONE", "")
DATA_PASSWORD = os.getenv("DATA_PASSWORD", "")
UPDATE_INTERVAL = max(2, int(os.getenv("UPDATE_INTERVAL_MS", "2000")) // 1000)

# Custom Telegram emoji IDs.
# If your hosting bot does not provide environment variables, paste IDs here.
CUSTOM_EMOJI = {
    "login": os.getenv("CUSTOM_EMOJI_LOGIN", ""),
    "wingo": os.getenv("CUSTOM_EMOJI_WINGO", ""),
    "trx": os.getenv("CUSTOM_EMOJI_TRX", ""),
    "predict": os.getenv("CUSTOM_EMOJI_PREDICT", ""),
    "win": os.getenv("CUSTOM_EMOJI_WIN", ""),
    "lose": os.getenv("CUSTOM_EMOJI_LOSE", ""),
    "admin": os.getenv("CUSTOM_EMOJI_ADMIN", ""),
    "add": os.getenv("CUSTOM_EMOJI_ADD", ""),
    "remove": os.getenv("CUSTOM_EMOJI_REMOVE", ""),
    "broadcast": os.getenv("CUSTOM_EMOJI_BROADCAST", ""),
    "allowed": os.getenv("CUSTOM_EMOJI_ALLOWED", ""),
    "main": os.getenv("CUSTOM_EMOJI_MAIN", ""),
    "result": os.getenv("CUSTOM_EMOJI_RESULT", ""),
    "stats": os.getenv("CUSTOM_EMOJI_STATS", ""),
    "search": os.getenv("CUSTOM_EMOJI_SEARCH", ""),
    "success": os.getenv("CUSTOM_EMOJI_SUCCESS", ""),
    "error": os.getenv("CUSTOM_EMOJI_ERROR", ""),
    "loading": os.getenv("CUSTOM_EMOJI_LOADING", ""),
    "next": os.getenv("CUSTOM_EMOJI_NEXT", ""),
    "input": os.getenv("CUSTOM_EMOJI_INPUT", ""),
    "data": os.getenv("CUSTOM_EMOJI_DATA", ""),
    "target": os.getenv("CUSTOM_EMOJI_TARGET", ""),
    "tutorial": os.getenv("CUSTOM_EMOJI_TUTORIAL", ""),
}

FALLBACK_EMOJI = {
    "login": "🔐",
    "wingo": "🟢",
    "trx": "🔴",
    "predict": "🎯",
    "win": "✅",
    "lose": "❌",
    "admin": "👑",
    "add": "➕",
    "remove": "➖",
    "broadcast": "📢",
    "allowed": "👥",
    "main": "🏠",
    "result": "📊",
    "stats": "📈",
    "search": "🔎",
    "success": "✨",
    "error": "🚫",
    "loading": "⏳",
    "next": "➡️",
    "input": "⌨️",
    "data": "💾",
    "target": "🎯",
    "tutorial": "🎥",
    "big": "🔴",
    "small": "🔵",
}


# ============================================================
# STORAGE
# ============================================================

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

FILES = {
    "allowed": os.path.join(DATA_DIR, "allowed_ids.json"),
    "users": os.path.join(DATA_DIR, "users.json"),
    "results": os.path.join(DATA_DIR, "results.json"),
    "predictions": os.path.join(DATA_DIR, "predictions.json"),
    "emojis": os.path.join(DATA_DIR, "emojis.json"),
    "tutorial": os.path.join(DATA_DIR, "tutorial.json"),
}

DEFAULTS = {
    "allowed": {"ids": []},
    "users": {},
    "results": {"WINGO": [], "TRX": []},
    "predictions": {},
    "emojis": {},
    "tutorial": {"url": ""},
}


def load_json(name):
    try:
        with open(FILES[name], "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULTS[name].copy()


def save_json(name, value):
    tmp = FILES[name] + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    os.replace(tmp, FILES[name])


allowed_ids = set(str(x) for x in load_json("allowed").get("ids", []))
users = load_json("users")
result_store = load_json("results")
predictions = load_json("predictions")
saved_emoji_ids = load_json("emojis")
tutorial_data = load_json("tutorial")

if not isinstance(result_store, dict):
    result_store = {"WINGO": [], "TRX": []}
if not isinstance(predictions, dict):
    predictions = {}
if not isinstance(users, dict):
    users = {}
if not isinstance(tutorial_data, dict):
    tutorial_data = {"url": ""}

history_meta = result_store.setdefault("_historyMeta", {})
reset_days = history_meta.setdefault("resetDay", {})

for k, v in saved_emoji_ids.items():
    if v:
        CUSTOM_EMOJI[k] = str(v).strip()

write_lock = threading.RLock()


def persist():
    with write_lock:
        save_json("allowed", {"ids": sorted(allowed_ids)})
        save_json("users", users)
        save_json("results", result_store)
        save_json("predictions", predictions)
        save_json("emojis", CUSTOM_EMOJI)
        save_json("tutorial", tutorial_data)


# ============================================================
# TELEGRAM / EMOJI HELPERS
# ============================================================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


def esc(value):
    s = str(value)
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


def valid_emoji_id(key):
    x = str(CUSTOM_EMOJI.get(key, "") or "").strip()
    return x if re.fullmatch(r"\d{5,30}", x) else ""


def icon(key):
    eid = valid_emoji_id(key)
    fallback = FALLBACK_EMOJI.get(key, "")
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{esc(fallback)}</tg-emoji>'
    return fallback


def ensure_text_emoji(text):
    value = str(text or "")
    if re.match(r"^\s*(?:<tg-emoji\b|[\U0001F000-\U0001FAFF\u2600-\u27BF])", value):
        return value
    if re.search(r"login|Password|Phone Number", value, re.I):
        return f"{icon('login')} {value}"
    if re.search(r"error|မအောင်မြင်|မမှန်|မရှိ|အသုံးပြုခွင့်မရှိ", value, re.I):
        return f"{icon('error')} {value}"
    if re.search(r"WIN|အောင်မြင်|ပြီးပါပြီ|အသုံးပြုနိုင်ပါပြီ", value, re.I):
        return f"{icon('success')} {value}"
    if re.search(r"LOSE", value, re.I):
        return f"{icon('lose')} {value}"
    if re.search(r"Prediction|Predict|ခန့်မှန်း", value, re.I):
        return f"{icon('predict')} {value}"
    if re.search(r"Period|result|Result", value, re.I):
        return f"{icon('result')} {value}"
    return f"{icon('success')} {value}"


def reply(chat_id, text, markup=None):
    return bot.send_message(
        chat_id,
        ensure_text_emoji(text),
        parse_mode="HTML",
        reply_markup=markup,
    )


def is_admin(uid):
    return str(uid) == str(ADMIN_CHAT_ID)


def is_allowed(uid):
    uid = str(uid)
    if is_admin(uid):
        return True
    if uid in allowed_ids:
        return True
    u = users.get(uid, {})
    game_id = str(u.get("gameId", "")).strip()
    return bool(game_id and game_id in allowed_ids)


# ============================================================
# KEYBOARDS
# ============================================================

BUTTONS = {
    "login": ("Login", "login"),
    "wingo": ("Wingo 1 Min", "wingo"),
    "trx": ("TRX", "trx"),
    "predict": ("Predict", "predict"),
    "win": ("WIN", "win"),
    "lose": ("LOSE", "lose"),
    "admin": ("Admin Panel", "admin"),
    "add": ("Add User", "add"),
    "remove": ("Remove User", "remove"),
    "broadcast": ("Broadcast", "broadcast"),
    "allowed": ("Allowed IDs", "allowed"),
    "main": ("Main Menu", "main"),
    "tutorial": ("Tutorial Video ကြည့်ရန်", "tutorial"),
}


def make_reply_button(key):
    text, _ = BUTTONS[key]
    eid = valid_emoji_id(key)

    b = types.KeyboardButton(text)
    # pyTelegramBotAPI versions differ in custom keyboard support.
    # Standard KeyboardButton remains compatible everywhere.
    if eid:
        try:
            b.icon_custom_emoji_id = eid
        except Exception:
            pass
    return b


def main_keyboard(logged_in, admin=False):
    rows = []
    if not logged_in:
        rows = [
            [make_reply_button("login"), make_reply_button("tutorial")]
        ]
    else:
        rows = [
            [make_reply_button("login")],
            [make_reply_button("wingo")],
            [make_reply_button("trx")],
            [make_reply_button("predict")],
            [make_reply_button("tutorial")],
        ]
        if admin:
            rows.append([make_reply_button("admin")])

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    for row in rows:
        kb.row(*row)
    return kb


def admin_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    kb.row(make_reply_button("add"), make_reply_button("remove"))
    kb.row(make_reply_button("broadcast"), make_reply_button("allowed"))
    kb.row(types.KeyboardButton("Add Tutorial Video Link"))
    kb.row(make_reply_button("main"))
    return kb


def win_lose_keyboard(pred_id):
    kb = types.InlineKeyboardMarkup()
    w = types.InlineKeyboardButton(
        f"{FALLBACK_EMOJI['win']} WIN",
        callback_data=f"pred_win:{pred_id}",
    )
    l = types.InlineKeyboardButton(
        f"{FALLBACK_EMOJI['lose']} LOSE",
        callback_data=f"pred_lose:{pred_id}",
    )
    kb.row(w, l)
    return kb


def emoji_admin_keyboard():
    keys = [
        "login", "wingo", "trx", "predict", "win", "lose",
        "admin", "add", "remove", "broadcast", "allowed", "main",
        "result", "stats", "search", "success", "error", "loading",
        "next", "input", "data", "target", "tutorial",
    ]
    kb = types.InlineKeyboardMarkup()
    for i in range(0, len(keys), 2):
        row = []
        for key in keys[i:i + 2]:
            row.append(
                types.InlineKeyboardButton(
                    f"{FALLBACK_EMOJI.get(key, '')} {key}",
                    callback_data=f"emoji_select:{key}",
                )
            )
        kb.row(*row)
    return kb


def tutorial_markup():
    url = str(tutorial_data.get("url", "") or "").strip()
    if not re.match(r"^https?://\S+$", url, re.I):
        return None
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("🎥 Tutorial Video ကြည့်ရန်", url=url))
    return kb


# ============================================================
# API
# ============================================================

session_lock = threading.RLock()
collector_session = None
collector_token = None
collector_header = "Bearer "


def api_headers(token_header="", token=""):
    return {
        "Authorization": f"{token_header or 'Bearer '}{token or ''}",
        "Content-Type": "application/json;charset=UTF-8",
        "Ar-Origin": "https://www.6win598.com",
        "Origin": "https://www.6win598.com",
        "Referer": "https://www.6win598.com/",
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 16) "
            "AppleWebKit/537.36 Chrome/140 Mobile Safari/537.36"
        ),
    }


def generate_signature(data):
    filtered = {}
    for k in sorted(data):
        if k in ("signature", "track", "xosoBettingData"):
            continue
        v = data[k]
        if v is not None and v != "":
            filtered[k] = v

    raw = json.dumps(
        filtered,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.md5(raw.encode("utf-8")).hexdigest().upper()


def post_api(endpoint, body, token_header="", token="", timeout=15):
    url = API_BASE_URL + endpoint.lstrip("/")
    headers = api_headers(token_header, token)
    return requests.post(
        url,
        json=body,
        headers=headers,
        timeout=timeout,
    )


def login_6lottery(phone, password):
    raw = str(phone or "").strip()
    digits = re.sub(r"\D", "", raw)

    if not digits:
        return {"ok": False, "message": "Login ID ထည့်ပါ။"}

    candidates = []

    def add(x):
        x = str(x or "").strip()
        if x and x not in candidates:
            candidates.append(x)

    add(raw)
    add(digits)

    if digits.startswith("0"):
        add(digits[1:])
        add("95" + digits)
        add("95" + digits[1:])
        add("959" + digits[1:])
    else:
        add("0" + digits)
        add("95" + digits)
        add("959" + digits)

    last_message = "Wrong account or password"

    for username in candidates:
        body = {
            "username": username,
            "pwd": str(password or ""),
            "phonetype": 1,
            "logintype": "mobile",
            "packId": "",
            "deviceId": DEVICE_ID,
            "language": LANGUAGE,
            "random": os.urandom(16).hex(),
        }
        body["signature"] = generate_signature(body)
        body["timestamp"] = int(time.time())

        try:
            r = post_api("Login", body, timeout=15)
            data = r.json() if r.content else {}
        except Exception as e:
            return {
                "ok": False,
                "message": f"Login Server ကို ချိတ်ဆက်မရပါ။ {e}",
            }

        if int(data.get("code", -1)) == 0 and data.get("data"):
            d = data["data"]
            token_header = d.get("tokenHeader", "Bearer ")
            token = d.get("token", "")

            if not token:
                return {
                    "ok": False,
                    "message": "Login အောင်မြင်သော်လည်း Token မရပါ။",
                }

            try:
                info_body = {
                    "language": LANGUAGE,
                    "random": os.urandom(16).hex(),
                }
                info_body["signature"] = generate_signature(info_body)
                info_body["timestamp"] = int(time.time())

                rr = post_api(
                    "GetUserInfo",
                    info_body,
                    token_header,
                    token,
                    timeout=15,
                )
                info_json = rr.json() if rr.content else {}
                user_info = info_json.get("data") if int(
                    info_json.get("code", -1)
                ) == 0 else None
            except Exception:
                user_info = None

            if not user_info:
                return {
                    "ok": False,
                    "stage": "gameid",
                    "message": "Account Login အောင်မြင်ပါသည်။ Game ID ကိုရယူ၍မရပါ။",
                }

            game_id = (
                user_info.get("userId")
                or user_info.get("userID")
                or user_info.get("id")
                or user_info.get("uid")
                or user_info.get("gameId")
                or user_info.get("gameID")
                or user_info.get("memberId")
                or user_info.get("memberID")
            )

            if game_id is None or str(game_id).strip() == "":
                return {
                    "ok": False,
                    "stage": "gameid",
                    "message": "Account Login အောင်မြင်ပါသည်။ Game ID မတွေ့ပါ။",
                }

            return {
                "ok": True,
                "token": token,
                "tokenHeader": token_header,
                "gameId": str(game_id),
                "userInfo": user_info,
            }

        last_message = data.get("msg") or last_message

    return {"ok": False, "message": last_message}


def collector_login(force=False):
    global collector_session, collector_token, collector_header

    with session_lock:
        if collector_session is not None and not force:
            return collector_session, collector_header, collector_token

        if not DATA_PHONE or not DATA_PASSWORD:
            return None, "", ""

        result = login_6lottery(DATA_PHONE, DATA_PASSWORD)
        if not result.get("ok"):
            collector_session = None
            return None, "", ""

        collector_token = result["token"]
        collector_header = result["tokenHeader"]
        collector_session = requests.Session()
        collector_session.headers.update(
            api_headers(collector_header, collector_token)
        )
        return collector_session, collector_header, collector_token


def extract_result(item):
    if not isinstance(item, dict):
        return None

    period = str(
        item.get("issueNumber")
        or item.get("period")
        or item.get("issue")
        or ""
    ).strip()

    raw = (
        item.get("number")
        if item.get("number") is not None
        else item.get("result")
        if item.get("result") is not None
        else item.get("num")
        if item.get("num") is not None
        else item.get("winNumber", "")
    )

    digits = re.sub(r"\D", "", str(raw))
    if not period or not digits:
        return None

    number = int(digits[-1])
    if number < 0 or number > 9:
        return None

    return {"period": period, "number": number}


def fetch_history(token_header, token, game, wanted):
    out = []
    seen = set()

    page_size = 10 if game == "TRX" else 100
    page = 1
    max_pages = (wanted + page_size - 1) // page_size + 10
    type_id = 13 if game == "TRX" else 1
    endpoint = (
        "GetTRXNoaverageEmerdList"
        if game == "TRX"
        else "GetNoaverageEmerdList"
    )

    for page in range(1, max_pages + 1):
        if len(out) >= wanted:
            break

        body = {
            "pageSize": page_size,
            "pageNo": page,
            "typeId": type_id,
            "language": LANGUAGE,
            "random": os.urandom(16).hex(),
        }
        body["signature"] = generate_signature(body)
        body["timestamp"] = int(time.time())

        try:
            r = post_api(
                endpoint,
                body,
                token_header,
                token,
                timeout=15,
            )
            data = r.json() if r.content else {}
        except Exception:
            break

        if int(data.get("code", -1)) != 0:
            break

        root = data.get("data") or {}
        if game == "TRX":
            items = (
                ((root.get("data") or {}).get("gameslist"))
                or root.get("gameslist")
                or []
            )
        else:
            items = root.get("list") or root.get("records") or []

        if not isinstance(items, list) or not items:
            break

        added = 0
        for item in items:
            x = extract_result(item)
            if x and x["period"] not in seen:
                seen.add(x["period"])
                out.append(x)
                added += 1
            if len(out) >= wanted:
                break

        if added == 0:
            break

        time.sleep(0.05)

    out.sort(key=lambda x: int(x["period"]) if x["period"].isdigit() else 0, reverse=True)
    return out[:wanted]


def fetch_trx_history(wanted=TRX_LIMIT):
    global collector_session

    session, header, token = collector_login()
    if not session:
        return []

    # Use the session directly because TRX requires the authenticated collector.
    out = []
    seen = set()
    page = 1
    total_page = 1

    while len(out) < wanted and page <= total_page:
        body = {
            "pageSize": 10,
            "pageNo": page,
            "typeId": 13,
            "language": 7,
            "random": os.urandom(16).hex(),
        }
        body["signature"] = generate_signature(body)
        body["timestamp"] = int(time.time())

        try:
            r = session.post(
                API_BASE_URL + "GetTRXNoaverageEmerdList",
                json=body,
                timeout=15,
            )
            data = r.json() if r.content else {}
        except Exception:
            break

        code = int(data.get("code", -1))

        if code == 4:
            collector_session = None
            session, header, token = collector_login(force=True)
            if not session:
                break
            continue

        if code != 0:
            break

        root = data.get("data") or {}
        total_page = int(root.get("totalPage") or total_page)
        games = ((root.get("data") or {}).get("gameslist")) or []

        if not games:
            break

        for item in games:
            x = extract_result(item)
            if x and x["period"] not in seen:
                seen.add(x["period"])
                out.append(x)
            if len(out) >= wanted:
                break

        page += 1
        time.sleep(0.05)

    out.sort(key=lambda x: int(x["period"]) if x["period"].isdigit() else 0, reverse=True)
    return out[:wanted]


# ============================================================
# DAILY HISTORY MANAGER
# ============================================================

def period_day(period):
    p = str(period or "").strip()
    return p[:8] if re.match(r"^\d{8}", p) else ""


def merge_daily_history(game, incoming, limit):
    old = result_store.get(game, [])
    if not isinstance(old, list):
        old = []

    combined = old + (incoming if isinstance(incoming, list) else [])
    by_period = {}

    for item in combined:
        p = str(item.get("period", "")).strip() if isinstance(item, dict) else ""
        if p and p not in by_period:
            by_period[p] = item

    unique = list(by_period.values())
    unique.sort(
        key=lambda x: int(str(x.get("period", "0")))
        if str(x.get("period", "0")).isdigit() else 0,
        reverse=True,
    )

    if not unique:
        return old

    newest_day = period_day(unique[0].get("period"))
    reset_day = str(reset_days.get(game, "") or "").strip()

    if not reset_day:
        reset_day = period_day(old[0].get("period")) if old else newest_day
        reset_days[game] = reset_day

    # New calendar day: newest 1700 become the base.
    if newest_day and reset_day != newest_day:
        reset_days[game] = newest_day
        return unique[:limit]

    # Same day: keep ALL accumulated records.
    return unique


# ============================================================
# PREDICTION
# ============================================================

def pct(n, total):
    return (n / total * 100.0) if total else 0.0


def predict(records, old_n, new_n):
    nums = []
    for r in records if isinstance(records, list) else []:
        try:
            n = int(r.get("number", r.get("result", r.get("resultNumber"))))
            if 0 <= n <= 9:
                nums.append(n)
        except Exception:
            pass

    a = int(old_n)
    b = int(new_n)

    overall = [0] * 10
    for n in nums:
        overall[n] += 1

    total = len(nums)
    big_overall = sum(overall[5:10])
    small_overall = sum(overall[0:5])

    pair_results = []
    old_results = []
    new_results = []

    for i in range(len(nums) - 2):
        if nums[i] == a and nums[i + 1] == b:
            pair_results.append(nums[i + 2])

    for i in range(len(nums) - 1):
        if nums[i] == a:
            old_results.append(nums[i + 1])
        if nums[i] == b:
            new_results.append(nums[i + 1])

    def stats(arr):
        counts = [0] * 10
        for n in arr:
            if 0 <= n <= 9:
                counts[n] += 1
        t = len(arr)
        big = sum(counts[5:10])
        small = sum(counts[0:5])
        return {
            "total": t,
            "count": counts,
            "big": big,
            "small": small,
            "bigPct": pct(big, t),
            "smallPct": pct(small, t),
        }

    pair = stats(pair_results)
    old = stats(old_results)
    new = stats(new_results)

    big_score = 0.0
    small_score = 0.0

    if pair["total"] > 0:
        big_score += pair["bigPct"] * 0.50
        small_score += pair["smallPct"] * 0.50

    if old["total"] > 0:
        big_score += old["bigPct"] * 0.25
        small_score += old["smallPct"] * 0.25

    if new["total"] > 0:
        big_score += new["bigPct"] * 0.25
        small_score += new["smallPct"] * 0.25

    prediction = "N/A"
    if pair["total"] or old["total"] or new["total"]:
        prediction = "BIG" if big_score >= small_score else "SMALL"

    return {
        "prediction": prediction,
        "overall": overall,
        "total": total,
        "bigOverall": big_overall,
        "smallOverall": small_overall,
        "bigOverallPct": pct(big_overall, total),
        "smallOverallPct": pct(small_overall, total),
        "pairResults": pair_results,
        "oldResults": old_results,
        "newResults": new_results,
        "pairStats": pair,
        "oldStats": old,
        "newStats": new,
        "bigScore": big_score,
        "smallScore": small_score,
        "confidence": max(big_score, small_score),
    }


def next_period(period):
    p = str(period or "").strip()
    if p.isdigit():
        return str(int(p) + 1)
    return p


def prediction_message(game, old_n, new_n, pred, current_period):
    total = int(pred.get("total", 0))
    counts = pred.get("overall", [0] * 10)

    big = sum(counts[5:10])
    small = sum(counts[0:5])

    if pred.get("prediction") == "BIG":
        ai = "Big ( အကြီး )"
    elif pred.get("prediction") == "SMALL":
        ai = "Small ( အသေး )"
    else:
        ai = "Data မလုံလောက်သေးပါ"

    game_name = "6 Lottery — TRX" if game == "TRX" else "6 Lottery — Wingo 1 Min"

    lines = [
        f"{icon('predict')} <b>AI Agent Predictor</b>",
        "================",
        f"{icon('trx' if game == 'TRX' else 'wingo')} {game_name}",
        "",
        f"{icon('input')} Input old → new: <b>{esc(old_n)}, {esc(new_n)}</b>",
        f"{icon('search')} Lookup: {esc(old_n)},{esc(new_n)} (3-way pattern)",
        "",
        f"{icon('data')} Total Data: <b>{total}</b>",
        "",
        f"{icon('big')} BIG (5–9): <b>{big}</b> ({pct(big, total):.2f}%)",
        f"{icon('small')} SMALL (0–4): <b>{small}</b> ({pct(small, total):.2f}%)",
        "",
        f"{icon('stats')} <b>နံပါတ်အလိုက်ရလဒ်များ</b>",
    ]

    for n in range(10):
        lines.append(f"{n}: {counts[n]} ({pct(counts[n], total):.2f}%)")

    lines += [
        "",
        f"{icon('next')} <b>လက်ရှိပွဲစဉ်:</b> <code>{esc(current_period)}</code>",
        f"{icon('predict')} Ai ခန့်မှန်းချက်ရလဒ် = <b>{ai}</b>",
        "",
        f"Period ပြီးဆုံးပါက {icon('win')} WIN သို့မဟုတ် {icon('lose')} LOSE ကို ကိုယ်တိုင်နှိပ်ပါ။",
    ]
    return "\n".join(lines)


# ============================================================
# BOT HANDLERS
# ============================================================

def ensure_user(uid):
    uid = str(uid)
    if uid not in users:
        users[uid] = {
            "id": uid,
            "state": None,
            "selectedGame": None,
        }
    return users[uid]


@bot.message_handler(commands=["start"])
def start_handler(message):
    uid = str(message.from_user.id)
    u = ensure_user(uid)
    persist()

    reply(
        message.chat.id,
        f"{icon('success')} <b>AI Agent Predictor</b>\n\n"
        f"{icon('login')} Login ဝင်ပြီးမှ Bot ကို အသုံးပြုနိုင်ပါသည်။",
        main_keyboard(bool(u.get("sessionToken")), is_admin(uid)),
    )


@bot.message_handler(commands=["id"])
def id_handler(message):
    reply(
        message.chat.id,
        f"🆔 Telegram ID: <code>{message.from_user.id}</code>",
    )


@bot.message_handler(func=lambda m: m.text == "Login")
def login_button(message):
    uid = str(message.from_user.id)
    u = ensure_user(uid)
    u["state"] = "LOGIN_PHONE"
    persist()
    reply(
        message.chat.id,
        f"{icon('input')} 6 Lottery <b>Phone Number</b> ထည့်ပါ။",
    )


@bot.message_handler(func=lambda m: m.text == "Wingo 1 Min")
def wingo_button(message):
    uid = str(message.from_user.id)
    if not is_allowed(uid):
        reply(
            message.chat.id,
            f"{icon('error')} အသုံးပြုခွင့်မရှိပါ။\n\n"
            f"Admin ထံဆက်သွယ်ပါ {esc(ADMIN_USERNAME)}",
            main_keyboard(False, False),
        )
        return

    u = ensure_user(uid)
    if not u.get("sessionToken"):
        reply(message.chat.id, f"{icon('login')} Login အရင်ဝင်ပါ။", main_keyboard(False))
        return

    u["selectedGame"] = "WINGO"
    u["state"] = None
    persist()

    count = len(result_store.get("WINGO", []))
    reply(
        message.chat.id,
        f"{icon('wingo')} Wingo 1 Min Data "
        f"<b>{count}/{WINGO_LIMIT}</b> အသင့်ရှိပါပြီ။",
        main_keyboard(True, is_admin(uid)),
    )


@bot.message_handler(func=lambda m: m.text == "TRX")
def trx_button(message):
    uid = str(message.from_user.id)
    if not is_allowed(uid):
        reply(
            message.chat.id,
            f"{icon('error')} အသုံးပြုခွင့်မရှိပါ။\n\n"
            f"Admin ထံဆက်သွယ်ပါ {esc(ADMIN_USERNAME)}",
            main_keyboard(False, False),
        )
        return

    u = ensure_user(uid)
    if not u.get("sessionToken"):
        reply(message.chat.id, f"{icon('login')} Login အရင်ဝင်ပါ။", main_keyboard(False))
        return

    u["selectedGame"] = "TRX"
    u["state"] = None
    persist()

    count = len(result_store.get("TRX", []))
    reply(
        message.chat.id,
        f"{icon('trx')} TRX Data "
        f"<b>{count}/{TRX_LIMIT}</b> အသင့်ရှိပါပြီ။",
        main_keyboard(True, is_admin(uid)),
    )


@bot.message_handler(func=lambda m: m.text == "Predict")
def predict_button(message):
    uid = str(message.from_user.id)
    if not is_allowed(uid):
        reply(
            message.chat.id,
            f"{icon('error')} အသုံးပြုခွင့်မရှိပါ။\n\n"
            f"Admin ထံဆက်သွယ်ပါ {esc(ADMIN_USERNAME)}",
            main_keyboard(False, False),
        )
        return

    u = ensure_user(uid)
    if not u.get("sessionToken"):
        reply(message.chat.id, f"{icon('login')} Login အရင်ဝင်ပါ။", main_keyboard(False))
        return

    if not u.get("selectedGame"):
        reply(
            message.chat.id,
            f"{icon('error')} Wingo 1 Min သို့မဟုတ် TRX ကို အရင်ရွေးပါ။",
            main_keyboard(True, is_admin(uid)),
        )
        return

    u["state"] = "PREDICT_INPUT"
    persist()

    reply(
        message.chat.id,
        f"{icon('input')} နောက်ဆုံး result နှစ်လုံးကို "
        f"old → new <code>0,2</code> ပုံစံဖြင့်ထည့်ပါ။",
    )


@bot.message_handler(func=lambda m: m.text == "Tutorial Video ကြည့်ရန်")
def tutorial_button(message):
    kb = tutorial_markup()
    if not kb:
        reply(
            message.chat.id,
            f"{icon('error')} <b>Tutorial Video မရသေးပါ။</b>\n\n"
            f"Admin မှ Tutorial Link ထည့်ပေးရန် လိုအပ်ပါသည်။",
        )
        return

    reply(
        message.chat.id,
        f"{icon('tutorial')} <b>Tutorial Video</b>\n\n"
        f"အောက်က Button ကိုနှိပ်ပြီး Video ကြည့်နိုင်ပါတယ်။",
        kb,
    )


@bot.message_handler(func=lambda m: m.text == "Admin Panel")
def admin_panel(message):
    uid = str(message.from_user.id)
    if not is_admin(uid):
        reply(message.chat.id, f"{icon('error')} Admin only!")
        return

    reply(
        message.chat.id,
        f"{icon('admin')} <b>Admin Panel</b>\n\n"
        f"{icon('target')} Select an action:",
        admin_keyboard(),
    )


@bot.message_handler(func=lambda m: m.text == "Main Menu")
def main_menu(message):
    uid = str(message.from_user.id)
    u = ensure_user(uid)
    u["state"] = None
    persist()
    reply(
        message.chat.id,
        f"{icon('main')} Main Menu",
        main_keyboard(bool(u.get("sessionToken")), is_admin(uid)),
    )


@bot.message_handler(func=lambda m: m.text == "Add User")
def add_user_button(message):
    uid = str(message.from_user.id)
    if not is_admin(uid):
        return
    ensure_user(uid)["state"] = "ADMIN_ADD"
    persist()
    reply(message.chat.id, f"{icon('add')} Telegram User ID ထည့်ပါ။")


@bot.message_handler(func=lambda m: m.text == "Remove User")
def remove_user_button(message):
    uid = str(message.from_user.id)
    if not is_admin(uid):
        return
    ensure_user(uid)["state"] = "ADMIN_REMOVE"
    persist()
    reply(message.chat.id, f"{icon('remove')} Remove လုပ်မယ့် Telegram User ID ထည့်ပါ။")


@bot.message_handler(func=lambda m: m.text == "Allowed IDs")
def allowed_button(message):
    uid = str(message.from_user.id)
    if not is_admin(uid):
        return

    ids = sorted(allowed_ids)
    body = "\n".join(f"{i+1}. <code>{esc(x)}</code>" for i, x in enumerate(ids))
    if not body:
        body = "Empty"

    reply(
        message.chat.id,
        f"{icon('allowed')} <b>Allowed IDs</b>\n\n"
        f"{body}\n\nTotal: {len(ids)}",
        admin_keyboard(),
    )


@bot.message_handler(func=lambda m: m.text == "Broadcast")
def broadcast_button(message):
    uid = str(message.from_user.id)
    if not is_admin(uid):
        return
    ensure_user(uid)["state"] = "ADMIN_BROADCAST"
    persist()
    reply(message.chat.id, f"{icon('broadcast')} Broadcast လုပ်မယ့် Message ကို ပို့ပါ။")


@bot.message_handler(func=lambda m: m.text == "Add Tutorial Video Link")
def add_tutorial_button(message):
    uid = str(message.from_user.id)
    if not is_admin(uid):
        return
    ensure_user(uid)["state"] = "ADMIN_TUTORIAL_LINK"
    persist()
    reply(
        message.chat.id,
        f"{icon('tutorial')} <b>Add Tutorial Video Link</b>\n\n"
        f"Tutorial Video Link ပို့ပါ။",
    )


@bot.message_handler(func=lambda m: True, content_types=["text"])
def text_handler(message):
    uid = str(message.from_user.id)
    text = str(message.text or "").strip()
    u = ensure_user(uid)

    if text.startswith("/"):
        return

    state = u.get("state")

    # ---------------- LOGIN PHONE ----------------
    if state == "LOGIN_PHONE":
        u["pendingPhone"] = text
        u["state"] = "LOGIN_PASSWORD"
        persist()
        reply(message.chat.id, f"{icon('input')} Password ထည့်ပါ။")
        return

    # ---------------- LOGIN PASSWORD ----------------
    if state == "LOGIN_PASSWORD":
        phone = u.get("pendingPhone", "")
        password = text

        reply(message.chat.id, f"{icon('loading')} 6 Lottery Login စစ်ဆေးနေပါသည်...")

        result = login_6lottery(phone, password)

        if not result.get("ok"):
            u["state"] = "LOGIN_PHONE"
            u.pop("pendingPhone", None)
            persist()
            reply(
                message.chat.id,
                f"{icon('error')} Login မအောင်မြင်ပါ။\n"
                f"{esc(result.get('message', 'Unknown error'))}",
            )
            return

        game_id = str(result["gameId"])

        if game_id not in allowed_ids and not is_admin(uid):
            u["state"] = None
            for k in ("pendingPhone", "sessionToken", "sessionTokenHeader", "gameId"):
                u.pop(k, None)
            persist()

            reply(
                message.chat.id,
                f"{icon('error')} <b>အသုံးပြုခွင့်မရှိပါ။</b>\n\n"
                f"Game ID: <code>{esc(game_id)}</code>\n\n"
                f"Admin ထံဆက်သွယ်ပါ {esc(ADMIN_USERNAME)}",
                main_keyboard(False, False),
            )
            return

        u["sessionToken"] = result["token"]
        u["sessionTokenHeader"] = result["tokenHeader"]
        u["gameId"] = game_id
        u["phone"] = phone
        u["state"] = None
        persist()

        # Initial history download in background so login response is fast.
        threading.Thread(
            target=initial_history_for_login,
            args=(result["tokenHeader"], result["token"]),
            daemon=True,
        ).start()

        reply(
            message.chat.id,
            f"{icon('success')} Login အောင်မြင်ပါပြီ။\n"
            f"Game ID: <code>{esc(game_id)}</code>\n\n"
            f"Bot အသုံးပြုနိုင်ပါပြီ။",
            main_keyboard(True, is_admin(uid)),
        )
        return

    # ---------------- PREDICTION INPUT ----------------
    if state == "PREDICT_INPUT" or (
        u.get("sessionToken")
        and u.get("selectedGame")
        and re.fullmatch(r"\s*[0-9]\s*,\s*[0-9]\s*", text)
    ):
        m = re.fullmatch(r"\s*([0-9])\s*,\s*([0-9])\s*", text)
        if not m:
            reply(
                message.chat.id,
                f"{icon('error')} Format မမှန်ပါ။ "
                f"<code>0,2</code> ပုံစံဖြင့် ထည့်ပါ။",
            )
            return

        old_n = int(m.group(1))
        new_n = int(m.group(2))
        game = u.get("selectedGame")
        records = result_store.get(game, [])

        if not records:
            reply(
                message.chat.id,
                f"{icon('loading')} {game} Data မရသေးပါ။ "
                f"ခဏစောင့်ပြီး ပြန်စမ်းပါ။",
            )
            return

        pred = predict(records, old_n, new_n)

        latest = str(records[0].get("period", "")).strip() if records else ""
        display_period = next_period(latest)

        pred_id = f"{uid}_{int(time.time()*1000)}_{os.urandom(4).hex()}"

        predictions[pred_id] = {
            "telegramId": uid,
            "game": game,
            "inputOld": old_n,
            "inputNew": new_n,
            "prediction": pred["prediction"],
            "predictedPeriod": display_period,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "status": "PENDING",
            "stats": pred,
        }

        u["state"] = None
        persist()

        # FAST REPLY: no live API wait here.
        reply(
            message.chat.id,
            prediction_message(
                game,
                old_n,
                new_n,
                pred,
                display_period,
            ),
            win_lose_keyboard(pred_id),
        )

        # Refresh live period/cache after the message has been sent.
        threading.Thread(
            target=background_refresh,
            args=(uid, game),
            daemon=True,
        ).start()
        return

    # ---------------- ADMIN TUTORIAL ----------------
    if is_admin(uid) and state == "ADMIN_TUTORIAL_LINK":
        if not re.match(r"^https?://\S+$", text, re.I):
            reply(
                message.chat.id,
                f"{icon('error')} Tutorial Link မမှန်ပါ။\n\n"
                f"https:// သို့မဟုတ် http:// link ပို့ပါ။",
            )
            return

        tutorial_data["url"] = text
        u["state"] = None
        persist()

        reply(
            message.chat.id,
            f"{icon('success')} <b>Tutorial Video Link သိမ်းပြီးပါပြီ။</b>\n\n"
            f"Link: <code>{esc(text)}</code>",
            admin_keyboard(),
        )
        return

    # ---------------- ADMIN EMOJI ----------------
    if is_admin(uid) and str(state or "").startswith("ADMIN_EMOJI_ID:"):
        key = str(state).split(":", 1)[1]
        if not re.fullmatch(r"\d{5,30}", text):
            reply(
                message.chat.id,
                f"{icon('error')} Emoji ID မမှန်ပါ။ နံပါတ်သီးသန့် ထည့်ပါ။",
            )
            return

        CUSTOM_EMOJI[key] = text
        save_json("emojis", CUSTOM_EMOJI)
        u["state"] = None
        persist()

        reply(
            message.chat.id,
            f"{icon('success')} <b>{esc(key)}</b> Custom Emoji ID သိမ်းပြီးပါပြီ။\n"
            f"ID: <code>{esc(text)}</code>",
            admin_keyboard(),
        )
        return

    # ---------------- ADMIN ADD ----------------
    if is_admin(uid) and state == "ADMIN_ADD":
        target = re.sub(r"\D", "", text)
        if not target:
            reply(
                message.chat.id,
                f"{icon('error')} Valid Game ID ထည့်ပါ။",
                admin_keyboard(),
            )
            return

        allowed_ids.add(target)
        u["state"] = None
        persist()

        reply(
            message.chat.id,
            f"{icon('success')} <b>Game ID Approved ဖြစ်ပါပြီ။</b>\n\n"
            f"Game ID: <code>{esc(target)}</code>",
            admin_keyboard(),
        )
        return

    # ---------------- ADMIN REMOVE ----------------
    if is_admin(uid) and state == "ADMIN_REMOVE":
        target = re.sub(r"\D", "", text)
        if not target:
            reply(
                message.chat.id,
                f"{icon('error')} Valid Game ID ထည့်ပါ။",
                admin_keyboard(),
            )
            return

        existed = target in allowed_ids
        allowed_ids.discard(target)
        u["state"] = None
        persist()

        if existed:
            msg = (
                f"{icon('success')} Game ID ဖယ်ပြီးပါပြီ။\n\n"
                f"Game ID: <code>{esc(target)}</code>"
            )
        else:
            msg = (
                f"{icon('error')} ဒီ Game ID Approved List ထဲမှာ မရှိပါ။\n\n"
                f"Game ID: <code>{esc(target)}</code>"
            )

        reply(message.chat.id, msg, admin_keyboard())
        return

    # ---------------- ADMIN BROADCAST ----------------
    if is_admin(uid) and state == "ADMIN_BROADCAST":
        u["state"] = None
        ok = 0
        fail = 0

        for target in list(allowed_ids):
            try:
                bot.send_message(
                    int(target),
                    f"{icon('broadcast')} {esc(text)}",
                    parse_mode="HTML",
                )
                ok += 1
            except Exception:
                fail += 1
            time.sleep(0.08)

        persist()

        reply(
            message.chat.id,
            f"{icon('success')} Broadcast ပြီးပါပြီ။\n\n"
            f"✅ Sent: {ok}\n❌ Failed: {fail}",
            admin_keyboard(),
        )
        return


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data or ""

    # Answer callback immediately.
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass

    if data.startswith("emoji_select:"):
        if not is_admin(call.from_user.id):
            try:
                bot.answer_callback_query(call.id, "Admin only!", show_alert=True)
            except Exception:
                pass
            return

        key = data.split(":", 1)[1]
        uid = str(call.from_user.id)
        u = ensure_user(uid)
        u["state"] = f"ADMIN_EMOJI_ID:{key}"
        persist()

        reply(
            call.message.chat.id,
            f"{icon('input')} <b>{esc(key)}</b> အတွက် "
            f"Custom Emoji ID (နံပါတ်သီးသန့်) ပို့ပေးပါ။",
        )
        return

    m = re.fullmatch(r"pred_(win|lose):(.+)", data)
    if not m:
        return

    status = "WIN" if m.group(1) == "win" else "LOSE"
    pred_id = m.group(2)
    p = predictions.get(pred_id)

    if not p:
        try:
            bot.answer_callback_query(call.id, "Prediction not found", show_alert=True)
        except Exception:
            pass
        return

    uid = str(call.from_user.id)
    if uid != str(p.get("telegramId")):
        try:
            bot.answer_callback_query(
                call.id,
                "ဒီ Prediction ကို သင်မဖန်တီးထားပါ။",
                show_alert=True,
            )
        except Exception:
            pass
        return

    if p.get("status") != "PENDING":
        try:
            bot.answer_callback_query(
                call.id,
                "ပြီးသားဖြစ်ပါတယ်။",
                show_alert=True,
            )
        except Exception:
            pass
        return

    # Mark immediately.
    p["status"] = status
    p["resolvedAt"] = datetime.now(timezone.utc).isoformat()

    u = ensure_user(uid)
    u["state"] = "PREDICT_INPUT"
    u["selectedGame"] = p.get("game")
    persist()

    target_period = str(p.get("predictedPeriod", "")).strip()

    # One final message. Lookup runs in the background.
    threading.Thread(
        target=resolve_result,
        args=(call.message.chat.id, uid, pred_id, target_period),
        daemon=True,
    ).start()


# ============================================================
# RESULT RESOLUTION
# ============================================================

def find_cached(game, period):
    for item in result_store.get(game, []):
        if str(item.get("period", "")).strip() == str(period):
            return item
    return None


def resolve_result(chat_id, uid, pred_id, target_period):
    p = predictions.get(pred_id)
    if not p:
        return

    game = p.get("game")
    result = find_cached(game, target_period)

    if not result and game == "TRX":
        try:
            live = fetch_trx_history(20)
            result = next(
                (
                    x for x in live
                    if str(x.get("period", "")).strip() == target_period
                ),
                None,
            )
            if live:
                result_store["TRX"] = merge_daily_history(
                    "TRX", live, TRX_LIMIT
                )
                persist()
        except Exception:
            pass

    if not result and game == "WINGO":
        u = users.get(uid, {})
        token = u.get("sessionToken", "")
        header = u.get("sessionTokenHeader", "Bearer ")

        if token:
            try:
                fresh = fetch_history(header, token, "WINGO", 20)
                result = next(
                    (
                        x for x in fresh
                        if str(x.get("period", "")).strip() == target_period
                    ),
                    None,
                )
            except Exception:
                pass

    p["result"] = result
    persist()

    result_number = str(result["number"]) if result else "မရသေးပါ"
    status = p.get("status", "WIN")

    reply(
        chat_id,
        f"{icon('win' if status == 'WIN' else 'lose')} "
        f"<b>{status} မှတ်တင်ပြီးပါပြီ။</b>\n\n"
        f"Period: <code>{esc(result.get('period', target_period) if result else target_period)}</code>\n"
        f"Result Number: <b>{esc(result_number)}</b>\n\n"
        f"နောက်ပွဲအတွက် နံပါတ်နှစ်လုံးကို old → new 0,2 ပုံစံဖြင့် ထည့်ပါ။",
        main_keyboard(True, is_admin(uid)),
    )


# ============================================================
# BACKGROUND DATA
# ============================================================

def initial_history_for_login(token_header, token):
    try:
        w = fetch_history(token_header, token, "WINGO", WINGO_LIMIT)
        if w:
            result_store["WINGO"] = merge_daily_history(
                "WINGO", w, WINGO_LIMIT
            )

        t = fetch_trx_history(TRX_LIMIT)
        if t:
            result_store["TRX"] = merge_daily_history(
                "TRX", t, TRX_LIMIT
            )

        persist()
    except Exception as e:
        print("[DATA] initial history error:", e)


def refresh_wingo():
    # Use an available logged-in user session.
    for u in users.values():
        if u.get("sessionToken"):
            try:
                rows = fetch_history(
                    u.get("sessionTokenHeader", "Bearer "),
                    u.get("sessionToken"),
                    "WINGO",
                    10,
                )
                if rows:
                    result_store["WINGO"] = merge_daily_history(
                        "WINGO", rows, WINGO_LIMIT
                    )
                return
            except Exception:
                continue


def refresh_trx():
    try:
        rows = fetch_trx_history(10)
        if rows:
            result_store["TRX"] = merge_daily_history(
                "TRX", rows, TRX_LIMIT
            )
    except Exception:
        pass


def background_refresh(uid, game):
    try:
        refresh_wingo()
        refresh_trx()
        persist()
    except Exception:
        pass


def live_updater():
    while True:
        try:
            refresh_wingo()
            refresh_trx()
            persist()
        except Exception as e:
            print("[LIVE] updater:", e)
        time.sleep(UPDATE_INTERVAL)


# ============================================================
# START
# ============================================================

def validate_config():
    if not BOT_TOKEN or BOT_TOKEN.startswith("PUT_"):
        print("❌ BOT_TOKEN မထည့်ရသေးပါ။")
        return False

    if not ADMIN_CHAT_ID or ADMIN_CHAT_ID.startswith("PUT_"):
        print("❌ ADMIN_CHAT_ID မထည့်ရသေးပါ။")
        return False

    return True


if __name__ == "__main__":
    if not validate_config():
        raise SystemExit(1)

    persist()

    print("🤖 Kaiyo AI Predict Python Bot started.")
    print("📥 Background live updater started.")

    threading.Thread(
        target=live_updater,
        daemon=True,
    ).start()

    while True:
        try:
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                skip_pending=True,
            )
        except KeyboardInterrupt:
            persist()
            break
        except Exception as e:
            print("[TELEGRAM] polling error:", e)
            time.sleep(3)
