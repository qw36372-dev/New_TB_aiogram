"""
Модели данных для вопросов, тестов, пользователей.
Использует Pydantic для валидации JSON из файлов вопросов.
"""
from dataclasses import dataclass, field
from typing import List, Set, Optional
from pydantic import BaseModel, Field, validator
import asyncio

from .enum import Difficulty
from .timers import TestTimer

class AnswerOption:
    """Вариант ответа."""
    text: str
    index: int  # 1-based для отображения

class Question(BaseModel):
    """Вопрос из библиотеки."""
    question: str = Field(..., min_length=1)
    options: List[str] = Field(..., min_items=3, max_items=6)
    correct_answers: Set[int] = Field(..., min_items=1)  # Индексы правильных (1-based)
    
    @validator('correct_answers')
    def validate_correct(cls, v):
        if not v:
            raise ValueError('Должен быть хотя бы один правильный ответ')
        return v

class UserData(BaseModel):
    """Данные пользователя."""
    full_name: str
    position: str
    department: str
    specialization: str
    difficulty: Difficulty

class TestResult(BaseModel):
    """Результат теста."""
    user: UserData
    correct_count: int
    total_questions: int
    grade: str
    percentage: float
    elapsed_time: str  # "15:51" формат

@dataclass
class CurrentTestState:
    """Текущее состояние теста пользователя."""
    user_id: int
    questions: List[Question]
    timer: Optional[TestTimer] = None
    answers_history: List[Set[int]] = field(default_factory=list)
    current_question_idx: int = 0
    selected_answers: Set[int] = field(default_factory=set)
    start_time: float = None
    timer_task: Optional[asyncio.Task] = None
    full_name: str = ""
    position: str = ""
    department: str = ""
    specialization: str = ""
    difficulty: Difficulty = Difficulty.BASIC
