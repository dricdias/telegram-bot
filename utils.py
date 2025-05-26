import os
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Base directory for storing files
BASE_DIR = 'arquivos'

def get_category_path(category_name):
    """Get the full path for a category directory."""
    category_path = os.path.join(BASE_DIR, category_name)
    return category_path

def ensure_category_exists(category_name):
    """Ensure that a category directory exists."""
    category_path = get_category_path(category_name)
    os.makedirs(category_path, exist_ok=True)
    return category_path

def get_file_path(category_name, file_name):
    """Get the full path for a file within a category."""
    return os.path.join(get_category_path(category_name), file_name)

def list_categories():
    """List all available categories."""
    if not os.path.exists(BASE_DIR):
        return []
    return [d for d in os.listdir(BASE_DIR) 
            if os.path.isdir(os.path.join(BASE_DIR, d))]

def list_files_in_category(category_name):
    """List all files in a specific category."""
    category_path = get_category_path(category_name)
    if not os.path.exists(category_path):
        return []
    return [f for f in os.listdir(category_path) 
            if os.path.isfile(os.path.join(category_path, f))]

def search_files(term):
    """Search for files across all categories matching a term."""
    results = []
    for category in list_categories():
        category_path = get_category_path(category)
        for file_name in os.listdir(category_path):
            if term.lower() in file_name.lower():
                results.append(f"{category}/{file_name}")
    return results

def rename_file(category, old_name, new_name):
    """Rename a file within a category."""
    old_path = get_file_path(category, old_name)
    new_path = get_file_path(category, new_name)
    
    if not os.path.exists(old_path):
        raise FileNotFoundError(f"File {old_name} not found in {category}")
    
    if os.path.exists(new_path):
        raise FileExistsError(f"File {new_name} already exists in {category}")
    
    os.rename(old_path, new_path)
    logger.info(f"Renamed file: {old_path} -> {new_path}")
    return True

def delete_file(category, file_name):
    """Delete a file from a category."""
    file_path = get_file_path(category, file_name)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_name} not found in {category}")
    
    os.remove(file_path)
    logger.info(f"Deleted file: {file_path}")
    return True
