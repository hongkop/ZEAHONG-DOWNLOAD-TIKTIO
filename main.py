import os
import logging
import requests
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from yt_dlp import YoutubeDL

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8438612815:AAEzGOX0RMAvh4EHXYis7ZmrN1CRZcUQNCU"

DOWNLOAD_FOLDER = './downloads/'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def extract_tiktok_url(text: str) -> str:
    """Extract TikTok URL from text"""
    # Match various TikTok URL patterns
    patterns = [
        r'https?://(?:www\.)?tiktok\.com/[^/\s]+/video/\d+',
        r'https?://vm\.tiktok\.com/[^\s]+',
        r'https?://vt\.tiktok\.com/[^\s]+',
        r'https?://(?:www\.)?tiktok\.com/t/[^\s]+',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group()
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('សួរស្អី! សូមផ្ញើរ Link TikTok ដែលអ្នកចង់ Download 😁\n\nSupported URLs:\n• tiktok.com/@user/video/123\n• vm.tiktok.com/ABC123/\n• vt.tiktok.com/XYZ456/')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    tiktok_url = extract_tiktok_url(text)
    
    if tiktok_url:
        # Store the URL for later use
        context.user_data['tiktok_url'] = tiktok_url
        
        # Create inline keyboard for download options
        keyboard = [
            [InlineKeyboardButton("📥 Download MP3", callback_data="mp3")],
            [InlineKeyboardButton("🎬 Download Video", callback_data="video")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ រកឃើញ Link TikTok!\nជម្រើសរបស់អ្នក៖ តើអ្នកចង់ទាញយកជា MP3 ឬ Video?",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text("❌ សូមផ្តល់ឲ្យតែ Link TikTok ត្រឹមត្រូវ។\n\nឧទាហរណ៍៖\nhttps://www.tiktok.com/@user/video/123456\nhttps://vm.tiktok.com/ABC123/")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    tiktok_url = context.user_data.get('tiktok_url')
    
    if not tiktok_url:
        await query.edit_message_text("មានបញ្ហា! សូមផ្ញើ់ Link ម្តងទៀត។")
        return
    
    await query.edit_message_text(f"⏳ កំពុងទាញយក TikTok {choice.upper()}...\nសូមមានអត្ថាៈចាំបន្តិច!")
    
    try:
        if choice == "mp3":
            success = await download_audio(context, query.message.chat_id, tiktok_url)
            if success:
                await query.edit_message_text("✅ ទាញយក MP3 បានជោគជ័យ!")
            else:
                await query.edit_message_text("❌ ទាញយក MP3 មិនបានជោគជ័យ! សូមព្យាយាមម្តងទៀត។")
        elif choice == "video":
            success = await download_video(context, query.message.chat_id, tiktok_url)
            if success:
                await query.edit_message_text("✅ ទាញយក Video បានជោគជ័យ!")
            else:
                await query.edit_message_text("❌ ទាញយក Video មិនបានជោគជ័យ! សូមព្យាយាមម្តងទៀត។")
            
    except Exception as e:
        logging.error(f"Error processing {choice}: {e}")
        await query.edit_message_text("❌ មានបញ្ហាក្នុងពេលទាញយក! សូមព្យាយាមម្តងទៀត។")

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
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info_dict = ydl.extract_info(tiktok_url, download=False)
            
            # Download the video
            ydl.download([tiktok_url])
            
            # Find the downloaded file
            filename = ydl.prepare_filename(info_dict)
            mp3_file_path = os.path.splitext(filename)[0] + '.mp3'

        # Check if file exists and send it
        if os.path.exists(mp3_file_path):
            with open(mp3_file_path, 'rb') as audio_file:
                await context.bot.send_audio(
                    chat_id=chat_id, 
                    audio=audio_file,
                    title=info_dict.get('title', 'TikTok Audio')[:64],
                    performer=info_dict.get('uploader', 'TikTok User')[:64]
                )
            
            # Clean up
            os.remove(mp3_file_path)
            return True
        else:
            logging.error("MP3 file not found after conversion")
            return False

    except Exception as e:
        logging.error(f"Error downloading audio: {e}")
        return False

async def download_video(context: ContextTypes.DEFAULT_TYPE, chat_id: int, tiktok_url: str) -> bool:
    """Download TikTok video"""
    try:
        ydl_opts = {
            'format': 'best[height<=720]',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title).100s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
        }

        with YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info_dict = ydl.extract_info(tiktok_url, download=False)
            
            # Download the video
            ydl.download([tiktok_url])
            
            # Find the downloaded file
            video_file_path = ydl.prepare_filename(info_dict)

        # Check if file exists and send it
        if os.path.exists(video_file_path):
            with open(video_file_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=info_dict.get('title', 'TikTok Video')[:1024],
                    supports_streaming=True
                )
            
            # Clean up
            os.remove(video_file_path)
            return True
        else:
            logging.error("Video file not found after download")
            return False

    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        # Try alternative method
        return await download_video_alternative(context, chat_id, tiktok_url)

async def download_video_alternative(context: ContextTypes.DEFAULT_TYPE, chat_id: int, tiktok_url: str) -> bool:
    """Alternative method for downloading TikTok videos"""
    try:
        # Use different yt-dlp options
        ydl_opts = {
            'format': 'mp4/mp3/best',
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, 'tiktok_%(id)s.%(ext)s'),
            'quiet': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(tiktok_url, download=True)
            video_file_path = ydl.prepare_filename(info_dict)

        if os.path.exists(video_file_path):
            with open(video_file_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption="TikTok Video",
                    supports_streaming=True
                )
            os.remove(video_file_path)
            return True
        return False
    except Exception as e:
        logging.error(f"Error in alternative download: {e}")
        return False

def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Start the Bot
    logging.info("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
