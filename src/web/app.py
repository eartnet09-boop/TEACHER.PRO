# src/web/app.py
"""
Aplicação web FastAPI - English Teacher Agent v4.0
Servidor principal com endpoints completos para estudo de inglês.
"""

import uuid
import logging
import asyncio
import time
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


# Middleware de rate limiting (simplificado)
if SECURITY_CONFIG["rate_limiting_enabled"]:
    from collections import defaultdict
    from datetime import datetime, timedelta
    
    rate_limit_store = defaultdict(list)
    
    @app.middleware("http")
    async def rate_limit(request: Request, call_next):
        """Rate limiting básico por IP"""
        client_ip = request.client.host if request.client else "unknown"
        now = datetime.now()
        window = timedelta(seconds=PERFORMANCE_CONFIG["rate_limit_window_seconds"])
        
        # Limpa entradas antigas
        rate_limit_store[client_ip] = [
            t for t in rate_limit_store[client_ip]
            if now - t < window
        ]
        
        if len(rate_limit_store[client_ip]) >= PERFORMANCE_CONFIG["rate_limit_requests"]:
            return JSONResponse(
                {"error": "Muitas requisições. Aguarde um momento."},
                status_code=429
            )
        
        rate_limit_store[client_ip].append(now)
        return await call_next(request)


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
    
    # Feature flags
    health_data["features"] = {
        k: v for k, v in FEATURE_FLAGS.items()
    }
    
    # Status geral
    all_ok = all(
        c.get("status") == "ok"
        for c in health_data["components"].values()
        if isinstance(c, dict)
    )
    health_data["status"] = "ok" if all_ok else "degraded"
    
    return JSONResponse(health_data)


@app.get("/api/config/summary")
async def config_summary():
    """Retorna resumo das configurações (sem secrets)"""
    from ..config import get_config_summary
    return JSONResponse({
        "success": True,
        "config": get_config_summary()
    })


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


@app.get("/api/session/{session_id}")
async def get_session_info(session_id: str):
    """Retorna informações da sessão"""
    session = await session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada ou expirada")
    
    return JSONResponse({
        "success": True,
        "session_id": session.session_id,
        "state": session.state.value,
        "history_count": len(session.history),
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
    })


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Encerra uma sessão"""
    await session_manager.delete_session(session_id)
    return JSONResponse({"success": True, "message": "Sessão encerrada"})


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
        
        logger.info(f"Áudio recebido: {len(content)} bytes, sessão: {session.session_id[:8]}")
        
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
            logger.debug("Conversão pydub: OK")
        except Exception as e:
            logger.warning(f"pydub falhou: {e}. Tentando ffmpeg...")
            import subprocess
            result = subprocess.run([
                "ffmpeg", "-i", str(temp_webm),
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                "-y", str(temp_wav)
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0 or not temp_wav.exists():
                raise Exception(f"Falha na conversão de áudio: {result.stderr}")
        
        # 3. Processamento de áudio
        try:
            audio_array, metadata = audio_processor.process_pipeline(
                temp_wav,
                output_path=temp_processed,
                remove_noise=True,
                normalize=True,
                trim_silence=True
            )
            logger.debug(f"Áudio processado: SNR={metadata.snr:.1f}dB")
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
            "processing_time_ms": 0,  # TODO: calcular
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
            "session_id": session.session_id if session else None
        }, status_code=400)
        
    except asyncio.TimeoutError:
        logger.error("Timeout no processamento")
        if session:
            session.state = SessionState.ERROR
        return JSONResponse({
            "success": False,
            "error": "Processamento excedeu o tempo limite. Tente novamente.",
            "session_id": session.session_id if session else None
        }, status_code=504)
        
    except Exception as e:
        logger.error(f"Erro na análise: {e}", exc_info=True)
        if session:
            session.state = SessionState.ERROR
        return JSONResponse({
            "success": False,
            "error": "Erro interno no processamento. Nossa equipe foi notificada.",
            "session_id": session.session_id if session else None
        }, status_code=500)
        
    finally:
        # Limpeza de arquivos temporários (com delay para TTS)
        async def cleanup_files():
            await asyncio.sleep(30)
            for temp_file in temp_files:
                try:
                    if temp_file and temp_file.exists():
                        temp_file.unlink()
                        logger.debug(f"Arquivo limpo: {temp_file.name}")
                except Exception as e:
                    logger.debug(f"Erro ao limpar {temp_file}: {e}")
        
        asyncio.create_task(cleanup_files())


# ============================================================
# ENDPOINTS - TTS (NOVO)
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
                headers={"Cache-Control": "public, max-age=3600"}
            )
        
        raise HTTPException(status_code=503, detail="Serviço TTS indisponível")
        
    except Exception as e:
        logger.error(f"Erro TTS: {e}")
        raise HTTPException(status_code=500, detail="Erro na síntese de voz")


# ============================================================
# ENDPOINTS - CATEGORIAS (NOVO)
# ============================================================

@app.get("/api/categories")
async def get_categories(
    user_id: str = Query("default", description="ID do usuário")
):
    """
    Retorna todas as categorias de estudo com progresso do usuário.
    """
    if not FEATURE_FLAGS["vocabulary_mode"]:
        raise HTTPException(status_code=404, detail="Modo vocabulário desabilitado")
    
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


@app.get("/api/categories/{category_id}")
async def get_category_detail(
    category_id: int,
    user_id: str = Query("default")
):
    """
    Retorna detalhes de uma categoria específica.
    """
    category = await CategoryRepository.get_by_id(category_id)
    
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    
    return JSONResponse({
        "success": True,
        "category": category
    })


# ============================================================
# ENDPOINTS - VOCABULÁRIO (NOVO)
# ============================================================

@app.get("/api/categories/{category_id}/words")
async def get_words_for_study(
    category_id: int,
    mode: str = Query("new", description="Modo: new, review, all"),
    limit: int = Query(10, ge=1, le=50, description="Quantidade de palavras"),
    user_id: str = Query("default")
):
    """
    Retorna palavras para estudo de uma categoria.
    
    Modos:
    - new: palavras novas ou menos praticadas
    - review: palavras que precisam de revisão (SRS)
    - all: todas as palavras da categoria
    """
    if not FEATURE_FLAGS["vocabulary_mode"]:
        raise HTTPException(status_code=404, detail="Modo vocabulário desabilitado")
    
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


@app.get("/api/words/search")
async def search_words(
    q: str = Query(..., min_length=1, description="Termo de busca"),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Busca palavras no vocabulário.
    Pesquisa em inglês e português.
    """
    if not q:
        raise HTTPException(status_code=400, detail="Termo de busca necessário")
    
    words = await VocabularyRepository.search(q)
    
    return JSONResponse({
        "success": True,
        "query": q,
        "total": len(words),
        "words": words[:limit]
    })


# ============================================================
# ENDPOINTS - PROGRESSO DO USUÁRIO (NOVO)
# ============================================================

@app.post("/api/study/word")
async def record_word_practice(request: dict):
    """
    Registra prática de uma palavra e retorna progresso atualizado.
    """
    word_id = request.get("word_id")
    score = request.get("score", 0)
    user_id = request.get("user_id", "default")
    
    if not word_id:
        raise HTTPException(status_code=400, detail="word_id é obrigatório")
    
    # Valida score
    score = max(0, min(100, float(score)))
    
    try:
        # Atualiza progresso da palavra
        progress = await ProgressRepository.update_progress(word_id, score, user_id)
        
        # Calcula XP ganho
        from ..config import GAMIFICATION_CONFIG
        xp_rules = GAMIFICATION_CONFIG["xp_rules"]
        xp_earned = xp_rules["practice_word_base"]
        
        if score >= 90:
            xp_earned += xp_rules["perfect_score_bonus"]
        elif score >= 70:
            xp_earned += xp_rules["good_score_bonus"]
        
        # Atualiza streak e aplica multiplicador
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
            "word_mastered": progress.get("mastered") == 1 if progress else False
        })
        
    except Exception as e:
        logger.error(f"Erro ao registrar progresso: {e}")
        raise HTTPException(status_code=500, detail="Erro ao salvar progresso")


@app.post("/api/study/session/complete")
async def complete_study_session(request: dict):
    """
    Finaliza uma sessão de estudo e retorna estatísticas.
    """
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
        
        # Cria sessão no banco
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
        
        # Busca estatísticas atualizadas
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
async def get_user_statistics(
    user_id: str = Query("default")
):
    """
    Retorna estatísticas completas do usuário.
    Inclui progresso, streaks, sessões recentes e categorias.
    """
    try:
        stats = await ProgressRepository.get_stats(user_id)
        streak = await SessionRepository.get_streak(user_id)
        recent = await SessionRepository.get_recent(user_id, limit=10)
        categories = await CategoryRepository.get_with_progress(user_id)
        
        # Calcula nível
        total_xp = (stats.get("total_words_practiced", 0) * 10) if stats else 0
        
        from ..config import GAMIFICATION_CONFIG
        levels = GAMIFICATION_CONFIG["levels"]
        current_level = levels[0]
        next_level = levels[1] if len(levels) > 1 else None
        
        for level in levels:
            if total_xp >= level["xp_required"]:
                current_level = level
        
        # Encontra próximo nível
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
# ENDPOINTS - DIÁLOGOS (NOVO)
# ============================================================

@app.get("/api/dialogs/themes")
async def get_dialog_themes():
    """
    Lista todos os temas de diálogo disponíveis.
    """
    if not FEATURE_FLAGS["dialog_mode"]:
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
    """
    Retorna todas as linhas de diálogo de um tema específico.
    """
    if not FEATURE_FLAGS["dialog_mode"]:
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


# ============================================================
# ENDPOINTS - CONQUISTAS (NOVO)
# ============================================================

@app.get("/api/user/achievements")
async def get_user_achievements(
    user_id: str = Query("default")
):
    """
    Retorna todas as conquistas e progresso do usuário.
    """
    if not FEATURE_FLAGS["achievements"]:
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
# ENDPOINTS - UTILITÁRIOS (NOVO)
# ============================================================

@app.get("/api/stats/database")
async def get_database_stats():
    """
    Retorna estatísticas do banco de dados.
    Útil para monitoramento e debugging.
    """
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