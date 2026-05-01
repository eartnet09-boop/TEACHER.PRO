# tests/test_unit_scorer.py
"""
Testes unitários do sistema de scoring.
Não depende de API, banco ou modelos - apenas lógica pura.
"""
import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pronunciation.scorer import PronunciationScorer, PronunciationLevel


class TestScorerLogic:
    """Testa a lógica pura do sistema de pontuação"""
    
    def setup_method(self):
        self.scorer = PronunciationScorer()
    
    def test_cosine_similarity_identical(self):
        """Vetores idênticos devem ter similaridade 1.0"""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0, 3.0])
        result = self.scorer._cosine_similarity(a, b)
        assert abs(result - 1.0) < 0.001, f"Similaridade deveria ser 1.0, foi {result}"
    
    def test_cosine_similarity_orthogonal(self):
        """Vetores ortogonais devem ter similaridade 0.0"""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        result = self.scorer._cosine_similarity(a, b)
        assert abs(result - 0.0) < 0.001, f"Similaridade deveria ser 0.0, foi {result}"
    
    def test_cosine_similarity_opposite(self):
        """Vetores opostos devem ter similaridade -1.0"""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([-1.0, -2.0, -3.0])
        result = self.scorer._cosine_similarity(a, b)
        assert abs(result - (-1.0)) < 0.001, f"Similaridade deveria ser -1.0, foi {result}"
    
    def test_cosine_similarity_zero_vector(self):
        """Vetor zero não deve causar divisão por zero"""
        a = np.array([0.0, 0.0, 0.0])
        b = np.array([1.0, 2.0, 3.0])
        result = self.scorer._cosine_similarity(a, b)
        assert result == 0.0, "Vetor zero deveria retornar 0.0"
    
    def test_classify_excellent(self):
        """Score >= 90 deve ser EXCELLENT"""
        assert self.scorer._classify_level(95) == PronunciationLevel.EXCELLENT
        assert self.scorer._classify_level(90) == PronunciationLevel.EXCELLENT
    
    def test_classify_good(self):
        """Score 75-89 deve ser GOOD"""
        assert self.scorer._classify_level(80) == PronunciationLevel.GOOD
        assert self.scorer._classify_level(75) == PronunciationLevel.GOOD
    
    def test_classify_fair(self):
        """Score 60-74 deve ser FAIR"""
        assert self.scorer._classify_level(65) == PronunciationLevel.FAIR
        assert self.scorer._classify_level(60) == PronunciationLevel.FAIR
    
    def test_classify_poor(self):
        """Score 40-59 deve ser POOR"""
        assert self.scorer._classify_level(50) == PronunciationLevel.POOR
        assert self.scorer._classify_level(40) == PronunciationLevel.POOR
    
    def test_classify_very_poor(self):
        """Score < 40 deve ser VERY_POOR"""
        assert self.scorer._classify_level(30) == PronunciationLevel.VERY_POOR
        assert self.scorer._classify_level(0) == PronunciationLevel.VERY_POOR
    
    def test_intrinsic_quality_normal(self):
        """Embedding normal deve ter qualidade > 0"""
        embedding = np.random.randn(768)
        embedding = embedding / np.linalg.norm(embedding)
        quality = self.scorer._intrinsic_quality(embedding)
        assert 0.0 < quality <= 1.0, f"Qualidade inválida: {quality}"
    
    def test_intrinsic_quality_zero(self):
        """Embedding zero deve ter qualidade 0"""
        embedding = np.zeros(768)
        quality = self.scorer._intrinsic_quality(embedding)
        assert quality == 0.0, f"Qualidade deveria ser 0.0, foi {quality}"
    
    def test_calculate_score_with_reference(self):
        """Score com referência deve ser maior que sem referência"""
        student_emb = np.random.randn(768)
        student_emb = student_emb / np.linalg.norm(student_emb)
        
        reference_emb = student_emb + np.random.randn(768) * 0.1
        reference_emb = reference_emb / np.linalg.norm(reference_emb)
        
        result_with_ref = self.scorer.calculate_score(
            student_embedding=student_emb,
            reference_embedding=reference_emb,
            expected_words=["hello", "world"]
        )
        
        result_without_ref = self.scorer.calculate_score(
            student_embedding=student_emb,
            reference_embedding=None,
            expected_words=["hello", "world"]
        )
        
        assert 0 <= result_with_ref.overall_score <= 100
        assert 0 <= result_without_ref.overall_score <= 100
    
    def test_word_scores_count(self):
        """Deve retornar score para cada palavra"""
        student_emb = np.random.randn(768)
        student_emb = student_emb / np.linalg.norm(student_emb)
        
        result = self.scorer.calculate_score(
            student_embedding=student_emb,
            expected_words=["the", "quick", "brown", "fox"]
        )
        
        assert len(result.word_scores) == 4
        assert "the" in result.word_scores
        assert "fox" in result.word_scores
    
    def test_recommendations_generated(self):
        """Deve gerar recomendações para qualquer nível"""
        student_emb = np.random.randn(768)
        student_emb = student_emb / np.linalg.norm(student_emb)
        
        result = self.scorer.calculate_score(
            student_embedding=student_emb,
            expected_words=["hello"]
        )
        
        assert len(result.recommendations) > 0
        assert isinstance(result.recommendations[0], str)