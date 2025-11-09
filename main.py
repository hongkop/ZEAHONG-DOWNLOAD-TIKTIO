import os
import logging
import requests
import re
import json
from urllib.parse import unquote
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = "8438612815:AAEzGOX0RMAvh4EHXYis7ZmrN1CRZcUQNCU"

DOWNLOAD_FOLDER = './downloads/'
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# TikTok API endpoints (public APIs)
TIKTOK_APIS = [
    "https://www.tikwm.com/api/",
    "https://tikdown.org/api/",
    "https://tiktok-downloader-download-tiktok-videos-without-watermark.p.rapidapi.com/video/index",
]

def extract_tiktok_url(text: str) -> str:
    """Extract TikTok URL from text"""
    patterns = [
        r'https?://(?:www\.)?tiktok\.com/[^/\s]+/video/\d+',
        r'https?://vm\.tiktok\.com/[^\s]+',
        r'https?://vt\.tiktok\.com/[^\s]+',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            url = match.group()
            # Convert short URLs to full URLs
            if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
                try:
                    response = requests.head(url, allow_redirects=True, timeout=10)
                    url = response.url
                except:
                    pass
            return url
    return None

def get_tiktok_video_data(url: str):
    """Get TikTok video data using public APIs"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://www.tikwm.com',
        'Referer': 'https://www.tikwm.com/',
    }
    
    # Try different APIs
    for api_url in TIKTOK_APIS:
        try:
            if 'tikwm.com' in api_url:
                payload = {'url': url}
                response = requests.post(api_url, data=payload, headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('code') == 0:
                        return data['data']
            
            elif 'tikdown.org' in api_url:
                payload = {'url': url}
                response = requests.post(api_url, data=payload, headers=headers, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    if 'video' in data:
                        return data
            
            elif 'rapidapi.com' in api_url:
                headers_rapid = {
                    'X-RapidAPI-Key': 'your-rapidapi-key',  # You might need to get a free key
                    'X-RapidAPI-Host': 'tiktok-downloader-download-tiktok-videos-without-watermark.p.rapidapi.com'
                }
                params = {'url': url}
                response = requests.get(api_url, headers=headers_rapid, params=params, timeout=30)
                if response.status_code == 200:
                    return response.json()
                    
        except Exception as e:
            logging.error(f"API {api_url} failed: {e}")
            continue
    
    return None

def download_tiktok_video(video_url: str, filename: str) -> bool:
    """Download TikTok video from URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.tiktok.com/',
        }
        
        response = requests.get(video_url, headers=headers, stream=True, timeout=60)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
    except Exception as e:
        logging.error(f"Download failed: {e}")
    
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        '🎵 TikTok Downloader Bot 🎵\n\n'
        'សួរស្ដី! សូមផ្ញើរ Link TikTok ដែលអ្នកចង់ទាញយក\n\n'
        'Supported URLs:\n'
        '• https://www.tiktok.com/@user/video/123\n'
        '• https://vm.tiktok.com/ABC123/\n'
        '• https://vt.tiktok.com/XYZ456/'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    tiktok_url = extract_tiktok_url(text)
    
    if tiktok_url:
        context.user_data['tiktok_url'] = tiktok_url
        
        keyboard = [
            [InlineKeyboardButton("📥 Download MP3", callback_data="mp3")],
            [InlineKeyboardButton("🎬 Download Video", callback_data="video")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ រកឃើញ Link TikTok!\n\nជម្រើសរបស់អ្នក៖ តើអ្នកចង់ទាញយកជា MP3 ឬ Video?",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "❌ សូមផ្ដល់ឲ្យតែ Link TikTok ត្រឹមត្រូវ។\n\n"
            "ឧទាហរណ៍៖\n"
            "• https://www.tiktok.com/@user/video/123456\n"
            "• https://vm.tiktok.com/ABC123/"
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    tiktok_url = context.user_data.get('tiktok_url')
    
    if not tiktok_url:
        await query.edit_message_text("❌ មានបញ្ហា! សូមផ្ញើ់ Link ម្ដងទៀត។")
        return
    
    await query.edit_message_text(f"⏳ កំពុងទាញយក TikTok {choice.upper()}...\nសូមមានអត្ថាចាំបន្ដិច!")
    
    try:
        # Get video data from TikTok API
        video_data = get_tiktok_video_data(tiktok_url)
        
        if not video_data:
            await query.edit_message_text("❌ មិនអាចទាញយកព័ត៌មានវីដេអូបានទេ។ សូមព្យាយាមម្ដងទៀត។")
            return
        
        if choice == "mp3":
            success = await download_and_send_audio(context, query.message.chat_id, video_data)
            if success:
                await query.edit_message_text("✅ ទាញយក MP3 បានជោគជ័យ!")
            else:
                await query.edit_message_text("❌ ទាញយក MP3 មិនបានជោគជ័យ! សូមព្យាយាមម្ដងទៀត។")
                
        elif choice == "video":
            success = await download_and_send_video(context, query.message.chat_id, video_data)
            if success:
                await query.edit_message_text("✅ ទាញយក Video បានជោគជ័យ!")
            else:
                await query.edit_message_text("❌ ទាញយក Video មិនបានជោគជ័យ! សូមព្យាយាមម្ដងទៀត។")
            
    except Exception as e:
        logging.error(f"Error processing {choice}: {e}")
        await query.edit_message_text("❌ មានបញ្ហាក្នុងពេលទាញយក! សូមព្យាយាមម្ដងទៀត។")

async def download_and_send_audio(context: ContextTypes.DEFAULT_TYPE, chat_id: int, video_data: dict) -> bool:
    """Download and send TikTok audio"""
    try:
        # For now, we'll send the video without watermark and let Telegram handle audio extraction
        # In a more advanced version, you could use ffmpeg to extract audio
        
        video_url = video_data.get('play') or video_data.get('video') or video_data.get('wmplay')
        if not video_url:
            # Try to find video URL in nested data
            for key, value in video_data.items():
                if isinstance(value, dict) and 'play' in value:
                    video_url = value['play']
                    break
        
        if not video_url:
            logging.error("No video URL found in data")
            return False
        
        # Download video
        filename = os.path.join(DOWNLOAD_FOLDER, f"tiktok_audio_{chat_id}.mp4")
        if download_tiktok_video(video_url, filename):
            # Send as video (Telegram will show it with audio)
            with open(filename, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption="🎵 TikTok Audio",
                    supports_streaming=True
                )
            # Clean up
            if os.path.exists(filename):
                os.remove(filename)
            return True
            
    except Exception as e:
        logging.error(f"Error in download_and_send_audio: {e}")
    
    return False

async def download_and_send_video(context: ContextTypes.DEFAULT_TYPE, chat_id: int, video_data: dict) -> bool:
    """Download and send TikTok video"""
    try:
        # Get video URL (prefer without watermark)
        video_url = (video_data.get('play') or 
                    video_data.get('hdplay') or 
                    video_data.get('video') or 
                    video_data.get('wmplay'))
        
        if not video_url:
            # Try to find video URL in nested data
            for key, value in video_data.items():
                if isinstance(value, dict):
                    video_url = value.get('play') or value.get('hdplay')
                    if video_url:
                        break
        
        if not video_url:
            logging.error("No video URL found in data")
            return False
        
        # Download video
        filename = os.path.join(DOWNLOAD_FOLDER, f"tiktok_video_{chat_id}.mp4")
        if download_tiktok_video(video_url, filename):
            # Get title/description
            title = video_data.get('title') or 'TikTok Video'
            if isinstance(title, str) and len(title) > 200:
                title = title[:200] + '...'
            
            # Send video
            with open(filename, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=video_file,
                    caption=title,
                    supports_streaming=True
                )
            # Clean up
            if os.path.exists(filename):
                os.remove(filename)
            return True
            
    except Exception as e:
        logging.error(f"Error in download_and_send_video: {e}")
    
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
