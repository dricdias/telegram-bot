import os
import logging
import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from utils import (
    BASE_DIR, ensure_category_exists, list_categories,
    list_files_in_category, search_files, rename_file,
    delete_file
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Command handlers
def start(update, context):
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

def menu(update, context):
    """Display the main menu with interactive buttons."""
    keyboard = [
        [InlineKeyboardButton("📂 Categorias", callback_data='categorias')],
        [InlineKeyboardButton("🔍 Buscar Arquivo", callback_data='buscar')],
        [InlineKeyboardButton("📝 Renomear Arquivo", callback_data='renomear')],
        [InlineKeyboardButton("❌ Excluir Arquivo", callback_data='excluir')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "🔍 Menu Principal - Escolha uma opção:", 
        reply_markup=reply_markup
    )

def categoria(update, context):
    """Set the current category for the user."""
    if not context.args:
        update.message.reply_text(
            "❌ Uso incorreto. Use: /categoria <nome>\n"
            "Exemplo: /categoria documentos"
        )
        return
    
    nome = ' '.join(context.args)
    context.user_data['categoria'] = nome
    
    # Ensure the category directory exists
    ensure_category_exists(nome)
    
    update.message.reply_text(
        f"✅ Categoria atual definida: 📁 {nome}\n"
        f"Todos os arquivos enviados serão salvos nesta categoria."
    )

def listar(update, context):
    """List files in a specific category."""
    if not context.args:
        update.message.reply_text(
            "❌ Uso incorreto. Use: /listar <categoria>\n"
            "Exemplo: /listar documentos"
        )
        return
    
    nome = ' '.join(context.args)
    categoria_path = os.path.join(BASE_DIR, nome)
    
    if not os.path.exists(categoria_path):
        update.message.reply_text(
            f"❌ Categoria '{nome}' não encontrada.\n"
            f"Use /categoria {nome} para criar esta categoria."
        )
        return
    
    arquivos = list_files_in_category(nome)
    
    if not arquivos:
        update.message.reply_text(
            f"📂 Categoria '{nome}' está vazia.\n"
            f"Envie arquivos depois de usar /categoria {nome}"
        )
    else:
        texto = "\n".join([f"📄 {arquivo}" for arquivo in arquivos])
        update.message.reply_text(
            f"📂 Arquivos na categoria '{nome}':\n\n{texto}"
        )

def salvar_arquivo(update, context):
    """Save a file or photo to the current category."""
    # Get the current category or use 'geral' as default
    categoria = context.user_data.get('categoria', 'geral')
    
    # Ensure the category directory exists
    pasta = ensure_category_exists(categoria)
    
    file = None
    nome_arquivo = "arquivo"
    
    try:
        if update.message.document:
            file = update.message.document.get_file()
            nome_arquivo = update.message.document.file_name
        elif update.message.photo:
            file = update.message.photo[-1].get_file()
            # Generate a more descriptive filename for photos
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_arquivo = f"foto_{timestamp}.jpg"
        else:
            update.message.reply_text(
                "❌ Por favor, envie um documento ou uma imagem."
            )
            return
        
        # Create the full path for the file
        caminho = os.path.join(pasta, nome_arquivo)
        
        # Check if file already exists
        if os.path.exists(caminho):
            # Add a timestamp to make the filename unique
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_base, extensao = os.path.splitext(nome_arquivo)
            nome_arquivo = f"{nome_base}_{timestamp}{extensao}"
            caminho = os.path.join(pasta, nome_arquivo)
        
        # Download the file
        file.download(caminho)
        
        # Respond with success message
        update.message.reply_text(
            f"✅ Arquivo salvo com sucesso!\n"
            f"📂 Categoria: {categoria}\n"
            f"📄 Nome do arquivo: {nome_arquivo}"
        )
        
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        update.message.reply_text(
            f"❌ Erro ao salvar o arquivo: {str(e)}\n"
            f"Por favor, tente novamente."
        )

def botao_clicado(update, context):
    """Handle button clicks from inline keyboards."""
    query = update.callback_query
    query.answer()  # Answer the callback query
    data = query.data
    
    if data == 'categorias':
        categorias = list_categories()
        if not categorias:
            query.edit_message_text(
                "📂 Nenhuma categoria disponível ainda.\n"
                "Use /categoria <nome> para criar uma nova categoria."
            )
        else:
            texto = "\n".join([f"📁 {cat}" for cat in categorias])
            query.edit_message_text(
                f"📂 Categorias disponíveis:\n\n{texto}\n\n"
                f"Use /listar <categoria> para ver os arquivos em uma categoria."
            )
    
    elif data == 'buscar':
        query.edit_message_text(
            "🔍 Busca de Arquivos\n\n"
            "Digite o nome (ou parte do nome) do arquivo que você está procurando:"
        )
        context.user_data['modo'] = 'buscar'
    
    elif data == 'renomear':
        query.edit_message_text(
            "📝 Renomear Arquivo\n\n"
            "Digite no formato:\n`categoria/nome_antigo.ext -> novo_nome.ext`\n\n"
            "Exemplo: `documentos/contrato.pdf -> contrato_2023.pdf`", 
            parse_mode='Markdown'
        )
        context.user_data['modo'] = 'renomear'
    
    elif data == 'excluir':
        query.edit_message_text(
            "❌ Excluir Arquivo\n\n"
            "Digite o caminho do arquivo a ser excluído no formato:\n"
            "`categoria/arquivo.ext`\n\n"
            "Exemplo: `fotos/imagem.jpg`",
            parse_mode='Markdown'
        )
        context.user_data['modo'] = 'excluir'

def tratar_texto(update, context):
    """Handle text messages based on the current mode."""
    modo = context.user_data.get('modo')
    
    if not modo:
        update.message.reply_text(
            "Use /menu para acessar as opções do bot."
        )
        return
    
    if modo == 'buscar':
        termo = update.message.text.lower()
        
        if len(termo) < 3:
            update.message.reply_text(
                "🔍 Por favor, digite pelo menos 3 caracteres para a busca."
            )
            return
        
        try:
            resultados = search_files(termo)
            
            if resultados:
                texto = "\n".join([f"📄 {resultado}" for resultado in resultados])
                update.message.reply_text(
                    f"🔍 Resultado da busca por '{termo}':\n\n{texto}"
                )
            else:
                update.message.reply_text(
                    f"🔍 Nenhum arquivo encontrado para '{termo}'."
                )
        except Exception as e:
            logger.error(f"Error during search: {e}")
            update.message.reply_text(
                f"❌ Erro durante a busca: {str(e)}"
            )
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
            
            update.message.reply_text(
                f"✅ Arquivo renomeado com sucesso!\n"
                f"📂 Categoria: {categoria}\n"
                f"📄 De: {nome_antigo}\n"
                f"📄 Para: {novo_nome}"
            )
            
        except FileNotFoundError:
            update.message.reply_text(
                "❌ Arquivo não encontrado. Verifique o nome e a categoria."
            )
        except FileExistsError:
            update.message.reply_text(
                "❌ Já existe um arquivo com este nome na categoria."
            )
        except Exception as e:
            logger.error(f"Error renaming file: {e}")
            update.message.reply_text(
                f"❌ Erro ao renomear o arquivo: {str(e)}"
            )
        finally:
            context.user_data.pop('modo', None)
    
    elif modo == 'excluir':
        try:
            entrada = update.message.text.strip()
            
            if '/' not in entrada:
                update.message.reply_text(
                    "❌ Formato inválido. Use: categoria/arquivo.ext"
                )
                return
            
            categoria, nome = entrada.split('/')
            
            delete_file(categoria, nome)
            
            update.message.reply_text(
                f"✅ Arquivo excluído com sucesso!\n"
                f"📂 Categoria: {categoria}\n"
                f"📄 Arquivo: {nome}"
            )
            
        except FileNotFoundError:
            update.message.reply_text(
                "❌ Arquivo não encontrado. Verifique o nome e a categoria."
            )
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            update.message.reply_text(
                f"❌ Erro ao excluir o arquivo: {str(e)}"
            )
        finally:
            context.user_data.pop('modo', None)
