# src/web/app.py
"""
Aplicação web FastAPI - English Teacher Agent v4.0
Servidor principal com endpoints completos para estudo de inglês.
"""

import uuid
import logging
import asyncio
import time
import json
import subprocess
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydub import AudioSegment
from contextlib import asynccontextmanager

from ..config import (
    SERVER_CONFIG,
    TEMP_DIR,
    FEATURE_FLAGS,
    PERFORMANCE_CONFIG,
    SECURITY_CONFIG,
)
from .session_manager import session_manager, SessionState

# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# LIFESPAN (Substitui on_event para FastAPI moderno)
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação"""
    # Startup
    logger.info("🚀 Iniciando English Teacher Agent v4.0...")
    
    # Inicializa banco de dados
    try:
        from ..data.database import db
        await db.initialize()
        
        # Executa seed se necessário
        from ..data.seeder import seeder
        await seeder.seed_all()
        
        logger.info("✅ Banco de dados inicializado")
    except Exception as e:
        logger.error(f"❌ Erro ao inicializar banco de dados: {e}")
    
    # Inicializa gerenciador de sessões
    await session_manager.start()
    
    logger.info(f"✅ Servidor pronto em http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Finalizando servidor...")
    await session_manager.stop()
    
    try:
        from ..data.database import db
        await db.close()
    except Exception:
        pass
    
    logger.info("✅ Servidor finalizado")


# ============================================================
# CRIAÇÃO DO APP
# ============================================================

app = FastAPI(
    title="English Teacher Agent",
    description="Professor de inglês por IA - 100% offline e privado",
    version="4.0.0",
    docs_url="/docs" if SERVER_CONFIG["environment"] == "development" else None,
    redoc_url="/redoc" if SERVER_CONFIG["environment"] == "development" else None,
    lifespan=lifespan,
)


# ============================================================
# MIDDLEWARES
# ============================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=SERVER_CONFIG["allowed_origins"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)


# Middleware de logging de requisições
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log detalhado de cada requisição"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.debug(
        f"{request.method} {request.url.path} "
        f"- {response.status_code} "
        f"- {duration:.3f}s"
    )
    
    return response


# ============================================================
# ARQUIVOS ESTÁTICOS
# ============================================================

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ============================================================
# IMPORTAÇÕES DOS MÓDULOS
# ============================================================

from ..transcription.chall_model import transcriber
from ..pronunciation.wavlm_analyzer import analyzer
from ..pronunciation.scorer import scorer as pronunciation_scorer
from ..llm.tutor import tutor
from ..tts.speaker import speaker
from ..audio.processor import audio_processor

# Repositórios de dados
from ..data.repository import (
    CategoryRepository,
    VocabularyRepository,
    DialogRepository,
    ProgressRepository,
    SessionRepository,
)


# ============================================================
# ENDPOINTS - PÁGINAS
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    """Página principal da aplicação"""
    html_path = static_dir / "index.html"
    
    if html_path.exists():
        return HTMLResponse(
            content=html_path.read_text(encoding='utf-8'),
            headers={"Cache-Control": "no-cache"}
        )
    
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>English Teacher Agent</title>
            <style>
                body {
                    font-family: sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    color: white;
                }
                .container { text-align: center; }
                h1 { font-size: 2.5em; }
                p { margin: 20px 0; }
                .btn {
                    padding: 12px 24px;
                    background: white;
                    color: #667eea;
                    border: none;
                    border-radius: 50px;
                    cursor: pointer;
                    font-size: 1em;
                    font-weight: bold;
                    text-decoration: none;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎧 English Teacher Agent</h1>
                <p>Arquivo index.html não encontrado em /static</p>
                <a href="/docs" class="btn">📊 Ver API Docs</a>
                <a href="/api/health" class="btn">❤️ Health Check</a>
            </div>
        </body>
        </html>
        """
    )


# ============================================================
# ENDPOINTS - SISTEMA
# ============================================================

@app.get("/api/health")
async def health_check():
    """
    Health check completo do sistema.
    Verifica disponibilidade de todos os componentes.
    """
    import torch
    
    health_data = {
        "status": "ok",
        "service": "English Teacher Agent",
        "version": "4.0.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "components": {}
    }
    
    # Verifica Ollama
    try:
        ollama_status = await tutor._check_ollama()
        health_data["components"]["ollama"] = {
            "status": "ok" if ollama_status.get("running") else "unavailable",
            "models": ollama_status.get("models", []),
        }
    except Exception as e:
        health_data["components"]["ollama"] = {"status": "error", "error": str(e)}
    
    # Verifica GPU
    health_data["components"]["gpu"] = {
        "available": torch.cuda.is_available(),
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    }
    
    # Verifica banco de dados
    try:
        from ..data.database import db
        stats = await db.fetch_one("SELECT COUNT(*) as count FROM vocabulary")
        health_data["components"]["database"] = {
            "status": "ok",
            "words_count": stats["count"] if stats else 0
        }
    except Exception as e:
        health_data["components"]["database"] = {"status": "error", "error": str(e)}
    
    # Sessões ativas
    health_data["components"]["sessions"] = {
        "active": len(session_manager.sessions)
    }
    
    # Status geral
    all_ok = all(
        c.get("status") == "ok"
        for c in health_data["components"].values()
        if isinstance(c, dict)
    )
    health_data["status"] = "ok" if all_ok else "degraded"
    
    return JSONResponse(health_data)


# ============================================================
# ENDPOINTS - SESSÃO
# ============================================================

@app.post("/api/session")
async def create_session():
    """Cria nova sessão de usuário"""
    session = await session_manager.create_session()
    
    return JSONResponse({
        "success": True,
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "expires_in_minutes": SECURITY_CONFIG["session_expiry_minutes"]
    })


# ============================================================
# ENDPOINTS - ANÁLISE DE PRONÚNCIA (CORE)
# ============================================================

@app.post("/api/analyze")
async def analyze_pronunciation(
    audio: UploadFile = File(...),
    expected: str = Form(""),
    session_id: Optional[str] = Form(None)
):
    """
    Analisa áudio do aluno e retorna score + feedback.
    Pipeline completo: áudio → transcrição → análise → scoring → feedback.
    """
    temp_files = []
    session = None
    
    try:
        # Validação da sessão
        if session_id:
            session = await session_manager.get_session(session_id)
        
        if not session:
            session = await session_manager.create_session()
        
        # Controle de concorrência
        async with session.lock:
            if session.state == SessionState.PROCESSING:
                return JSONResponse({
                    "success": False,
                    "error": "Sessão ocupada. Aguarde o processamento atual.",
                    "session_id": session.session_id
                }, status_code=409)
            
            session.state = SessionState.PROCESSING
        
        # 1. Salva áudio recebido
        unique_id = uuid.uuid4().hex
        temp_webm = TEMP_DIR / f"recording_{unique_id}.webm"
        temp_wav = TEMP_DIR / f"recording_{unique_id}.wav"
        temp_processed = TEMP_DIR / f"processed_{unique_id}.wav"
        temp_files = [temp_webm, temp_wav, temp_processed]
        
        content = await audio.read()
        
        if len(content) < 1000:
            raise ValueError("Áudio muito curto ou vazio")
        
        with open(temp_webm, "wb") as f:
            f.write(content)
        
        logger.info(f"Áudio recebido: {len(content)} bytes")
        
        # 2. Conversão WebM → WAV
        try:
            audio_segment = AudioSegment.from_file(str(temp_webm))
            audio_segment = (
                audio_segment
                .set_frame_rate(16000)
                .set_channels(1)
                .set_sample_width(2)
            )
            audio_segment.export(str(temp_wav), format="wav")
        except Exception as e:
            logger.warning(f"pydub falhou: {e}. Tentando ffmpeg...")
            result = subprocess.run([
                "ffmpeg", "-i", str(temp_webm),
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                "-y", str(temp_wav)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0 or not temp_wav.exists():
                raise Exception(f"Falha na conversão de áudio")
        
        # 3. Processamento de áudio
        try:
            audio_array, metadata = audio_processor.process_pipeline(
                temp_wav,
                output_path=temp_processed,
                remove_noise=True,
                normalize=True,
                trim_silence=True
            )
        except Exception as e:
            logger.warning(f"Processamento falhou: {e}. Usando arquivo original.")
            temp_processed = temp_wav
        
        # 4. Transcrição
        transcription_result = transcriber.transcribe(temp_processed)
        actual_text = transcription_result.get("text", "")
        logger.info(f"Transcrição: '{actual_text}'")
        
        # 5. Comparação com esperado
        comparison = transcriber.compare_with_expected(actual_text, expected)
        
        # 6. Análise de pronúncia (WavLM + Scorer)
        pronunciation_result = await analyzer.analyze(temp_processed, expected)
        
        # 7. Feedback do tutor IA
        feedback = await tutor.generate_feedback(
            expected=expected,
            actual=actual_text,
            errors=comparison.get("errors", []),
            pronunciation_score=pronunciation_result.get("overall_score", 0)
        )
        
        # 8. Monta resposta
        result = {
            "success": True,
            "session_id": session.session_id,
            "transcription": actual_text if actual_text else "[Não foi possível transcrever]",
            "expected_text": expected,
            "pronunciation_score": pronunciation_result.get("overall_score", 0),
            "word_scores": pronunciation_result.get("word_scores", {}),
            "pronunciation_level": pronunciation_result.get("level", "fair"),
            "errors": comparison.get("errors", []),
            "similarity": pronunciation_result.get("similarity", 0),
            "phoneme_accuracy": pronunciation_result.get("phoneme_accuracy", 0),
            "fluency_score": pronunciation_result.get("fluency_score", 0),
            "problematic_words": pronunciation_result.get("problematic_words", []),
            "strong_words": pronunciation_result.get("strong_words", []),
            "recommendations": pronunciation_result.get("recommendations", []),
            "feedback": feedback,
        }
        
        # Registra no histórico
        session.add_to_history(result)
        session.state = SessionState.READY
        
        return JSONResponse(result)
        
    except ValueError as e:
        logger.warning(f"Erro de validação: {e}")
        if session:
            session.state = SessionState.READY
        return JSONResponse({
            "success": False,
            "error": str(e),
        }, status_code=400)
        
    except Exception as e:
        logger.error(f"Erro na análise: {e}", exc_info=True)
        if session:
            session.state = SessionState.ERROR
        return JSONResponse({
            "success": False,
            "error": "Erro interno no processamento.",
        }, status_code=500)
        
    finally:
        # Limpeza de arquivos temporários
        async def cleanup_files():
            await asyncio.sleep(30)
            for temp_file in temp_files:
                try:
                    if temp_file and temp_file.exists():
                        temp_file.unlink()
                except Exception:
                    pass
        
        asyncio.create_task(cleanup_files())


# ============================================================
# ENDPOINTS - TTS
# ============================================================

@app.post("/api/speak")
async def speak_text(request: dict):
    """Sintetiza voz a partir de texto"""
    text = request.get("text", "").strip()
    
    if not text or len(text) < 2:
        raise HTTPException(status_code=400, detail="Texto muito curto")
    
    if len(text) > 500:
        raise HTTPException(status_code=400, detail="Texto muito longo (máx. 500 caracteres)")
    
    try:
        audio_path = await speaker.speak(text)
        
        if audio_path and audio_path.exists():
            return FileResponse(
                audio_path,
                media_type="audio/wav",
                filename=f"speech_{hash(text)}.wav",
            )
        
        raise HTTPException(status_code=503, detail="Serviço TTS indisponível")
        
    except Exception as e:
        logger.error(f"Erro TTS: {e}")
        raise HTTPException(status_code=500, detail="Erro na síntese de voz")


# ============================================================
# ENDPOINTS - CATEGORIAS E VOCABULÁRIO
# ============================================================

@app.get("/api/categories")
async def get_categories(
    user_id: str = Query("default")
):
    """Retorna todas as categorias de estudo com progresso do usuário."""
    try:
        categories = await CategoryRepository.get_with_progress(user_id)
        
        return JSONResponse({
            "success": True,
            "total": len(categories),
            "categories": categories
        })
    except Exception as e:
        logger.error(f"Erro ao buscar categorias: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar categorias")


@app.get("/api/categories/{category_id}/words")
async def get_words_for_study(
    category_id: int,
    mode: str = Query("new"),
    limit: int = Query(10, ge=1, le=50),
    user_id: str = Query("default")
):
    """Retorna palavras para estudo de uma categoria."""
    try:
        if mode == "all":
            words = await VocabularyRepository.get_by_category(category_id)
            words = words[:limit]
        else:
            words = await VocabularyRepository.get_words_for_study(
                category_id=category_id,
                user_id=user_id,
                limit=limit,
                mode=mode
            )
        
        category = await CategoryRepository.get_by_id(category_id)
        
        return JSONResponse({
            "success": True,
            "category": category,
            "mode": mode,
            "total": len(words),
            "words": words
        })
    except Exception as e:
        logger.error(f"Erro ao buscar palavras: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar palavras")


# ============================================================
# ENDPOINTS - PROGRESSO DO USUÁRIO
# ============================================================

@app.post("/api/study/word")
async def record_word_practice(request: dict):
    """Registra prática de uma palavra e retorna progresso atualizado."""
    word_id = request.get("word_id")
    score = request.get("score", 0)
    user_id = request.get("user_id", "default")
    
    if not word_id:
        raise HTTPException(status_code=400, detail="word_id é obrigatório")
    
    score = max(0, min(100, float(score)))
    
    try:
        progress = await ProgressRepository.update_progress(word_id, score, user_id)
        
        from ..config import GAMIFICATION_CONFIG
        xp_rules = GAMIFICATION_CONFIG["xp_rules"]
        xp_earned = xp_rules["practice_word_base"]
        
        if score >= 90:
            xp_earned += xp_rules["perfect_score_bonus"]
        elif score >= 70:
            xp_earned += xp_rules["good_score_bonus"]
        
        streak = await SessionRepository.update_streak(user_id)
        if streak.get("current_streak", 0) > 1:
            multiplier = min(
                xp_rules["max_streak_multiplier"],
                xp_rules["streak_multiplier_base"] + 
                streak["current_streak"] * xp_rules["streak_multiplier_increment"]
            )
            xp_earned = int(xp_earned * multiplier)
        
        return JSONResponse({
            "success": True,
            "progress": progress,
            "xp_earned": xp_earned,
            "streak": streak,
        })
        
    except Exception as e:
        logger.error(f"Erro ao registrar progresso: {e}")
        raise HTTPException(status_code=500, detail="Erro ao salvar progresso")


@app.post("/api/study/session/complete")
async def complete_study_session(request: dict):
    """Finaliza uma sessão de estudo e retorna estatísticas."""
    theme = request.get("theme", "")
    mode = request.get("mode", "vocabulary")
    words_data = request.get("words", [])
    duration = request.get("duration", 0)
    user_id = request.get("user_id", "default")
    
    if not words_data:
        raise HTTPException(status_code=400, detail="Nenhuma palavra praticada")
    
    try:
        total = len(words_data)
        correct = sum(1 for w in words_data if w.get("score", 0) >= 70)
        avg_score = sum(w.get("score", 0) for w in words_data) / total
        xp_earned = sum(w.get("xp_earned", 0) for w in words_data)
        
        session_id = await SessionRepository.create_session(
            theme=theme,
            mode=mode,
            words_practiced=total,
            correct_words=correct,
            average_score=avg_score,
            xp_earned=xp_earned,
            duration=duration,
            user_id=user_id
        )
        
        stats = await ProgressRepository.get_stats(user_id)
        streak = await SessionRepository.get_streak(user_id)
        
        return JSONResponse({
            "success": True,
            "session_id": session_id,
            "stats": {
                "total_words": total,
                "correct_words": correct,
                "accuracy": round(correct / total * 100, 1) if total > 0 else 0,
                "average_score": round(avg_score, 1),
                "xp_earned": xp_earned,
                "duration_seconds": duration
            },
            "user_stats": stats,
            "streak": streak
        })
        
    except Exception as e:
        logger.error(f"Erro ao finalizar sessão: {e}")
        raise HTTPException(status_code=500, detail="Erro ao salvar sessão")


@app.get("/api/user/stats")
async def get_user_statistics(user_id: str = Query("default")):
    """Retorna estatísticas completas do usuário."""
    try:
        stats = await ProgressRepository.get_stats(user_id)
        streak = await SessionRepository.get_streak(user_id)
        recent = await SessionRepository.get_recent(user_id, limit=10)
        categories = await CategoryRepository.get_with_progress(user_id)
        
        total_xp = (stats.get("total_words_practiced", 0) * 10) if stats else 0
        
        from ..config import GAMIFICATION_CONFIG
        levels = GAMIFICATION_CONFIG["levels"]
        current_level = levels[0]
        next_level = None
        
        for level in levels:
            if total_xp >= level["xp_required"]:
                current_level = level
        
        for level in levels:
            if level["xp_required"] > total_xp:
                next_level = level
                break
        
        return JSONResponse({
            "success": True,
            "user_id": user_id,
            "stats": stats,
            "streak": streak,
            "level": {
                "current": current_level,
                "next": next_level,
                "total_xp": total_xp,
                "xp_to_next": (next_level["xp_required"] - total_xp) if next_level else 0
            },
            "categories_progress": categories,
            "recent_sessions": recent
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar estatísticas")


# ============================================================
# ENDPOINTS - DIÁLOGOS
# ============================================================

@app.get("/api/dialogs/themes")
async def get_dialog_themes():
    """Lista todos os temas de diálogo disponíveis."""
    if not FEATURE_FLAGS.get("dialog_mode", True):
        raise HTTPException(status_code=404, detail="Modo diálogo desabilitado")
    
    try:
        themes = await DialogRepository.get_all_themes()
        
        return JSONResponse({
            "success": True,
            "total": len(themes),
            "themes": themes
        })
    except Exception as e:
        logger.error(f"Erro ao buscar temas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar temas")


@app.get("/api/dialogs/{theme}")
async def get_dialog_by_theme(theme: str):
    """Retorna todas as linhas de diálogo de um tema específico."""
    if not FEATURE_FLAGS.get("dialog_mode", True):
        raise HTTPException(status_code=404, detail="Modo diálogo desabilitado")
    
    try:
        dialogs = await DialogRepository.get_by_theme(theme)
        
        if not dialogs:
            raise HTTPException(status_code=404, detail=f"Tema '{theme}' não encontrado")
        
        return JSONResponse({
            "success": True,
            "theme": theme,
            "total_lines": len(dialogs),
            "dialogs": dialogs
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar diálogos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar diálogos")


@app.post("/api/dialogs/evaluate")
async def evaluate_dialog_response(request: dict):
    """
    Avalia a resposta do usuário em um diálogo interativo.
    Compara com a resposta esperada e retorna score + feedback.
    """
    user_response = request.get("user_response", "").strip()
    expected_response = request.get("expected_response", "").strip()
    theme = request.get("theme", "")
    
    if not user_response or not expected_response:
        raise HTTPException(
            status_code=400, 
            detail="user_response e expected_response são obrigatórios"
        )
    
    try:
        from difflib import SequenceMatcher
        
        user_clean = user_response.lower().strip().rstrip('.!?,')
        expected_clean = expected_response.lower().strip().rstrip('.!?,')
        
        similarity = SequenceMatcher(None, user_clean, expected_clean).ratio()
        
        user_words = set(user_clean.split())
        expected_words = set(expected_clean.split())
        
        if expected_words:
            word_similarity = len(user_words & expected_words) / len(expected_words)
        else:
            word_similarity = 0
        
        score = round((similarity * 0.6 + word_similarity * 0.4) * 100)
        
        if score >= 90:
            feedback = "✅ Perfeito! Resposta excelente!"
        elif score >= 75:
            feedback = "✅ Muito bem! Quase perfeito."
        elif score >= 60:
            feedback = "⚠️ Boa tentativa! Mas pode melhorar."
        elif score >= 40:
            feedback = "💪 Continue tentando! Veja a resposta esperada."
        else:
            feedback = "❌ Resposta muito diferente. Estude o exemplo."
        
        return JSONResponse({
            "success": True,
            "score": score,
            "feedback": feedback,
            "correct_answer": expected_response,
            "user_answer": user_response,
            "similarity": round(similarity, 3),
            "word_similarity": round(word_similarity, 3),
            "theme": theme
        })
        
    except Exception as e:
        logger.error(f"Erro ao avaliar resposta do diálogo: {e}")
        raise HTTPException(status_code=500, detail="Erro ao avaliar resposta")


@app.post("/api/dialogs/free-chat")
async def free_chat(request: dict):
    """
    Modo de conversa livre com o tutor IA.
    O usuário digita qualquer coisa e a IA responde como um nativo.
    
    Request Body:
    {
        "message": "I'd like to order a pizza",
        "context": "restaurant",
        "history": [
            {"role": "assistant", "text": "Welcome! What can I get for you?"},
            {"role": "user", "text": "Hi, I'm hungry"}
        ]
    }
    """
    message = request.get("message", "").strip()
    context = request.get("context", "casual conversation")
    history = request.get("history", [])
    
    if not message:
        raise HTTPException(status_code=400, detail="Mensagem é obrigatória")
    
    if len(message) > 200:
        raise HTTPException(status_code=400, detail="Mensagem muito longa (máx. 200 caracteres)")
    
    logger.info(f"Free chat: contexto='{context}', mensagem='{message[:50]}...'")
    
    try:
        history_text = ""
        for msg in history[-10:]:
            role = "Native speaker" if msg.get("role") == "assistant" else "Student"
            history_text += f"{role}: {msg.get('text', '')}\n"
        
        prompt = f"""You are a native English speaker in a {context} situation.
You're talking to someone learning English. Be natural, friendly, and helpful.

CONVERSATION HISTORY:
{history_text}
Student: {message}

RULES:
1. Respond ONLY in English (natural, conversational)
2. Keep responses under 20 words
3. If the student makes a grammar mistake, subtly use the correct form in your response
4. Ask follow-up questions to keep the conversation going
5. Occasionally offer a tip about more natural phrasing

Respond with ONLY a JSON (no other text):
{{"response": "Your natural English response", "translation": "Brazilian Portuguese translation", "tip": "Optional tip about natural English or empty string"}}"""
        
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": "qwen2.5-coder:3b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.8,
                    "num_predict": 200,
                    "top_p": 0.95
                }
            }
            
            async with session.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    response_text = result.get("response", "")
                    
                    try:
                        start = response_text.find('{')
                        end = response_text.rfind('}') + 1
                        if start >= 0 and end > start:
                            data = json.loads(response_text[start:end])
                            return JSONResponse({
                                "success": True,
                                "response": data.get("response", response_text[:200]),
                                "translation": data.get("translation", ""),
                                "tip": data.get("tip", ""),
                                "context": context
                            })
                    except json.JSONDecodeError:
                        pass
                    
                    return JSONResponse({
                        "success": True,
                        "response": response_text.strip()[:200],
                        "translation": "",
                        "tip": "",
                        "context": context
                    })
                else:
                    logger.error(f"Ollama retornou status {response.status}")
                    
    except aiohttp.ClientError as e:
        logger.error(f"Erro de conexão com Ollama: {e}")
    except Exception as e:
        logger.error(f"Erro no free-chat: {e}")
    
    return JSONResponse({
        "success": True,
        "response": f"I understand you're talking about {context}. Could you tell me more?",
        "translation": f"Entendo que você está falando sobre {context}. Pode me contar mais?",
        "tip": "",
        "context": context,
        "offline_fallback": True
    })


# ============================================================
# ENDPOINTS - CONQUISTAS
# ============================================================

@app.get("/api/user/achievements")
async def get_user_achievements(user_id: str = Query("default")):
    """Retorna todas as conquistas e progresso do usuário."""
    if not FEATURE_FLAGS.get("achievements", True):
        raise HTTPException(status_code=404, detail="Conquistas desabilitadas")
    
    try:
        from ..data.database import db
        achievements = await db.fetch_all(
            """SELECT * FROM achievements 
               WHERE user_id = ? OR user_id = 'default'
               ORDER BY completed DESC, achievement_key""",
            (user_id,)
        )
        
        total = len(achievements)
        unlocked = sum(1 for a in achievements if a.get("completed"))
        
        return JSONResponse({
            "success": True,
            "total": total,
            "unlocked": unlocked,
            "progress_percent": round(unlocked / total * 100, 1) if total > 0 else 0,
            "achievements": achievements
        })
    except Exception as e:
        logger.error(f"Erro ao buscar conquistas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar conquistas")


# ============================================================
# ENDPOINTS - UTILITÁRIOS
# ============================================================

@app.get("/api/stats/database")
async def get_database_stats():
    """Retorna estatísticas do banco de dados."""
    try:
        from ..data.database import db
        
        tables = ["categories", "vocabulary", "dialogs", "user_progress", 
                  "study_sessions", "achievements"]
        
        stats = {}
        for table in tables:
            count = await db.fetch_one(f"SELECT COUNT(*) as count FROM {table}")
            stats[table] = count["count"] if count else 0
        
        db_size = Path("english_teacher.db").stat().st_size if Path("english_teacher.db").exists() else 0
        
        return JSONResponse({
            "success": True,
            "database_size_mb": round(db_size / 1024 / 1024, 2),
            "tables": stats
        })
    except Exception as e:
        logger.error(f"Erro ao buscar stats do banco: {e}")
        raise HTTPException(status_code=500, detail="Erro ao carregar estatísticas")


# ============================================================
# TRATAMENTO GLOBAL DE EXCEÇÕES
# ============================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handler para erros 404"""
    return JSONResponse({
        "success": False,
        "error": "Endpoint não encontrado",
        "path": str(request.url.path)
    }, status_code=404)


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    """Handler para erros 500"""
    logger.error(f"Erro interno: {exc}", exc_info=True)
    return JSONResponse({
        "success": False,
        "error": "Erro interno do servidor"
    }, status_code=500)