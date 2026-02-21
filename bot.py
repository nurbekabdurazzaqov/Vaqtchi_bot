import sqlite3
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# TOKEN VA ID LAR
TOKEN = "7707636600:AAGMhVPyns29hOX3BRtpEj3bQQeUOo1GUwg"
OWNER_ID = 5351101319

# KARTALAR
VISA_CARD = "4916 9909 6190 2001"
HUMO_CARD = "9860 1001 2583 7540"
CARD_OWNER = "Nurbek Abdurazzoqov"

# NARXLAR
MONTHLY_PRICE = 49000
YEARLY_PRICE = 349000

# DATABASE
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER,
    plan TEXT,
    days INTEGER,
    price INTEGER,
    expire_date TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# START KOMANDASI
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💎 Oylik Premium", callback_data="monthly")],
        [InlineKeyboardButton("👑 Yillik Premium", callback_data="yearly")]
    ]
    await update.message.reply_text(
        f"💎 PREMIUM TARIFLAR\n\n"
        f"📅 Oylik: {MONTHLY_PRICE:,} so'm\n"
        f"👑 Yillik: {YEARLY_PRICE:,} so'm\n\n"
        f"Tarifni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# TARIF TANLASH
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
    
    cursor.execute("DELETE FROM payments WHERE admin_id=? AND status='pending'", (query.from_user.id,))
    
    cursor.execute("INSERT INTO payments (admin_id, plan, days, price) VALUES (?, ?, ?, ?)",
                  (query.from_user.id, plan, days, price))
    conn.commit()
    
    await query.edit_message_text(
        f"💳 TO'LOV MA'LUMOTI\n\n"
        f"Tarif: {plan}\n"
        f"Muddat: {days} kun\n"
        f"Summa: {price:,} so'm\n\n"
        f"💳 Kartalar:\n"
        f"Visa: {VISA_CARD}\n"
        f"Humo: {HUMO_CARD}\n"
        f"Karta egasi: {CARD_OWNER}\n\n"
        f"To'lovdan so'ng screenshot yuboring."
    )

# SCREENSHOT QABUL QILISH
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    cursor.execute("SELECT plan, days, price FROM payments WHERE admin_id=? AND status='pending'", (user_id,))
    payment = cursor.fetchone()
    
    if payment:
        plan, days, price = payment
        keyboard = [[InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{user_id}_{days}_{price}")]]
        
        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"💰 To'lov keldi\nAdmin: {user_id}\nTarif: {plan}\nSumma: {price:,} so'm",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await update.message.reply_text("⌛ To'lov tekshirilmoqda...")
    else:
        await update.message.reply_text("❌ Sizda kutilayotgan to'lov yo'q")

# TASDIQLASH
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != OWNER_ID:
        await query.edit_message_caption("❌ Siz tasdiqlay olmaysiz")
        return
    
    data = query.data.split("_")
    admin_id = int(data[1])
    days = int(data[2])
    price = int(data[3])
    
    expire = datetime.now() + timedelta(days=days)
    
    cursor.execute("UPDATE payments SET status='approved', expire_date=? WHERE admin_id=? AND status='pending'",
                  (expire.strftime("%Y-%m-%d %H:%M:%S"), admin_id))
    conn.commit()
    
    await context.bot.send_message(
        chat_id=admin_id,
        text=f"✅ Premium {days} kun aktiv qilindi!\n📅 Tugash sanasi: {expire.strftime('%d.%m.%Y')}"
    )
    await query.edit_message_caption("✅ Tasdiqlandi")

# STATISTIKA
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    
    cursor.execute("SELECT COALESCE(SUM(price), 0) FROM payments WHERE status='approved'")
    total_income = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT admin_id) FROM payments WHERE status='approved'")
    active_users = cursor.fetchone()[0]
    
    await update.message.reply_text(
        f"📊 STATISTIKA\n\n"
        f"💰 Umumiy daromad: {total_income:,} so'm\n"
        f"👥 Faol premiumlar: {active_users} ta"
    )

# MUDDAT TEKSHIRISH
async def check_expire(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    
    cursor.execute("SELECT admin_id, expire_date FROM payments WHERE status='approved' AND expire_date IS NOT NULL")
    rows = cursor.fetchall()
    
    for admin_id, expire_date in rows:
        try:
            expire_time = datetime.strptime(expire_date, "%Y-%m-%d %H:%M:%S")
            
            if now >= expire_time:
                cursor.execute("UPDATE payments SET status='expired' WHERE admin_id=?", (admin_id,))
                conn.commit()
                await context.bot.send_message(chat_id=admin_id, text="❌ Premium muddati tugadi!")
        except:
            pass

# ASOSIY FUNKSIYA
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(plan_handler, pattern="^(monthly|yearly)$"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(approve, pattern="^approve_"))
    
    job_queue = app.job_queue
    job_queue.run_repeating(check_expire, interval=86400, first=10)
    
    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
