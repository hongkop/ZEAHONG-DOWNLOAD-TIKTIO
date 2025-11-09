import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from yt_dlp import YoutubeDL

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8438612815:AAEzGOX0RMAvh4EHXYis7ZmrN1CRZcUQNCU"

DOWNLOAD_FOLDER = './'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('សួរស្អី! សូមផ្ញើរ Link TikTok ដែលអ្នកចង់ Download 😁')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.text and ('tiktok.com' in update.message.text or 'vm.tiktok.com' in update.message.text or 'vt.tiktok.com' in update.message.text):
        tiktok_url = update.message.text
        
        # Store the URL for later use
        context.user_data['tiktok_url'] = tiktok_url
        
        # Create inline keyboard for download options
        keyboard = [
            [InlineKeyboardButton("📥 Download MP3", callback_data="mp3")],
            [InlineKeyboardButton("🎬 Download Video", callback_data="video")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "ជម្រើសរបស់អ្នក៖ តើអ្នកចង់ទាញយកជា MP3 ឬ Video?",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("សូមផ្តល់ឲ្យតែ Link TikTok ត្រឹមត្រូវ។")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    tiktok_url = context.user_data.get('tiktok_url')
    
    if not tiktok_url:
        await query.edit_message_text("មានបញ្ហា! សូមផ្ញើ់ Link ម្តងទៀត។")
        return
    
    await query.edit_message_text(f"⏳ កំពុងទាញយក... {choice.upper()}")
    
    try:
        if choice == "mp3":
            await download_audio(context, query.message.chat_id, tiktok_url)
            await query.edit_message_text("✅ ទាញយក MP3 បានជោគជ័យ!")
        elif choice == "video":
            await download_video(context, query.message.chat_id, tiktok_url)
            await query.edit_message_text("✅ ទាញយក Video បានជោគជ័យ!")
            
    except Exception as e:
        logging.error(f"Error processing {choice}: {e}")
        await query.edit_message_text("❌ មានបញ្ហាក្នុងពេលទាញយក! សូមព្យាយាមម្តងទៀត។")

async def download_audio(context: ContextTypes.DEFAULT_TYPE, chat_id: int, tiktok_url: str) -> None:
    """Download TikTok video as MP3"""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(tiktok_url, download=True)
            mp3_file_path = ydl.prepare_filename(info_dict)
            # Replace extension with .mp3
            mp3_file_path = os.path.splitext(mp3_file_path)[0] + '.mp3'

        # Send the MP3 file to the user
        with open(mp3_file_path, 'rb') as audio_file:
            await context.bot.send_audio(
                chat_id=chat_id, 
                audio=audio_file,
                title=info_dict.get('title', 'TikTok Audio'),
                performer=info_dict.get('uploader', 'TikTok User')
            )

        # Clean up the MP3 file after sending
        if os.path.exists(mp3_file_path):
            os.remove(mp3_file_path)

    except Exception as e:
        logging.error(f"Error downloading audio: {e}")
        raise

async def download_video(context: ContextTypes.DEFAULT_TYPE, chat_id: int, tiktok_url: str) -> None:
    """Download TikTok video"""
    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'quiet': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(tiktok_url, download=True)
            video_file_path = ydl.prepare_filename(info_dict)

        # Send the video file to the user
        with open(video_file_path, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption=info_dict.get('title', 'TikTok Video'),
                supports_streaming=True
            )

        # Clean up the video file after sending
        if os.path.exists(video_file_path):
            os.remove(video_file_path)

    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        raise

def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
