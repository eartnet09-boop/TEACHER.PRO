
"""
Camada de acesso a dados (Repository Pattern)
Abstrai todas as operações de banco de dados
"""
import logging
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from .database import db
from .models import (
    Category, Vocabulary, Dialog, UserProgress,
    StudySession, Achievement, UserLevel,
    WordForStudy
)

logger = logging.getLogger(__name__)


class CategoryRepository:
    """Acesso a dados de categorias"""
    
    @staticmethod
    async def get_all() -> List[Dict]:
        return await db.fetch_all(
            """SELECT c.*, 
               COUNT(v.id) as total_words,
               COUNT(CASE WHEN p.mastered = 1 THEN 1 END) as mastered_words
               FROM categories c
               LEFT JOIN vocabulary v ON c.id = v.category_id
               LEFT JOIN user_progress p ON v.id = p.word_id
               GROUP BY c.id
               ORDER BY c.name"""
        )
    
    @staticmethod
    async def get_by_id(category_id: int) -> Optional[Dict]:
        return await db.fetch_one(
            "SELECT * FROM categories WHERE id = ?",
            (category_id,)
        )
    
    @staticmethod
    async def get_by_name(name: str) -> Optional[Dict]:
        return await db.fetch_one(
            "SELECT * FROM categories WHERE name = ?",
            (name,)
        )
    
    @staticmethod
    async def get_with_progress(user_id: str = "default") -> List[Dict]:
        return await db.fetch_all(
            """SELECT c.*,
               COUNT(DISTINCT v.id) as total_words,
               COUNT(DISTINCT CASE WHEN p.mastered = 1 THEN v.id END) as mastered_words,
               ROUND(AVG(CASE WHEN p.score > 0 THEN p.score END), 1) as average_score
               FROM categories c
               LEFT JOIN vocabulary v ON c.id = v.category_id
               LEFT JOIN user_progress p ON v.id = p.word_id AND p.user_id = ?
               GROUP BY c.id
               ORDER BY c.name""",
            (user_id,)
        )


class VocabularyRepository:
    """Acesso a dados de vocabulário"""
    
    @staticmethod
    async def get_by_category(category_id: int) -> List[Dict]:
        return await db.fetch_all(
            """SELECT * FROM vocabulary 
               WHERE category_id = ? 
               ORDER BY difficulty, english""",
            (category_id,)
        )
    
    @staticmethod
    async def get_words_for_study(
        category_id: int,
        user_id: str = "default",
        limit: int = 10,
        mode: str = "new"
    ) -> List[Dict]:
        """Busca palavras para estudo baseado no modo"""
        if mode == "review":
            # Palavras que precisam de revisão (SRS)
            return await db.fetch_all(
                """SELECT v.*, p.score, p.attempts, p.mastered,
                   p.next_review, p.consecutive_correct
                   FROM vocabulary v
                   LEFT JOIN user_progress p ON v.id = p.word_id AND p.user_id = ?
                   WHERE v.category_id = ?
                   AND (p.next_review IS NULL OR p.next_review <= datetime('now'))
                   AND (p.mastered = 0 OR p.mastered IS NULL)
                   ORDER BY p.score ASC
                   LIMIT ?""",
                (user_id, category_id, limit)
            )
        else:
            # Palavras novas ou menos praticadas
            return await db.fetch_all(
                """SELECT v.*, p.score, p.attempts, p.mastered
                   FROM vocabulary v
                   LEFT JOIN user_progress p ON v.id = p.word_id AND p.user_id = ?
                   WHERE v.category_id = ?
                   ORDER BY p.attempts ASC NULLS FIRST, RANDOM()
                   LIMIT ?""",
                (user_id, category_id, limit)
            )
    
    @staticmethod
    async def get_by_id(word_id: int) -> Optional[Dict]:
        return await db.fetch_one(
            "SELECT * FROM vocabulary WHERE id = ?",
            (word_id,)
        )
    
    @staticmethod
    async def search(query: str) -> List[Dict]:
        return await db.fetch_all(
            """SELECT * FROM vocabulary 
               WHERE english LIKE ? OR portuguese LIKE ?
               LIMIT 20""",
            (f"%{query}%", f"%{query}%")
        )


class ProgressRepository:
    """Acesso a dados de progresso do usuário"""
    
    @staticmethod
    async def get_word_progress(word_id: int, user_id: str = "default") -> Optional[Dict]:
        return await db.fetch_one(
            "SELECT * FROM user_progress WHERE word_id = ? AND user_id = ?",
            (word_id, user_id)
        )
    
    @staticmethod
    async def update_progress(
        word_id: int,
        score: float,
        user_id: str = "default"
    ) -> Dict:
        """Atualiza ou cria progresso de uma palavra"""
        existing = await ProgressRepository.get_word_progress(word_id, user_id)
        
        mastered = 1 if score >= 90 else 0
        now = datetime.now().isoformat()
        
        if existing:
            # Atualiza progresso existente
            attempts = existing["attempts"] + 1
            consecutive = existing["consecutive_correct"] + 1 if score >= 70 else 0
            
            # Calcula próxima revisão (SRS simplificado)
            if score >= 80:
                interval_days = min(30, (existing["consecutive_correct"] + 1) * 3)
            elif score >= 60:
                interval_days = max(1, existing["consecutive_correct"])
            else:
                interval_days = 1
            
            next_review = (datetime.now() + timedelta(days=interval_days)).isoformat()
            
            await db.execute(
                """UPDATE user_progress 
                   SET score = ?, attempts = ?, last_practice = ?,
                       next_review = ?, mastered = ?, consecutive_correct = ?
                   WHERE word_id = ? AND user_id = ?""",
                (score, attempts, now, next_review, mastered, consecutive,
                 word_id, user_id)
            )
        else:
            # Cria novo progresso
            next_review = (datetime.now() + timedelta(days=1)).isoformat()
            
            await db.execute(
                """INSERT INTO user_progress 
                   (word_id, user_id, score, attempts, last_practice, 
                    next_review, mastered, consecutive_correct)
                   VALUES (?, ?, ?, 1, ?, ?, ?, ?)""",
                (word_id, user_id, score, now, next_review, mastered,
                 1 if score >= 70 else 0)
            )
        
        return await ProgressRepository.get_word_progress(word_id, user_id)
    
    @staticmethod
    async def get_stats(user_id: str = "default") -> Dict:
        """Estatísticas gerais do usuário"""
        return await db.fetch_one(
            """SELECT 
               COUNT(DISTINCT word_id) as total_words_practiced,
               COUNT(CASE WHEN mastered = 1 THEN 1 END) as total_words_mastered,
               ROUND(AVG(score), 1) as average_score
               FROM user_progress 
               WHERE user_id = ?""",
            (user_id,)
        )


class DialogRepository:
    """Acesso a dados de diálogos"""
    
    @staticmethod
    async def get_by_theme(theme: str) -> List[Dict]:
        return await db.fetch_all(
            """SELECT * FROM dialogs 
               WHERE theme = ? 
               ORDER BY order_num""",
            (theme,)
        )
    
    @staticmethod
    async def get_all_themes() -> List[str]:
        rows = await db.fetch_all(
            "SELECT DISTINCT theme FROM dialogs ORDER BY theme"
        )
        return [r["theme"] for r in rows]


class SessionRepository:
    """Acesso a dados de sessões de estudo"""
    
    @staticmethod
    async def create_session(
        theme: str,
        mode: str,
        words_practiced: int,
        correct_words: int,
        average_score: float,
        xp_earned: int,
        duration: int = 0,
        user_id: str = "default"
    ) -> int:
        return await db.execute(
            """INSERT INTO study_sessions 
               (user_id, theme, mode, words_practiced, correct_words,
                average_score, duration_seconds, xp_earned)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, theme, mode, words_practiced, correct_words,
             average_score, duration, xp_earned)
        )
    
    @staticmethod
    async def get_recent(user_id: str = "default", limit: int = 10) -> List[Dict]:
        return await db.fetch_all(
            """SELECT * FROM study_sessions 
               WHERE user_id = ? 
               ORDER BY date DESC LIMIT ?""",
            (user_id, limit)
        )
    
    @staticmethod
    async def get_streak(user_id: str = "default") -> Dict:
        """Calcula streak atual do usuário"""
        sessions = await db.fetch_all(
            """SELECT DISTINCT date(date) as study_date 
               FROM study_sessions 
               WHERE user_id = ? 
               ORDER BY study_date DESC LIMIT 60""",
            (user_id,)
        )
        
        if not sessions:
            return {"current_streak": 0, "longest_streak": 0}
        
        # Calcula streak atual
        current_streak = 0
        today = datetime.now().date()
        
        for i, session in enumerate(sessions):
            session_date = datetime.strptime(session["study_date"], "%Y-%m-%d").date()
            expected_date = today - timedelta(days=i)
            
            if session_date == expected_date:
                current_streak += 1
            else:
                break
        
        # Calcula maior streak
        longest_streak = 1
        temp_streak = 1
        
        for i in range(1, len(sessions)):
            current = datetime.strptime(sessions[i-1]["study_date"], "%Y-%m-%d").date()
            previous = datetime.strptime(sessions[i]["study_date"], "%Y-%m-%d").date()
            
            if (current - previous).days == 1:
                temp_streak += 1
                longest_streak = max(longest_streak, temp_streak)
            else:
                temp_streak = 1
        
        return {
            "current_streak": current_streak,
            "longest_streak": longest_streak
        }
    
    @staticmethod
    async def update_streak(user_id: str = "default") -> Dict:
        """Atualiza informações de streak do usuário"""
        streak_data = await SessionRepository.get_streak(user_id)
        
        existing = await db.fetch_one(
            "SELECT * FROM user_streaks WHERE user_id = ?",
            (user_id,)
        )
        
        if existing:
            new_longest = max(existing["longest_streak"], streak_data["longest_streak"])
            await db.execute(
                """UPDATE user_streaks 
                   SET current_streak = ?, longest_streak = ?,
                       last_study_date = datetime('now')
                   WHERE user_id = ?""",
                (streak_data["current_streak"], new_longest, user_id)
            )
        else:
            await db.execute(
                """INSERT INTO user_streaks (user_id, current_streak, longest_streak, last_study_date)
                   VALUES (?, ?, ?, datetime('now'))""",
                (user_id, streak_data["current_streak"], streak_data["longest_streak"])
            )
        
        return streak_data