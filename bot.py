import os
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CallbackQueryHandler, CommandHandler
import asyncio

TOKEN = os.getenv ("TOKEN")

conn = sqlite3.connect("members.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS members (
    admin_id INTEGER,
    chat_id INTEGER,
    user_id INTEGER,
    expire_date TEXT,
    type TEXT,
    status TEXT,
    PRIMARY KEY(admin_id, chat_id, user_id)
)
""")
conn.commit()

# Asosiy bo‘lim tugmalari
def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📌 Free 1-5 kun", callback_data="free_section")],
        [InlineKeyboardButton("📌 Premium 5-30 kun", callback_data="premium_section")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Kunlar tugmalari
def get_days_keyboard(section):
    if section == "free":
        keyboard = [
            [InlineKeyboardButton(f"{i} kun", callback_data=f"free_{i}") for i in range(1,6)]
        ]
    else:  # premium
        keyboard = [
            [InlineKeyboardButton(f"{i} kun", callback_data=f"premium_{i}") for i in [5,10,15,20,25,30]]
        ]
    return InlineKeyboardMarkup(keyboard)

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! Quyidagi 2 bo‘limdan birini tanlang:\n\n"
        "1️⃣ Free 1-5 kun – sinov uchun, bepul ishlaydi, foydalanuvchilar 1–5 kun kuzatiladi va avtomatik chiqariladi.\n"
        "2️⃣ Premium 5-30 kun – to‘lov asosida ishlaydi, foydalanuvchilar tanlangan muddat davomida kuzatiladi, to‘lovdan so‘ng admin tasdiqlaydi.",
        reply_markup=get_main_menu()
    )

# Callback tugmalar ishlashi
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    admin_id = query.from_user.id
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    data = query.data

    # Bo‘lim tanlash
    if data in ["free_section", "premium_section"]:
        section = "free" if data=="free_section" else "premium"
        if section == "free":
            text = ("🆓 Free bo‘limini tanladingiz.\n\n"
                    "✅ 1–5 kun bepul sinov\n"
                    "✅ Foydalanuvchilar muddat tugagach avtomatik chiqariladi\n"
                    "⏳ Kunlar tanlash uchun quyidagi tugmalardan birini bosing:")
        else:
            text = ("💎 Premium bo‘limini tanladingiz.\n\n"
                    "✅ 5–30 kun tanlash mumkin\n"
                    "✅ To‘lov qilish kerak (Uzcard / Humo)\n"
                    "💳 Uzcard: 8600xxxxxx\n"
                    "💳 Humo: 9860xxxxxx\n"
                    "⏳ Kunlar tanlash uchun quyidagi tugmalardan birini bosing:")

        await query.edit_message_text(
            text,
            reply_markup=get_days_keyboard(section)
        )
        return

    # Kun tanlash
    if data.startswith("free"):
        days = int(data.split("_")[1])
        expire_date = datetime.now() + timedelta(days=days)
        type_user = "free"
        await query.edit_message_text(f"🆓 Free {days} kun muvaffaqiyatli boshlanadi!\nFoydalanuvchilar {days} kun kuzatiladi va avtomatik chiqariladi.")
    elif data.startswith("premium"):
        days = int(data.split("_")[1])
        expire_date = datetime.now() + timedelta(days=days)
        type_user = "premium"
        await query.edit_message_text(
            f"💎 Premium {days} kun tanlandi.\n"
            f"To‘lov qilgandan so‘ng /approve buyruq bilan tasdiqlang.\n"
            f"💳 Uzcard: 8600xxxxxx\n"
            f"💳 Humo: 9860xxxxxx"
        )

    # Database saqlash
    cursor.execute(
        "INSERT OR REPLACE INTO members VALUES (?, ?, ?, ?, ?, ?)",
        (admin_id, chat_id, user_id, expire_date.isoformat(), type_user, "active")
    )
    conn.commit()

# Foydalanuvchilarni tekshirish (avtomatik chiqarish)
async def check_members(app):
    while True:
        cursor.execute("SELECT admin_id, chat_id, user_id, expire_date FROM members WHERE status='active'")
        rows = cursor.fetchall()
        for admin_id, chat_id, user_id, expire_date in rows:
            if datetime.now() > datetime.fromisoformat(expire_date):
                try:
                    await app.bot.ban_chat_member(chat_id, user_id)
                    await app.bot.unban_chat_member(chat_id, user_id)
                    cursor.execute(
                        "UPDATE members SET status='removed' WHERE admin_id=? AND chat_id=? AND user_id=?",
                        (admin_id, chat_id, user_id)
                    )
                    conn.commit()
                except:
                    pass
        await asyncio.sleep(3600)

# Admin tasdiqlash komandasi
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 3:
        await update.message.reply_text("/approve admin_id chat_id kunlar")
        return
    admin_id = int(context.args[0])
    chat_id = int(context.args[1])
    days = int(context.args[2])
    expire_date = datetime.now() + timedelta(days=days)

    cursor.execute(
        "UPDATE members SET expire_date=?, type='premium', status='active' WHERE admin_id=? AND chat_id=?",
        (expire_date.isoformat(), admin_id, chat_id)
    )
    conn.commit()
    await update.message.reply_text(f"✅ Admin {admin_id} uchun {days} kun premium tasdiqlandi!")

# Asosiy ishga tushirish
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(CommandHandler("approve", approve))
    asyncio.create_task(check_members(app))
    await app.run_polling()

asyncio.run(main())
