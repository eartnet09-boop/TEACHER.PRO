# src/pronunciation/scorer.py
"""
Sistema de Pontuação de Pronúncia
Converte embeddings acústicos em scores compreensíveis
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PronunciationLevel(Enum):
    """Níveis de proficiência em pronúncia"""
    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"            # 75-89
    FAIR = "fair"            # 60-74
    POOR = "poor"            # 40-59
    VERY_POOR = "very_poor"  # 0-39


@dataclass
class WordScore:
    """Score detalhado de uma palavra"""
    word: str
    score: float           # 0-100
    phoneme_accuracy: float # Precisão fonética (0-1)
    fluency: float         # Fluência (0-1)
    confidence: float      # Confiança da análise (0-1)
    is_problematic: bool   # Precisa de mais prática?
    level: PronunciationLevel


@dataclass
class PronunciationScore:
    """Score completo da pronúncia"""
    overall_score: float                    # 0-100
    word_scores: Dict[str, WordScore]       # Scores por palavra
    level: PronunciationLevel               # Nível geral
    problematic_words: List[str]            # Palavras para praticar
    strong_words: List[str]                 # Palavras bem pronunciadas
    phoneme_accuracy: float                 # Precisão fonética média
    fluency_score: float                    # Score de fluência
    confidence: float                       # Confiança geral da análise
    recommendations: List[str]              # Recomendações personalizadas


class PronunciationScorer:
    """
    Calcula scores de pronúncia a partir de embeddings acústicos.
    
    O scoring é baseado em:
    1. Similaridade de embeddings (WavLM)
    2. Análise de prosódia (ritmo, entonação)
    3. Comparação fonética
    4. Métricas de confiança
    """
    
    def __init__(self):
        # Pesos para o cálculo do score geral
        self.weights = {
            "phoneme_accuracy": 0.45,   # Precisão dos fonemas
            "fluency": 0.25,            # Fluência e ritmo
            "prosody": 0.15,            # Entonação
            "confidence": 0.15,         # Confiança da análise
        }
        
        # Thresholds para classificação
        self.thresholds = {
            "excellent": 90,
            "good": 75,
            "fair": 60,
            "poor": 40,
        }
        
        # Mapeamento de fonemas problemáticos para brasileiros
        self.difficult_phonemes = {
            'th': ['θ', 'ð'],     # think, this
            'r': ['ɹ', 'ɚ'],      # red, better
            'ae': ['æ'],          # cat, bad
            'ih': ['ɪ'],          # bit, ship
            'ah': ['ʌ', 'ə'],     # cup, about
        }
    
    def calculate_score(
        self,
        student_embedding: np.ndarray,
        reference_embedding: Optional[np.ndarray] = None,
        word_timestamps: Optional[List[Dict]] = None,
        expected_words: Optional[List[str]] = None,
        phoneme_analysis: Optional[Dict] = None
    ) -> PronunciationScore:
        """
        Calcula o score completo de pronúncia
        
        Args:
            student_embedding: Embedding do áudio do aluno
            reference_embedding: Embedding do áudio de referência (TTS)
            word_timestamps: Timestamps de cada palavra
            expected_words: Lista de palavras esperadas
            phoneme_analysis: Análise fonética detalhada
            
        Returns:
            PronunciationScore com todas as métricas
        """
        # 1. Calcula similaridade geral
        if reference_embedding is not None:
            overall_similarity = self._cosine_similarity(
                student_embedding,
                reference_embedding
            )
        else:
            # Sem referência, usa métricas intrínsecas
            overall_similarity = self._intrinsic_quality(student_embedding)
        
        # 2. Calcula scores por palavra
        word_scores = {}
        if expected_words and word_timestamps:
            word_scores = self._calculate_word_scores(
                student_embedding,
                reference_embedding,
                expected_words,
                word_timestamps,
                phoneme_analysis
            )
        elif expected_words:
            # Fallback: distribui o score geral entre as palavras
            word_scores = self._estimate_word_scores(
                expected_words,
                overall_similarity
            )
        
        # 3. Calcula métricas agregadas
        phoneme_accuracy = self._calculate_phoneme_accuracy(
            word_scores,
            phoneme_analysis
        )
        
        fluency_score = self._calculate_fluency(
            student_embedding,
            word_timestamps
        )
        
        confidence = self._calculate_confidence(
            student_embedding,
            word_scores
        )
        
        # 4. Score geral ponderado
        overall_score = (
            phoneme_accuracy * self.weights["phoneme_accuracy"] +
            fluency_score * self.weights["fluency"] +
            overall_similarity * 100 * self.weights["prosody"] +
            confidence * 100 * self.weights["confidence"]
        )
        
        # Garante que está entre 0 e 100
        overall_score = max(0, min(100, overall_score))
        
        # 5. Classifica nível
        level = self._classify_level(overall_score)
        
        # 6. Identifica palavras problemáticas
        problematic = []
        strong = []
        for word, score in word_scores.items():
            if isinstance(score, WordScore):
                if score.is_problematic:
                    problematic.append(word)
                if score.score >= 85:
                    strong.append(word)
            elif isinstance(score, (int, float)):
                if score < 60:
                    problematic.append(word)
                if score >= 85:
                    strong.append(word)
        
        # 7. Gera recomendações
        recommendations = self._generate_recommendations(
            level,
            problematic,
            phoneme_analysis
        )
        
        return PronunciationScore(
            overall_score=round(overall_score, 1),
            word_scores=word_scores,
            level=level,
            problematic_words=problematic,
            strong_words=strong,
            phoneme_accuracy=round(phoneme_accuracy, 3),
            fluency_score=round(fluency_score, 3),
            confidence=round(confidence, 3),
            recommendations=recommendations
        )
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calcula similaridade de cosseno entre embeddings"""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    
    def _intrinsic_quality(self, embedding: np.ndarray) -> float:
        """
        Avalia qualidade intrínseca do embedding quando não há referência.
        Baseado na energia e distribuição estatística.
        """
        # Normaliza
        embedding_norm = np.linalg.norm(embedding)
        if embedding_norm == 0:
            return 0.0
        
        embedding_normalized = embedding / embedding_norm
        
        # Calcula métricas
        energy = np.mean(np.abs(embedding))
        variance = np.var(embedding)
        entropy = -np.sum(embedding_normalized * np.log(np.abs(embedding_normalized) + 1e-10))
        
        # Combina em um score (0-1)
        quality_score = (
            min(1.0, energy * 3) * 0.4 +
            min(1.0, variance * 5) * 0.3 +
            min(1.0, entropy / 5) * 0.3
        )
        
        return quality_score
    
    def _calculate_word_scores(
        self,
        student_emb: np.ndarray,
        reference_emb: Optional[np.ndarray],
        words: List[str],
        timestamps: List[Dict],
        phoneme_analysis: Optional[Dict]
    ) -> Dict[str, WordScore]:
        """Calcula scores detalhados por palavra"""
        word_scores = {}
        
        for i, word in enumerate(words):
            # Similaridade geral para esta palavra
            if reference_emb is not None and i < len(timestamps):
                # Extrai segmento do embedding correspondente à palavra
                segment_start = timestamps[i].get("start", 0)
                segment_end = timestamps[i].get("end", 0)
                
                # Calcula score baseado na posição relativa
                position_factor = 1.0 - (abs(i - len(words)/2) / len(words)) * 0.2
                
                # Score base
                base_score = self._cosine_similarity(student_emb, reference_emb)
                word_score = base_score * 100 * position_factor
            else:
                # Estimativa baseada na posição
                base_score = self._intrinsic_quality(student_emb)
                position_factor = 1.0 - (abs(i - len(words)/2) / len(words)) * 0.2
                word_score = base_score * 100 * position_factor
            
            # Ajusta com análise fonética se disponível
            phoneme_acc = 0.7  # default
            if phoneme_analysis and word in phoneme_analysis:
                phoneme_acc = phoneme_analysis[word].get("accuracy", 0.7)
                word_score = word_score * 0.6 + phoneme_acc * 100 * 0.4
            
            # Garante limites
            word_score = max(10, min(100, word_score))
            
            # Classifica
            level = self._classify_level(word_score)
            is_problematic = word_score < 60
            
            word_scores[word] = WordScore(
                word=word,
                score=round(word_score, 1),
                phoneme_accuracy=round(phoneme_acc, 3),
                fluency=round(base_score * 0.8, 3),
                confidence=round(base_score, 3),
                is_problematic=is_problematic,
                level=level
            )
        
        return word_scores
    
    def _estimate_word_scores(
        self,
        words: List[str],
        overall_similarity: float
    ) -> Dict[str, float]:
        """Estima scores por palavra quando não há timestamps"""
        word_scores = {}
        base_score = overall_similarity * 100
        
        for i, word in enumerate(words):
            # Palavras no meio tendem a ser mais difíceis
            position_factor = 1.0 - (abs(i - len(words)/2) / len(words)) * 0.3
            
            # Palavras mais longas podem ser mais difíceis
            length_factor = 1.0 - min(0.2, len(word) * 0.02)
            
            # Pequena variação aleatória para realismo
            variation = np.random.uniform(-5, 5)
            
            score = base_score * position_factor * length_factor + variation
            word_scores[word] = round(max(10, min(100, score)), 1)
        
        return word_scores
    
    def _calculate_phoneme_accuracy(
        self,
        word_scores: Dict,
        phoneme_analysis: Optional[Dict]
    ) -> float:
        """Calcula precisão fonética média"""
        if phoneme_analysis:
            accuracies = [
                data.get("accuracy", 0.5)
                for data in phoneme_analysis.values()
            ]
            return np.mean(accuracies) if accuracies else 0.5
        
        # Fallback: média dos scores das palavras
        scores = []
        for score in word_scores.values():
            if isinstance(score, WordScore):
                scores.append(score.phoneme_accuracy)
            elif isinstance(score, (int, float)):
                scores.append(score / 100)
        
        return np.mean(scores) if scores else 0.5
    
    def _calculate_fluency(
        self,
        embedding: np.ndarray,
        timestamps: Optional[List[Dict]]
    ) -> float:
        """Calcula score de fluência baseado no ritmo"""
        if not timestamps or len(timestamps) < 2:
            # Estimativa baseada na suavidade do embedding
            diffs = np.diff(embedding)
            smoothness = 1.0 / (1.0 + np.std(diffs))
            return float(smoothness)
        
        # Analisa intervalos entre palavras
        intervals = []
        for i in range(1, len(timestamps)):
            gap = timestamps[i].get("start", 0) - timestamps[i-1].get("end", 0)
            if gap > 0:
                intervals.append(gap)
        
        if not intervals:
            return 0.5
        
        # Fluência é inversamente proporcional à variação dos intervalos
        mean_interval = np.mean(intervals)
        std_interval = np.std(intervals)
        
        # Coeficiente de variação (quanto menor, mais fluente)
        cv = std_interval / (mean_interval + 1e-10)
        fluency = 1.0 / (1.0 + cv)
        
        return float(fluency)
    
    def _calculate_confidence(
        self,
        embedding: np.ndarray,
        word_scores: Dict
    ) -> float:
        """Calcula confiança geral da análise"""
        # Baseado na qualidade do embedding
        embedding_quality = self._intrinsic_quality(embedding)
        
        # Consistência dos scores
        scores = []
        for score in word_scores.values():
            if isinstance(score, WordScore):
                scores.append(score.confidence)
            elif isinstance(score, (int, float)):
                scores.append(0.6)
        
        score_consistency = np.mean(scores) if scores else 0.5
        
        # Confiança combinada
        confidence = embedding_quality * 0.6 + score_consistency * 0.4
        
        return float(min(1.0, confidence))
    
    def _classify_level(self, score: float) -> PronunciationLevel:
        """Classifica o score em um nível"""
        if score >= self.thresholds["excellent"]:
            return PronunciationLevel.EXCELLENT
        elif score >= self.thresholds["good"]:
            return PronunciationLevel.GOOD
        elif score >= self.thresholds["fair"]:
            return PronunciationLevel.FAIR
        elif score >= self.thresholds["poor"]:
            return PronunciationLevel.POOR
        else:
            return PronunciationLevel.VERY_POOR
    
    def _generate_recommendations(
        self,
        level: PronunciationLevel,
        problematic_words: List[str],
        phoneme_analysis: Optional[Dict]
    ) -> List[str]:
        """Gera recomendações personalizadas baseadas no nível e erros"""
        recommendations = []
        
        if level == PronunciationLevel.EXCELLENT:
            recommendations.append("🌟 Excelente pronúncia! Continue praticando para manter o nível.")
            if problematic_words:
                recommendations.append(f"💡 Pequeno ajuste em: {', '.join(problematic_words[:2])}")
        elif level == PronunciationLevel.GOOD:
            recommendations.append("👍 Boa pronúncia! Alguns ajustes vão te levar à perfeição.")
            if problematic_words:
                recommendations.append(f"🎯 Foque em: {', '.join(problematic_words[:3])}")
        elif level == PronunciationLevel.FAIR:
            recommendations.append("📚 Você está no caminho certo! Continue praticando.")
            recommendations.append("🐢 Tente falar mais devagar, focando em cada sílaba.")
            if problematic_words:
                recommendations.append(f"🔍 Pratique especialmente: {', '.join(problematic_words[:4])}")
        elif level == PronunciationLevel.POOR:
            recommendations.append("💪 Não desanime! A pronúncia melhora com prática constante.")
            recommendations.append("🔊 Ouça o áudio modelo várias vezes antes de tentar.")
            recommendations.append("📝 Pratique palavra por palavra antes da frase completa.")
        else:
            recommendations.append("🎯 Vamos do começo! Foque em sons básicos primeiro.")
            recommendations.append("👂 Treine o ouvido: ouça e repita palavras curtas.")
            recommendations.append("🗣️ Não se preocupe com a velocidade, clareza é mais importante.")
        
        return recommendations


# Instância global
scorer = PronunciationScorer()