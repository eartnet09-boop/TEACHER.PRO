"""
Pacote de dados do English Teacher Agent
Gerencia banco de dados, modelos e acesso a dados
"""
from .database import DatabaseManager
from .models import (
    Category, Vocabulary, Dialog, UserProgress,
    StudySession, Achievement, UserLevel
)
from .seeder import DataSeeder
from .repository import (
    CategoryRepository, VocabularyRepository,
    DialogRepository, ProgressRepository,
    SessionRepository
)

__all__ = [
    'DatabaseManager',
    'Category', 'Vocabulary', 'Dialog', 'UserProgress',
    'StudySession', 'Achievement', 'UserLevel',
    'DataSeeder',
    'CategoryRepository', 'VocabularyRepository',
    'DialogRepository', 'ProgressRepository',
    'SessionRepository',
]