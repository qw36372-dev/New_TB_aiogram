"""
Генерация PDF‑сертификата о прохождении теста.
Использует ReportLab.
"""
from pathlib import Path
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config.settings import settings
from .models import TestResult

async def generate_certificate(result: TestResult, bot_username: str) -> Path:
    """
    Генерирует PDF‑сертификат.
    
    Returns:
        Путь к файлу для отправки.
    """
    filename = settings.certs_dir / f"cert_{result.user_data.full_name.replace(' ', '_')}_{int(datetime.now().timestamp())}.pdf"
    
    doc = SimpleDocTemplate(str(filename), pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Кастомный стиль для заголовка
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        textColor=colors.darkblue,
        spaceAfter=30,
        alignment=1  # Центр
    )
    
    # Русский шрифт (если есть в системе, иначе Courier)
    try:
        pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
        font_name = 'DejaVuSans'
    except:
        font_name = 'Helvetica'
    
    # Заголовок
    story.append(Paragraph("СЕРТИФИКАТ<br/><br/>о прохождении тестирования", title_style))
    story.append(Spacer(1, 1*cm))
    
    # Данные
    fields = [
        f"Ф.И.О.: {result.user_data.full_name}",
        f"Должность: {result.user_data.position}",
        f"Подразделение: {result.user_data.department}",
        f"Специализация: {result.user_data.specialization.replace('_', ' ').title()}",
        f"Уровень сложности: {result.user_data.difficulty.value.capitalize()}",
        f"Оценка: {result.grade}",
        f"Количество правильных ответов: {result.correct_count} из {result.total_questions}",
        f"Процент правильных ответов: {result.percentage:.0f}%",
        f"Время тестирования: {result.elapsed_time}",
        f"Дата: {datetime.now().strftime('%d.%m.%Y')}",
        f"Бот: @{bot_username}"
    ]
    
    for field in fields:
        p = Paragraph(field, styles['Normal'], fontName=font_name)
        story.append(p)
        story.append(Spacer(1, 0.5*cm))
    
    doc.build(story)
    return filename
