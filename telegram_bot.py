import os
import logging
import datetime
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
logger = logging.getLogger(__name__)

# Base directory for storing files
BASE_DIR = 'arquivos'
os.makedirs(BASE_DIR, exist_ok=True)


# Helper functions
def ensure_category_exists(category_name):
    """Ensure that a category directory exists."""
    category_path = os.path.join(BASE_DIR, category_name)
    os.makedirs(category_path, exist_ok=True)
    return category_path


def list_categories():
    """List all available categories."""
    if not os.path.exists(BASE_DIR):
        return []
    return [
        d for d in os.listdir(BASE_DIR)
        if os.path.isdir(os.path.join(BASE_DIR, d))
    ]


def list_files_in_category(category_name):
    """List all files in a specific category."""
    category_path = os.path.join(BASE_DIR, category_name)
    if not os.path.exists(category_path):
        return []
    return [
        f for f in os.listdir(category_path)
        if os.path.isfile(os.path.join(category_path, f))
    ]


def search_files(term):
    """Search for files across all categories matching a term."""
    results = []
    for category in list_categories():
        category_path = os.path.join(BASE_DIR, category)
        for file_name in os.listdir(category_path):
            if term.lower() in file_name.lower():
                results.append(f"{category}/{file_name}")
    return results


def rename_file(category, old_name, new_name):
    """Rename a file within a category."""
    old_path = os.path.join(BASE_DIR, category, old_name)
    new_path = os.path.join(BASE_DIR, category, new_name)

    if not os.path.exists(old_path):
        raise FileNotFoundError(f"File {old_name} not found in {category}")

    if os.path.exists(new_path):
        raise FileExistsError(f"File {new_name} already exists in {category}")

    os.rename(old_path, new_path)
    logger.info(f"Renamed file: {old_path} -> {new_path}")
    return True


def delete_file(category, file_name):
    """Delete a file from a category."""
    file_path = os.path.join(BASE_DIR, category, file_name)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_name} not found in {category}")

    os.remove(file_path)
    logger.info(f"Deleted file: {file_path}")
    return True


# Command handlers
def start(update: Update, context: CallbackContext) -> None:
    """Send a welcome message when the command /start is issued."""
    welcome_message = (
        "👋 Bem-vindo ao Organizador de Arquivos Bot!\n\n"
        "Este bot ajuda você a organizar seus arquivos em categorias.\n\n"
        "Comandos disponíveis:\n"
        "• /menu - Mostrar o menu principal\n"
        "• /categoria <nome> - Definir a categoria atual\n"
        "• /listar <categoria> - Listar arquivos em uma categoria\n\n"
        "Você também pode enviar arquivos ou fotos diretamente para salvá-los."
    )
    update.message.reply_text(welcome_message)


def menu(update: Update, context: CallbackContext) -> None:
    """Display the main menu with interactive buttons."""
    keyboard = [
        [InlineKeyboardButton("📂 Categorias", callback_data='categorias')],
        [InlineKeyboardButton("📊 Dashboard", callback_data='dashboard')],
        [InlineKeyboardButton("📝 Nova Nota", callback_data='criar_nota')],
        [InlineKeyboardButton("🔍 Buscar Arquivo", callback_data='buscar')],
        [InlineKeyboardButton("📝 Renomear Arquivo", callback_data='renomear')],
        [InlineKeyboardButton("❌ Excluir Arquivo", callback_data='excluir')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("🔍 Menu Principal - Escolha uma opção:",
                              reply_markup=reply_markup)


def categoria(update: Update, context: CallbackContext) -> None:
    """Set the current category for the user."""
    if not context.args:
        update.message.reply_text("❌ Uso incorreto. Use: /categoria <nome>\n"
                                  "Exemplo: /categoria documentos")
        return

    nome = ' '.join(context.args)
    context.user_data['categoria'] = nome

    # Ensure the category directory exists
    ensure_category_exists(nome)

    update.message.reply_text(
        f"✅ Categoria atual definida: 📁 {nome}\n"
        f"Todos os arquivos enviados serão salvos nesta categoria.")


def listar(update: Update, context: CallbackContext) -> None:
    """List files in a specific category."""
    if not context.args:
        update.message.reply_text("❌ Uso incorreto. Use: /listar <categoria>\n"
                                  "Exemplo: /listar documentos")
        return

    nome = ' '.join(context.args)
    categoria_path = os.path.join(BASE_DIR, nome)

    if not os.path.exists(categoria_path):
        update.message.reply_text(
            f"❌ Categoria '{nome}' não encontrada.\n"
            f"Use /categoria {nome} para criar esta categoria.")
        return

    arquivos = list_files_in_category(nome)

    if not arquivos:
        update.message.reply_text(
            f"📂 Categoria '{nome}' está vazia.\n"
            f"Envie arquivos depois de usar /categoria {nome}")
    else:
        texto = "\n".join([f"📄 {arquivo}" for arquivo in arquivos])
        update.message.reply_text(
            f"📂 Arquivos na categoria '{nome}':\n\n{texto}")


def solicitar_categoria(update: Update, context: CallbackContext) -> None:
    """Ask for a category when a file is uploaded."""
    # Store file info temporarily
    if update.message.document:
        file = update.message.document.get_file()
        nome_arquivo = update.message.document.file_name
        context.user_data['temp_file'] = {
            'file_id': update.message.document.file_id,
            'nome': nome_arquivo,
            'tipo': 'document'
        }
        # Ask if user wants to rename the file
        keyboard = [[
            InlineKeyboardButton("✏️ Renomear Arquivo",
                                 callback_data='renomear_antes_salvar')
        ],
                    [
                        InlineKeyboardButton(
                            "➡️ Continuar Sem Renomear",
                            callback_data='continuar_sem_renomear')
                    ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            f"📄 Arquivo: {nome_arquivo}\n\n"
            f"Deseja renomear o arquivo antes de salvá-lo?",
            reply_markup=reply_markup)
        return
    elif update.message.photo:
        file = update.message.photo[-1].get_file()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"foto_{timestamp}.jpg"
        context.user_data['temp_file'] = {
            'file_id': update.message.photo[-1].file_id,
            'nome': nome_arquivo,
            'tipo': 'photo'
        }
        # Ask if user wants to rename the file
        keyboard = [[
            InlineKeyboardButton("✏️ Renomear Foto",
                                 callback_data='renomear_antes_salvar')
        ],
                    [
                        InlineKeyboardButton(
                            "➡️ Continuar Sem Renomear",
                            callback_data='continuar_sem_renomear')
                    ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            f"📷 Foto: {nome_arquivo}\n\n"
            f"Deseja renomear a foto antes de salvá-la?",
            reply_markup=reply_markup)
        return
    else:
        update.message.reply_text(
            "❌ Por favor, envie um documento ou uma imagem.")
        return


def mostrar_opcoes_categoria(update: Update, context: CallbackContext) -> None:
    """Show category options for saving a file."""
    # Get existing categories
    categorias = list_categories()

    # Check if user already has a default category
    categoria_atual = context.user_data.get('categoria')

    # Get file name from temp storage
    temp_file = context.user_data.get('temp_file', {})
    nome_arquivo = temp_file.get('nome', 'arquivo')

    # Create keyboard with categories and option to create new
    keyboard = []

    # Add current category as first option if it exists
    if categoria_atual:
        keyboard.append([
            InlineKeyboardButton(f"📁 {categoria_atual} (Atual)",
                                 callback_data=f'save_to:{categoria_atual}')
        ])

    # Add other existing categories
    for cat in categorias:
        if cat != categoria_atual:
            keyboard.append([
                InlineKeyboardButton(f"📁 {cat}",
                                     callback_data=f'save_to:{cat}')
            ])

    # Add option to create new category
    keyboard.append([
        InlineKeyboardButton("➕ Criar Nova Categoria",
                             callback_data='nova_categoria')
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Ask for category
    if update.callback_query:
        update.callback_query.edit_message_text(
            f"📄 Arquivo: {nome_arquivo}\n\n"
            f"📂 Escolha uma categoria para salvar ou crie uma nova:",
            reply_markup=reply_markup)
    else:
        update.message.reply_text(
            f"📄 Arquivo: {nome_arquivo}\n\n"
            f"📂 Escolha uma categoria para salvar ou crie uma nova:",
            reply_markup=reply_markup)


def salvar_arquivo_categoria(update: Update, context: CallbackContext,
                             categoria: str) -> None:
    """Save a file to a specific category."""
    # Get file info from temp storage
    temp_file = context.user_data.get('temp_file')
    if not temp_file:
        return

    try:
        # Ensure the category directory exists
        pasta = ensure_category_exists(categoria)

        nome_arquivo = temp_file['nome']

        # Create the full path for the file
        caminho = os.path.join(pasta, nome_arquivo)

        # Check if file already exists
        if os.path.exists(caminho):
            # Add a timestamp to make the filename unique
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_base, extensao = os.path.splitext(nome_arquivo)
            nome_arquivo = f"{nome_base}_{timestamp}{extensao}"
            caminho = os.path.join(pasta, nome_arquivo)

        # Handle different types of files
        if temp_file['tipo'] == 'note':
            # Save note content to text file
            with open(caminho, 'w', encoding='utf-8') as f:
                f.write(temp_file['conteudo'])
        else:
            # Use the temporary file path to create the final file
            temp_file_path = temp_file['caminho']
            if os.path.exists(temp_file_path):
                # Copy the file from temp location to final destination
                with open(temp_file_path, 'rb') as source_file:
                    with open(caminho, 'wb') as dest_file:
                        dest_file.write(source_file.read())

                # Remove the temporary file
                try:
                    os.remove(temp_file_path)
                except Exception as e:
                    logger.error(f"Error removing temp file: {e}")

        # Set this as the current category for future uploads
        context.user_data['categoria'] = categoria

        # Create keyboard with options
        keyboard = [[
            InlineKeyboardButton(
                "👁️ Visualizar Arquivo",
                callback_data=f'visualizar:{categoria}/{nome_arquivo}')
        ],
                    [
                        InlineKeyboardButton(
                            "📂 Ver Categoria",
                            callback_data=f'voltar_categoria:{categoria}')
                    ],
                    [
                        InlineKeyboardButton("🔍 Menu Principal",
                                             callback_data='voltar_menu')
                    ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Determine success message based on file type
        if temp_file['tipo'] == 'note':
            success_message = f"✅ Nota salva com sucesso!\n📂 Categoria: {categoria}\n📄 Nome: {nome_arquivo}"
        else:
            success_message = f"✅ Arquivo salvo com sucesso!\n📂 Categoria: {categoria}\n📄 Nome: {nome_arquivo}"

        # Respond with success message
        return success_message, reply_markup

    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return f"❌ Erro ao salvar o arquivo: {str(e)}\nPor favor, tente novamente.", None
    finally:
        # Clean up temp data
        if 'temp_file' in context.user_data:
            del context.user_data['temp_file']


def salvar_arquivo(update: Update, context: CallbackContext) -> None:
    """Handle file uploads by asking if user wants to rename before saving."""
    message = update.message

    # Check if message contains a file
    if message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_type = 'document'
    elif message.photo:
        # Get the highest resolution photo
        file_id = message.photo[-1].file_id
        # Photos don't have filenames, so create one with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"photo_{timestamp}.jpg"
        file_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        file_name = message.video.file_name or f"video_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        file_type = 'video'
    elif message.audio:
        file_id = message.audio.file_id
        file_name = message.audio.file_name or f"audio_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        file_type = 'audio'
    elif message.voice:
        file_id = message.voice.file_id
        file_name = f"voice_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.ogg"
        file_type = 'voice'
    else:
        # Not a file
        message.reply_text(
            "❌ Formato não suportado. Por favor, envie documentos, fotos, vídeos ou áudios."
        )
        return

    # Download the file
    file = context.bot.get_file(file_id)

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        file.download(custom_path=temp.name)

        # Store file info in user_data
        context.user_data['temp_file'] = {
            'nome': file_name,
            'caminho': temp.name,
            'tipo': file_type,
            'file_id': file_id
        }

        # Ask if the user wants to rename the file before saving
        keyboard = [[
            InlineKeyboardButton("✏️ Renomear",
                                 callback_data='renomear_antes_salvar')
        ],
                    [
                        InlineKeyboardButton(
                            "✅ Continuar sem renomear",
                            callback_data='continuar_sem_renomear')
                    ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message.reply_text(
            f"🗂️ Arquivo recebido: {file_name}\n\n"
            f"Deseja renomear este arquivo antes de salvá-lo?",
            reply_markup=reply_markup)


def visualizar_arquivo(update: Update, context: CallbackContext) -> None:
    """Send the file for viewing."""
    try:
        # Extract file path from callback data
        file_path = context.user_data.get('current_file_path')
        if not file_path or '/' not in file_path:
            update.message.reply_text("❌ Arquivo não encontrado.")
            return

        category, filename = file_path.split('/', 1)
        full_path = os.path.join(BASE_DIR, category, filename)

        if not os.path.exists(full_path):
            update.message.reply_text("❌ Arquivo não encontrado.")
            return

        # Check if it's an image
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        _, ext = os.path.splitext(filename.lower())
        is_image = ext in image_extensions

        # Create keyboard with a Share button
        keyboard = [[
            InlineKeyboardButton("📤 Compartilhar",
                                 callback_data=f'compartilhar:{file_path}')
        ], [InlineKeyboardButton("🔙 Voltar", callback_data='voltar_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if is_image:
            # Send the image for viewing
            with open(full_path, 'rb') as f:
                update.message.reply_photo(
                    photo=f,
                    caption=f"📷 Imagem: {filename}\n📂 Categoria: {category}",
                    reply_markup=reply_markup)
        else:
            # Send as document
            with open(full_path, 'rb') as f:
                update.message.reply_document(
                    document=f,
                    caption=f"📄 Documento: {filename}\n📂 Categoria: {category}",
                    reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error viewing file: {e}")
        update.message.reply_text(f"❌ Erro ao visualizar o arquivo: {str(e)}")


def botao_clicado(update: Update, context: CallbackContext) -> None:
    """Handle button clicks from inline keyboards."""
    query = update.callback_query
    query.answer()  # Answer the callback query
    data = query.data

    # Handle delete file request
    if data.startswith('excluir_'):
        # Extract category and filename
        parts = data[len('excluir_'):].split('|')
        if len(parts) == 2:
            categoria, nome_arquivo = parts

            try:
                # Delete the file
                file_path = os.path.join(BASE_DIR, categoria, nome_arquivo)
                if os.path.exists(file_path):
                    os.remove(file_path)

                    # Send confirmation message
                    keyboard = [[
                        InlineKeyboardButton(
                            "🔙 Voltar para a categoria",
                            callback_data=f"listar_{categoria}")
                    ]]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    query.edit_message_text(
                        f"✅ Arquivo *{nome_arquivo}* excluído com sucesso da categoria *{categoria}*.",
                        reply_markup=reply_markup,
                        parse_mode='Markdown')
                else:
                    query.edit_message_text(f"❌ Arquivo não encontrado.")
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
                query.edit_message_text(f"❌ Erro ao excluir arquivo: {str(e)}")
            return

    # Rename file before saving
    if data == 'renomear_antes_salvar':
        try:
            temp_file = context.user_data.get('temp_file', {})
            nome_atual = temp_file.get('nome', '')

            query.edit_message_text(
                f"📝 Renomear Arquivo\n\n"
                f"Nome atual: {nome_atual}\n\n"
                f"Por favor, digite o novo nome para o arquivo:")
            context.user_data['modo'] = 'renomear_antes_salvar'
            return
        except Exception as e:
            logger.error(f"Error renaming before save: {e}")
            query.edit_message_text(
                f"❌ Erro ao preparar renomeação: {str(e)}\n"
                f"Por favor, tente novamente.")
            return

    # Continue without renaming
    elif data == 'continuar_sem_renomear':
        mostrar_opcoes_categoria(update, context)
        return

    # Handling text as note
    elif data == 'salvar_como_nota':
        try:
            # Get the temporary stored text
            text = context.user_data.get('temp_texto', '')

            if not text:
                query.edit_message_text("❌ Erro: texto não encontrado.")
                return

            # Ask for a title for the note
            query.edit_message_text("📝 Salvar Texto como Nota\n\n"
                                    "Digite um título para esta nota:")

            # Store text content and set mode
            context.user_data['nota_conteudo'] = text
            context.user_data['modo'] = 'criar_nota_titulo'

            # Clean up
            if 'temp_texto' in context.user_data:
                del context.user_data['temp_texto']

            return
        except Exception as e:
            logger.error(f"Error saving text as note: {e}")
            query.edit_message_text(f"❌ Erro ao salvar nota: {str(e)}\n"
                                    f"Por favor, tente novamente.")
            return

    # Ignore text message
    elif data == 'ignorar_texto':
        query.edit_message_text("✓ Mensagem ignorada.")

        # Clean up
        if 'temp_texto' in context.user_data:
            del context.user_data['temp_texto']

        return

    # Handle saving note with default title
    elif data == 'salvar_nota_padrao':
        try:
            # Check if temp_file exists
            if 'temp_file' not in context.user_data:
                query.edit_message_text("❌ Erro: nota não encontrada.")
                return

            # Get the temp file info and show category options
            mostrar_opcoes_categoria(update, context)
            return
        except Exception as e:
            logger.error(f"Error saving note with default title: {e}")
            query.edit_message_text(f"❌ Erro ao salvar nota: {str(e)}\n"
                                    f"Por favor, tente novamente.")
            return

    # Handle choosing title for note
    elif data == 'escolher_titulo_nota':
        try:
            # Ask for a title for the note
            query.edit_message_text(
                "📝 Escolher Título da Nota\n\n"
                "Digite um título personalizado para esta nota:")
            context.user_data['modo'] = 'renomear_antes_salvar'
            return
        except Exception as e:
            logger.error(f"Error when asking for note title: {e}")
            query.edit_message_text(
                f"❌ Erro ao preparar renomeação: {str(e)}\n"
                f"Por favor, tente novamente.")
            return

    # Create note option
    elif data == 'criar_nota':
        try:
            query.edit_message_text("📝 Criar Nova Nota\n\n"
                                    "Digite o título para sua nota:")
            context.user_data['modo'] = 'criar_nota_titulo'
            return
        except Exception as e:
            logger.error(f"Error creating note: {e}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Erro ao criar nota. Por favor, tente novamente.")
            return

    # Dashboard options
    if data == 'dashboard':
        from dashboard import get_dashboard_stats, create_dashboard_message, get_dashboard_keyboard

        # Get statistics
        stats = get_dashboard_stats()
        message = create_dashboard_message(stats)
        keyboard = get_dashboard_keyboard()

        try:
            if hasattr(query, 'message') and query.message:
                query.edit_message_text(text=message,
                                        reply_markup=keyboard,
                                        parse_mode='Markdown')
            else:
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=message,
                                         reply_markup=keyboard,
                                         parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error showing dashboard: {e}")
            # Send a new message instead of editing
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=message,
                                     reply_markup=keyboard,
                                     parse_mode='Markdown')
        return

    # Dashboard visualization options
    elif data == 'dashboard_bar':
        from dashboard import generate_category_bar_chart

        # Generate bar chart
        chart_buffer = generate_category_bar_chart()

        if chart_buffer:
            try:
                context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=chart_buffer,
                    caption=
                    "📊 *Gráfico de Barras - Arquivos por Categoria*\n\nUse /menu para voltar.",
                    parse_mode='Markdown')
                # Try to delete the original message
                try:
                    if hasattr(query, 'message') and query.message:
                        query.delete_message()
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")
            except Exception as e:
                logger.error(f"Error sending bar chart: {e}")
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Erro ao gerar o gráfico de barras.")
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=
                "❌ Não há dados suficientes para gerar o gráfico. Adicione arquivos às suas categorias primeiro."
            )
        return

    elif data == 'dashboard_pie':
        from dashboard import generate_category_pie_chart

        # Generate pie chart
        chart_buffer = generate_category_pie_chart()

        if chart_buffer:
            try:
                context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=chart_buffer,
                    caption=
                    "🍩 *Gráfico de Pizza - Distribuição de Arquivos por Categoria*\n\nUse /menu para voltar.",
                    parse_mode='Markdown')
                # Try to delete the original message
                try:
                    if hasattr(query, 'message') and query.message:
                        query.delete_message()
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")
            except Exception as e:
                logger.error(f"Error sending pie chart: {e}")
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Erro ao gerar o gráfico de pizza.")
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=
                "❌ Não há dados suficientes para gerar o gráfico. Adicione arquivos às suas categorias primeiro."
            )
        return

    elif data == 'dashboard_growth':
        from dashboard import generate_category_growth_chart

        # Generate growth chart
        chart_buffer = generate_category_growth_chart()

        if chart_buffer:
            try:
                context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=chart_buffer,
                    caption=
                    "📈 *Gráfico de Crescimento - Evolução de Arquivos por Categoria*\n\nUse /menu para voltar.",
                    parse_mode='Markdown')
                # Try to delete the original message
                try:
                    if hasattr(query, 'message') and query.message:
                        query.delete_message()
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")
            except Exception as e:
                logger.error(f"Error sending growth chart: {e}")
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Erro ao gerar o gráfico de crescimento.")
        else:
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=
                "❌ Não há dados suficientes para gerar o gráfico. Adicione arquivos às suas categorias primeiro."
            )
        return

    # Handle save to category
    if data.startswith('save_to:'):
        categoria = data.split(':', 1)[1]
        message, reply_markup = salvar_arquivo_categoria(
            update, context, categoria)
        if message:
            if hasattr(query, 'message') and query.message:
                query.edit_message_text(text=message,
                                        reply_markup=reply_markup)
            else:
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=message,
                                         reply_markup=reply_markup)
        return

    # Handle new category creation
    elif data == 'nova_categoria':
        query.edit_message_text("➕ Criar Nova Categoria\n\n"
                                "Digite o nome da nova categoria:")
        context.user_data['modo'] = 'nova_categoria'
        return

    # Handle viewing/sharing files
    elif data.startswith('visualizar:'):
        file_path = data.split(':', 1)[1]
        context.user_data['current_file_path'] = file_path

        # Get file info
        category, filename = file_path.split('/', 1)
        full_path = os.path.join(BASE_DIR, category, filename)

        if not os.path.exists(full_path):
            if hasattr(query, 'message') and query.message:
                query.edit_message_text("❌ Arquivo não encontrado.")
            else:
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text="❌ Arquivo não encontrado.")
            return

        # Check if it's an image
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        _, ext = os.path.splitext(filename.lower())
        is_image = ext in image_extensions

        # Create keyboard with Share, Delete and Back buttons
        keyboard = [[
            InlineKeyboardButton("📤 Compartilhar",
                                 callback_data=f'compartilhar:{file_path}')
        ],
                    [
                        InlineKeyboardButton(
                            "🗑️ Excluir",
                            callback_data=f'excluir_{category}|{filename}')
                    ],
                    [
                        InlineKeyboardButton(
                            "🔙 Voltar",
                            callback_data=f'voltar_categoria:{category}')
                    ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            if is_image:
                # Send the image for viewing
                with open(full_path, 'rb') as f:
                    context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=f,
                        caption=
                        f"📷 Imagem: {filename}\n📂 Categoria: {category}",
                        reply_markup=reply_markup)
            else:
                # Send as document
                with open(full_path, 'rb') as f:
                    context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=f,
                        caption=
                        f"📄 Documento: {filename}\n📂 Categoria: {category}",
                        reply_markup=reply_markup)

            # Try to delete the original message
            try:
                if hasattr(query, 'message') and query.message:
                    query.delete_message()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Erro ao enviar o arquivo: {str(e)}")

    elif data.startswith('compartilhar:'):
        file_path = data.split(':', 1)[1]
        category, filename = file_path.split('/', 1)
        full_path = os.path.join(BASE_DIR, category, filename)

        if not os.path.exists(full_path):
            if hasattr(query, 'message') and query.message:
                query.edit_message_text("❌ Arquivo não encontrado.")
            else:
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text="❌ Arquivo não encontrado.")
            return

        # Generate a shareable message
        share_text = (f"📁 Compartilhado do Organizador de Arquivos Bot\n\n"
                      f"📄 Arquivo: {filename}\n"
                      f"📂 Categoria: {category}\n\n"
                      f"Para acessar este arquivo, solicite ao proprietário.")

        # Create button to go back
        keyboard = [[
            InlineKeyboardButton("🔙 Voltar",
                                 callback_data=f'visualizar:{file_path}')
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            if hasattr(query, 'message') and query.message:
                query.edit_message_text(
                    text=f"🔗 Mensagem para compartilhar:\n\n{share_text}\n\n"
                    f"Copie a mensagem acima para compartilhar as informações do arquivo.",
                    reply_markup=reply_markup)
            else:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"🔗 Mensagem para compartilhar:\n\n{share_text}\n\n"
                    f"Copie a mensagem acima para compartilhar as informações do arquivo.",
                    reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error sharing file: {e}")
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"❌ Erro ao compartilhar: {str(e)}")

    elif data.startswith('voltar_categoria:'):
        category = data.split(':', 1)[1]
        # Show files in this category
        arquivos = list_files_in_category(category)

        # Create menu message
        if not arquivos:
            menu_text = f"📂 Categoria '{category}' está vazia.\nEnvie arquivos para adicionar a esta categoria."
            keyboard = [[
                InlineKeyboardButton("🔙 Voltar para Categorias",
                                     callback_data='categorias')
            ]]
        else:
            menu_text = f"📂 Arquivos na categoria '{category}':\nClique em um arquivo para visualizar:"
            # Create buttons for each file
            keyboard = []
            for arquivo in arquivos:
                file_path = f"{category}/{arquivo}"
                keyboard.append([
                    InlineKeyboardButton(
                        f"📄 {arquivo}",
                        callback_data=f'visualizar:{file_path}')
                ])

            # Add a back button
            keyboard.append([
                InlineKeyboardButton("🔙 Voltar para Categorias",
                                     callback_data='categorias')
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            if hasattr(query, 'message') and query.message:
                query.edit_message_text(text=menu_text,
                                        reply_markup=reply_markup)
            else:
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=menu_text,
                                         reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error showing category: {e}")
            # Send a new message instead of editing
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=menu_text,
                                     reply_markup=reply_markup)

    elif data == 'voltar_menu':
        # Go back to main menu
        keyboard = [
            [InlineKeyboardButton("📂 Categorias", callback_data='categorias')],
            [
                InlineKeyboardButton("➕ Nova Categoria",
                                     callback_data='criar_categoria_menu')
            ],
            [InlineKeyboardButton("🔍 Buscar Arquivo", callback_data='buscar')],
            [
                InlineKeyboardButton("📝 Renomear Arquivo",
                                     callback_data='renomear')
            ],
            [
                InlineKeyboardButton("❌ Excluir Arquivo",
                                     callback_data='excluir')
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            if hasattr(query, 'message') and query.message:
                query.edit_message_text(
                    text="🔍 Menu Principal - Escolha uma opção:",
                    reply_markup=reply_markup)
            else:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="🔍 Menu Principal - Escolha uma opção:",
                    reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error showing menu: {e}")
            # Send a new message instead of editing
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🔍 Menu Principal - Escolha uma opção:",
                reply_markup=reply_markup)

    # Menu options
    elif data == 'categorias':
        categorias = list_categories()

        if not categorias:
            menu_text = ("📂 Nenhuma categoria disponível ainda.\n"
                         "Clique em 'Nova Categoria' para criar uma.")
            keyboard = [[
                InlineKeyboardButton("➕ Nova Categoria",
                                     callback_data='criar_categoria_menu')
            ],
                        [
                            InlineKeyboardButton("🔙 Voltar ao Menu",
                                                 callback_data='voltar_menu')
                        ]]
        else:
            menu_text = ("📂 Categorias disponíveis:\n"
                         "Clique em uma categoria para ver os arquivos:")
            # Create buttons for each category
            keyboard = []
            for cat in categorias:
                keyboard.append([
                    InlineKeyboardButton(
                        f"📁 {cat}", callback_data=f'voltar_categoria:{cat}')
                ])

            # Add buttons to create new category and go back
            keyboard.append([
                InlineKeyboardButton("➕ Nova Categoria",
                                     callback_data='criar_categoria_menu')
            ])
            keyboard.append([
                InlineKeyboardButton("🔙 Voltar ao Menu",
                                     callback_data='voltar_menu')
            ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            if hasattr(query, 'message') and query.message:
                query.edit_message_text(text=menu_text,
                                        reply_markup=reply_markup)
            else:
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=menu_text,
                                         reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error showing categories: {e}")
            # Send a new message instead of editing
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=menu_text,
                                     reply_markup=reply_markup)

    elif data == 'criar_categoria_menu':
        try:
            if hasattr(query, 'message') and query.message:
                query.edit_message_text("➕ Criar Nova Categoria\n\n"
                                        "Digite o nome da nova categoria:")
            else:
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text="➕ Criar Nova Categoria\n\n"
                                         "Digite o nome da nova categoria:")
            context.user_data['modo'] = 'nova_categoria'
        except Exception as e:
            logger.error(f"Error showing create category: {e}")
            # Send a new message instead of editing
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="➕ Criar Nova Categoria\n\n"
                                     "Digite o nome da nova categoria:")
            context.user_data['modo'] = 'nova_categoria'

    elif data == 'buscar':
        try:
            if hasattr(query, 'message') and query.message:
                query.edit_message_text(
                    "🔍 Busca de Arquivos\n\n"
                    "Digite o nome (ou parte do nome) do arquivo que você está procurando:"
                )
            else:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="🔍 Busca de Arquivos\n\n"
                    "Digite o nome (ou parte do nome) do arquivo que você está procurando:"
                )
            context.user_data['modo'] = 'buscar'
        except Exception as e:
            logger.error(f"Error showing search: {e}")
            # Send a new message instead of editing
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🔍 Busca de Arquivos\n\n"
                "Digite o nome (ou parte do nome) do arquivo que você está procurando:"
            )
            context.user_data['modo'] = 'buscar'

    elif data == 'renomear':
        try:
            if hasattr(query, 'message') and query.message:
                query.edit_message_text(
                    "📝 Renomear Arquivo\n\n"
                    "Digite no formato:\n`categoria/nome_antigo.ext -> novo_nome.ext`\n\n"
                    "Exemplo: `documentos/contrato.pdf -> contrato_2023.pdf`",
                    parse_mode='Markdown')
            else:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="📝 Renomear Arquivo\n\n"
                    "Digite no formato:\n`categoria/nome_antigo.ext -> novo_nome.ext`\n\n"
                    "Exemplo: `documentos/contrato.pdf -> contrato_2023.pdf`",
                    parse_mode='Markdown')
            context.user_data['modo'] = 'renomear'
        except Exception as e:
            logger.error(f"Error showing rename: {e}")
            # Send a new message instead of editing
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📝 Renomear Arquivo\n\n"
                "Digite no formato:\n`categoria/nome_antigo.ext -> novo_nome.ext`\n\n"
                "Exemplo: `documentos/contrato.pdf -> contrato_2023.pdf`",
                parse_mode='Markdown')
            context.user_data['modo'] = 'renomear'

    elif data == 'excluir':
        try:
            if hasattr(query, 'message') and query.message:
                query.edit_message_text(
                    "❌ Excluir Arquivo\n\n"
                    "Digite o caminho do arquivo a ser excluído no formato:\n"
                    "`categoria/arquivo.ext`\n\n"
                    "Exemplo: `fotos/imagem.jpg`",
                    parse_mode='Markdown')
            else:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Excluir Arquivo\n\n"
                    "Digite o caminho do arquivo a ser excluído no formato:\n"
                    "`categoria/arquivo.ext`\n\n"
                    "Exemplo: `fotos/imagem.jpg`",
                    parse_mode='Markdown')
            context.user_data['modo'] = 'excluir'
        except Exception as e:
            logger.error(f"Error showing delete: {e}")
            # Send a new message instead of editing
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Excluir Arquivo\n\n"
                "Digite o caminho do arquivo a ser excluído no formato:\n"
                "`categoria/arquivo.ext`\n\n"
                "Exemplo: `fotos/imagem.jpg`",
                parse_mode='Markdown')
            context.user_data['modo'] = 'excluir'


def tratar_texto(update: Update, context: CallbackContext) -> None:
    """Handle text messages based on the current mode."""
    modo = context.user_data.get('modo')

    if not modo:
        # If user sends a plain text message with no specific mode, assume it's a note
        text = update.message.text

        # Check if text is not too short (to avoid accidental messages)
        if len(text) > 3:
            # Ask for a title for the note
            keyboard = [[
                InlineKeyboardButton("Salvar com título padrão",
                                     callback_data='salvar_nota_padrao')
            ],
                        [
                            InlineKeyboardButton(
                                "Escolher título",
                                callback_data='escolher_titulo_nota')
                        ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Store the content temporarily
            context.user_data['temp_nota_conteudo'] = text

            # Create timestamp for unique naming
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"nota_{timestamp}.txt"

            # Save as temp file
            context.user_data['temp_file'] = {
                'nome': nome_arquivo,
                'tipo': 'note',
                'conteudo': text
            }

            # Ask the user if they want to customize the title
            update.message.reply_text(
                "📝 *Nota de Texto Detectada*\n\n"
                "Deseja escolher um título personalizado ou salvar com título padrão?",
                reply_markup=reply_markup,
                parse_mode='Markdown')
            return
        else:
            update.message.reply_text(
                "Use /menu para acessar as opções do bot.")
            return

    if modo == 'renomear_antes_salvar':
        # Handle renaming before saving
        novo_nome = update.message.text.strip()

        if not novo_nome:
            update.message.reply_text(
                "❌ Por favor, forneça um nome válido para o arquivo.")
            return

        # Update file name in temp storage
        if 'temp_file' in context.user_data:
            # Preserve file extension if there is one
            temp_file = context.user_data['temp_file']
            nome_atual = temp_file.get('nome', '')

            # Check if the original file has an extension and new name doesn't
            if '.' in nome_atual and not '.' in novo_nome:
                extensao = nome_atual.split('.')[-1]  # Get extension
                novo_nome = f"{novo_nome}.{extensao}"  # Add extension to new name

            context.user_data['temp_file']['nome'] = novo_nome

            # Show category options
            mostrar_opcoes_categoria(update, context)
        else:
            update.message.reply_text(
                "❌ Erro: Nenhum arquivo para renomear. Por favor, envie o arquivo novamente."
            )

        context.user_data.pop('modo', None)
        return

    elif modo == 'criar_nota_titulo':
        # Get the title for the note
        titulo = update.message.text.strip()

        if not titulo:
            update.message.reply_text(
                "❌ Por favor, forneça um título válido para a nota.")
            return

        # Store title and ask for content
        context.user_data['nota_titulo'] = titulo
        context.user_data['modo'] = 'criar_nota_conteudo'

        update.message.reply_text(
            f"📝 Título da nota: {titulo}\n\n"
            f"Agora, por favor, digite o conteúdo da sua nota:")
        return

    elif modo == 'criar_nota_conteudo':
        # Get the content of the note
        conteudo = update.message.text
        titulo = context.user_data.get('nota_titulo', 'Nota sem título')

        if not conteudo:
            update.message.reply_text(
                "❌ Por favor, forneça algum conteúdo para a nota.")
            return

        # Create a text file with the note
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"{titulo}_{timestamp}.txt"

        # Clean up filename
        nome_arquivo = nome_arquivo.replace('/', '_').replace('\\', '_')

        # Store note info for saving
        context.user_data['temp_file'] = {
            'nome': nome_arquivo,
            'tipo': 'note',
            'conteudo': conteudo
        }

        # Show category options for saving the note
        mostrar_opcoes_categoria(update, context)

        context.user_data.pop('modo', None)
        context.user_data.pop('nota_titulo', None)
        return

    elif modo == 'nova_categoria':
        # Handle new category creation
        nome_categoria = update.message.text.strip()

        if not nome_categoria:
            update.message.reply_text(
                "❌ Por favor, forneça um nome válido para a categoria.")
            return

        # Check if we need to save a file to this category
        if context.user_data.get('temp_file'):
            # We have a file waiting to be saved
            message, reply_markup = salvar_arquivo_categoria(
                update, context, nome_categoria)
            update.message.reply_text(text=message, reply_markup=reply_markup)
        else:
            # Just create the category
            ensure_category_exists(nome_categoria)
            context.user_data['categoria'] = nome_categoria

            # Create keyboard with options
            keyboard = [[
                InlineKeyboardButton(
                    "📂 Ver Categoria",
                    callback_data=f'voltar_categoria:{nome_categoria}')
            ],
                        [
                            InlineKeyboardButton("🔍 Menu Principal",
                                                 callback_data='voltar_menu')
                        ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            update.message.reply_text(
                f"✅ Categoria '{nome_categoria}' criada com sucesso!\n"
                f"Esta agora é sua categoria padrão para upload de arquivos.",
                reply_markup=reply_markup)

        context.user_data.pop('modo', None)

    elif modo == 'buscar':
        termo = update.message.text.lower()

        if len(termo) < 3:
            update.message.reply_text(
                "🔍 Por favor, digite pelo menos 3 caracteres para a busca.")
            return

        try:
            resultados = search_files(termo)

            if resultados:
                # Create buttons for each file
                keyboard = []
                for resultado in resultados:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"📄 {resultado}",
                            callback_data=f'visualizar:{resultado}')
                    ])

                # Add a back button
                keyboard.append([
                    InlineKeyboardButton("🔙 Voltar ao Menu",
                                         callback_data='voltar_menu')
                ])
                reply_markup = InlineKeyboardMarkup(keyboard)

                update.message.reply_text(
                    f"🔍 Resultado da busca por '{termo}':\nClique em um arquivo para visualizar:",
                    reply_markup=reply_markup)
            else:
                update.message.reply_text(
                    f"🔍 Nenhum arquivo encontrado para '{termo}'.")
        except Exception as e:
            logger.error(f"Error during search: {e}")
            update.message.reply_text(f"❌ Erro durante a busca: {str(e)}")
        finally:
            context.user_data.pop('modo', None)

    elif modo == 'renomear':
        try:
            entrada = update.message.text.strip()

            if '->' not in entrada:
                update.message.reply_text(
                    "❌ Formato inválido. Use: categoria/nome_antigo.ext -> novo_nome.ext"
                )
                return

            parte1, novo_nome = entrada.split('->')

            if '/' not in parte1:
                update.message.reply_text(
                    "❌ Formato inválido. Especifique a categoria: categoria/nome_antigo.ext"
                )
                return

            categoria, nome_antigo = parte1.strip().split('/')
            novo_nome = novo_nome.strip()

            rename_file(categoria, nome_antigo, novo_nome)

            update.message.reply_text(f"✅ Arquivo renomeado com sucesso!\n"
                                      f"📂 Categoria: {categoria}\n"
                                      f"📄 De: {nome_antigo}\n"
                                      f"📄 Para: {novo_nome}")

        except FileNotFoundError:
            update.message.reply_text(
                "❌ Arquivo não encontrado. Verifique o nome e a categoria.")
        except FileExistsError:
            update.message.reply_text(
                "❌ Já existe um arquivo com este nome na categoria.")
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            update.message.reply_text(
                f"❌ Erro ao renomear o arquivo: {str(e)}")
        finally:
            context.user_data.pop('modo', None)

    elif modo == 'excluir':
        try:
            entrada = update.message.text.strip()

            if '/' not in entrada:
                update.message.reply_text(
                    "❌ Formato inválido. Use: categoria/arquivo.ext")
                return

            categoria, nome = entrada.split('/')

            delete_file(categoria, nome)

            update.message.reply_text(f"✅ Arquivo excluído com sucesso!\n"
                                      f"📂 Categoria: {categoria}\n"
                                      f"📄 Arquivo: {nome}")

        except FileNotFoundError:
            update.message.reply_text(
                "❌ Arquivo não encontrado. Verifique o nome e a categoria.")
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            update.message.reply_text(f"❌ Erro ao excluir o arquivo: {str(e)}")
        finally:
            context.user_data.pop('modo', None)


def main() -> None:
    """Start the bot."""
    # Get token from environment variable with fallback
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not TOKEN:
        logger.error(
            "No token provided. Set the TELEGRAM_BOT_TOKEN environment variable."
        )
        print(
            "Please set the TELEGRAM_BOT_TOKEN environment variable with your bot token from BotFather."
        )
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
    dispatcher.add_handler(
        MessageHandler(Filters.document | Filters.photo, salvar_arquivo))

    # Handle button clicks in inline keyboards
    dispatcher.add_handler(CallbackQueryHandler(botao_clicado))

    # Handle text messages that are not commands
    dispatcher.add_handler(
        MessageHandler(Filters.text & ~Filters.command, tratar_texto))

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
