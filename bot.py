import sqlite3
import os
import logging
import asyncio
import sys
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import InvalidToken

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# TOKENLAR - MUHIM! To'g'ridan-to'g'ri yozamiz
TOKEN = "8593303902:AAGMhVPyns29h0X3BRtpF3h0nal1Qllw"
OWNER_ID = 5351101319

logger.info(f"📌 Token: {TOKEN[:10]}...")
logger.info(f"📌 Owner ID: {OWNER_ID}")

# KARTALAR
VISA_CARD = "4916 9909 6190 2001"
HUMO_CARD = "9860 1001 2583 7540"
CARD_OWNER = "Nurbek Abdurazzoqov"

# NARXLAR
MONTHLY_PRICE = 49000
YEARLY_PRICE = 349000

# DATABASE
logger.info("📁 Database ulanyapti...")
try:
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
except Exception as e:
    logger.error(f"❌ Database xatolik: {e}")

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"👤 /start: {user.id}")
    
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
    
    logger.info(f"👤 Tarif: {user.id} - {query.data}")
    
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
        f"💳 Karta:\n"
        f"Visa: {VISA_CARD}\n"
        f"Humo: {HUMO_CARD}\n"
        f"👤 Egasi: {CARD_OWNER}\n\n"
        f"📸 To'lov screenshotini yuboring!"
    )

# FOTO
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📸 Screenshot: {user.id}")
    
    cursor.execute("SELECT plan, days, price FROM payments WHERE admin_id=? AND status='pending'", (user.id,))
    payment = cursor.fetchone()
    
    if payment:
        plan, days, price = payment
        keyboard = [[InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve_{user.id}_{days}_{price}")]]
        
        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"💰 To'lov\n👤 ID: {user.id}\n📌 {plan}\n💰 {price:,} so'm",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await update.message.reply_text("✅ To'lov qabul qilindi! Admin tekshiryapti.")
    else:
        await update.message.reply_text("❌ Kutilayotgan to'lov yo'q")

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
        text=f"✅ Premium {days} kun aktiv!\n📅 Tugash: {expire}"
    )
    await query.edit_message_caption("✅ Tasdiqlandi!")

# STATISTIKA
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    
    cursor.execute("SELECT COUNT(*), SUM(price) FROM payments WHERE status='approved'")
    count, total = cursor.fetchone()
    total = total or 0
    
    await update.message.reply_text(
        f"📊 STATISTIKA\n\n"
        f"👥 Faol: {count}\n"
        f"💰 Daromad: {total:,} so'm"
    )

# ASOSIY FUNKSIYA
def main():
    """Botni ishga tushirish"""
    try:
        logger.info("🤖 Bot ishga tushyapti...")
        
        # Application yaratish
        app = Application.builder().token(TOKEN).build()
        logger.info("✅ Application yaratildi")
        
        # Handlerlar
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("stats", stats))
        app.add_handler(CallbackQueryHandler(plan_handler, pattern="^(monthly|yearly)$"))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        app.add_handler(CallbackQueryHandler(approve, pattern="^approve_"))
        logger.info("✅ Handlerlar qo'shildi")
        
        # Pollingni boshlash
        logger.info("🚀 Bot polling ishga tushmoqda...")
        app.run_polling()
        
    except InvalidToken:
        logger.error("❌ TOKEN XATO! Bot token noto'g'ri!")
        logger.error(f"Token: {TOKEN}")
    except Exception as e:
        logger.error(f"❌ Bot xatolik: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    logger.info("🚀 Bot moduli ishga tushdi!")
    main()
