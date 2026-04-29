# src/config.py
"""
Configurações centrais do English Teacher Agent v4.0
Arquivo de configuração unificado para todos os módulos do sistema.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

# ============================================================
# VARIÁVEIS DE AMBIENTE
# ============================================================

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ============================================================
# DIRETÓRIOS DO PROJETO
# ============================================================

BASE_DIR = Path(__file__).parent.parent
SRC_DIR = BASE_DIR / "src"
TEMP_DIR = BASE_DIR / "temp"
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = SRC_DIR / "web" / "static"
DATA_DIR = SRC_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Criação automática de diretórios
for directory in [TEMP_DIR, MODELS_DIR, STATIC_DIR, DATA_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONFIGURAÇÕES DO SERVIDOR
# ============================================================

SERVER_CONFIG: Dict[str, Any] = {
    "host": os.getenv("HOST", "0.0.0.0"),
    "port": int(os.getenv("PORT", "8000")),
    "reload": os.getenv("RELOAD", "false").lower() == "true",
    "workers": int(os.getenv("WORKERS", "1")),
    "timeout_keep_alive": int(os.getenv("TIMEOUT_KEEP_ALIVE", "30")),
    "graceful_timeout": int(os.getenv("GRACEFUL_TIMEOUT", "10")),
    "max_upload_size": int(os.getenv("MAX_UPLOAD_SIZE", "10485760")),  # 10 MB
    "allowed_origins": os.getenv("ALLOWED_ORIGINS", "*").split(","),
    "environment": os.getenv("ENVIRONMENT", "development"),
}


# ============================================================
# CONFIGURAÇÕES DO BANCO DE DADOS
# ============================================================

DATABASE_CONFIG: Dict[str, Any] = {
    "path": BASE_DIR / os.getenv("DB_PATH", "english_teacher.db"),
    "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
    "timeout": int(os.getenv("DB_TIMEOUT", "30")),
    "busy_timeout": int(os.getenv("DB_BUSY_TIMEOUT", "5000")),
    "journal_mode": os.getenv("DB_JOURNAL_MODE", "WAL"),
    "foreign_keys": os.getenv("DB_FOREIGN_KEYS", "ON"),
    "synchronous": os.getenv("DB_SYNCHRONOUS", "NORMAL"),
    "cache_size": int(os.getenv("DB_CACHE_SIZE", "-64000")),
    "auto_vacuum": os.getenv("DB_AUTO_VACUUM", "INCREMENTAL"),
    "temp_store": os.getenv("DB_TEMP_STORE", "MEMORY"),
    "backup_enabled": os.getenv("DB_BACKUP_ENABLED", "true").lower() == "true",
    "backup_interval_hours": int(os.getenv("DB_BACKUP_INTERVAL", "24")),
    "backup_path": BASE_DIR / os.getenv("DB_BACKUP_PATH", "backups"),
}


# ============================================================
# CONFIGURAÇÕES DE ÁUDIO
# ============================================================

AUDIO_CONFIG: Dict[str, Any] = {
    "sample_rate": int(os.getenv("AUDIO_SAMPLE_RATE", "16000")),
    "channels": int(os.getenv("AUDIO_CHANNELS", "1")),
    "sample_width": int(os.getenv("AUDIO_SAMPLE_WIDTH", "2")),  # 16-bit
    "max_duration": int(os.getenv("AUDIO_MAX_DURATION", "10")),
    "min_duration": float(os.getenv("AUDIO_MIN_DURATION", "0.5")),
    "silence_threshold": float(os.getenv("AUDIO_SILENCE_THRESHOLD", "0.01")),
    "min_speech_duration": float(os.getenv("AUDIO_MIN_SPEECH_DURATION", "0.5")),
    "noise_reduction_enabled": os.getenv("AUDIO_NOISE_REDUCTION", "true").lower() == "true",
    "noise_reduction_prop_decrease": float(os.getenv("AUDIO_NOISE_PROP_DECREASE", "0.9")),
    "normalization_enabled": os.getenv("AUDIO_NORMALIZATION", "true").lower() == "true",
    "target_loudness_lufs": float(os.getenv("AUDIO_TARGET_LUFS", "-23.0")),
    "trim_silence_enabled": os.getenv("AUDIO_TRIM_SILENCE", "true").lower() == "true",
    "trim_silence_threshold_db": int(os.getenv("AUDIO_TRIM_THRESHOLD_DB", "20")),
    "supported_formats": ["wav", "webm", "mp3", "ogg", "flac", "m4a"],
    "max_file_size_mb": int(os.getenv("AUDIO_MAX_FILE_SIZE_MB", "20")),
}


# ============================================================
# CONFIGURAÇÕES DOS MODELOS DE IA
# ============================================================

MODEL_CONFIG: Dict[str, Dict[str, Any]] = {
    "transcription": {
        "name": os.getenv("TRANSCRIPTION_MODEL", "tiny"),
        "device": os.getenv("DEVICE", "cpu"),
        "max_length": int(os.getenv("TRANSCRIPTION_MAX_LENGTH", "256")),
        "temperature": float(os.getenv("TRANSCRIPTION_TEMPERATURE", "0.0")),
        "beam_size": int(os.getenv("TRANSCRIPTION_BEAM_SIZE", "1")),
        "language": os.getenv("TRANSCRIPTION_LANGUAGE", "en"),
        "fp16": os.getenv("TRANSCRIPTION_FP16", "false").lower() == "true",
        "download_root": str(MODELS_DIR),
        "cache_enabled": os.getenv("TRANSCRIPTION_CACHE", "true").lower() == "true",
    },
    "wavlm": {
        "name": os.getenv("WAVLM_MODEL", "microsoft/wavlm-base-plus"),
        "device": os.getenv("DEVICE", "cpu"),
        "embedding_size": int(os.getenv("WAVLM_EMBEDDING_SIZE", "768")),
        "cache_dir": str(MODELS_DIR),
        "normalize_embeddings": os.getenv("WAVLM_NORMALIZE", "true").lower() == "true",
        "max_audio_length_seconds": int(os.getenv("WAVLM_MAX_AUDIO_LENGTH", "30")),
        "batch_size": int(os.getenv("WAVLM_BATCH_SIZE", "1")),
    },
    "aligner": {
        "name": os.getenv("ALIGNER_MODEL", "facebook/wav2vec2-base-960h"),
        "device": os.getenv("DEVICE", "cpu"),
        "cache_dir": str(MODELS_DIR),
        "stride_samples": int(os.getenv("ALIGNER_STRIDE", "320")),
        "min_confidence": float(os.getenv("ALIGNER_MIN_CONFIDENCE", "0.5")),
    },
    "tutor": {
        "name": os.getenv("LLM_MODEL", "qwen2.5-coder:3b"),
        "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.3")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "300")),
        "top_p": float(os.getenv("LLM_TOP_P", "0.9")),
        "top_k": int(os.getenv("LLM_TOP_K", "40")),
        "repeat_penalty": float(os.getenv("LLM_REPEAT_PENALTY", "1.1")),
        "timeout_seconds": int(os.getenv("LLM_TIMEOUT", "30")),
        "retry_attempts": int(os.getenv("LLM_RETRY_ATTEMPTS", "3")),
        "cache_responses": os.getenv("LLM_CACHE", "true").lower() == "true",
        "cache_ttl_minutes": int(os.getenv("LLM_CACHE_TTL", "60")),
    },
}


# ============================================================
# CONFIGURAÇÕES DE TTS (TEXT-TO-SPEECH)
# ============================================================

TTS_CONFIG: Dict[str, Any] = {
    "engine": os.getenv("TTS_ENGINE", "edge"),
    "voice": os.getenv("TTS_VOICE", "en-US-AriaNeural"),
    "rate": float(os.getenv("TTS_RATE", "1.0")),
    "pitch": int(os.getenv("TTS_PITCH", "0")),
    "volume": int(os.getenv("TTS_VOLUME", "100")),
    "fallback_engine": os.getenv("TTS_FALLBACK_ENGINE", "gtts"),
    "cache_audio": os.getenv("TTS_CACHE", "true").lower() == "true",
    "cache_dir": TEMP_DIR / "tts_cache",
    "cache_max_size_mb": int(os.getenv("TTS_CACHE_MAX_SIZE", "500")),
    "format": os.getenv("TTS_FORMAT", "wav"),
    "silence_padding_ms": int(os.getenv("TTS_SILENCE_PADDING", "200")),
}


# ============================================================
# CONFIGURAÇÕES DE SCORING E AVALIAÇÃO
# ============================================================

SCORING_CONFIG: Dict[str, Any] = {
    "thresholds": {
        "excellent": float(os.getenv("SCORE_EXCELLENT", "90")),
        "good": float(os.getenv("SCORE_GOOD", "75")),
        "fair": float(os.getenv("SCORE_FAIR", "60")),
        "poor": float(os.getenv("SCORE_POOR", "40")),
    },
    "levels": {
        "excellent": {"label": "Excelente", "emoji": "🌟", "color": "#28a745"},
        "good": {"label": "Bom", "emoji": "👍", "color": "#17a2b8"},
        "fair": {"label": "Regular", "emoji": "📚", "color": "#ffc107"},
        "poor": {"label": "Ruim", "emoji": "💪", "color": "#fd7e14"},
        "very_poor": {"label": "Muito Ruim", "emoji": "🎯", "color": "#dc3545"},
    },
    "weights": {
        "phoneme_accuracy": float(os.getenv("WEIGHT_PHONEME", "0.45")),
        "fluency": float(os.getenv("WEIGHT_FLUENCY", "0.25")),
        "prosody": float(os.getenv("WEIGHT_PROSODY", "0.15")),
        "confidence": float(os.getenv("WEIGHT_CONFIDENCE", "0.15")),
    },
    "similarity_scale_factor": float(os.getenv("SIMILARITY_SCALE", "120")),
    "min_score": float(os.getenv("MIN_SCORE", "10")),
    "max_score": float(os.getenv("MAX_SCORE", "100")),
    "random_variation_range": float(os.getenv("RANDOM_VARIATION", "5")),
}


# ============================================================
# CONFIGURAÇÕES DE ESTUDO
# ============================================================

STUDY_CONFIG: Dict[str, Any] = {
    "words_per_session": int(os.getenv("STUDY_WORDS_PER_SESSION", "10")),
    "min_score_to_pass": float(os.getenv("STUDY_MIN_SCORE_TO_PASS", "70")),
    "max_daily_sessions": int(os.getenv("STUDY_MAX_DAILY_SESSIONS", "5")),
    "review_intervals_days": [1, 3, 7, 14, 30, 90, 180],
    "mastery_threshold": float(os.getenv("STUDY_MASTERY_THRESHOLD", "90")),
    "review_threshold": float(os.getenv("STUDY_REVIEW_THRESHOLD", "60")),
    "max_words_per_review": int(os.getenv("STUDY_MAX_REVIEW_WORDS", "20")),
    "new_words_vs_review_ratio": float(os.getenv("STUDY_NEW_VS_REVIEW", "0.7")),
    "pronunciation_practice_phrases": [
        {
            "text": "The quick brown fox jumps over the lazy dog",
            "phonetic": "/ðə kwɪk braʊn fɑks dʒʌmps ˈoʊvər ðə ˈleɪzi dɔɡ/",
            "difficulty": "medium",
            "focus": "consonant_clusters"
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
            "focus": "th_sound"
        },
        {
            "text": "Peter Piper picked a peck of pickled peppers",
            "phonetic": "/ˈpiːtər ˈpaɪpər pɪkt ə pɛk əv ˈpɪkəld ˈpɛpərz/",
            "difficulty": "hard",
            "focus": "p_sound"
        },
        {
            "text": "Hello, how are you today?",
            "phonetic": "/həˈloʊ, haʊ ɑːr juː təˈdeɪ?/",
            "difficulty": "easy",
            "focus": "greetings"
        },
        {
            "text": "What time does the train leave?",
            "phonetic": "/wʌt taɪm dʌz ðə treɪn liːv?/",
            "difficulty": "easy",
            "focus": "questions"
        },
        {
            "text": "I would like a cup of coffee please",
            "phonetic": "/aɪ wʊd laɪk ə kʌp əv ˈkɔːfi pliːz/",
            "difficulty": "easy",
            "focus": "requests"
        },
    ],
}


# ============================================================
# CONFIGURAÇÕES DE GAMIFICAÇÃO
# ============================================================

GAMIFICATION_CONFIG: Dict[str, Any] = {
    "levels": [
        {"level": 1, "title": "🌱 Iniciante", "xp_required": 0, "perks": []},
        {"level": 2, "title": "🌿 Aprendiz", "xp_required": 100, "perks": ["Desbloqueia modo revisão"]},
        {"level": 3, "title": "🌳 Estudante", "xp_required": 300, "perks": ["Desbloqueia diálogos"]},
        {"level": 4, "title": "⭐ Intermediário", "xp_required": 600, "perks": ["Frases mais longas"]},
        {"level": 5, "title": "🌟 Avançado", "xp_required": 1000, "perks": ["Modo livre"]},
        {"level": 6, "title": "💫 Fluente", "xp_required": 2000, "perks": ["Conteúdo premium"]},
        {"level": 7, "title": "👑 Mestre", "xp_required": 5000, "perks": ["Todos os recursos"]},
    ],
    "xp_rules": {
        "practice_word_base": int(os.getenv("XP_PRACTICE_WORD", "10")),
        "perfect_score_bonus": int(os.getenv("XP_PERFECT_BONUS", "20")),
        "good_score_bonus": int(os.getenv("XP_GOOD_BONUS", "10")),
        "category_complete_bonus": int(os.getenv("XP_CATEGORY_BONUS", "100")),
        "dialog_complete_bonus": int(os.getenv("XP_DIALOG_BONUS", "50")),
        "daily_first_session_bonus": int(os.getenv("XP_DAILY_BONUS", "25")),
        "streak_multiplier_base": float(os.getenv("XP_STREAK_BASE", "1.0")),
        "streak_multiplier_increment": float(os.getenv("XP_STREAK_INCREMENT", "0.1")),
        "max_streak_multiplier": float(os.getenv("XP_MAX_STREAK_MULTIPLIER", "3.0")),
    },
    "achievements": [
        {"key": "first_word", "title": "🎯 Primeira Palavra", "description": "Pratique sua primeira palavra", "icon": "🎯", "target": 1},
        {"key": "streak_3", "title": "🔥 3 Dias Seguidos", "description": "Pratique 3 dias consecutivos", "icon": "🔥", "target": 3},
        {"key": "streak_7", "title": "⭐ 7 Dias Seguidos", "description": "Pratique 7 dias consecutivos", "icon": "⭐", "target": 7},
        {"key": "streak_14", "title": "🌟 14 Dias Seguidos", "description": "Pratique 14 dias consecutivos", "icon": "🌟", "target": 14},
        {"key": "streak_30", "title": "👑 30 Dias Seguidos", "description": "Pratique 30 dias consecutivos", "icon": "👑", "target": 30},
        {"key": "words_10", "title": "📖 10 Palavras", "description": "Pratique 10 palavras", "icon": "🔤", "target": 10},
        {"key": "words_50", "title": "📚 50 Palavras", "description": "Pratique 50 palavras", "icon": "📖", "target": 50},
        {"key": "words_100", "title": "📕 100 Palavras", "description": "Pratique 100 palavras", "icon": "📚", "target": 100},
        {"key": "words_500", "title": "📗 500 Palavras", "description": "Pratique 500 palavras", "icon": "📙", "target": 500},
        {"key": "score_100", "title": "💯 Nota Perfeita", "description": "Tire 100 em uma palavra", "icon": "💯", "target": 1},
        {"key": "perfect_streak_5", "title": "✨ 5 Perfeitas Seguidas", "description": "Acerte 5 palavras com nota 100 em sequência", "icon": "✨", "target": 5},
        {"key": "perfect_streak_10", "title": "🌟 10 Perfeitas Seguidas", "description": "Acerte 10 palavras com nota 100 em sequência", "icon": "🌟", "target": 10},
        {"key": "category_master", "title": "🏅 Mestre de Categoria", "description": "Domine 100% de uma categoria", "icon": "🏅", "target": 1},
        {"key": "all_categories", "title": "🏆 Conhecedor", "description": "Pratique palavras de todas as categorias", "icon": "🏆", "target": 10},
        {"key": "dialog_first", "title": "🗣️ Primeiro Diálogo", "description": "Complete seu primeiro diálogo", "icon": "💬", "target": 1},
        {"key": "dialog_5", "title": "🎭 Ator", "description": "Complete 5 diálogos", "icon": "🎭", "target": 5},
        {"key": "night_owl", "title": "🦉 Coruja", "description": "Estude depois das 22h", "icon": "🦉", "target": 1},
        {"key": "early_bird", "title": "🐦 Madrugador", "description": "Estude antes das 7h", "icon": "🐦", "target": 1},
        {"key": "weekend_warrior", "title": "⚔️ Guerreiro de Fim de Semana", "description": "Estude sábado e domingo", "icon": "⚔️", "target": 2},
    ],
}


# ============================================================
# CATEGORIAS DE ESTUDO
# ============================================================

STUDY_CATEGORIES: List[Dict[str, str]] = [
    {"id": "animals", "name": "Animais", "icon": "🐱", "color": "#4CAF50", "description": "Nomes de animais em inglês"},
    {"id": "colors", "name": "Cores", "icon": "🎨", "color": "#2196F3", "description": "Cores e tonalidades"},
    {"id": "airport", "name": "Aeroporto", "icon": "✈️", "color": "#FF9800", "description": "Vocabulário de viagem"},
    {"id": "restaurant", "name": "Restaurante", "icon": "🍽️", "color": "#E91E63", "description": "Como pedir comida"},
    {"id": "home", "name": "Casa", "icon": "🏠", "color": "#9C27B0", "description": "Objetos e cômodos"},
    {"id": "family", "name": "Família", "icon": "👨‍👩‍👧", "color": "#00BCD4", "description": "Membros da família"},
    {"id": "food", "name": "Comida", "icon": "🍕", "color": "#FF5722", "description": "Alimentos e bebidas"},
    {"id": "clothes", "name": "Roupas", "icon": "👕", "color": "#795548", "description": "Vestuário e acessórios"},
    {"id": "body", "name": "Corpo Humano", "icon": "🏃", "color": "#607D8B", "description": "Partes do corpo"},
    {"id": "weather", "name": "Clima", "icon": "🌤️", "color": "#03A9F4", "description": "Tempo e estações"},
]


# ============================================================
# CONFIGURAÇÕES DE LOGGING
# ============================================================

LOG_CONFIG: Dict[str, Any] = {
    "level": os.getenv("LOG_LEVEL", "INFO"),
    "format": os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ),
    "date_format": os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S"),
    "file": LOGS_DIR / os.getenv("LOG_FILE", "app.log"),
    "max_file_size_mb": int(os.getenv("LOG_MAX_FILE_SIZE", "10")),
    "backup_count": int(os.getenv("LOG_BACKUP_COUNT", "5")),
    "console_output": os.getenv("LOG_CONSOLE", "true").lower() == "true",
    "file_output": os.getenv("LOG_FILE_OUTPUT", "true").lower() == "true",
    "module_levels": {
        "src.web.app": os.getenv("LOG_LEVEL_WEB", "INFO"),
        "src.data.database": os.getenv("LOG_LEVEL_DB", "INFO"),
        "src.audio.processor": os.getenv("LOG_LEVEL_AUDIO", "INFO"),
        "src.pronunciation": os.getenv("LOG_LEVEL_PRONUNCIATION", "INFO"),
        "src.llm.tutor": os.getenv("LOG_LEVEL_LLM", "INFO"),
    },
}


# ============================================================
# CONFIGURAÇÕES DE PERFORMANCE
# ============================================================

PERFORMANCE_CONFIG: Dict[str, Any] = {
    "gpu_enabled": os.getenv("GPU_ENABLED", "false").lower() == "true",
    "cpu_threads": int(os.getenv("CPU_THREADS", str(os.cpu_count() or 4))),
    "torch_num_threads": int(os.getenv("TORCH_NUM_THREADS", "4")),
    "torch_interop_threads": int(os.getenv("TORCH_INTEROP_THREADS", "4")),
    "model_cache_enabled": os.getenv("MODEL_CACHE", "true").lower() == "true",
    "model_cache_size": int(os.getenv("MODEL_CACHE_SIZE", "3")),
    "embedding_cache_enabled": os.getenv("EMBEDDING_CACHE", "true").lower() == "true",
    "embedding_cache_max_size": int(os.getenv("EMBEDDING_CACHE_SIZE", "100")),
    "tts_cache_enabled": os.getenv("TTS_CACHE", "true").lower() == "true",
    "tts_cache_max_entries": int(os.getenv("TTS_CACHE_ENTRIES", "50")),
    "request_timeout_seconds": int(os.getenv("REQUEST_TIMEOUT", "60")),
    "max_concurrent_requests": int(os.getenv("MAX_CONCURRENT_REQUESTS", "10")),
    "rate_limit_requests": int(os.getenv("RATE_LIMIT_REQUESTS", "60")),
    "rate_limit_window_seconds": int(os.getenv("RATE_LIMIT_WINDOW", "60")),
}


# ============================================================
# CONFIGURAÇÕES DE SEGURANÇA
# ============================================================

SECURITY_CONFIG: Dict[str, Any] = {
    "secret_key": os.getenv("SECRET_KEY", "dev-secret-change-in-production"),
    "session_expiry_minutes": int(os.getenv("SESSION_EXPIRY", "30")),
    "max_sessions_per_user": int(os.getenv("MAX_SESSIONS", "3")),
    "csrf_protection": os.getenv("CSRF_PROTECTION", "false").lower() == "true",
    "cors_enabled": os.getenv("CORS_ENABLED", "true").lower() == "true",
    "rate_limiting_enabled": os.getenv("RATE_LIMITING", "false").lower() == "true",
    "max_upload_size_mb": int(os.getenv("MAX_UPLOAD_SIZE_MB", "20")),
    "allowed_file_types": [".wav", ".webm", ".mp3", ".ogg"],
}


# ============================================================
# CONFIGURAÇÕES DE FEATURE FLAGS
# ============================================================

FEATURE_FLAGS: Dict[str, bool] = {
    "vocabulary_mode": os.getenv("FEATURE_VOCABULARY", "true").lower() == "true",
    "dialog_mode": os.getenv("FEATURE_DIALOGS", "true").lower() == "true",
    "pronunciation_mode": os.getenv("FEATURE_PRONUNCIATION", "true").lower() == "true",
    "gamification": os.getenv("FEATURE_GAMIFICATION", "true").lower() == "true",
    "achievements": os.getenv("FEATURE_ACHIEVEMENTS", "true").lower() == "true",
    "spaced_repetition": os.getenv("FEATURE_SRS", "true").lower() == "true",
    "offline_mode": os.getenv("FEATURE_OFFLINE", "true").lower() == "true",
    "online_enhancements": os.getenv("FEATURE_ONLINE_ENHANCE", "false").lower() == "true",
    "tts_reference": os.getenv("FEATURE_TTS_REFERENCE", "true").lower() == "true",
    "dark_mode": os.getenv("FEATURE_DARK_MODE", "false").lower() == "true",
    "analytics": os.getenv("FEATURE_ANALYTICS", "false").lower() == "true",
}


# ============================================================
# FUNÇÃO UTILITÁRIA
# ============================================================

def get_config_summary() -> Dict[str, Any]:
    """
    Retorna um resumo das configurações para diagnóstico.
    Não expõe secrets ou valores sensíveis.
    """
    return {
        "version": "4.0.0",
        "environment": SERVER_CONFIG["environment"],
        "host": SERVER_CONFIG["host"],
        "port": SERVER_CONFIG["port"],
        "database_path": str(DATABASE_CONFIG["path"]),
        "models_directory": str(MODELS_DIR),
        "temp_directory": str(TEMP_DIR),
        "gpu_enabled": PERFORMANCE_CONFIG["gpu_enabled"],
        "device": MODEL_CONFIG["transcription"]["device"],
        "features": {k: v for k, v in FEATURE_FLAGS.items()},
        "supported_audio_formats": AUDIO_CONFIG["supported_formats"],
        "categories_count": len(STUDY_CATEGORIES),
        "levels_count": len(GAMIFICATION_CONFIG["levels"]),
        "achievements_count": len(GAMIFICATION_CONFIG["achievements"]),
    }


# ============================================================
# CONFIGURAÇÃO DO SISTEMA
# ============================================================

# Configura variáveis de ambiente do PyTorch
if not PERFORMANCE_CONFIG["gpu_enabled"]:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

os.environ["OMP_NUM_THREADS"] = str(PERFORMANCE_CONFIG["cpu_threads"])
os.environ["MKL_NUM_THREADS"] = str(PERFORMANCE_CONFIG["cpu_threads"])

# Configura logging básico
logging.basicConfig(
    level=getattr(logging, LOG_CONFIG["level"]),
    format=LOG_CONFIG["format"],
    datefmt=LOG_CONFIG["date_format"],
)