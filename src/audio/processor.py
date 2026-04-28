"""
Processamento de áudio profissional com redução de ruído real
"""
import numpy as np
import librosa
import soundfile as sf
import noisereduce as nr
import pyloudnorm as pyln
from pathlib import Path
from typing import Optional, Tuple
import logging
from dataclasses import dataclass

from ..config import AUDIO_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class AudioMetadata:
    """Metadados do áudio processado"""
    duration: float
    sample_rate: int
    rms_energy: float
    snr: float  # Signal-to-Noise Ratio
    is_speech: bool


class AudioProcessor:
    """Processador de áudio com técnicas profissionais"""
    
    def __init__(self, target_sr: int = 16000):
        self.target_sr = target_sr
        self.meter = pyln.Meter(target_sr)  # Loudness meter
        
    def process_pipeline(
        self,
        audio_path: Path,
        output_path: Optional[Path] = None,
        remove_noise: bool = True,
        normalize: bool = True,
        trim_silence: bool = True
    ) -> Tuple[np.ndarray, AudioMetadata]:
        """
        Pipeline completo de processamento de áudio
        
        Args:
            audio_path: Caminho do áudio original
            output_path: Caminho para salvar áudio processado
            remove_noise: Aplicar redução de ruído
            normalize: Normalizar loudness
            trim_silence: Remover silêncio das bordas
            
        Returns:
            Tuple com array de áudio processado e metadados
        """
        # 1. Carregar áudio
        y, sr = librosa.load(str(audio_path), sr=self.target_sr, mono=True)
        logger.info(f"Áudio carregado: {len(y)/sr:.2f}s, {sr}Hz")
        
        # 2. Remover silêncio das bordas
        if trim_silence:
            y = self._trim_silence(y)
        
        # 3. Redução de ruído (antes da normalização!)
        if remove_noise:
            y = self._reduce_noise(y, sr)
        
        # 4. Normalização de loudness (LUFS)
        if normalize:
            y = self._normalize_loudness(y, sr)
        
        # 5. Garantir que não há clipping
        y = np.clip(y, -1.0, 1.0)
        
        # 6. Calcular metadados
        metadata = self._compute_metadata(y, sr)
        
        # 7. Salvar se necessário
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), y, sr)
            logger.info(f"Áudio processado salvo: {output_path}")
        
        return y, metadata
    
    def _trim_silence(self, y: np.ndarray, top_db: int = 20, frame_length: int = 2048, hop_length: int = 512) -> np.ndarray:
        """
        Remove silêncio do início e fim usando energia
        
        Args:
            y: Array de áudio
            top_db: Threshold em dB abaixo do máximo
            frame_length: Tamanho do frame
            hop_length: Hop length
            
        Returns:
            Áudio sem silêncio nas bordas
        """
        # Calcula RMS energy
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)
        
        # Encontra frames acima do threshold
        non_silent = rms_db > -top_db
        
        if not np.any(non_silent):
            logger.warning("Áudio inteiro classificado como silêncio")
            return y
        
        # Encontra primeiro e último frame não-silencioso
        start_idx = np.argmax(non_silent) * hop_length
        end_idx = (len(non_silent) - np.argmax(non_silent[::-1])) * hop_length
        
        # Adiciona pequeno buffer (50ms)
        buffer = int(0.05 * self.target_sr)
        start_idx = max(0, start_idx - buffer)
        end_idx = min(len(y), end_idx + buffer)
        
        return y[start_idx:end_idx]
    
    def _reduce_noise(self, y: np.ndarray, sr: int) -> np.ndarray:
        """
        Redução de ruído usando noisereduce
        Usa os primeiros 200ms como amostra de ruído
        """
        try:
            # Usa início do áudio como perfil de ruído (assume que começa com silêncio)
            noise_sample = y[:int(0.2 * sr)]  # Primeiros 200ms
            
            # Redução de ruído estacionário
            y_clean = nr.reduce_noise(
                y=y,
                sr=sr,
                y_noise=noise_sample,
                prop_decrease=0.9,  # Reduz ruído em 90%
                n_fft=1024,
                win_length=1024,
                hop_length=512
            )
            
            # Redução de ruído não-estacionário
            y_clean = nr.reduce_noise(
                y=y_clean,
                sr=sr,
                stationary=False,
                prop_decrease=0.8,
                n_fft=1024,
                win_length=1024,
                hop_length=512
            )
            
            logger.info("Redução de ruído aplicada com sucesso")
            return y_clean
            
        except Exception as e:
            logger.warning(f"Erro na redução de ruído: {e}. Retornando áudio original.")
            return y
    
    def _normalize_loudness(self, y: np.ndarray, sr: int, target_loudness: float = -23.0) -> np.ndarray:
        """
        Normaliza loudness para padrão EBU R128
        
        Args:
            y: Array de áudio
            sr: Sample rate
            target_loudness: LUFS alvo (padrão broadcast: -23 LUFS)
            
        Returns:
            Áudio normalizado
        """
        try:
            # Mede loudness atual
            current_loudness = self.meter.integrated_loudness(y)
            
            # Normaliza
            y_normalized = pyln.normalize.loudness(y, current_loudness, target_loudness)
            
            # Evita clipping
            max_val = np.max(np.abs(y_normalized))
            if max_val > 0.99:
                y_normalized = y_normalized / max_val * 0.99
                
            logger.info(f"Loudness normalizado: {current_loudness:.1f} -> {target_loudness:.1f} LUFS")
            return y_normalized
            
        except Exception as e:
            logger.warning(f"Erro na normalização: {e}. Usando peak normalization.")
            # Fallback para peak normalization
            peak = np.max(np.abs(y))
            if peak > 0:
                return y / peak * 0.95
            return y
    
    def _compute_metadata(self, y: np.ndarray, sr: int) -> AudioMetadata:
        """Calcula metadados do áudio"""
        duration = len(y) / sr
        
        # RMS energy
        rms = np.sqrt(np.mean(y**2))
        
        # Detecta se há fala (heurística simples)
        is_speech = duration > 0.5 and rms > 0.01
        
        # Estima SNR (Signal-to-Noise Ratio)
        # Usa percentis para separar sinal de ruído
        energy = y**2
        signal_energy = np.percentile(energy, 90)
        noise_energy = np.percentile(energy, 10)
        snr = 10 * np.log10(signal_energy / (noise_energy + 1e-10))
        
        return AudioMetadata(
            duration=duration,
            sample_rate=sr,
            rms_energy=float(rms),
            snr=float(snr),
            is_speech=is_speech
        )


# Instância global
audio_processor = AudioProcessor()