# src/pronunciation/wavlm_analyzer.py
"""
Analisador de pronúncia usando WavLM com comparação real de embeddings
e integração com o sistema de scoring profissional.
"""
import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
import logging

from .scorer import scorer as pronunciation_scorer

logger = logging.getLogger(__name__)


class WavLMAnalyzer:
    """
    Analisador fonético com WavLM Base Plus.
    
    Pipeline de análise:
    1. Extrai embeddings do áudio do aluno
    2. Gera áudio de referência via TTS
    3. Extrai embeddings do áudio de referência
    4. Calcula similaridade de cosseno
    5. Usa o PronunciationScorer para gerar scores detalhados
    6. Retorna métricas completas para feedback
    """
    
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = "cpu"
        self._loaded = False
        self._reference_cache = {}  # Cache de embeddings de referência
        
    def _load_model(self):
        """Carrega WavLM Base Plus"""
        if self._loaded:
            return
            
        try:
            from transformers import WavLMModel, Wav2Vec2FeatureExtractor
            
            model_name = "microsoft/wavlm-base-plus"
            logger.info(f"🔄 Carregando {model_name}...")
            
            self.processor = Wav2Vec2FeatureExtractor.from_pretrained(
                model_name,
                cache_dir="./models"
            )
            
            self.model = WavLMModel.from_pretrained(
                model_name,
                cache_dir="./models"
            )
            
            # Otimizações
            self.model.eval()
            
            # Desabilita gradientes para economia de memória
            for param in self.model.parameters():
                param.requires_grad = False
            
            self._loaded = True
            logger.info("✅ WavLM Base Plus carregado com sucesso")
            
            # Log do tamanho do modelo
            total_params = sum(p.numel() for p in self.model.parameters())
            logger.info(f"   Parâmetros totais: {total_params:,}")
            logger.info(f"   Dispositivo: {self.device}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao carregar WavLM: {e}")
            raise
    
    def _extract_embedding(self, audio_path: Path) -> np.ndarray:
        """
        Extrai embedding do áudio usando WavLM.
        
        Args:
            audio_path: Caminho do arquivo WAV (16kHz, mono)
            
        Returns:
            np.ndarray: Embedding de 768 dimensões
        """
        self._load_model()
        
        try:
            # Carrega áudio
            waveform, sr = torchaudio.load(str(audio_path))
            
            # Resample se necessário
            if sr != 16000:
                resampler = torchaudio.transforms.Resample(sr, 16000)
                waveform = resampler(waveform)
                logger.debug(f"Áudio resampled: {sr}Hz → 16000Hz")
            
            # Converte para mono
            if waveform.shape[0] > 1:
                waveform = waveform.mean(dim=0, keepdim=True)
            
            # Normaliza volume
            waveform = waveform / (waveform.abs().max() + 1e-8)
            
            # Processa com WavLM
            inputs = self.processor(
                waveform.squeeze(0).numpy(),
                sampling_rate=16000,
                return_tensors="pt"
            )
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Pooling: média dos hidden states (melhor que CLS token para áudio)
                embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
            
            # Normaliza o embedding
            embedding_norm = np.linalg.norm(embedding)
            if embedding_norm > 0:
                embedding = embedding / embedding_norm
            
            logger.debug(f"Embedding extraído: shape={embedding.shape}, "
                        f"norm={np.linalg.norm(embedding):.3f}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Erro ao extrair embedding: {e}")
            raise
    
    def _get_cached_reference(self, text: str) -> Optional[np.ndarray]:
        """Recupera embedding de referência do cache"""
        cache_key = text.lower().strip()
        return self._reference_cache.get(cache_key)
    
    def _cache_reference(self, text: str, embedding: np.ndarray):
        """Armazena embedding de referência no cache"""
        cache_key = text.lower().strip()
        self._reference_cache[cache_key] = embedding
        
        # Limita tamanho do cache (mantém últimas 50 frases)
        if len(self._reference_cache) > 50:
            # Remove entrada mais antiga
            oldest_key = next(iter(self._reference_cache))
            del self._reference_cache[oldest_key]
    
    async def analyze(
        self, 
        audio_path: Path, 
        expected_text: str,
        use_cache: bool = True
    ) -> Dict:
        """
        Analisa pronúncia comparando com texto esperado.
        
        Args:
            audio_path: Caminho do áudio WAV do aluno
            expected_text: Texto de referência (frase esperada)
            use_cache: Usar cache de embeddings de referência
            
        Returns:
            Dict com scores detalhados:
            {
                "overall_score": float (0-100),
                "word_scores": Dict[str, float],
                "level": str,
                "problematic_words": List[str],
                "strong_words": List[str],
                "recommendations": List[str],
                "phoneme_accuracy": float,
                "fluency_score": float,
                "similarity": float,
                "confidence": float
            }
        """
        try:
            logger.info(f"🎯 Analisando pronúncia: '{expected_text}'")
            
            # 1. Extrai embedding do aluno
            try:
                student_embedding = self._extract_embedding(audio_path)
                logger.debug(f"Embedding do aluno extraído: {student_embedding.shape}")
            except Exception as e:
                logger.error(f"Erro ao processar áudio do aluno: {e}")
                return self._fallback_analysis(expected_text, "Erro no processamento do áudio")
            
            # 2. Obtém embedding de referência
            reference_embedding = None
            
            # Tenta cache primeiro
            if use_cache:
                reference_embedding = self._get_cached_reference(expected_text)
                if reference_embedding is not None:
                    logger.debug("Usando embedding de referência do cache")
            
            # Se não está em cache, gera via TTS
            if reference_embedding is None:
                reference_path = await self._get_reference_audio(expected_text)
                
                if reference_path and reference_path.exists():
                    try:
                        reference_embedding = self._extract_embedding(reference_path)
                        
                        # Armazena no cache
                        if use_cache:
                            self._cache_reference(expected_text, reference_embedding)
                        
                        logger.debug("Embedding de referência gerado via TTS")
                    except Exception as e:
                        logger.warning(f"Erro ao processar áudio de referência: {e}")
                else:
                    logger.warning("Áudio de referência não disponível")
            
            # 3. Calcula score usando o PronunciationScorer
            if reference_embedding is not None:
                # Análise completa com referência
                score_result = pronunciation_scorer.calculate_score(
                    student_embedding=student_embedding,
                    reference_embedding=reference_embedding,
                    expected_words=expected_text.split(),
                    word_timestamps=None,  # Pode ser adicionado depois
                    phoneme_analysis=None   # Pode ser adicionado depois
                )
            else:
                # Análise sem referência (intrínseca)
                logger.info("Realizando análise sem áudio de referência")
                score_result = pronunciation_scorer.calculate_score(
                    student_embedding=student_embedding,
                    reference_embedding=None,
                    expected_words=expected_text.split(),
                    word_timestamps=None,
                    phoneme_analysis=None
                )
            
            # 4. Calcula similaridade adicional
            if reference_embedding is not None:
                similarity = float(
                    pronunciation_scorer._cosine_similarity(
                        student_embedding, 
                        reference_embedding
                    )
                )
            else:
                similarity = pronunciation_scorer._intrinsic_quality(student_embedding)
            
            # 5. Monta resultado final
            result = {
                "overall_score": score_result.overall_score,
                "word_scores": {
                    word: score.score if hasattr(score, 'score') else score
                    for word, score in score_result.word_scores.items()
                },
                "level": score_result.level.value,
                "problematic_words": score_result.problematic_words,
                "strong_words": score_result.strong_words,
                "recommendations": score_result.recommendations,
                "phoneme_accuracy": score_result.phoneme_accuracy,
                "fluency_score": score_result.fluency_score,
                "similarity": round(similarity, 3),
                "confidence": score_result.confidence,
                "has_reference": reference_embedding is not None
            }
            
            # 6. Log do resultado
            logger.info(
                f"✅ Análise concluída: "
                f"Score={result['overall_score']:.1f}, "
                f"Nível={result['level']}, "
                f"Palavras problemáticas={len(result['problematic_words'])}, "
                f"Similaridade={result['similarity']:.3f}"
            )
            
            # Log de palavras específicas
            if result['problematic_words']:
                logger.info(f"⚠️  Palavras para praticar: {', '.join(result['problematic_words'])}")
            if result['strong_words']:
                logger.info(f"💪 Palavras bem pronunciadas: {', '.join(result['strong_words'])}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro na análise de pronúncia: {e}", exc_info=True)
            return self._fallback_analysis(expected_text, str(e))
    
    def _fallback_analysis(self, expected_text: str, error_msg: str = "") -> Dict:
        """
        Análise de fallback quando ocorre erro.
        Retorna scores neutros para não prejudicar o aluno.
        """
        logger.warning(f"Usando análise de fallback. Erro: {error_msg}")
        
        words = expected_text.split()
        word_scores = {word: 50.0 for word in words}
        
        return {
            "overall_score": 50.0,
            "word_scores": word_scores,
            "level": "fair",
            "problematic_words": [],
            "strong_words": [],
            "recommendations": [
                "🔄 Não foi possível realizar uma análise precisa.",
                "🎤 Tente gravar novamente em um ambiente mais silencioso.",
                "🔊 Fale mais próximo ao microfone e articule bem as palavras."
            ],
            "phoneme_accuracy": 0.5,
            "fluency_score": 0.5,
            "similarity": 0.5,
            "confidence": 0.3,
            "has_reference": False,
            "error": error_msg
        }
    
    async def _get_reference_audio(self, text: str) -> Optional[Path]:
        """
        Gera áudio de referência usando TTS.
        
        Args:
            text: Texto para sintetizar
            
        Returns:
            Path do áudio gerado ou None se falhar
        """
        try:
            from ..tts.speaker import speaker
            
            logger.debug(f"Gerando áudio de referência para: '{text[:50]}...'")
            audio_path = await speaker.speak(text)
            
            if audio_path and audio_path.exists():
                logger.debug(f"Áudio de referência gerado: {audio_path}")
                return audio_path
            else:
                logger.warning("TTS retornou arquivo inválido")
                return None
                
        except ImportError:
            logger.warning("Módulo TTS não disponível")
            return None
        except Exception as e:
            logger.warning(f"Erro ao gerar áudio de referência: {e}")
            return None
    
    def clear_cache(self):
        """Limpa o cache de embeddings de referência"""
        cache_size = len(self._reference_cache)
        self._reference_cache.clear()
        logger.info(f"🧹 Cache limpo: {cache_size} embeddings removidos")
    
    def get_cache_stats(self) -> Dict:
        """Retorna estatísticas do cache"""
        return {
            "cached_phrases": len(self._reference_cache),
            "phrases": list(self._reference_cache.keys())[:10]  # Primeiras 10
        }


# Instância global
analyzer = WavLMAnalyzer()