import os
import pytz
TIMEZONE = pytz.timezone(“Asia/Amman”)

import json
import asyncio
import httpx
from datetime import datetime, time
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

TOKEN = os.environ.get(“BOT_TOKEN”)
CHAT_ID = int(os.environ.get(“CHAT_ID”))
GEMINI_KEY = os.environ.get(“GEMINI_KEY”)
DATA_FILE = “entries.json”

async def classify_with_gemini(text):
try:
url = f”https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}”
prompt = f””“صنّف هذا النشاط في فئة واحدة فقط:

- منتج: شغل، دراسة، رياضة، قراءة، تعلم، صلاة، أي نشاط مفيد
- ضياع: سوشيال ميديا، نوم زيادة، فراغ، تسويف
- محايد: أكل، استراحة عادية، أنشطة يومية طبيعية

النشاط: “{text}”

رد بكلمة واحدة فقط: منتج أو ضياع أو محايد”””

```
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json={
            "contents": [{"parts": [{"text": prompt}]}]
        }, timeout=10)
        data = response.json()
        result = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if "منتج" in result:
            return "productive"
        elif "ضياع" in result:
            return "waste"
        else:
            return "neutral"
except:
    return classify_fallback(text)
```

def classify_fallback(text):
lower = text.lower()
PRODUCTIVE = [“شغل”,“اجتماع”,“كود”,“برمجة”,“دراسة”,“قراءة”,“تعلم”,“مشروع”,
“تقرير”,“تصميم”,“كتابة”,“بحث”,“تخطيط”,“تدريب”,“رياضة”,
“اشتغل”,“ذاكر”,“حضرت”,“راجعت”,“كتبت”,“انجزت”,“خلصت”,
“صلي”,“صلاة”,“صليت”,“بصلي”,
“work”,“meeting”,“code”,“study”,“reading”,“project”,“exercise”]
WASTE = [“يوتيوب”,“انستا”,“تويتر”,“سناب”,“تيك توك”,“نايم”,“نوم”,
“يلعب”,“لعب”,“سوشيال”,“نتفلكس”,“يتصفح”,“تصفح”,
“بطال”,“مافي شي”,“لا شي”,“ما بسوي شي”,“فاضي”,“عاطل”,
“جالس بس”,“قاعد بس”,“موبايل”,“ريلز”,“شورتس”,
“youtube”,“instagram”,“twitter”,“tiktok”,“gaming”,“scroll”,“netflix”]
if any(k in lower for k in PRODUCTIVE):
return “productive”
if any(k in lower for k in WASTE):
return “waste”
return “neutral”

def load_entries():
if os.path.exists(DATA_FILE):
with open(DATA_FILE, “r”, encoding=“utf-8”) as f:
return json.load(f)
return []

def save_entries(entries):
with open(DATA_FILE, “w”, encoding=“utf-8”) as f:
json.dump(entries, f, ensure_ascii=False, indent=2)

def clear_entries():
save_entries([])

async def ask_checkin(context: ContextTypes.DEFAULT_TYPE):
now = datetime.now(TIMEZONE).strftime(”%I:%M %p”)
await context.bot.send_message(
chat_id=CHAT_ID,
text=f”⏱ *{now}*\n\nالحين بالضبط — وش تسوي؟”,
parse_mode=“Markdown”
)

async def send_report(context: ContextTypes.DEFAULT_TYPE):
entries = load_entries()
if not entries:
await context.bot.send_message(chat_id=CHAT_ID, text=“📭 ما في سجلات اليوم.”)
return

```
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
    verdict = "⚡ نص ونص. فيه تسرب واضح."
elif prod_pct >= 30:
    verdict = "⚠️ الوقت المنتج أقل من النص."
else:
    verdict = "🛑 اليوم راح. ابدأ بكرة بنية مختلفة."

report = f"📊 *تقرير اليوم*\n\n"
report += f"✅ منتج: {prod_pct}% — {prod_hours:.1f} ساعة\n"
report += f"🟡 محايد: {neutral_pct}%\n"
report += f"❌ ضياع: {waste_pct}% — {waste_hours:.1f} ساعة\n\n"
report += f"*التفاصيل:*\n"

for e in entries:
    icon = "✅" if e["type"] == "productive" else "❌" if e["type"] == "waste" else "🟡"
    report += f"{icon} {e['time']} — {e['text']}\n"

report += f"\n{verdict}"

await context.bot.send_message(chat_id=CHAT_ID, text=report, parse_mode="Markdown")
clear_entries()
```

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
text = update.message.text.strip()

```
if text.lower() in ["/start", "start", "ابدأ"]:
    await update.message.reply_text(
        "👋 أهلاً! البوت شغال.\n\nكل نص ساعة راح يسألك وش تسوي.\nجاوب بصدق — بآخر اليوم تشوف تقريرك.\n\n/report — لو تبي التقرير الحين"
    )
    return

if text.lower() in ["/report", "تقرير", "report"]:
    await send_report(context)
    return

entry_type = await classify_with_gemini(text)
now = datetime.now(TIMEZONE).strftime("%I:%M %p")

entries = load_entries()
entries.append({"time": now, "text": text, "type": entry_type})
save_entries(entries)

icons = {"productive": "✅", "waste": "❌", "neutral": "🟡"}
labels = {"productive": "منتج", "waste": "ضياع وقت", "neutral": "محايد"}

await update.message.reply_text(
    f"{icons[entry_type]} *{labels[entry_type]}* — تم التسجيل",
    parse_mode="Markdown"
)
```

async def main():
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler(“start”, handle_message))
app.add_handler(CommandHandler(“report”, handle_message))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

```
job_queue = app.job_queue
job_queue.run_repeating(ask_checkin, interval=1800, first=10)
job_queue.run_daily(send_report, time=time(hour=22, minute=0))

print("Bot is running with Gemini AI...")
await app.run_polling()
```

if **name** == “**main**”:
import nest_asyncio
nest_asyncio.apply()
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
