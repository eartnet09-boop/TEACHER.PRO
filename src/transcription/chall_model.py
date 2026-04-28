# src/transcription/chall_model.py
"""
Modelo de transcrição que preserva erros
Usa Whisper tiny com configuração especial para não auto-corrigir
"""
import torch
import numpy as np
from pathlib import Path
from typing import Dict, List
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ChaLLTranscriber:
    """
    Transcrição que preserva erros de pronúncia.
    Usa Whisper tiny com temperatura 0 para transcrição literal.
    """
    
    def __init__(self):
        self.model = None
        self.device = "cpu"
        self._loaded = False
        
    def _load_model(self):
        """Carrega modelo Whisper tiny"""
        if self._loaded:
            return
            
        try:
            import whisper
            from ..config import MODEL_CONFIG
            
            model_name = "tiny"  # Whisper tiny (mais leve)
            logger.info(f"Carregando Whisper {model_name}...")
            
            self.device = MODEL_CONFIG.get("chall_model", {}).get("device", "cpu")
            self.model = whisper.load_model(
                model_name,
                device=self.device,
                download_root="./models"
            )
            
            self._loaded = True
            logger.info(f"Whisper {model_name} carregado em {self.device}")
            
        except ImportError:
            logger.error("whisper não instalado. Instale com: pip install openai-whisper")
            raise
        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {e}")
            raise
    
    def transcribe(self, audio_path: Path) -> Dict:
        """
        Transcreve áudio preservando erros
        
        Args:
            audio_path: Caminho do arquivo WAV
            
        Returns:
            Dict com texto transcrito
        """
        self._load_model()
        
        try:
            # Configura para transcrição literal (sem correção)
            result = self.model.transcribe(
                str(audio_path),
                language="en",
                temperature=0.0,  # Determinístico
                beam_size=1,      # Sem beam search (mais literal)
                best_of=1,
                fp16=False,
                without_timestamps=True
            )
            
            text = result["text"].strip()
            logger.info(f"Transcrição: '{text}'")
            
            # Detecta possíveis segmentos de áudio vazio
            segments = result.get("segments", [])
            avg_logprob = np.mean([s.get("avg_logprob", -1) for s in segments]) if segments else -1
            
            return {
                "text": text,
                "confidence": avg_logprob,
                "language": result.get("language", "en")
            }
            
        except Exception as e:
            logger.error(f"Erro na transcrição: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def compare_with_expected(self, actual: str, expected: str) -> Dict:
        """
        Compara transcrição com texto esperado
        
        Returns:
            Dict com erros e similaridade
        """
        if not actual or not expected:
            return {
                "similarity": 0.0,
                "errors": [],
                "correct_words": 0,
                "total_words": len(expected.split())
            }
        
        actual_lower = actual.lower().strip()
        expected_lower = expected.lower().strip()
        
        # Similaridade geral
        similarity = SequenceMatcher(None, actual_lower, expected_lower).ratio()
        
        # Análise palavra por palavra
        actual_words = actual_lower.split()
        expected_words = expected_lower.split()
        
        errors = []
        correct = 0
        
        for i, exp_word in enumerate(expected_words):
            if i < len(actual_words):
                act_word = actual_words[i]
                if act_word == exp_word:
                    correct += 1
                else:
                    # Tenta encontrar correspondência aproximada
                    word_sim = SequenceMatcher(None, act_word, exp_word).ratio()
                    if word_sim < 0.6:  # Muito diferente = erro
                        errors.append({
                            "word": exp_word,
                            "expected": exp_word,
                            "actual": act_word,
                            "position": i,
                            "type": "wrong",
                            "similarity": round(word_sim, 2)
                        })
            else:
                errors.append({
                    "word": exp_word,
                    "expected": exp_word,
                    "actual": "[faltando]",
                    "position": i,
                    "type": "missing"
                })
        
        # Palavras extras
        if len(actual_words) > len(expected_words):
            for i in range(len(expected_words), len(actual_words)):
                errors.append({
                    "word": actual_words[i],
                    "expected": "",
                    "actual": actual_words[i],
                    "position": i,
                    "type": "extra"
                })
        
        return {
            "similarity": round(similarity, 3),
            "errors": errors,
            "correct_words": correct,
            "total_words": len(expected_words),
            "accuracy": round(correct / max(len(expected_words), 1) * 100, 1)
        }


# Instância global
transcriber = ChaLLTranscriber()