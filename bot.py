import os
import logging
from telegram.ext import (
    Updater, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    Filters
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get token from environment variable with fallback
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not TOKEN:
    logger.error("No token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
    exit(1)

# Create the base directory for storing files
BASE_DIR = 'arquivos'
os.makedirs(BASE_DIR, exist_ok=True)

def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token
    updater = Updater(TOKEN)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Import handlers
    from handlers import (
        start, menu, categoria, listar, salvar_arquivo,
        botao_clicado, tratar_texto
    )

    # Add handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("menu", menu))
    dispatcher.add_handler(CommandHandler("categoria", categoria))
    dispatcher.add_handler(CommandHandler("listar", listar))
    
    # Handle file uploads (documents and photos)
    dispatcher.add_handler(MessageHandler(
        Filters.document | Filters.photo, 
        salvar_arquivo
    ))
    
    # Handle button clicks in inline keyboards
    dispatcher.add_handler(CallbackQueryHandler(botao_clicado))
    
    # Handle text messages that are not commands
    dispatcher.add_handler(MessageHandler(
        Filters.text & ~Filters.command, 
        tratar_texto
    ))

    # Start the Bot
    logger.info("🤖 Bot is now running!")
    updater.start_polling()
    
    # Run the bot until you send a signal to stop
    updater.idle()

if __name__ == '__main__':
    main()
