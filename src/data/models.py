"""
Modelos de dados Pydantic para validação e serialização
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DifficultyLevel(str, Enum):
    """Níveis de dificuldade"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class StudyMode(str, Enum):
    """Modos de estudo disponíveis"""
    VOCABULARY = "vocabulary"
    DIALOG = "dialog"
    FREE = "free"
    REVIEW = "review"


class Category(BaseModel):
    """Categoria de estudo"""
    id: Optional[int] = None
    name: str
    icon: str
    description: str
    color: str = "#667eea"
    total_words: int = 0
    mastered_words: int = 0
    
    class Config:
        from_attributes = True


class Vocabulary(BaseModel):
    """Palavra do vocabulário"""
    id: Optional[int] = None
    category_id: int
    english: str
    portuguese: str
    phonetic: str = ""
    difficulty: DifficultyLevel = DifficultyLevel.EASY
    audio_url: Optional[str] = None
    example_sentence: str = ""
    image_url: Optional[str] = None
    
    class Config:
        from_attributes = True


class Dialog(BaseModel):
    """Linha de diálogo"""
    id: Optional[int] = None
    theme: str
    role: str
    line: str
    translation: str = ""
    order_num: int = 0
    expected_response: Optional[str] = None
    
    class Config:
        from_attributes = True


class UserProgress(BaseModel):
    """Progresso do usuário em uma palavra"""
    id: Optional[int] = None
    word_id: int
    user_id: str = "default"
    score: float = 0.0
    attempts: int = 0
    last_practice: Optional[datetime] = None
    next_review: Optional[datetime] = None
    mastered: bool = False
    consecutive_correct: int = 0
    
    class Config:
        from_attributes = True


class StudySession(BaseModel):
    """Sessão de estudo"""
    id: Optional[int] = None
    user_id: str = "default"
    date: datetime = Field(default_factory=datetime.now)
    theme: str = ""
    mode: StudyMode = StudyMode.VOCABULARY
    words_practiced: int = 0
    correct_words: int = 0
    average_score: float = 0.0
    duration_seconds: int = 0
    xp_earned: int = 0
    
    class Config:
        from_attributes = True


class Achievement(BaseModel):
    """Conquista do usuário"""
    id: Optional[int] = None
    user_id: str = "default"
    achievement_key: str
    title: str
    description: str
    icon: str
    unlocked_at: Optional[datetime] = None
    progress: float = 0.0  # 0-100
    completed: bool = False
    
    class Config:
        from_attributes = True


class UserLevel(BaseModel):
    """Nível do usuário"""
    user_id: str = "default"
    level: int = 1
    title: str = "🌱 Iniciante"
    current_xp: int = 0
    xp_to_next_level: int = 100
    total_xp: int = 0
    streak_days: int = 0
    last_study_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class WordForStudy(BaseModel):
    """Palavra formatada para estudo (inclui progresso)"""
    vocabulary: Vocabulary
    progress: Optional[UserProgress] = None
    needs_review: bool = False
    
    class Config:
        from_attributes = True


class StudyResponse(BaseModel):
    """Resposta de uma sessão de estudo"""
    session_id: int
    word: Vocabulary
    score: float
    is_correct: bool
    xp_earned: int
    feedback: str
    pronunciation_score: Optional[float] = None
    

class UserStats(BaseModel):
    """Estatísticas completas do usuário"""
    level: UserLevel
    total_words_practiced: int
    total_words_mastered: int
    total_sessions: int
    average_score: float
    current_streak: int
    longest_streak: int
    achievements_unlocked: int
    total_achievements: int
    categories_progress: List[dict]
    recent_sessions: List[StudySession]