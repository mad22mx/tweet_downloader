import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from bs4 import BeautifulSoup

from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access your API key
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_USERNAME = os.getenv('CHANNEL_USERNAME')

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

CHOOSING_QUALITY = range(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if await is_user_member_of_channel(context, user_id):
        await update.message.reply_text('Hi! Send me a Twitter link to download the video.')
    else:
        await update.message.reply_text(f'Please join our channel to use this bot: {CHANNEL_USERNAME}')

async def is_user_member_of_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

async def fetch_twitter_content(link_to_download):
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36"
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument(f'user-agent={user_agent}')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--start-maximized')
    chrome_options.add_argument('--allow-running-insecure-content')
    chrome_options.add_argument('--disable-extensions')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get(link_to_download)
        wait = WebDriverWait(driver, 10)
        tweet_text_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'article div[data-testid="tweetText"]')))
        tweet_html = tweet_text_element.get_attribute('innerHTML')

        soup = BeautifulSoup(tweet_html, 'html.parser')
        tweet_text = ''.join(element if isinstance(element, str) else element.get_text() if element.name != 'img' else element['alt'] for element in soup.contents)

        # Check for video
        video_elements = driver.find_elements(By.CSS_SELECTOR, 'video')
        if video_elements:
            # Navigate to the video download site
            driver.get('https://ssstwitter.com/en')
            tweet_input = driver.find_element(By.ID, 'main_page_text')
            tweet_input.send_keys(link_to_download)

            submit_button = driver.find_element(By.ID, 'submit')
            submit_button.click()

            download_links = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'result_overlay')))
            video_links = []
            for link in download_links.find_elements(By.CSS_SELECTOR, '.download_link'):
                url = link.get_attribute('href')
                quality = link.text.split()[-1]
                
                if quality == "1280x720":
                    continue
                video_links.append([quality, url])

            return tweet_text, {'type': 'video', 'links': video_links}

        # Check for pictures
        image_elements = driver.find_elements(By.CSS_SELECTOR, 'article div[data-testid="tweetPhoto"] img')
        if image_elements:
            image_urls = [img.get_attribute('src') for img in image_elements]
            return tweet_text, {'type': 'pictures', 'links': image_urls}

        return tweet_text, {'type': 'none', 'links': []}
    except Exception as e:
        logger.error(f"Error fetching Twitter content: {e}")
        return None, {'type': 'error', 'links': []}
    finally:
        driver.quit()

def download_file(url):
    local_filename = url.split('/')[-1]
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_filename
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if not await is_user_member_of_channel(context, user_id):
        await update.message.reply_text(f'Please join our channel to use this bot: {CHANNEL_USERNAME}')
        return ConversationHandler.END

    url = update.message.text
    if "twitter.com" in url or "x.com" in url:
        processing_message = await update.message.reply_text('Processing request...')
        tweet_text, content = await fetch_twitter_content(url)
        if content['type'] == 'video':
            video_links = content['links']
            if video_links:
                context.user_data['video_links'] = video_links
                context.user_data['tweet_text'] = tweet_text

                keyboard = [
                    [InlineKeyboardButton(f"{quality}", callback_data=str(i))]
                    for i, (quality, _) in enumerate(video_links)
                ]
                keyboard.append([InlineKeyboardButton("Quit", callback_data="quit")])
                reply_markup = InlineKeyboardMarkup(keyboard)

                await processing_message.edit_text("Choose the quality by clicking one of the buttons below:", reply_markup=reply_markup)
            else:
                await processing_message.edit_text('Could not find video in the given Twitter link.')
        elif content['type'] == 'pictures':
            image_urls = content['links']
            if image_urls:
                trademark_text = "📲 Downloaded by @formerlytwitterbot"
                full_text = tweet_text

                photo_media = [InputMediaPhoto(media=url) for url in image_urls]
                photo_media[0] = InputMediaPhoto(media=image_urls[0], caption=full_text)

                await context.bot.send_media_group(chat_id=update.message.chat_id, media=photo_media)
                await processing_message.delete()
            else:
                await processing_message.edit_text('Could not find pictures in the given Twitter link.')
        else:
            await processing_message.edit_text('Could not find any media in the given Twitter link.')
    else:
        await update.message.reply_text('Please send a valid Twitter or X link.')

async def choose_quality(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "quit":
        await query.edit_message_text('Process cancelled. If you want to download another video, please send a new Twitter link.')
        return ConversationHandler.END

    try:
        user_choice = int(query.data)
        video_links = context.user_data['video_links']
        if 0 <= user_choice < len(video_links):
            video_url = video_links[user_choice][1]
            video_path = download_file(video_url)
            if video_path:
                tweet_text = context.user_data['tweet_text']
                trademark_text = "📲 Downloaded by @formerlytwitterbot"
                full_text = tweet_text

                await context.bot.send_video(chat_id=query.message.chat_id, video=open(video_path, 'rb'), caption=full_text)
                await query.edit_message_text("Video sent successfully.")
            else:
                await query.edit_message_text('Failed to download video.')
        else:
            await query.edit_message_text('Invalid choice. Please select a valid option.')
    except ValueError:
        await query.edit_message_text('Invalid input. Please select a valid option.')

def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        states={
            CHOOSING_QUALITY: [CallbackQueryHandler(choose_quality)],
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(choose_quality))

    application.run_polling()

if __name__ == '__main__':
    main()