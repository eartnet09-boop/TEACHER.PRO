"""
Alinhamento forçado (Forced Alignment) usando Wav2Vec2 com CTC
Alinha transcrição de referência com áudio para localizar fonemas
"""
import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AlignmentSegment:
    """Segmento de áudio alinhado"""
    word: str
    phoneme: str
    start_time: float  # segundos
    end_time: float    # segundos
    confidence: float  # 0-1
    audio_array: Optional[np.ndarray] = None


class ForcedAligner:
    """
    Alinhador forçado que mapeia palavras/fonemas para timestamps no áudio.
    
    Funcionamento:
    1. Recebe áudio + transcrição de referência
    2. Usa Wav2Vec2 com CTC para gerar matriz de probabilidades
    3. Aplica algoritmo de alinhamento temporal (Viterbi/CTC)
    4. Retorna timestamps para cada palavra/fonema
    """
    
    def __init__(self, device: str = "cpu"):
        self.device = device
        self.model = None
        self.processor = None
        self._loaded = False
        
    def _load_model(self):
        """Carrega modelo Wav2Vec2 para alinhamento"""
        if self._loaded:
            return
            
        try:
            from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
            
            model_name = "facebook/wav2vec2-base-960h"
            logger.info(f"Carregando {model_name} para alinhamento...")
            
            self.processor = Wav2Vec2Processor.from_pretrained(model_name)
            self.model = Wav2Vec2ForCTC.from_pretrained(model_name)
            self.model = self.model.to(self.device)
            self.model.eval()
            
            self._loaded = True
            logger.info("Modelo de alinhamento carregado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao carregar modelo de alinhamento: {e}")
            raise
    
    def align(
        self,
        audio_path: Path,
        reference_text: str,
        return_phonemes: bool = False
    ) -> List[AlignmentSegment]:
        """
        Alinha transcrição de referência com áudio
        
        Args:
            audio_path: Caminho do arquivo WAV (16kHz, mono)
            reference_text: Texto de referência (o que deveria ser falado)
            return_phonemes: Se True, retorna alinhamento por fonema
            
        Returns:
            Lista de AlignmentSegment com timestamps
        """
        self._load_model()
        
        # 1. Carrega áudio
        waveform, sample_rate = torchaudio.load(str(audio_path))
        
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(sample_rate, 16000)
            waveform = resampler(waveform)
            sample_rate = 16000
        
        # Garante mono
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        
        # 2. Processa áudio com Wav2Vec2
        input_values = self.processor(
            waveform.squeeze(0).numpy(),
            sampling_rate=16000,
            return_tensors="pt"
        ).input_values.to(self.device)
        
        with torch.no_grad():
            outputs = self.model(input_values)
            logits = outputs.logits  # (1, time_steps, vocab_size)
        
        # 3. Prepara tokens da referência
        tokens = self.processor.tokenizer(reference_text.lower(), return_tensors="pt")
        input_ids = tokens.input_ids.squeeze(0)  # remove batch dimension
        
        # 4. Alinhamento CTC
        trellis = self._get_trellis(logits, input_ids)
        path = self._viterbi_path(trellis)
        segments = self._merge_segments(path, input_ids, waveform, sample_rate)
        
        # 5. Converte tokens para palavras/fonemas
        aligned_segments = self._tokens_to_segments(
            segments, 
            reference_text,
            return_phonemes
        )
        
        return aligned_segments
    
    def _get_trellis(self, emission, tokens, blank_id=0):
        """Constrói trellis para Viterbi"""
        num_frames = emission.size(1)
        num_tokens = len(tokens)
        
        # Adiciona blanks entre tokens
        trellis = torch.zeros((num_frames, num_tokens + 1))
        trellis[:, 0] = emission[0, :, blank_id]  # probabilidade do blank
        
        for t in range(num_tokens):
            trellis[:, t + 1] = emission[0, :, tokens[t]]
            
        return trellis
    
    def _viterbi_path(self, trellis):
        """Algoritmo de Viterbi para encontrar melhor caminho"""
        T, S = trellis.shape
        dp = torch.full((T, S), -float('inf'))
        backpointer = torch.zeros((T, S), dtype=torch.long)
        
        # Inicialização
        dp[0, 0] = trellis[0, 0]  # blank
        if S > 1:
            dp[0, 1] = trellis[0, 1]  # primeiro token
        
        # Preenchimento
        for t in range(1, T):
            for s in range(S):
                # Transições possíveis:
                # 1. Manter no mesmo estado (blank→blank, token→token)
                # 2. Blank → próximo token
                # 3. Token → blank
                
                candidates = [(dp[t-1, s], s)]  # mesmo estado
                
                if s > 0:
                    candidates.append((dp[t-1, s-1], s-1))  # blank → token
                if s < S - 1:
                    candidates.append((dp[t-1, s+1], s+1))  # token → blank
                
                best_val, best_prev = max(candidates, key=lambda x: x[0])
                dp[t, s] = best_val + trellis[t, s]
                backpointer[t, s] = best_prev
        
        # Backtracking
        path = []
        curr = S - 1
        for t in range(T - 1, -1, -1):
            path.append(curr)
            curr = backpointer[t, curr].item()
        path.reverse()
        
        return path
    
    def _merge_segments(self, path, tokens, waveform, sample_rate):
        """Agrupa frames do mesmo token em segmentos"""
        segments = []
        current_token = path[0]
        start_frame = 0
        
        frames_per_sec = sample_rate / 320  # Wav2Vec2: stride = 320 samples
        
        for frame, token in enumerate(path[1:], 1):
            if token != current_token:
                # Salva segmento anterior
                if current_token > 0:  # ignora blank
                    token_idx = current_token - 1
                    token_id = tokens[token_idx].item() if token_idx < len(tokens) else None
                    
                    if token_id is not None:
                        start_time = start_frame / frames_per_sec
                        end_time = frame / frames_per_sec
                        
                        # Extrai áudio do segmento
                        start_sample = int(start_time * sample_rate)
                        end_sample = int(end_time * sample_rate)
                        audio_segment = waveform[0, start_sample:end_sample].numpy()
                        
                        segments.append({
                            "token_id": token_id,
                            "start": start_time,
                            "end": end_time,
                            "audio": audio_segment
                        })
                
                current_token = token
                start_frame = frame
        
        return segments
    
    def _tokens_to_segments(
        self, 
        segments: List[Dict], 
        reference_text: str,
        return_phonemes: bool
    ) -> List[AlignmentSegment]:
        """Converte tokens para palavras/fonemas"""
        words = reference_text.lower().split()
        aligned = []
        
        for i, seg in enumerate(segments):
            # Tenta decodificar token
            try:
                token_text = self.processor.decode([seg["token_id"]])
            except:
                token_text = ""
            
            # Associa ao word mais próximo
            word_idx = min(i * len(words) // max(len(segments), 1), len(words) - 1)
            word = words[word_idx]
            
            # Converte para fonema aproximado (simplificado)
            phoneme = self._approximate_phoneme(token_text) if return_phonemes else token_text
            
            aligned.append(AlignmentSegment(
                word=word,
                phoneme=phoneme,
                start_time=seg["start"],
                end_time=seg["end"],
                confidence=0.8,
                audio_array=seg["audio"]
            ))
        
        return aligned
    
    def _approximate_phoneme(self, token: str) -> str:
        """Conversão simplificada token→fonema (ARPAbet aproximado)"""
        phoneme_map = {
            'a': 'AE', 'e': 'EH', 'i': 'IH', 'o': 'OW', 'u': 'UW',
            'th': 'TH', 'sh': 'SH', 'ch': 'CH', 'ng': 'NG',
            'p': 'P', 'b': 'B', 't': 'T', 'd': 'D', 'k': 'K', 'g': 'G',
            'f': 'F', 'v': 'V', 's': 'S', 'z': 'Z',
            'm': 'M', 'n': 'N', 'l': 'L', 'r': 'R',
            'w': 'W', 'y': 'Y', 'h': 'HH',
        }
        return phoneme_map.get(token.lower(), token.upper())


# Instância global
aligner = ForcedAligner()