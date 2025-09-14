import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import json
import os

# Bot konfiguratsiyasi
BOT_TOKEN = "8075883424:AAG_YIGTkefoBY60AHoCl5rNUUU3tF3cVx4"  # Bot tokeningizni bu yerga kiriting
ADMIN_CHAT_ID = 8113300476  # Admin chat ID sini bu yerga kiriting
CHANNEL_USERNAME = "@Frontend_dasturchilar_jamoasi"  # Kanal username ini bu yerga kiriting (@ bilan)
CHANNEL_ID = -1002910135551  # Kanal ID sini bu yerga kiriting

# Ma'lumotlar saqlash uchun fayl
DATA_FILE = "bot_data.json"

# Logging sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ma'lumotlarni yuklash
def load_data():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"videos": {}, "admin_states": {}}

# Ma'lumotlarni saqlash
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Global ma'lumotlar
bot_data = load_data()

# Foydalanuvchi kanalga obuna bo'lganligini tekshirish
async def check_subscription(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Obuna tekshirishda xatolik: {e}")
        return False

# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id == ADMIN_CHAT_ID:
        await update.message.reply_text(
            "ADMIN - Xush kelibsiz!\n\n"
            "Video yuborish uchun videoni botga yuboring."
        )
        return
    
    # Oddiy foydalanuvchi uchun obuna tekshirish
    is_subscribed = await check_subscription(context, user_id)
    
    if not is_subscribed:
        keyboard = [[InlineKeyboardButton("Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Botdan foydalanish uchun avval kanalimizga obuna bo'ling!\n\n"
            "Obuna bo'lgandan keyin /start ni qayta bosing.",
            reply_markup=reply_markup
        )
        return
    
    # Obuna bo'lgan foydalanuvchi uchun
    keyboard = [[InlineKeyboardButton("Kod kiritish", callback_data="enter_code")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Botga xush kelibsiz!\n\n"
        "Video olish uchun kod kiritish tugmasini bosing.",
        reply_markup=reply_markup
    )

# Kod kiritish tugmasi bosilganda
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == "enter_code":
        # Obuna tekshirish
        is_subscribed = await check_subscription(context, user_id)
        
        if not is_subscribed:
            keyboard = [[InlineKeyboardButton("Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "Botdan foydalanish uchun avval kanalimizga obuna bo'ling!\n\n"
                "Obuna bo'lgandan keyin /start ni qayta bosing.",
                reply_markup=reply_markup
            )
            return
        
        await query.edit_message_text("Video kodini kiriting:")
        context.user_data['waiting_for_code'] = True


# Video yuborish (faqat admin uchun)
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id != ADMIN_CHAT_ID:
        await update.message.reply_text("Sizda video yuborish huquqi yo'q!")
        return
    
    # Video ma'lumotlarini saqlash
    video = update.message.video
    context.user_data['pending_video'] = {
        'file_id': video.file_id,
        'file_name': video.file_name or "video",
        'duration': video.duration,
        'file_size': video.file_size
    }
    
    await update.message.reply_text("Video uchun nom kiriting:")
    bot_data['admin_states'][str(user_id)] = 'waiting_for_name'
    save_data(bot_data)

# Matn xabarlarini qayta ishlash
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text
    
    # Admin uchun
    if user_id == ADMIN_CHAT_ID:
        admin_state = bot_data['admin_states'].get(str(user_id))
        
        if admin_state == 'waiting_for_name':
            context.user_data['video_name'] = text
            await update.message.reply_text("Video uchun noyob kod kiriting:")
            bot_data['admin_states'][str(user_id)] = 'waiting_for_code'
            save_data(bot_data)
            return
            
        elif admin_state == 'waiting_for_code':
            # Kod noyobligini tekshirish
            if text in bot_data['videos']:
                await update.message.reply_text("Bu kod allaqachon mavjud! Boshqa kod kiriting:")
                return
            
            # Video ma'lumotlarini saqlash
            pending_video = context.user_data.get('pending_video')
            video_name = context.user_data.get('video_name')
            
            if pending_video and video_name:
                bot_data['videos'][text] = {
                    'name': video_name,
                    'file_id': pending_video['file_id'],
                    'file_name': pending_video['file_name'],
                    'duration': pending_video['duration'],
                    'file_size': pending_video['file_size']
                }
                
                # Admin holatini tozalash
                del bot_data['admin_states'][str(user_id)]
                save_data(bot_data)
                
                # Context ma'lumotlarini tozalash
                context.user_data.clear()
                
                await update.message.reply_text(
                    f"Video muvaffaqiyatli saqlandi!\n\n"
                    f"Nom: {video_name}\n"
                    f"Kod: {text}\n\n"
                    f"Yana video yuborish uchun videoni yuboring."
                )
            else:
                await update.message.reply_text("Xatolik yuz berdi. Qaytadan video yuboring.")
            return
    
    # Oddiy foydalanuvchi uchun
    else:
        # Obuna tekshirish
        is_subscribed = await check_subscription(context, user_id)
        
        if not is_subscribed:
            keyboard = [[InlineKeyboardButton("Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Botdan foydalanish uchun avval kanalimizga obuna bo'ling!",
                reply_markup=reply_markup
            )
            return
        
        # Kod kutilayotgan holatda
        if context.user_data.get('waiting_for_code'):
            if text in bot_data['videos']:
                video_info = bot_data['videos'][text]
                
                await update.message.reply_text(f"Video topildi: {video_info['name']}")
                
                # Videoni yuborish
                await context.bot.send_video(
                    chat_id=user_id,
                    video=video_info['file_id'],
                    caption=f"{video_info['name']}"
                )
                
                context.user_data['waiting_for_code'] = False

                # Yana kod kiritish tugmasini ko'rsatish
                keyboard = [[InlineKeyboardButton("Boshqa kod kiritish", callback_data="enter_code")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "Boshqa video olish uchun tugmani bosing:",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    "Bunday kod topilmadi! Qaytadan urinib ko'ring yoki /start ni bosing."
                )
        else:
            keyboard = [[InlineKeyboardButton("Kod kiritish", callback_data="enter_code")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "Video olish uchun kod kiritish tugmasini bosing:",
                reply_markup=reply_markup
            )

# Xatoliklarni qayta ishlash
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Xatolik yuz berdi: {context.error}")

def main() -> None:
    """Botni ishga tushirish"""
    # Application yaratish
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.VIDEO, handle_video))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Xatolik handlerini qo'shish
    application.add_error_handler(error_handler)
    
    # Botni ishga tushirish
    print("Bot ishga tushmoqda...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

