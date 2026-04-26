import os
import pytz
TIMEZONE = pytz.timezone("Asia/Amman")
import json
import asyncio
import httpx
from datetime import datetime, time
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
GEMINI_KEY = os.environ.get("GEMINI_KEY")
DATA_FILE = "entries.json"

async def classify_with_gemini(text):
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
        prompt = f"Classify this activity into exactly one category. Categories: productive (work, study, exercise, reading, learning, prayer, any useful activity) or waste (social media, excessive sleep, idle time, procrastination) or neutral (eating, normal rest, daily routine). Activity: {text}. Reply with one word only: productive or waste or neutral"
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={
                "contents": [{"parts": [{"text": prompt}]}]
            }, timeout=10)
            data = response.json()
            result = data["candidates"][0]["content"]["parts"][0]["text"].strip().lower()
            if "productive" in result:
                return "productive"
            elif "waste" in result:
                return "waste"
            else:
                return "neutral"
    except:
        return classify_fallback(text)

def classify_fallback(text):
    lower = text.lower()
    PRODUCTIVE = ["work","meeting","code","study","reading","project","exercise",
                  "writing","research","planning","email","call","gym","training",
                  "prayer","learn","practice","review","design","build"]
    WASTE = ["youtube","instagram","twitter","snapchat","tiktok","sleeping","gaming",
             "scroll","netflix","nothing","idle","procrastinate","wasting","bored",
             "social media","reels","shorts"]
    if any(k in lower for k in PRODUCTIVE):
        return "productive"
    if any(k in lower for k in WASTE):
        return "waste"
    return "neutral"

def load_entries():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_entries(entries):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

def clear_entries():
    save_entries([])

async def ask_checkin(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(TIMEZONE).strftime("%I:%M %p")
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=f"What are you doing right now? ({now})",
    )

async def send_report(context: ContextTypes.DEFAULT_TYPE):
    entries = load_entries()
    if not entries:
        await context.bot.send_message(chat_id=CHAT_ID, text="No entries for today.")
        return
    total = len(entries)
    productive = [e for e in entries if e["type"] == "productive"]
    waste = [e for e in entries if e["type"] == "waste"]
    neutral = [e for e in entries if e["type"] == "neutral"]
    prod_pct = round(len(productive) / total * 100)
    waste_pct = round(len(waste) / total * 100)
    neutral_pct = round(len(neutral) / total * 100)
    prod_hours = len(productive) * 0.5
    waste_hours = len(waste) * 0.5
    if prod_pct >= 70:
        verdict = "Strong day. Keep it up."
    elif prod_pct >= 50:
        verdict = "50/50. There is clear time leakage."
    elif prod_pct >= 30:
        verdict = "Productive time is less than half. Fix your priorities."
    else:
        verdict = "Day is gone. Start tomorrow with a different mindset."
    report = "Daily Report\n\n"
    report += f"Productive: {prod_pct}% - {prod_hours:.1f} hrs\n"
    report += f"Neutral: {neutral_pct}%\n"
    report += f"Wasted: {waste_pct}% - {waste_hours:.1f} hrs\n\n"
    report += "Details:\n"
    for e in entries:
        icon = "+" if e["type"] == "productive" else "-" if e["type"] == "waste" else "o"
        report += f"{icon} {e['time']} - {e['text']}\n"
    report += f"\n{verdict}"
    await context.bot.send_message(chat_id=CHAT_ID, text=report)
    clear_entries()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() in ["/start", "start"]:
        await update.message.reply_text(
            "Bot is running. Every 30 minutes I will ask what you are doing. Answer honestly. Use /report anytime to see your daily breakdown."
        )
        return
    if text.lower() in ["/report", "report"]:
        await send_report(context)
        return
    entry_type = await classify_with_gemini(text)
    now = datetime.now(TIMEZONE).strftime("%I:%M %p")
    entries = load_entries()
    entries.append({"time": now, "text": text, "type": entry_type})
    save_entries(entries)
    labels = {"productive": "Productive", "waste": "Wasted time", "neutral": "Neutral"}
    await update.message.reply_text(f"{labels[entry_type]} - Logged.")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", handle_message))
    app.add_handler(CommandHandler("report", handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    job_queue = app.job_queue
    job_queue.run_repeating(ask_checkin, interval=1800, first=10)
    job_queue.run_daily(send_report, time=time(hour=22, minute=0))
    print("Bot is running with Gemini AI...")
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
