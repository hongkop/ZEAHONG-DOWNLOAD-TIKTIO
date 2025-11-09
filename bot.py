import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from yt_dlp import YoutubeDL

# Configure logging
logging.basicConfig(
    format='%(asasctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Use environment variable for security, with fallback for testing
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8438612815:AAEzGOX0RMAvh4EHXYis7ZmrN1CRZcUQNCU')

DOWNLOAD_FOLDER = './downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('👋 Hello! Send me a TikTok link to download videos or audio! 😊\n\nSupported formats:\n• tiktok.com/\n• vm.tiktok.com/\n• vt.tiktok.com/')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        '📖 How to use:\n\n'
        '1. Send any TikTok URL\n'
        '2. Choose download option\n'
        '3. Wait for processing\n\n'
        'Supported URLs:\n'
        '• https://www.tiktok.com/@username/video/123456789\n'
        '• https://vm.tiktok.com/ABC123/\n'
        '• https://vt.tiktok.com/XYZ789/'
    )

def is_tiktok_url(url: str) -> bool:
    """Check if the URL is a valid TikTok URL"""
    tiktok_patterns = [
        r'https?://(www\.)?tiktok\.com/',
        r'https?://vm\.tiktok\.com/',
        r'https?://vt\.tiktok\.com/'
    ]
    
    for pattern in tiktok_patterns:
        if re.search(pattern, url):
            return True
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text.strip()
    
    if is_tiktok_url(user_message):
        tiktok_url = user_message
        
        # Store the URL for later use
        context.user_data['tiktok_url'] = tiktok_url
        
        # Create inline keyboard for download options
        keyboard = [
            [InlineKeyboardButton("🎵 Download MP3 (Audio)", callback_data="mp3")],
            [InlineKeyboardButton("🎬 Download Video (480p)", callback_data="video")],
            [InlineKeyboardButton("📹 Download HD Video", callback_data="hd_video")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📥 Choose download format:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ Please send a valid TikTok URL.\n\nExample:\nhttps://www.tiktok.com/@username/video/123456789")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    tiktok_url = context.user_data.get('tiktok_url')
    
    if not tiktok_url:
        await query.edit_message_text("❌ Error! Please send the TikTok link again.")
        return
    
    # Show downloading message
    download_messages = {
        "mp3": "🎵 Downloading audio...",
        "video": "🎬 Downloading video...",
        "hd_video": "📹 Downloading HD video..."
    }
    
    await query.edit_message_text(f"⏳ {download_messages.get(choice, 'Processing...')}")
    
    try:
        if choice == "mp3":
            success = await download_audio(context, query.message.chat_id, tiktok_url)
            if success:
                await query.edit_message_text("✅ Audio downloaded successfully! 🎵")
            else:
                await query.edit_message_text("❌ Failed to download audio. Please try again.")
        elif choice == "video":
            success = await download_video(context, query.message.chat_id, tiktok_url, quality='best[height<=480]')
            if success:
                await query.edit_message_text("✅ Video downloaded successfully! 🎬")
            else:
                await query.edit_message_text("❌ Failed to download video. Please try again.")
        elif choice == "hd_video":
            success = await download_video(context, query.message.chat_id, tiktok_url, quality='best')
            if success:
                await query.edit_message_text("✅ HD video downloaded successfully! 📹")
            else:
                await query.edit_message_text("❌ Failed to download HD video. File might be too large.")
            
    except Exception as e:
        logging.error(f"Error processing {choice}: {str(e)}")
        await query.edit_message_text("❌ Download error! Please try again with a different video.")

async def download_audio(context: ContextTypes.DEFAULT_TYPE, chat_id: int, tiktok_url: str) -> bool:
    """Download TikTok video as MP3"""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title).100s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True,
            'no_warnings': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(tiktok_url, download=True)
            mp3_file_path = ydl.prepare_filename(info_dict)
            mp3_file_path = os.path.splitext(mp3_file_path)[0] + '.mp3'

        # Send the MP3 file to the user
        with open(mp3_file_path, 'rb') as audio_file:
            await context.bot.send_audio(
                chat_id=chat_id, 
                audio=audio_file,
                title=info_dict.get('title', 'TikTok Audio')[:64],
                performer=info_dict.get('uploader', 'TikTok User')[:64],
                duration=info_dict.get('duration', 0)
            )

        # Clean up
        if os.path.exists(mp3_file_path):
            os.remove(mp3_file_path)
        return True

    except Exception as e:
        logging.error(f"Error downloading audio: {str(e)}")
        return False

async def download_video(context: ContextTypes.DEFAULT_TYPE, chat_id: int, tiktok_url: str, quality: str = 'best[height<=480]') -> bool:
    """Download TikTok video"""
    try:
        ydl_opts = {
            'format': quality,
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title).100s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(tiktok_url, download=True)
            video_file_path = ydl.prepare_filename(info_dict)

        # Check file size
        file_size = os.path.getsize(video_file_path)
        if file_size > 50 * 1024 * 1024:  # 50MB Telegram limit
            if os.path.exists(video_file_path):
                os.remove(video_file_path)
            return False

        # Send the video file to the user
        with open(video_file_path, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption=info_dict.get('title', 'TikTok Video')[:1024],
                supports_streaming=True,
                duration=info_dict.get('duration', 0)
            )

        # Clean up
        if os.path.exists(video_file_path):
            os.remove(video_file_path)
        return True

    except Exception as e:
        logging.error(f"Error downloading video: {str(e)}")
        return False

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logging.error(f"Exception while handling an update: {context.error}")

def main() -> None:
    # Create application
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logging.info("🤖 TikTok Downloader Bot is starting...")
    print("Bot is running... Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == '__main__':
    main()
