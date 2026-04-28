# src/tts/speaker.py
"""
Síntese de voz usando Edge TTS (gratuito e rápido)
"""
import asyncio
import tempfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Speaker:
    """Sintetizador de voz"""
    
    def __init__(self):
        self.voice = "en-US-AriaNeural"
        
    async def speak(self, text: str) -> Path:
        """
        Gera áudio a partir de texto
        
        Args:
            text: Texto para sintetizar
            
        Returns:
            Path do arquivo de áudio gerado
        """
        try:
            import edge_tts
            
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            
            output_path = temp_dir / f"tts_{hash(text)}.wav"
            
            # Se já existe, retorna cache
            if output_path.exists():
                return output_path
            
            # Gera áudio
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(str(output_path))
            
            logger.info(f"Áudio TTS gerado: {output_path}")
            return output_path
            
        except ImportError:
            logger.warning("edge_tts não instalado. Instale com: pip install edge-tts")
            
            # Fallback: cria arquivo silencioso
            return self._create_silent_audio()
            
        except Exception as e:
            logger.error(f"Erro TTS: {e}")
            return self._create_silent_audio()
    
    def _create_silent_audio(self) -> Path:
        """Cria arquivo de áudio silencioso como fallback"""
        import numpy as np
        import soundfile as sf
        
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        
        output_path = temp_dir / "tts_silent.wav"
        
        # 1 segundo de silêncio
        silence = np.zeros(16000)
        sf.write(str(output_path), silence, 16000)
        
        return output_path


# Instância global
speaker = Speaker()