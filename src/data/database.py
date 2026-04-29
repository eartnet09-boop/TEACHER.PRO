"""
Gerenciador de Banco de Dados SQLite
Singleton pattern para conexão única e thread-safe
"""
import sqlite3
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime

from ..config import DATABASE_CONFIG

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Gerenciador singleton do banco de dados SQLite.
    Garante uma única conexão e gerencia migrations.
    """
    
    _instance: Optional['DatabaseManager'] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.db_path = DATABASE_CONFIG["path"]
        self.connection: Optional[sqlite3.Connection] = None
        self._initialized = True
        
        logger.info(f"DatabaseManager inicializado: {self.db_path}")
    
    async def initialize(self):
        """Inicializa banco de dados e executa migrations"""
        async with self._lock:
            await self._connect()
            await self._create_tables()
            await self._run_migrations()
            logger.info("✅ Banco de dados inicializado com sucesso")
    
    async def _connect(self):
        """Estabelece conexão com o banco"""
        self.connection = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=DATABASE_CONFIG["timeout"]
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=5000")
    
    async def _create_tables(self):
        """Cria todas as tabelas do banco de dados"""
        
        # Tabela de categorias
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                icon TEXT DEFAULT '📚',
                description TEXT DEFAULT '',
                color TEXT DEFAULT '#667eea',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE INDEX IF NOT EXISTS idx_categories_name 
            ON categories(name);
        """)
        
        # Tabela de vocabulário
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                english TEXT NOT NULL,
                portuguese TEXT NOT NULL,
                phonetic TEXT DEFAULT '',
                difficulty TEXT DEFAULT 'easy',
                audio_url TEXT,
                example_sentence TEXT DEFAULT '',
                image_url TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
                UNIQUE(category_id, english)
            );
            
            CREATE INDEX IF NOT EXISTS idx_vocabulary_category 
            ON vocabulary(category_id);
            
            CREATE INDEX IF NOT EXISTS idx_vocabulary_english 
            ON vocabulary(english);
            
            CREATE INDEX IF NOT EXISTS idx_vocabulary_difficulty 
            ON vocabulary(difficulty);
        """)
        
        # Tabela de diálogos
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS dialogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                theme TEXT NOT NULL,
                role TEXT NOT NULL,
                line TEXT NOT NULL,
                translation TEXT DEFAULT '',
                order_num INTEGER DEFAULT 0,
                expected_response TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            
            CREATE INDEX IF NOT EXISTS idx_dialogs_theme 
            ON dialogs(theme);
            
            CREATE INDEX IF NOT EXISTS idx_dialogs_order 
            ON dialogs(theme, order_num);
        """)
        
        # Tabela de progresso do usuário
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER NOT NULL,
                user_id TEXT DEFAULT 'default',
                score REAL DEFAULT 0.0,
                attempts INTEGER DEFAULT 0,
                last_practice TEXT,
                next_review TEXT,
                mastered INTEGER DEFAULT 0,
                consecutive_correct INTEGER DEFAULT 0,
                FOREIGN KEY (word_id) REFERENCES vocabulary(id) ON DELETE CASCADE,
                UNIQUE(user_id, word_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_progress_user 
            ON user_progress(user_id);
            
            CREATE INDEX IF NOT EXISTS idx_progress_review 
            ON user_progress(next_review);
        """)
        
        # Tabela de sessões de estudo
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'default',
                date TEXT DEFAULT (datetime('now')),
                theme TEXT DEFAULT '',
                mode TEXT DEFAULT 'vocabulary',
                words_practiced INTEGER DEFAULT 0,
                correct_words INTEGER DEFAULT 0,
                average_score REAL DEFAULT 0.0,
                duration_seconds INTEGER DEFAULT 0,
                xp_earned INTEGER DEFAULT 0
            );
            
            CREATE INDEX IF NOT EXISTS idx_sessions_user 
            ON study_sessions(user_id);
            
            CREATE INDEX IF NOT EXISTS idx_sessions_date 
            ON study_sessions(date);
        """)
        
        # Tabela de conquistas
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'default',
                achievement_key TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                icon TEXT DEFAULT '🏆',
                unlocked_at TEXT,
                progress REAL DEFAULT 0.0,
                completed INTEGER DEFAULT 0,
                UNIQUE(user_id, achievement_key)
            );
        """)
        
        # Tabela de streak
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS user_streaks (
                user_id TEXT PRIMARY KEY DEFAULT 'default',
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_study_date TEXT,
                total_xp INTEGER DEFAULT 0,
                current_level INTEGER DEFAULT 1
            );
        """)
        
        self.connection.commit()
    
    async def _run_migrations(self):
        """Executa migrations pendentes"""
        # Verifica se a coluna image_url existe
        cursor = self.connection.execute("PRAGMA table_info(vocabulary)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'image_url' not in columns:
            self.connection.execute(
                "ALTER TABLE vocabulary ADD COLUMN image_url TEXT"
            )
            logger.info("Migration: image_url adicionado à vocabulary")
        
        self.connection.commit()
    
    @asynccontextmanager
    async def get_cursor(self):
        """Context manager para cursor do banco"""
        if not self.connection:
            await self._connect()
        
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Erro no banco de dados: {e}")
            raise
        finally:
            cursor.close()
    
    async def execute(self, query: str, params: tuple = ()) -> int:
        """Executa uma query e retorna o lastrowid"""
        async with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.lastrowid
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Busca um único registro"""
        async with self.get_cursor() as cursor:
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """Busca múltiplos registros"""
        async with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    async def close(self):
        """Fecha conexão com o banco"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Conexão com banco de dados fechada")


# Instância global
db = DatabaseManager()