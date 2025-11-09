import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from yt_dlp import YoutubeDL

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get token from environment variable
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8502597211:AAHWTdyQIayG60dbJ_6x9J1oDhnWDgfiiPg')

DOWNLOAD_FOLDER = './downloads'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello! Send me a TikTok link to download 😊')

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
    if update.message.text and is_tiktok_url(update.message.text):
        tiktok_url = update.message.text
        
        # Store the URL for later use
        context.user_data['tiktok_url'] = tiktok_url
        
        # Create inline keyboard for download options
        keyboard = [
            [InlineKeyboardButton("📥 Download MP3", callback_data="mp3")],
            [InlineKeyboardButton("🎬 Download Video", callback_data="video")],
            [InlineKeyboardButton("🎬 Download HD Video", callback_data="hd_video")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Choose your option: Download as MP3 or Video?",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("Please provide a valid TikTok link.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    tiktok_url = context.user_data.get('tiktok_url')
    
    if not tiktok_url:
        await query.edit_message_text("Error! Please send the link again.")
        return
    
    await query.edit_message_text(f"⏳ Downloading... {choice.upper()}")
    
    try:
        if choice == "mp3":
            success = await download_audio(context, query.message.chat_id, tiktok_url)
            if success:
                await query.edit_message_text("✅ MP3 downloaded successfully!")
            else:
                await query.edit_message_text("❌ Failed to download MP3!")
        elif choice == "video":
            success = await download_video(context, query.message.chat_id, tiktok_url, quality='best[height<=480]')
            if success:
                await query.edit_message_text("✅ Video downloaded successfully!")
            else:
                await query.edit_message_text("❌ Failed to download Video!")
        elif choice == "hd_video":
            success = await download_video(context, query.message.chat_id, tiktok_url, quality='best')
            if success:
                await query.edit_message_text("✅ HD Video downloaded successfully!")
            else:
                await query.edit_message_text("❌ Failed to download HD Video!")
            
    except Exception as e:
        logging.error(f"Error processing {choice}: {e}")
        await query.edit_message_text("❌ Download error! Please try again.")

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
                performer=info_dict.get('uploader', 'TikTok')[:64]
            )

        # Clean up
        if os.path.exists(mp3_file_path):
            os.remove(mp3_file_path)
        return True

    except Exception as e:
        logging.error(f"Error downloading audio: {e}")
        return False

async def download_video(context: ContextTypes.DEFAULT_TYPE, chat_id: int, tiktok_url: str, quality: str = 'best[height<=480]') -> bool:
    """Download TikTok video"""
    try:
        ydl_opts = {
            'format': quality,
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title).100s.%(ext)s'),
            'quiet': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(tiktok_url, download=True)
            video_file_path = ydl.prepare_filename(info_dict)

        # Check file size
        file_size = os.path.getsize(video_file_path)
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            if os.path.exists(video_file_path):
                os.remove(video_file_path)
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Video file too large for Telegram (max 50MB)"
            )
            return False

        # Send the video file to the user
        with open(video_file_path, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption=info_dict.get('title', 'TikTok Video')[:1024],
                supports_streaming=True
            )

        # Clean up
        if os.path.exists(video_file_path):
            os.remove(video_file_path)
        return True

    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        return False

def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))

    application.run_polling()

if __name__ == '__main__':
    main()
