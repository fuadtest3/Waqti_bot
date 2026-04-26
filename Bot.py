import os
import json
import asyncio
from datetime import datetime, time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
DATA_FILE = "entries.json"

PRODUCTIVE_KEYWORDS = [
    "شغل", "اجتماع", "ميتنق", "كود", "برمجة", "دراسة", "قراءة", "تعلم", "مشروع",
    "تقرير", "ايميل", "بريد", "تصميم", "كتابة", "بحث", "تخطيط", "تدريب", "رياضة",
    "work", "meeting", "code", "study", "reading", "project", "report", "design",
    "writing", "research", "planning", "email", "call", "exercise", "gym", "gym"
]

WASTE_KEYWORDS = [
    "يوتيوب", "انستا", "تويتر", "سناب", "تيك توك", "نايم", "نوم", "يلعب", "لعب",
    "سوشيال", "نتفلكس", "يتصفح", "تصفح", "بطال", "مافي شي", "لا شي", "استراحه", "استراحة",
    "youtube", "instagram", "twitter", "snapchat", "tiktok", "sleeping", "gaming",
    "scroll", "netflix", "nothing", "idle"
]

def classify(text):
    lower = text.lower()
    productive = any(k in lower for k in PRODUCTIVE_KEYWORDS)
    waste = any(k in lower for k in WASTE_KEYWORDS)
    if productive and not waste:
        return "productive"
    if waste and not productive:
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
    now = datetime.now().strftime("%I:%M %p")
    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=f"⏱ *{now}*\n\nالحين بالضبط — وش تسوي؟",
        parse_mode="Markdown"
    )

async def send_report(context: ContextTypes.DEFAULT_TYPE):
    entries = load_entries()
    if not entries:
        await context.bot.send_message(chat_id=CHAT_ID, text="📭 ما في سجلات اليوم.")
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
        verdict = "🔥 يوم قوي. استمر."
    elif prod_pct >= 50:
        verdict = "⚡ نص ونص. فيه تسرب واضح، راجع وقتك."
    elif prod_pct >= 30:
        verdict = "⚠️ الوقت المنتج أقل من النص. لازم تعيد الأولويات."
    else:
        verdict = "🛑 اليوم راح. ابدأ بكرة بنية مختلفة."

    report = f"""📊 *تقرير اليوم*

✅ منتج: {prod_pct}% — {prod_hours:.1f} ساعة
🟡 محايد: {neutral_pct}%
❌ ضياع: {waste_pct}% — {waste_hours:.1f} ساعة

*التفاصيل:*
"""
    for e in entries:
        icon = "✅" if e["type"] == "productive" else "❌" if e["type"] == "waste" else "🟡"
        report += f"{icon} {e['time']} — {e['text']}\n"

    report += f"\n{verdict}"

    await context.bot.send_message(chat_id=CHAT_ID, text=report, parse_mode="Markdown")
    clear_entries()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.lower() in ["/start", "start", "ابدأ"]:
        await update.message.reply_text(
            "👋 أهلاً! البوت شغال.\n\nكل نص ساعة راح يسألك وش تسوي.\nجاوب بصدق — بآخر اليوم تشوف تقريرك.\n\n/report — لو تبي التقرير الحين"
        )
        return

    if text.lower() in ["/report", "تقرير", "report"]:
        await send_report(context)
        return

    entry_type = classify(text)
    now = datetime.now().strftime("%I:%M %p")

    entries = load_entries()
    entries.append({"time": now, "text": text, "type": entry_type})
    save_entries(entries)

    icons = {"productive": "✅", "waste": "❌", "neutral": "🟡"}
    labels = {"productive": "منتج", "waste": "ضياع وقت", "neutral": "محايد"}

    await update.message.reply_text(
        f"{icons[entry_type]} *{labels[entry_type]}* — تم التسجيل",
        parse_mode="Markdown"
    )

async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", handle_message))
    app.add_handler(CommandHandler("report", handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Schedule check-ins every 30 minutes
    job_queue = app.job_queue
    job_queue.run_repeating(ask_checkin, interval=1800, first=10)

    # Daily report at 10 PM
    job_queue.run_daily(send_report, time=time(hour=22, minute=0))

    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
