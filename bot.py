import os
import sqlite3
from datetime import datetime, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

TOKEN = os.getenv("TOKEN")
OWNER_ID = 5351101319

# ================= NARXLAR =================
MONTHLY_PRICE = 49000
YEARLY_PRICE = 349000

# ================= DATABASE =================
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    admin_id INTEGER,
    plan TEXT,
    days INTEGER,
    price INTEGER,
    expire_date TEXT,
    status TEXT
)
""")
conn.commit()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💎 Oylik Premium", callback_data="monthly")],
        [InlineKeyboardButton("👑 Yillik Premium", callback_data="yearly")]
    ]

    await update.message.reply_text(
        f"💎 PREMIUM TARIFLAR\n\n"
        f"📅 Oylik: {MONTHLY_PRICE:,} so‘m\n"
        f"👑 Yillik: {YEARLY_PRICE:,} so‘m\n\n"
        f"Tarifni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= PLAN TANLASH =================
async def plan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "monthly":
        plan = "Oylik"
        days = 30
        price = MONTHLY_PRICE

    else:
        plan = "Yillik"
        days = 365
        price = YEARLY_PRICE

    cursor.execute(
        "INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?)",
        (query.from_user.id, plan, days, price, None, "pending")
    )
    conn.commit()

    await query.edit_message_text(
        f"💳 TO‘LOV MA’LUMOTI\n\n"
        f"Tarif: {plan}\n"
        f"Muddat: {days} kun\n"
        f"Summa: {price:,} so‘m\n\n"
        f"💳 Kartalar:\n"
        f"Visa: 4916 9909 6190 2001\n"
        f"Humo: 9860 1001 2583 7540\n"
        f"Karta egasi: Nurbek Abdurazzoqov\n\n"
        f"To‘lovdan so‘ng screenshot yuboring."
    )

# ================= SCREENSHOT QABUL =================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    cursor.execute(
        "SELECT plan, days, price FROM payments WHERE admin_id=? AND status='pending'",
        (user_id,)
    )
    payment = cursor.fetchone()

    if payment:
        plan, days, price = payment

        keyboard = [[
            InlineKeyboardButton(
                "✅ Tasdiqlash",
                callback_data=f"approve_{user_id}_{days}_{price}"
            )
        ]]

        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"💰 To‘lov keldi\nAdmin: {user_id}\nTarif: {plan}\nSumma: {price:,}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await update.message.reply_text("⌛ To‘lov tekshirilmoqda...")

# ================= TASDIQLASH =================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")
    admin_id = int(data[1])
    days = int(data[2])
    price = int(data[3])

    expire = datetime.now() + timedelta(days=days)

    cursor.execute("""
        UPDATE payments
        SET status='approved',
            expire_date=?
        WHERE admin_id=? AND status='pending'
    """, (expire.strftime("%Y-%m-%d %H:%M:%S"), admin_id))
    conn.commit()

    await context.bot.send_message(
        chat_id=admin_id,
        text=f"✅ Premium {days} kun aktiv qilindi!\n\n📅 Tugash sanasi: {expire.date()}"
    )

    await query.edit_message_caption("✅ Tasdiqlandi")

# ================= STATISTIKA =================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    cursor.execute("SELECT SUM(price) FROM payments WHERE status='approved'")
    total_income = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM payments WHERE status='approved'")
    active_users = cursor.fetchone()[0]

    cursor.execute("""
        SELECT SUM(price) FROM payments
        WHERE status='approved'
        AND strftime('%m', expire_date)=strftime('%m','now')
    """)
    monthly_income = cursor.fetchone()[0] or 0

    await update.message.reply_text(
        f"📊 STATISTIKA\n\n"
        f"💰 Umumiy daromad: {total_income:,} so‘m\n"
        f"📅 Shu oy daromad: {monthly_income:,} so‘m\n"
        f"👥 Faol premiumlar: {active_users} ta"
    )

# ================= EXPIRE CHECK =================
async def check_expire(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()

    cursor.execute("""
        SELECT admin_id, expire_date FROM payments
        WHERE status='approved'
    """)
    rows = cursor.fetchall()

    for admin_id, expire_date in rows:
        expire_time = datetime.strptime(expire_date, "%Y-%m-%d %H:%M:%S")

        # 3 kun oldin eslatma
        if expire_time - now <= timedelta(days=3) and expire_time > now:
            await context.bot.send_message(
                chat_id=admin_id,
                text="⚠️ Premium muddati 3 kundan so‘ng tugaydi."
            )

        # Tugagan bo‘lsa
        if now >= expire_time:
            cursor.execute("""
                UPDATE payments
                SET status='expired'
                WHERE admin_id=?
            """, (admin_id,))
            conn.commit()

            await context.bot.send_message(
                chat_id=admin_id,
                text="❌ Premium muddati tugadi."
            )

# ================= MAIN =================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(plan_handler, pattern="^(monthly|yearly)$"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(approve, pattern="^approve_"))

    app.job_queue.run_repeating(check_expire, interval=86400, first=10)

    app.run_polling()

if __name__ == "__main__":
    main()
