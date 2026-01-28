"""
Модели для тестов: Pydantic v2, 4 уровня сложности.
Question: из JSON (difficulty optional → BASIC).
CurrentTestState: toggle-ответы, таймер, результаты.
"""
from typing import List, Set, Optional
from pydantic import BaseModel, Field, validator
from enum import Enum
from config.settings import Difficulty

class Question(BaseModel):
    """Вопрос из библиотеки."""
    question: str = Field(..., min_length=1, max_length=2000)
    options: List[str] = Field(..., min_items=3, max_items=6)
    correct_answers: Set[int] = Field(..., min_items=1, max_items=len(options))
    difficulty: Difficulty = Difficulty.BASIC  # Default для JSON без поля

    @validator('correct_answers')
    def validate_correct(cls, v, values):
        max_opt = len(values.get('options', []))
        if any(i < 1 or i > max_opt for i in v):
            raise ValueError('correct_answers: 1-based индексы 1..N')
        return v

class CurrentTestState(BaseModel):
    """Состояние текущего теста."""
    questions: List[Question]
    current_index: int = 0
    selected_answers: Set[int] = Field(default_factory=set)
    start_time: Optional[float] = None
    timer_task: Optional['asyncio.Task'] = None  # Forward ref
    full_name: str = ""
    position: str = ""
    department: str = ""
    specialization: str = ""
    difficulty: Difficulty = Difficulty.BASIC

    @validator('current_index')
    def validate_index(cls, v, values):
        questions = values.get('questions', [])
        if not questions or v >= len(questions):
            raise ValueError('current_index валиден для questions')
        return v
