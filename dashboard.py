import os
import io
import datetime
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator
import matplotlib.dates as mdates
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from utils import list_categories, list_files_in_category, BASE_DIR

def count_files_by_date(category_name):
    """Count files by creation date for a specific category."""
    category_path = os.path.join(BASE_DIR, category_name)
    if not os.path.exists(category_path):
        return {}
    
    # Dictionary to store dates and counts
    date_counts = {}
    
    for file_name in os.listdir(category_path):
        file_path = os.path.join(category_path, file_name)
        if os.path.isfile(file_path):
            # Get creation time and convert to date
            create_time = os.path.getctime(file_path)
            date = datetime.datetime.fromtimestamp(create_time).strftime('%Y-%m-%d')
            
            # Increment count for this date
            date_counts[date] = date_counts.get(date, 0) + 1
    
    return date_counts

def generate_category_growth_chart(categories=None):
    """Generate a chart showing category growth over time."""
    if categories is None:
        categories = list_categories()
    
    if not categories:
        return None
    
    # Setup the plot
    plt.figure(figsize=(10, 6))
    plt.style.use('ggplot')
    
    # Colors for different categories
    colors = plt.cm.tab10.colors
    
    # For each category
    for i, category in enumerate(categories):
        date_counts = count_files_by_date(category)
        
        if not date_counts:
            continue
        
        # Sort dates
        dates = sorted(date_counts.keys())
        counts = [date_counts[date] for date in dates]
        
        # Convert string dates to datetime for plotting
        x_dates = [datetime.datetime.strptime(date, '%Y-%m-%d') for date in dates]
        
        # Cumulative sum to show growth
        cumulative_counts = np.cumsum(counts)
        
        # Plot with animation effect (marker size indicates activity)
        plt.plot(x_dates, cumulative_counts, '-o', label=category, 
                 color=colors[i % len(colors)], linewidth=2,
                 markersize=[4 + min(count * 2, 10) for count in counts])
    
    # Add labels and title with styling
    plt.title('Crescimento de Arquivos por Categoria', fontsize=16, fontweight='bold')
    plt.xlabel('Data', fontsize=12)
    plt.ylabel('Número Total de Arquivos', fontsize=12)
    
    # Format x-axis to show dates nicely
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=2))
    
    # Add grid and legend
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(title='Categorias', fontsize=10, title_fontsize=12)
    
    # Tight layout
    plt.tight_layout()
    
    # Instead of showing, save to a bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    
    return buf

def generate_category_pie_chart():
    """Generate a pie chart showing the distribution of files across categories."""
    categories = list_categories()
    
    if not categories:
        return None
    
    # Count files in each category
    counts = []
    labels = []
    
    for category in categories:
        files = list_files_in_category(category)
        if files:
            counts.append(len(files))
            labels.append(category)
    
    if not counts:
        return None
    
    # Create figure
    plt.figure(figsize=(8, 8))
    plt.style.use('ggplot')
    
    # Create pie chart with explosion effect for largest category
    explode = [0.1 if c == max(counts) else 0 for c in counts]
    
    # Create pie chart with custom colors and styling
    wedges, texts, autotexts = plt.pie(
        counts, 
        explode=explode,
        labels=labels, 
        autopct='%1.1f%%',
        shadow=True, 
        startangle=90,
        textprops={'fontsize': 12, 'fontweight': 'bold'},
        wedgeprops={'edgecolor': 'w', 'linewidth': 2}
    )
    
    # Style the percentage text
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    # Equal aspect ratio ensures that pie is drawn as a circle
    plt.axis('equal')
    
    # Add title with styling
    plt.title('Distribuição de Arquivos por Categoria', fontsize=16, fontweight='bold')
    
    # Tight layout
    plt.tight_layout()
    
    # Save to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    
    return buf

def generate_category_bar_chart():
    """Generate a bar chart showing file counts by category."""
    categories = list_categories()
    
    if not categories:
        return None
    
    # Count files in each category
    counts = []
    
    for category in categories:
        files = list_files_in_category(category)
        counts.append(len(files))
    
    if not any(counts):
        return None
    
    # Create figure
    plt.figure(figsize=(10, 6))
    plt.style.use('ggplot')
    
    # Create animated bar chart
    bars = plt.bar(categories, counts, color=plt.cm.viridis(np.linspace(0, 1, len(categories))))
    
    # Add data labels on top of bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                 f'{int(height)}', ha='center', va='bottom', fontweight='bold')
    
    # Add styling
    plt.title('Número de Arquivos por Categoria', fontsize=16, fontweight='bold')
    plt.xlabel('Categoria', fontsize=12)
    plt.ylabel('Número de Arquivos', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    
    # Ensure y-axis starts at 0 and uses integers
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    
    # Add grid
    plt.grid(True, linestyle='--', alpha=0.7, axis='y')
    
    # Tight layout
    plt.tight_layout()
    
    # Save to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    
    return buf

def get_dashboard_stats():
    """Get statistics for the dashboard."""
    categories = list_categories()
    total_files = 0
    largest_category = None
    largest_category_count = 0
    newest_category = None
    newest_category_time = 0
    
    if categories:
        for category in categories:
            category_path = os.path.join(BASE_DIR, category)
            files = list_files_in_category(category)
            file_count = len(files)
            total_files += file_count
            
            # Check if this is the largest category
            if file_count > largest_category_count:
                largest_category = category
                largest_category_count = file_count
            
            # Check creation time of category
            if os.path.exists(category_path):
                create_time = os.path.getctime(category_path)
                if create_time > newest_category_time:
                    newest_category_time = create_time
                    newest_category = category
    
    stats = {
        'total_categories': len(categories),
        'total_files': total_files,
        'largest_category': largest_category,
        'largest_category_count': largest_category_count,
        'newest_category': newest_category,
        'newest_category_time': datetime.datetime.fromtimestamp(newest_category_time).strftime('%d/%m/%Y') if newest_category_time else None
    }
    
    return stats

def create_dashboard_message(stats):
    """Create a formatted dashboard message with stats."""
    if not stats['total_categories']:
        return "📊 Dashboard\n\nNenhuma categoria encontrada. Use o comando /menu e crie uma categoria para começar."
    
    message = "📊 *DASHBOARD DE CATEGORIAS*\n\n"
    message += f"📁 *Total de Categorias:* {stats['total_categories']}\n"
    message += f"📄 *Total de Arquivos:* {stats['total_files']}\n\n"
    
    if stats['largest_category']:
        message += f"🏆 *Categoria Mais Utilizada:* {stats['largest_category']} ({stats['largest_category_count']} arquivos)\n"
    
    if stats['newest_category']:
        message += f"🆕 *Categoria Mais Recente:* {stats['newest_category']} ({stats['newest_category_time']})\n"
    
    message += "\nEscolha uma visualização abaixo para analisar suas categorias:"
    
    return message

def get_dashboard_keyboard():
    """Create the dashboard keyboard with visualization options."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Gráfico de Barras", callback_data='dashboard_bar'),
            InlineKeyboardButton("🍩 Gráfico de Pizza", callback_data='dashboard_pie')
        ],
        [
            InlineKeyboardButton("📈 Crescimento", callback_data='dashboard_growth'),
            InlineKeyboardButton("🔄 Atualizar Stats", callback_data='dashboard')
        ],
        [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data='voltar_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)