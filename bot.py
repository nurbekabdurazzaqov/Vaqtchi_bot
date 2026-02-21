import sqlite3
import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# TOKENLAR
TOKEN = os.environ.get("TELEGRAM_TOKEN", "7707636600:AAGMhVPyns29hOX3BRtpEj3bQQeUOo1GUwg")
OWNER_ID = int(os.environ.get("OWNER_ID", "5351101319"))

# KARTALAR
VISA_CARD = "4916 9909 6190 2001"
HUMO_CARD = "9860 1001 2583 7540"
CARD_OWNER = "Nurbek Abdurazzoqov"

# NARXLAR
MONTHLY_PRICE = 49000
YEARLY_PRICE = 349000

# DATABASE
logger.info("📁 Database ulanyapti...")
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER,
    plan TEXT,
    days INTEGER,
    price INTEGER,
    expire_date TEXT,
    status TEXT DEFAULT 'pending'
)""")
conn.commit()
logger.info("✅ Database tayyor")

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"👤 /start komandasi: {user.id} ({user.first_name})")
    
    keyboard = [
        [InlineKeyboardButton("💎 Oylik Premium", callback_data="monthly")],
        [InlineKeyboardButton("👑 Yillik Premium", callback_data="yearly")]
    ]
    await update.message.reply_text(
        f"💎 TARIFLAR\n\n"
        f"📅 Oylik: {MONTHLY_PRICE:,} so'm\n"
        f"👑 Yillik: {YEARLY_PRICE:,} so'm\n\n"
        f"Kerakli tarifni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# TANLASH
async def plan_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    logger.info(f"👤 Tarif tanlandi: {user.id} - {query.data}")
    
    if query.data == "monthly":
        plan, days, price = "Oylik", 30, MONTHLY_PRICE
    else:
        plan, days, price = "Yillik", 365, YEARLY_PRICE
    
    cursor.execute("DELETE FROM payments WHERE admin_id=? AND status='pending'", (user.id,))
    cursor.execute("INSERT INTO payments (admin_id, plan, days, price) VALUES (?,?,?,?)",
                  (user.id, plan, days, price))
    conn.commit()
    
    await query.edit_message_text(
        f"💳 TO'LOV MA'LUMOTLARI\n\n"
        f"📌 Tarif: {plan}\n"
        f"💰 Summa: {price:,} so'm\n\n"
        f"💳 Karta raqamlari:\n"
        f"Visa: {VISA_CARD}\n"
        f"Humo: {HUMO_CARD}\n"
        f"👤 Karta egasi: {CARD_OWNER}\n\n"
        f"📸 To'lov qilgandan so'ng screenshot yuboring!"
    )

# FOTO
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📸 Screenshot keldi: {user.id}")
    
    cursor.execute("SELECT plan, days, price FROM payments WHERE admin_id=? AND status='pending'", (user.id,))
    payment = cursor.fetchone()
    
    if payment:
        plan, days, price = payment
        keyboard = [[InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{user.id}_{days}_{price}")]]
        
        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"💰 To'lov tekshiruvi\n"
                   f"👤 Foydalanuvchi: {user.id}\n"
                   f"📌 Tarif: {plan}\n"
                   f"💰 Summa: {price:,} so'm",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await update.message.reply_text("✅ To'lov qabul qilindi! Admin tekshiryapti.")
    else:
        await update.message.reply_text("❌ Sizda kutilayotgan to'lov yo'q")

# TASDIQLASH
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != OWNER_ID:
        await query.edit_message_caption("❌ Siz admin emassiz!")
        return
    
    data = query.data.split("_")
    admin_id, days = int(data[1]), int(data[2])
    expire = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    
    cursor.execute("UPDATE payments SET status='approved', expire_date=? WHERE admin_id=?", (expire, admin_id))
    conn.commit()
    
    await context.bot.send_message(
        chat_id=admin_id,
        text=f"✅ Premium {days} kun aktiv qilindi!\n📅 Tugash sanasi: {expire}"
    )
    await query.edit_message_caption("✅ To'lov tasdiqlandi!")

# STATISTIKA
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    
    cursor.execute("SELECT COUNT(*), SUM(price) FROM payments WHERE status='approved'")
    count, total = cursor.fetchone()
    total = total or 0
    
    await update.message.reply_text(
        f"📊 STATISTIKA\n\n"
        f"👥 Faol foydalanuvchilar: {count}\n"
        f"💰 Umumiy daromad: {total:,} so'm"
    )

# ASOSIY FUNKSIYA
def main():
    logger.info("🤖 Bot ishga tushyapti...")
    
    try:
        # Bot app ni yaratish
        app = Application.builder().token(TOKEN).build()
        
        # Handlerlarni qo'shish
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("stats", stats))
        app.add_handler(CallbackQueryHandler(plan_handler, pattern="^(monthly|yearly)$"))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(CallbackQueryHandler(approve, pattern="^approve_"))
        
        logger.info(f"✅ Token tekshirildi: {TOKEN[:10]}...")
        logger.info("✅ Handlerlar qo'shildi")
        logger.info("🚀 Bot polling ishga tushdi!")
        
        # Botni ishga tushirish
        app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Bot xatolik: {e}")
        raise e

if __name__ == "__main__":
    main()
