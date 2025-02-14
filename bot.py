import logging
import json
import os
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Set up logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)

# File for storing break data
BREAKS_FILE = "breaks.json"

# Global Config
BREAK_LIMITS = {"Toilet": 2, "Drinking": 2, "Shop": 2, "Smoke": 2}
BREAK_DURATION = 15  # minutes

# Load data
def load_breaks():
    if not os.path.exists(BREAKS_FILE):
        return {}
    with open(BREAKS_FILE, "r") as f:
        return json.load(f)

# Save data
def save_breaks(data):
    with open(BREAKS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Start Break
async def start_break(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Toilet", callback_data="Toilet")],
        [InlineKeyboardButton("Drinking", callback_data="Drinking")],
        [InlineKeyboardButton("Shop", callback_data="Shop")],
        [InlineKeyboardButton("Smoke", callback_data="Smoke")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select your break type:", reply_markup=reply_markup)

# Handle Break Selection
async def handle_break_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    break_type = query.data
    now = datetime.datetime.now()

    breaks = load_breaks()

    # Check if user already has an active break
    if user_id in breaks and breaks[user_id]["status"] == "ongoing":
        await query.message.reply_text("❌ You must end your current break first.")
        return

    # Check if break limit is reached
    active_breaks = [b for b in breaks.values() if b["break_type"] == break_type and b["status"] == "ongoing"]
    if len(active_breaks) >= BREAK_LIMITS[break_type]:
        await query.message.reply_text(f"❌ Only {BREAK_LIMITS[break_type]} people can take a {break_type} break at once.")
        return

    # Start the break
    breaks[user_id] = {
        "break_type": break_type,
        "start_time": now.isoformat(),
        "status": "ongoing",
        "overtime": 0
    }
    save_breaks(breaks)

    keyboard = [[InlineKeyboardButton("End Break", callback_data="end_break")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(f"✅ Your {break_type} break has started.\nClick below to end it.", reply_markup=reply_markup)

# End Break
async def end_break(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    breaks = load_breaks()
    if user_id not in breaks or breaks[user_id]["status"] != "ongoing":
        await query.message.reply_text("❌ You have no active break.")
        return

    now = datetime.datetime.now()
    start_time = datetime.datetime.fromisoformat(breaks[user_id]["start_time"])
    duration = (now - start_time).total_seconds() / 60

    overtime = int(duration - BREAK_DURATION) if duration > BREAK_DURATION else 0
    breaks[user_id]["status"] = "ended"
    breaks[user_id]["end_time"] = now.isoformat()
    breaks[user_id]["overtime"] = overtime
    save_breaks(breaks)

    fine_message = f"⚠️ You exceeded the break limit by {overtime} minutes. Fine: 100PKR pending admin review." if overtime else "✅ No fine."
    await query.message.reply_text(f"✅ Break ended. Duration: {int(duration)} minutes.\n{fine_message}")

# Show Current Breaks
async def break_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    breaks = load_breaks()
    active_breaks = {uid: data for uid, data in breaks.items() if data["status"] == "ongoing"}

    if not active_breaks:
        await update.message.reply_text("No active breaks.")
        return

    msg = "📋 *Current Breaks:*\n"
    for uid, data in active_breaks.items():
        start_time = datetime.datetime.fromisoformat(data["start_time"]).strftime("%H:%M")
        msg += f"👤 {uid} - {data['break_type']} (Started: {start_time})\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

# Show Break History
async def break_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    breaks = load_breaks()
    user_breaks = [data for uid, data in breaks.items() if uid == user_id]

    if not user_breaks:
        await update.message.reply_text("You have no break history.")
        return

    msg = "📜 *Your Last Breaks:*\n"
    for data in user_breaks[-5:]:  # Show last 5 breaks
        start_time = datetime.datetime.fromisoformat(data["start_time"]).strftime("%d-%m %H:%M")
        end_time = datetime.datetime.fromisoformat(data["end_time"]).strftime("%H:%M") if "end_time" in data else "Ongoing"
        duration = f"{int((datetime.datetime.fromisoformat(data['end_time']) - datetime.datetime.fromisoformat(data['start_time'])).total_seconds() / 60)} min" if "end_time" in data else "Ongoing"
        msg += f"🔹 {data['break_type']} | {start_time}-{end_time} | {duration}\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

# Command Handlers
def main():
    bot_token = "7695331037:AAGXq8STSEryfiKCak9Igtaa5zcoElbN2yU"
    app = Application.builder().token(bot_token).build()

    app.add_handler(CommandHandler("break", start_break))
    app.add_handler(CommandHandler("breakstatus", break_status))
    app.add_handler(CommandHandler("breakhistory", break_history))
    app.add_handler(CallbackQueryHandler(handle_break_selection, pattern="^(Toilet|Drinking|Shop|Smoke)$"))
    app.add_handler(CallbackQueryHandler(end_break, pattern="^end_break$"))

    logging.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
