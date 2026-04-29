"""
Processamento de áudio profissional com redução de ruído real.
Pipeline completo: carregamento → trim silêncio → redução ruído → normalização → metadados.
"""

import numpy as np
import librosa
import soundfile as sf
import noisereduce as nr
import pyloudnorm as pyln
from pathlib import Path
from typing import Optional, Tuple
import logging
from dataclasses import dataclass, field

from ..config import AUDIO_CONFIG

logger = logging.getLogger(__name__)


# ============================================================
# DATACLASSES
# ============================================================

@dataclass
class AudioMetadata:
    """Metadados do áudio processado para diagnóstico e monitoramento."""
    duration: float
    sample_rate: int
    rms_energy: float
    snr: float
    peak_amplitude: float
    is_speech: bool
    has_clipping: bool
    loudness_lufs: float
    warnings: list = field(default_factory=list)


# ============================================================
# PROCESSADOR PRINCIPAL
# ============================================================

class AudioProcessor:
    """
    Processador de áudio com técnicas profissionais de DSP.
    
    Pipeline:
    1. Carregamento (librosa)
    2. Remoção de silêncio nas bordas
    3. Redução de ruído (noisereduce)
    4. Normalização de loudness (LUFS)
    5. Prevenção de clipping
    6. Extração de metadados
    """
    
    def __init__(self, target_sr: int = None):
        """
        Inicializa o processador de áudio.
        
        Args:
            target_sr: Sample rate alvo (padrão: config)
        """
        self.target_sr = target_sr or AUDIO_CONFIG.get("sample_rate", 16000)
        
        # Inicializa medidor de loudness (EBU R128)
        try:
            self.loudness_meter = pyln.Meter(self.target_sr)
        except Exception as e:
            logger.warning(f"Não foi possível inicializar medidor LUFS: {e}")
            self.loudness_meter = None
        
        # Configurações
        self.trim_top_db = AUDIO_CONFIG.get("trim_silence_threshold_db", 20)
        self.noise_prop_decrease = AUDIO_CONFIG.get("noise_reduction_prop_decrease", 0.9)
        self.target_loudness = AUDIO_CONFIG.get("target_loudness_lufs", -23.0)
        self.min_speech_duration = AUDIO_CONFIG.get("min_speech_duration", 0.5)
        self.silence_threshold = AUDIO_CONFIG.get("silence_threshold", 0.01)
    
    # ============================================================
    # PIPELINE PRINCIPAL
    # ============================================================
    
    def process_pipeline(
        self,
        audio_path: Path,
        output_path: Optional[Path] = None,
        remove_noise: bool = True,
        normalize: bool = True,
        trim_silence: bool = True,
        aggressive_noise_reduction: bool = False,
    ) -> Tuple[np.ndarray, AudioMetadata]:
        """
        Pipeline completo de processamento de áudio.
        
        Args:
            audio_path: Caminho do arquivo de áudio original
            output_path: Caminho para salvar áudio processado (opcional)
            remove_noise: Aplicar redução de ruído
            normalize: Normalizar loudness
            trim_silence: Remover silêncio das bordas
            aggressive_noise_reduction: Modo agressivo (remove mais ruído, pode distorcer)
            
        Returns:
            Tuple: (array de áudio processado, metadados)
            
        Raises:
            FileNotFoundError: Se arquivo não existe
            ValueError: Se áudio é inválido ou muito curto
        """
        warnings_list = []
        
        # 1. VALIDAÇÃO E CARREGAMENTO
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {audio_path}")
        
        try:
            y, sr = librosa.load(
                str(audio_path),
                sr=self.target_sr,
                mono=True,
                res_type='kaiser_best'
            )
        except Exception as e:
            raise ValueError(f"Erro ao carregar áudio: {e}")
        
        original_duration = len(y) / sr
        
        # Valida duração mínima
        if original_duration < 0.1:
            raise ValueError(f"Áudio muito curto: {original_duration:.2f}s (mínimo 0.1s)")
        
        logger.info(f"Áudio carregado: {original_duration:.2f}s, {sr}Hz, {len(y)} samples")
        
        # 2. REMOÇÃO DE SILÊNCIO DAS BORDAS
        if trim_silence:
            y, trim_info = self._trim_silence(y)
            trim_duration = len(y) / sr
            
            if trim_duration < 0.1:
                warnings_list.append("Áudio ficou muito curto após remoção de silêncio")
                logger.warning("Após trim, áudio ficou com menos de 0.1s")
        
        # Verifica se ainda tem áudio após trim
        if len(y) < int(0.1 * sr):
            logger.warning("Áudio essencialmente vazio após processamento inicial")
            metadata = self._compute_metadata(y, sr, warnings_list)
            if output_path:
                self._save_audio(y, sr, output_path)
            return y, metadata
        
        # 3. REDUÇÃO DE RUÍDO
        if remove_noise:
            try:
                y = self._reduce_noise(y, sr, aggressive=aggressive_noise_reduction)
            except Exception as e:
                warnings_list.append(f"Redução de ruído falhou: {e}")
                logger.warning(f"Redução de ruído falhou, continuando sem: {e}")
        
        # 4. NORMALIZAÇÃO DE LOUDNESS
        if normalize:
            try:
                y, norm_info = self._normalize_loudness(y, sr)
                if norm_info.get("fallback"):
                    warnings_list.append("Normalização LUFS falhou, usando peak normalization")
            except Exception as e:
                warnings_list.append(f"Normalização falhou: {e}")
                logger.warning(f"Normalização falhou, continuando sem: {e}")
        
        # 5. PREVENÇÃO DE CLIPPING
        y = self._prevent_clipping(y)
        
        # 6. METADADOS
        metadata = self._compute_metadata(y, sr, warnings_list)
        
        # 7. SALVAR (OPCIONAL)
        if output_path:
            self._save_audio(y, sr, output_path)
        
        # Log resumo
        logger.info(
            f"Processamento concluído: "
            f"duração={metadata.duration:.2f}s, "
            f"SNR={metadata.snr:.1f}dB, "
            f"LUFS={metadata.loudness_lufs:.1f}, "
            f"speech={'Sim' if metadata.is_speech else 'Não'}, "
            f"warnings={len(metadata.warnings)}"
        )
        
        return y, metadata
    
    # ============================================================
    # REMOÇÃO DE SILÊNCIO
    # ============================================================
    
    def _trim_silence(
        self,
        y: np.ndarray,
        top_db: int = None,
        frame_length: int = 2048,
        hop_length: int = 512
    ) -> Tuple[np.ndarray, dict]:
        """
        Remove silêncio do início e fim do áudio.
        Usa energia RMS para detectar segmentos com fala.
        
        Args:
            y: Array de áudio
            top_db: Threshold em dB abaixo do pico
            frame_length: Tamanho da janela de análise
            hop_length: Passo entre janelas
            
        Returns:
            Tuple: (áudio trimado, dicionário com informações)
        """
        top_db = top_db or self.trim_top_db
        
        try:
            # Calcula energia RMS por frame
            rms = librosa.feature.rms(
                y=y,
                frame_length=frame_length,
                hop_length=hop_length
            )[0]
            
            # Converte para dB (relativo ao pico)
            rms_db = librosa.amplitude_to_db(rms, ref=np.max(rms) if np.max(rms) > 0 else 1.0)
            
            # Encontra frames com energia acima do threshold
            non_silent = rms_db > -top_db
            
            if not np.any(non_silent):
                logger.warning("Nenhum segmento de fala detectado (áudio pode ser silêncio)")
                return y, {"trimmed": False, "reason": "no_speech_detected"}
            
            # Encontra primeiro e último frame com fala
            first_frame = np.argmax(non_silent)
            last_frame = len(non_silent) - np.argmax(non_silent[::-1]) - 1
            
            # Converte frames para samples
            start_sample = first_frame * hop_length
            end_sample = min(len(y), (last_frame + 1) * hop_length)
            
            # Adiciona buffer de 100ms antes e depois
            buffer_samples = int(0.1 * self.target_sr)
            start_sample = max(0, start_sample - buffer_samples)
            end_sample = min(len(y), end_sample + buffer_samples)
            
            # Aplica trim
            y_trimmed = y[start_sample:end_sample]
            
            duration_before = len(y) / self.target_sr
            duration_after = len(y_trimmed) / self.target_sr
            
            logger.debug(
                f"Trim silêncio: {duration_before:.2f}s → {duration_after:.2f}s "
                f"(removeu {duration_before - duration_after:.2f}s)"
            )
            
            return y_trimmed, {
                "trimmed": True,
                "duration_before": round(duration_before, 3),
                "duration_after": round(duration_after, 3),
                "removed_seconds": round(duration_before - duration_after, 3)
            }
            
        except Exception as e:
            logger.warning(f"Erro ao remover silêncio: {e}")
            return y, {"trimmed": False, "reason": str(e)}
    
    # ============================================================
    # REDUÇÃO DE RUÍDO
    # ============================================================
    
    def _reduce_noise(
        self,
        y: np.ndarray,
        sr: int,
        aggressive: bool = False
    ) -> np.ndarray:
        """
        Redução de ruído de fundo usando noisereduce.
        
        Estratégia:
        1. Usa primeiros 200ms como perfil de ruído
        2. Aplica redução estacionária
        3. Aplica redução não-estacionária
        
        Args:
            y: Array de áudio
            sr: Sample rate
            aggressive: Se True, usa redução mais forte
            
        Returns:
            Áudio com ruído reduzido
        """
        # Verifica se há áudio suficiente para análise de ruído
        noise_sample_duration = 0.15 if aggressive else 0.2
        noise_samples = int(noise_sample_duration * sr)
        
        if len(y) < noise_samples * 2:
            logger.debug("Áudio muito curto para redução de ruído efetiva")
            return y
        
        try:
            # Extrai perfil de ruído do início (assume que começa com silêncio/ruído)
            noise_profile = y[:noise_samples]
            
            # Verifica se o perfil de ruído tem energia (não é silêncio total)
            noise_energy = np.mean(noise_profile ** 2)
            signal_energy = np.mean(y[noise_samples:] ** 2)
            
            if noise_energy < 1e-8:
                logger.debug("Perfil de ruído com energia muito baixa, pulando redução")
                return y
            
            # Parâmetros baseados no modo
            prop_decrease = 0.95 if aggressive else self.noise_prop_decrease
            n_fft = 2048 if aggressive else 1024
            
            # 1ª passagem: ruído estacionário
            y_clean = nr.reduce_noise(
                y=y,
                sr=sr,
                y_noise=noise_profile,
                prop_decrease=prop_decrease,
                n_fft=n_fft,
                win_length=n_fft,
                hop_length=n_fft // 2,
                time_mask_smooth_ms=50,
                freq_mask_smooth_hz=500,
            )
            
            # 2ª passagem: ruído não-estacionário (mais suave)
            if not aggressive:
                y_clean = nr.reduce_noise(
                    y=y_clean,
                    sr=sr,
                    stationary=False,
                    prop_decrease=0.6,
                    n_fft=1024,
                    win_length=1024,
                    hop_length=512,
                    time_mask_smooth_ms=25,
                )
            
            # Verifica se a redução não destruiu o áudio
            energy_before = np.mean(y ** 2)
            energy_after = np.mean(y_clean ** 2)
            
            if energy_after < energy_before * 0.01:
                logger.warning("Redução de ruído removeu energia demais, usando original")
                return y
            
            logger.info(
                f"Redução de ruído: "
                f"energia {energy_before:.6f} → {energy_after:.6f} "
                f"({(1 - energy_after/energy_before)*100:.0f}% reduzida)"
            )
            
            return y_clean
            
        except Exception as e:
            logger.warning(f"Erro na redução de ruído: {e}. Retornando áudio original.")
            return y
    
    # ============================================================
    # NORMALIZAÇÃO
    # ============================================================
    
    def _normalize_loudness(
        self,
        y: np.ndarray,
        sr: int,
        target_loudness: float = None
    ) -> Tuple[np.ndarray, dict]:
        """
        Normaliza loudness para padrão EBU R128.
        Com fallback robusto para peak normalization.
        
        Args:
            y: Array de áudio
            sr: Sample rate
            target_loudness: LUFS alvo (padrão: -23)
            
        Returns:
            Tuple: (áudio normalizado, dicionário com info)
        """
        target_loudness = target_loudness or self.target_loudness
        
        # Verifica energia mínima
        energy = np.mean(y ** 2)
        if energy < 1e-8:
            logger.warning("Energia do áudio muito baixa, pulando normalização")
            return y, {"normalized": False, "reason": "energy_too_low", "fallback": True}
        
        # Tenta normalização LUFS
        if self.loudness_meter is not None:
            try:
                current_loudness = self.loudness_meter.integrated_loudness(y)
                
                # Verifica se loudness é válido
                if np.isinf(current_loudness) or np.isnan(current_loudness):
                    raise ValueError(f"Loudness inválido: {current_loudness}")
                
                # Normaliza
                y_normalized = pyln.normalize.loudness(y, current_loudness, target_loudness)
                
                # Previne clipping
                max_val = np.max(np.abs(y_normalized))
                if max_val > 0.99:
                    y_normalized = y_normalized / max_val * 0.99
                
                logger.info(
                    f"Loudness normalizado: "
                    f"{current_loudness:.1f} → {target_loudness:.1f} LUFS"
                )
                
                return y_normalized, {
                    "normalized": True,
                    "method": "lufs",
                    "before_lufs": round(float(current_loudness), 1),
                    "after_lufs": target_loudness,
                    "fallback": False
                }
                
            except Exception as e:
                logger.warning(f"Normalização LUFS falhou: {e}")
        
        # Fallback: peak normalization
        return self._peak_normalize(y), {
            "normalized": True,
            "method": "peak",
            "fallback": True
        }
    
    def _peak_normalize(self, y: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
        """
        Normalização por pico (fallback simples e robusto).
        
        Args:
            y: Array de áudio
            target_peak: Amplitude pico alvo (0-1)
            
        Returns:
            Áudio normalizado
        """
        peak = np.max(np.abs(y))
        
        if peak < 1e-8:
            logger.warning("Pico muito baixo para normalização")
            return y
        
        gain = target_peak / peak
        
        # Limita ganho máximo para evitar amplificar ruído
        max_gain = 10.0  # +20dB máximo
        gain = min(gain, max_gain)
        
        y_normalized = y * gain
        
        logger.debug(f"Peak normalization: pico {peak:.4f} → {target_peak:.4f} (ganho: {gain:.2f}x)")
        
        return y_normalized
    
    # ============================================================
    # PREVENÇÃO DE CLIPPING
    # ============================================================
    
    def _prevent_clipping(self, y: np.ndarray) -> np.ndarray:
        """
        Garante que o áudio não tenha clipping.
        Aplica limiter suave se necessário.
        
        Args:
            y: Array de áudio
            
        Returns:
            Áudio sem clipping
        """
        max_val = np.max(np.abs(y))
        
        if max_val > 0.99:
            # Aplica soft clipping
            threshold = 0.9
            y_clipped = np.where(
                np.abs(y) > threshold,
                np.sign(y) * (threshold + (1 - threshold) * np.tanh((np.abs(y) - threshold) / (1 - threshold))),
                y
            )
            logger.debug(f"Soft clipping aplicado (pico original: {max_val:.3f})")
            return y_clipped
        
        return y
    
    # ============================================================
    # METADADOS
    # ============================================================
    
    def _compute_metadata(
        self,
        y: np.ndarray,
        sr: int,
        warnings_list: list = None
    ) -> AudioMetadata:
        """
        Calcula metadados detalhados do áudio processado.
        
        Args:
            y: Array de áudio
            sr: Sample rate
            warnings_list: Lista de avisos do pipeline
            
        Returns:
            AudioMetadata com todas as métricas
        """
        duration = len(y) / sr
        
        # Energia RMS
        rms_energy = float(np.sqrt(np.mean(y ** 2)))
        
        # Amplitude de pico
        peak_amplitude = float(np.max(np.abs(y)))
        
        # Detecta clipping
        has_clipping = peak_amplitude > 0.99
        
        # Detecta se há fala
        is_speech = duration >= self.min_speech_duration and rms_energy > self.silence_threshold
        
        # Estima SNR (Signal-to-Noise Ratio)
        energy = y ** 2
        signal_percentile = np.percentile(energy, 90)
        noise_percentile = np.percentile(energy, 10)
        
        if noise_percentile > 0:
            snr = float(10 * np.log10(signal_percentile / noise_percentile))
        else:
            snr = 100.0  # Sem ruído detectado
        
        # Mede loudness final
        loudness_lufs = -70.0  # Valor padrão
        if self.loudness_meter is not None and duration >= 0.5:
            try:
                loudness_lufs = float(self.loudness_meter.integrated_loudness(y))
            except Exception:
                pass
        
        return AudioMetadata(
            duration=round(duration, 3),
            sample_rate=sr,
            rms_energy=round(rms_energy, 6),
            snr=round(snr, 1),
            peak_amplitude=round(peak_amplitude, 4),
            is_speech=is_speech,
            has_clipping=has_clipping,
            loudness_lufs=round(loudness_lufs, 1),
            warnings=warnings_list or []
        )
    
    # ============================================================
    # UTILITÁRIOS
    # ============================================================
    
    def _save_audio(self, y: np.ndarray, sr: int, output_path: Path):
        """
        Salva áudio processado em arquivo WAV.
        
        Args:
            y: Array de áudio
            sr: Sample rate
            output_path: Caminho de saída
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            sf.write(str(output_path), y, sr, subtype='PCM_16')
            logger.debug(f"Áudio salvo: {output_path} ({output_path.stat().st_size} bytes)")
        except Exception as e:
            logger.error(f"Erro ao salvar áudio: {e}")
    
    def get_audio_info(self, audio_path: Path) -> dict:
        """
        Retorna informações básicas de um arquivo de áudio sem processá-lo.
        
        Args:
            audio_path: Caminho do arquivo
            
        Returns:
            Dicionário com informações
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            return {"exists": False}
        
        try:
            y, sr = librosa.load(str(audio_path), sr=None, mono=True)
            duration = len(y) / sr
            
            return {
                "exists": True,
                "duration": round(duration, 2),
                "sample_rate": sr,
                "channels": 1,
                "file_size_kb": round(audio_path.stat().st_size / 1024, 1),
                "peak_amplitude": round(float(np.max(np.abs(y))), 4),
                "rms_energy": round(float(np.sqrt(np.mean(y ** 2))), 6),
            }
        except Exception as e:
            return {"exists": True, "error": str(e)}


# ============================================================
# INSTÂNCIA GLOBAL
# ============================================================

audio_processor = AudioProcessor()