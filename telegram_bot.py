import os
import logging
import datetime
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Base directory for storing files
BASE_DIR = 'arquivos'
os.makedirs(BASE_DIR, exist_ok=True)

# ... (código das funções auxiliares permanece o mesmo até a função botao_clicado)

def botao_clicado(update: Update, context: CallbackContext) -> None:
    """Handle button clicks from inline keyboards."""
    query = update.callback_query
    query.answer()  # Answer the callback query
    data = query.data
    
    # ... (outros handlers permanecem os mesmos até o bloco compartilhar)

    elif data.startswith('compartilhar:'):
        file_path = data.split(':', 1)[1]
        category, filename = file_path.split('/', 1)
        full_path = os.path.join(BASE_DIR, category, filename)
        
        if not os.path.exists(full_path):
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Arquivo não encontrado."
            )
            return
            
        # Generate a shareable message
        share_text = (
            f"📁 Compartilhado do Organizador de Arquivos Bot\n\n"
            f"📄 Arquivo: {filename}\n"
            f"📂 Categoria: {category}\n\n"
            f"Para acessar este arquivo, solicite ao proprietário."
        )
        
        # Create button to go back
        keyboard = [[InlineKeyboardButton("🔙 Voltar", callback_data=f'visualizar:{file_path}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            # Send as a new message instead of editing
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🔗 Mensagem para compartilhar:\n\n{share_text}\n\n"
                     f"Copie a mensagem acima para compartilhar as informações do arquivo.",
                reply_markup=reply_markup
            )
            
            # Try to delete the original message if it exists
            try:
                if hasattr(query, 'message') and query.message:
                    query.delete_message()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
                
        except Exception as e:
            logger.error(f"Error sharing file: {e}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Erro ao compartilhar: {str(e)}"
            )

    # ... (restante do código permanece o mesmo)

def main() -> None:
    """Start the bot."""
    # Get token from environment variable with fallback
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not TOKEN:
        logger.error("No token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
        print("Please set the TELEGRAM_BOT_TOKEN environment variable with your bot token from BotFather.")
        return

    # Create the Updater and pass it your bot's token
    updater = Updater(TOKEN)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add command handlers
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
    # Import and start the keep_alive server
    from keep_alive import keep_alive
    keep_alive()
    
    # Start the bot
    main()
