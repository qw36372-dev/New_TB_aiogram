"""
Логотип и приветствие (читается из logo.txt).
"""
from pathlib import Path
from config.settings import settings

LOGO_PATH = settings.assets_dir / "logo.txt"

def get_logo_text() -> str:
    """Возвращает текст логотипа."""
    if LOGO_PATH.exists():
        with open(LOGO_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    return "🚀 ФЕДЕРАЛЬНАЯ СЛУЖБА СУДЕБНЫХ ПРИСТАВОВ 🚀\nВыберите специализацию!"
