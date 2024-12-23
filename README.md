# Tweet Downloader Telegram Bot

This project enables the downloading of tweets from Twitter that include images or videos.

## Usage

1. Clone the repository.
2. Create a `.env` file in the project directory.
3. Create a bot on Telegram using BOTFATHER.
4. Add the following entries to the `.env` file:
```
TELEGRAM_BOT_TOKEN ='YOUR_TELEGRAM_BOT_TOKEN_FROM_BOTFATHER'
CHANNEL_USERNAME = '@THE USERNAME OF A CHANNEL YOU WANT THE USER TO JOIN INORDER TO USE THE BOT'
```
5. Run 'pip3 install -r requirements.txt' to install required modules.

```
# FFmpeg is required for this project. Install it with:
#   Linux: sudo apt-get install ffmpeg
#   macOS: brew install ffmpeg
#   Windows: Download from https://ffmpeg.org/download.html

```

5. Run the script to activate the bot.
6. Open the newly created bot on Telegram and start it using the `/start` command.
7. Send the bot a link to download tweets that contain videos or images.

## Bot Link

Explore the bot: [t.me/formerlytwitterbot](https://t.me/formerlytwitterbot)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
