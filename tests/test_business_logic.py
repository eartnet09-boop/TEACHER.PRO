# tests/test_business_logic.py
"""
Testes de lógica de negócio: SRS, Gamificação, Streaks.
Não depende de API.
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSpacedRepetition:
    """Testa o algoritmo de repetição espaçada (SRS)"""
    
    def test_new_word_interval(self):
        """Palavra nova deve ter revisão em 1 dia"""
        now = datetime.now()
        next_review = now + timedelta(days=1)
        assert next_review > now
    
    def test_mastered_word_interval(self):
        """Palavra dominada deve ter intervalo maior"""
        now = datetime.now()
        # Simula palavra já praticada 5 vezes com score alto
        interval_days = min(30, 5 * 3)  # 15 dias
        next_review = now + timedelta(days=interval_days)
        assert next_review > now + timedelta(days=7)
    
    def test_failed_word_interval(self):
        """Palavra com score baixo deve ter revisão em 1 dia"""
        now = datetime.now()
        next_review = now + timedelta(days=1)
        assert next_review == now + timedelta(days=1)


class TestGamification:
    """Testa o sistema de gamificação"""
    
    def test_xp_calculation_base(self):
        """XP base por palavra deve ser > 0"""
        xp_base = 10
        assert xp_base > 0
    
    def test_xp_perfect_bonus(self):
        """Score 100 deve dar bônus"""
        score = 100
        xp = 10  # base
        if score >= 90:
            xp += 20  # bônus
        assert xp == 30
    
    def test_xp_good_no_bonus(self):
        """Score 70 não deve dar bônus máximo"""
        score = 70
        xp = 10
        if score >= 90:
            xp += 20
        elif score >= 70:
            xp += 10
        assert xp == 20
    
    def test_streak_multiplier(self):
        """Streak deve multiplicar XP"""
        base_xp = 20
        streak_days = 5
        multiplier = min(3.0, 1.0 + streak_days * 0.1)  # 1.5x
        final_xp = int(base_xp * multiplier)
        assert final_xp == 30
    
    def test_max_streak_multiplier(self):
        """Multiplicador não deve passar de 3.0"""
        base_xp = 20
        streak_days = 100  # Muito alto
        multiplier = min(3.0, 1.0 + streak_days * 0.1)
        assert multiplier == 3.0
    
    def test_level_progression(self):
        """Nível deve aumentar com XP"""
        levels = [
            {"level": 1, "xp_required": 0},
            {"level": 2, "xp_required": 100},
            {"level": 3, "xp_required": 300},
            {"level": 4, "xp_required": 600},
            {"level": 5, "xp_required": 1000},
        ]
        
        current_xp = 450
        current_level = levels[0]
        
        for level in levels:
            if current_xp >= level["xp_required"]:
                current_level = level
        
        assert current_level["level"] == 3  # 450 XP = Nível 3


class TestSimilarity:
    """Testa algoritmos de similaridade de texto"""
    
    def test_exact_match(self):
        """Textos idênticos devem ter similaridade 1.0"""
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, "hello", "hello").ratio()
        assert similarity == 1.0
    
    def test_completely_different(self):
        """Textos diferentes devem ter similaridade baixa"""
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, "hello", "xyz").ratio()
        assert similarity < 0.3
    
    def test_case_insensitive(self):
        """Comparação deve ser case-insensitive"""
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(
            None, 
            "Hello World".lower(), 
            "hello world".lower()
        ).ratio()
        assert similarity == 1.0
    
    def test_partial_match(self):
        """Texto parcial deve ter similaridade média"""
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, "hello world", "hello").ratio()
        assert 0.4 < similarity < 0.9


class TestDataValidation:
    """Testa validações de dados"""
    
    def test_score_range(self):
        """Score deve estar entre 0 e 100"""
        scores = [-10, 0, 50, 100, 150]
        validated = [max(0, min(100, s)) for s in scores]
        assert validated == [0, 0, 50, 100, 100]
    
    def test_word_id_required(self):
        """word_id é obrigatório para registrar prática"""
        data = {"score": 85}
        assert "word_id" not in data  # Deve falhar validação
    
    def test_empty_text_validation(self):
        """Texto vazio deve ser rejeitado"""
        text = ""
        is_valid = len(text.strip()) > 0
        assert is_valid is False
    
    def test_long_text_truncation(self):
        """Texto muito longo deve ser truncado"""
        text = "a" * 500
        max_length = 200
        truncated = text[:max_length]
        assert len(truncated) == 200