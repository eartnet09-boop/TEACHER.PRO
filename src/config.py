# src/config.py
"""
Configurações centrais do English Teacher Agent
"""
import os
from pathlib import Path

# Tenta carregar dotenv (opcional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv é opcional, usa variáveis de ambiente do sistema

# Diretórios
BASE_DIR = Path(__file__).parent.parent
TEMP_DIR = BASE_DIR / "temp"
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "src" / "web" / "static"

# Cria diretórios
TEMP_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Configurações do servidor
SERVER_CONFIG = {
    "host": os.getenv("HOST", "0.0.0.0"),
    "port": int(os.getenv("PORT", "8000")),
    "reload": os.getenv("RELOAD", "false").lower() == "true",
    "workers": int(os.getenv("WORKERS", "1")),
}

# Configurações de áudio
AUDIO_CONFIG = {
    "sample_rate": 16000,
    "channels": 1,
    "sample_width": 2,
    "max_duration": 10,
    "silence_threshold": 0.01,
    "min_speech_duration": 0.5,
}

# Configurações dos modelos
MODEL_CONFIG = {
    "chall_model": {
        "name": "tiny",  # Whisper tiny
        "device": os.getenv("DEVICE", "cpu"),
        "max_length": 256,
    },
    "wavlm_model": {
        "name": "microsoft/wavlm-base-plus",
        "device": os.getenv("DEVICE", "cpu"),
        "embedding_size": 768,
    },
    "llm_model": {
        "name": os.getenv("LLM_MODEL", "qwen2.5-coder:3b"),
        "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "temperature": 0.3,
        "max_tokens": 300,
    },
}

# Configurações TTS
TTS_CONFIG = {
    "engine": os.getenv("TTS_ENGINE", "edge"),
    "voice": os.getenv("TTS_VOICE", "en-US-AriaNeural"),
    "rate": float(os.getenv("TTS_RATE", "1.0")),
}

# Configurações de scoring
SCORING_CONFIG = {
    "perfect_threshold": 0.9,
    "good_threshold": 0.75,
    "fair_threshold": 0.5,
    "weights": {
        "phoneme_accuracy": 0.4,
        "word_accuracy": 0.3,
        "fluency": 0.2,
        "intonation": 0.1,
    }
}

# Frases padrão para prática
DEFAULT_PHRASES = [
    {
        "text": "The quick brown fox jumps over the lazy dog",
        "phonetic": "/ðə kwɪk braʊn fɑks dʒʌmps ˈoʊvər ðə ˈleɪzi dɔɡ/",
        "difficulty": "medium",
        "focus": "consonant clusters"
    },
    {
        "text": "She sells seashells by the seashore",
        "phonetic": "/ʃi sɛlz ˈsiːʃɛlz baɪ ðə ˈsiːʃɔːr/",
        "difficulty": "hard",
        "focus": "sibilants"
    },
    {
        "text": "I think three thin things",
        "phonetic": "/aɪ θɪŋk θri θɪn θɪŋz/",
        "difficulty": "medium",
        "focus": "th sound"
    },
    {
        "text": "Hello, how are you today?",
        "phonetic": "/həˈloʊ, haʊ ɑːr juː təˈdeɪ?/",
        "difficulty": "easy",
        "focus": "greetings"
    },
]