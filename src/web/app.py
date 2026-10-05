# src/web/app.py
"""
English Teacher Agent v4.1 - Servidor Principal
Aplicação web FastAPI com modo híbrido (offline + online).
Arquitetura modular com roteadores, middleware e pipeline de IA completo.
"""

import uuid
import logging
import asyncio
import time
import json
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydub import AudioSegment
from contextlib import asynccontextmanager

from ..config import (
    SERVER_CONFIG, TEMP_DIR, FEATURE_FLAGS,
    PERFORMANCE_CONFIG, SECURITY_CONFIG,
)
from .session_manager import session_manager, SessionState

logger = logging.getLogger(__name__)


# ============================================================
# LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando English Teacher Agent v4.1...")
    try:
        from ..data.database import db
        await db.initialize()
        from ..data.seeder import seeder
        await seeder.seed_all()
        logger.info("✅ Banco de dados inicializado")
    except Exception as e:
        logger.error(f"❌ Banco: {e}")
    await session_manager.start()
    logger.info(f"✅ Servidor pronto em http://{SERVER_CONFIG['host']}:{SERVER_CONFIG['port']}")
    yield
    logger.info("🛑 Finalizando...")
    await session_manager.stop()
    try:
        from ..data.database import db
        await db.close()
    except Exception: pass


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="English Teacher Agent",
    description="Professor de inglês por IA - 100% offline e privado | Modo Híbrido",
    version="4.1.0",
    docs_url="/docs" if SERVER_CONFIG["environment"] == "development" else None,
    redoc_url="/redoc" if SERVER_CONFIG["environment"] == "development" else None,
    lifespan=lifespan,
)

from .routers import live_data
app.include_router(live_data.router)

if SECURITY_CONFIG["cors_enabled"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=SERVER_CONFIG["allowed_origins"],
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
        max_age=3600,
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    logger.debug(f"{request.method} {request.url.path} - {response.status_code} - {time.time()-start:.3f}s")
    return response

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

from ..transcription.chall_model import transcriber
from ..pronunciation.wavlm_analyzer import analyzer
from ..llm.tutor import tutor
from ..llm.dialog_engine import dialog_engine
from ..tts.speaker import speaker
from ..audio.processor import audio_processor
from ..data.repository import (
    CategoryRepository, VocabularyRepository, DialogRepository,
    ProgressRepository, SessionRepository,
)


# ============================================================
# PÁGINAS
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = static_dir / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding='utf-8'), headers={"Cache-Control": "no-cache"})
    return HTMLResponse(content="<h1>index.html não encontrado</h1>")


# ============================================================
# SISTEMA
# ============================================================

@app.get("/api/health")
async def health_check():
    import torch
    h = {"status":"ok","service":"English Teacher Agent","version":"4.1.0",
         "timestamp":time.strftime("%Y-%m-%d %H:%M:%S"),"components":{}}
    try:
        os = await tutor._check_ollama()
        h["components"]["ollama"] = {"status":"ok" if os.get("running") else "unavailable","models":os.get("models",[])}
    except: h["components"]["ollama"] = {"status":"error"}
    h["components"]["gpu"] = {"available":torch.cuda.is_available(),"device":torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"}
    try:
        from ..data.database import db
        s = await db.fetch_one("SELECT COUNT(*) as count FROM vocabulary")
        h["components"]["database"] = {"status":"ok","words_count":s["count"] if s else 0}
    except: h["components"]["database"] = {"status":"error"}
    h["components"]["sessions"] = {"active":len(session_manager.sessions)}
    return JSONResponse(h)


# ============================================================
# SESSÃO
# ============================================================

@app.post("/api/session")
async def create_session():
    s = await session_manager.create_session()
    return JSONResponse({"success":True,"session_id":s.session_id,"created_at":s.created_at.isoformat()})


# ============================================================
# ANÁLISE DE PRONÚNCIA
# ============================================================

@app.post("/api/analyze")
async def analyze_pronunciation(audio: UploadFile = File(...), expected: str = Form(""), session_id: Optional[str] = Form(None)):
    temp_files = []; session = None
    try:
        content = await audio.read(SERVER_CONFIG["max_upload_size"] + 1)
        if len(content) > SERVER_CONFIG["max_upload_size"]:
            return JSONResponse({"success": False, "error": "Arquivo excede o limite permitido"}, status_code=413)
        if len(content) < 1000: raise ValueError("Áudio muito curto")
        if session_id: session = await session_manager.get_session(session_id)
        if not session: session = await session_manager.create_session()
        async with session.lock:
            if session.state == SessionState.PROCESSING:
                return JSONResponse({"success":False,"error":"Sessão ocupada"}, status_code=409)
            session.state = SessionState.PROCESSING
        uid = uuid.uuid4().hex
        tw, twv, tp = TEMP_DIR/f"rec_{uid}.webm", TEMP_DIR/f"rec_{uid}.wav", TEMP_DIR/f"proc_{uid}.wav"
        temp_files = [tw, twv, tp]
        with open(tw, "wb") as f: f.write(content)
        try:
            seg = AudioSegment.from_file(str(tw)).set_frame_rate(16000).set_channels(1).set_sample_width(2)
            seg.export(str(twv), format="wav")
        except:
            subprocess.run(["ffmpeg","-i",str(tw),"-acodec","pcm_s16le","-ar","16000","-ac","1","-y",str(twv)], capture_output=True, text=True, timeout=30)
        try: audio_processor.process_pipeline(twv, output_path=tp, remove_noise=True, normalize=True, trim_silence=True)
        except: tp = twv
        tr = transcriber.transcribe(tp)
        at = tr.get("text","")
        comp = transcriber.compare_with_expected(at, expected)
        pr = await analyzer.analyze(tp, expected)
        fb = await tutor.generate_feedback(expected=expected, actual=at, errors=comp.get("errors",[]), pronunciation_score=pr.get("overall_score",0))
        result = {"success":True,"session_id":session.session_id,"transcription":at or "[Não foi possível]",
            "pronunciation_score":pr.get("overall_score",0),"word_scores":pr.get("word_scores",{}),
            "pronunciation_level":pr.get("level","fair"),"errors":comp.get("errors",[]),
            "similarity":pr.get("similarity",0),"feedback":fb}
        session.add_to_history(result); session.state = SessionState.READY
        return JSONResponse(result)
    except ValueError as e:
        if session: session.state = SessionState.READY
        return JSONResponse({"success":False,"error":str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Erro análise: {e}", exc_info=True)
        if session: session.state = SessionState.ERROR
        return JSONResponse({"success":False,"error":"Erro interno"}, status_code=500)
    finally:
        async def cleanup():
            await asyncio.sleep(30)
            for f in temp_files:
                try:
                    if f and f.exists(): f.unlink()
                except: pass
        asyncio.create_task(cleanup())


# ============================================================
# TTS
# ============================================================

@app.post("/api/speak")
async def speak_text(request: dict):
    text = request.get("text","").strip()
    if not text or len(text) < 2: raise HTTPException(400, "Texto muito curto")
    if len(text) > 500: raise HTTPException(400, "Texto muito longo")
    try:
        ap = await speaker.speak(text)
        if ap and ap.exists(): return FileResponse(ap, media_type="audio/wav")
        raise HTTPException(503, "TTS indisponível")
    except Exception as e:
        logger.error(f"TTS: {e}")
        raise HTTPException(500, "Erro TTS")


# ============================================================
# CATEGORIAS & VOCABULÁRIO
# ============================================================

@app.get("/api/categories")
async def get_categories(user_id: str = Query("default")):
    cats = await CategoryRepository.get_with_progress(user_id)
    return JSONResponse({"success":True,"total":len(cats),"categories":cats})

@app.get("/api/categories/{category_id}/words")
async def get_words(category_id: int, mode: str = Query("new"), limit: int = Query(10, ge=1, le=50), user_id: str = Query("default")):
    words = await VocabularyRepository.get_words_for_study(category_id=category_id, user_id=user_id, limit=limit, mode=mode) if mode != "all" else (await VocabularyRepository.get_by_category(category_id))[:limit]
    cat = await CategoryRepository.get_by_id(category_id)
    return JSONResponse({"success":True,"category":cat,"mode":mode,"total":len(words),"words":words})


# ============================================================
# PROGRESSO
# ============================================================

@app.post("/api/study/word")
async def record_word(request: dict):
    wid = request.get("word_id"); score = request.get("score",0); uid = request.get("user_id","default")
    if not wid: raise HTTPException(400, "word_id obrigatório")
    score = max(0, min(100, float(score)))
    prog = await ProgressRepository.update_progress(wid, score, uid)
    from ..config import GAMIFICATION_CONFIG
    xp = GAMIFICATION_CONFIG["xp_rules"]["practice_word_base"]
    if score >= 90: xp += GAMIFICATION_CONFIG["xp_rules"]["perfect_score_bonus"]
    elif score >= 70: xp += GAMIFICATION_CONFIG["xp_rules"]["good_score_bonus"]
    streak = await SessionRepository.update_streak(uid)
    if streak.get("current_streak",0) > 1:
        mult = min(GAMIFICATION_CONFIG["xp_rules"]["max_streak_multiplier"], GAMIFICATION_CONFIG["xp_rules"]["streak_multiplier_base"] + streak["current_streak"] * GAMIFICATION_CONFIG["xp_rules"]["streak_multiplier_increment"])
        xp = int(xp * mult)
    return JSONResponse({"success":True,"progress":prog,"xp_earned":xp,"streak":streak})

@app.post("/api/study/session/complete")
async def complete_session(request: dict):
    wd = request.get("words",[])
    if not wd: raise HTTPException(400, "Nenhuma palavra")
    total = len(wd); correct = sum(1 for w in wd if w.get("score",0) >= 70)
    avg = sum(w.get("score",0) for w in wd) / total; xp = sum(w.get("xp_earned",0) for w in wd)
    sid = await SessionRepository.create_session(theme=request.get("theme",""), mode=request.get("mode","vocabulary"), words_practiced=total, correct_words=correct, average_score=avg, xp_earned=xp, duration=request.get("duration",0), user_id=request.get("user_id","default"))
    stats = await ProgressRepository.get_stats(request.get("user_id","default"))
    streak = await SessionRepository.get_streak(request.get("user_id","default"))
    return JSONResponse({"success":True,"session_id":sid,"stats":{"total_words":total,"correct_words":correct,"accuracy":round(correct/total*100,1) if total>0 else 0,"average_score":round(avg,1),"xp_earned":xp},"user_stats":stats,"streak":streak})

@app.get("/api/user/stats")
async def user_stats(user_id: str = Query("default")):
    stats = await ProgressRepository.get_stats(user_id)
    streak = await SessionRepository.get_streak(user_id)
    recent = await SessionRepository.get_recent(user_id, 10)
    cats = await CategoryRepository.get_with_progress(user_id)
    total_xp = (stats.get("total_words_practiced",0) * 10) if stats else 0
    from ..config import GAMIFICATION_CONFIG
    levels = GAMIFICATION_CONFIG["levels"]
    cl = levels[0]; nl = None
    for lv in levels:
        if total_xp >= lv["xp_required"]: cl = lv
    for lv in levels:
        if lv["xp_required"] > total_xp: nl = lv; break
    return JSONResponse({"success":True,"user_id":user_id,"stats":stats,"streak":streak,
        "level":{"current":cl,"next":nl,"total_xp":total_xp,"xp_to_next":(nl["xp_required"]-total_xp) if nl else 0},
        "categories_progress":cats,"recent_sessions":recent})


# ============================================================
# DIÁLOGOS
# ============================================================

@app.get("/api/dialogs/themes")
async def dialog_themes():
    themes = await DialogRepository.get_all_themes()
    return JSONResponse({"success":True,"total":len(themes),"themes":themes})

@app.get("/api/dialogs/{theme}")
async def dialog_by_theme(theme: str):
    dialogs = await DialogRepository.get_by_theme(theme)
    if not dialogs: raise HTTPException(404, f"Tema '{theme}' não encontrado")
    return JSONResponse({"success":True,"theme":theme,"total_lines":len(dialogs),"dialogs":dialogs})

@app.post("/api/dialogs/evaluate")
async def dialog_evaluate(request: dict):
    ur = request.get("user_response","").strip(); er = request.get("expected_response","").strip()
    if not ur or not er: raise HTTPException(400, "Parâmetros obrigatórios")
    from difflib import SequenceMatcher
    uc = ur.lower().strip().rstrip('.!?,'); ec = er.lower().strip().rstrip('.!?,')
    sim = SequenceMatcher(None, uc, ec).ratio()
    uw = set(uc.split()); ew = set(ec.split())
    ws = len(uw & ew) / len(ew) if ew else 0
    score = round((sim * 0.6 + ws * 0.4) * 100)
    fb = "✅ Perfeito!" if score>=90 else "✅ Muito bem!" if score>=75 else "⚠️ Boa!" if score>=60 else "💪 Continue!" if score>=40 else "❌ Estude."
    return JSONResponse({"success":True,"score":score,"feedback":fb,"correct_answer":er,"similarity":round(sim,3)})


# ============================================================
# DIÁLOGOS - FREE CHAT (MODO HÍBRIDO)
# ============================================================

@app.post("/api/dialogs/free-chat")
async def free_chat(request: dict):
    """Conversa livre com IA + dados online em tempo real"""
    message = request.get("message", "").strip()
    context = request.get("context", "casual conversation")
    history = request.get("history", [])
    use_live = request.get("use_live_data", True)
    
    if not message: raise HTTPException(400, "Mensagem obrigatória")
    if len(message) > 200: raise HTTPException(400, "Mensagem muito longa")
    
    # --- MODO HÍBRIDO: busca dados online ---
    live_prompt = ""
    image_url = ""
    live_used = False
    
    if use_live:
        try:
            from ..enhancements.context_engine import context_engine
            ctx = await context_engine.build_context(theme=context)
            if ctx and ctx.contextual_prompt:
                live_prompt = f"\n🌐 LIVE DATA (use naturally):\n{ctx.contextual_prompt}\n"
                live_used = True
            image_url = await context_engine.get_image_for_theme(context)
        except Exception as e:
            logger.warning(f"Online indisponível: {e}")
    
    # --- Prompt para Ollama ---
    hist = "".join([f"{'Agent' if m.get('role')=='assistant' else 'Student'}: {m.get('text','')}\n" for m in history[-10:]])
    
    prompt = f"""You are a native English speaker in a {context} situation.
CONVERSATION: {hist}Student: {message}{live_prompt}
RULES: Respond ONLY in English (under 20 words). Be natural. If LIVE DATA provided, use it.
Respond ONLY JSON: {{"response":"...","translation":"...","tip":"..."}}"""
    
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:11434/api/generate", json={
                "model": "qwen2.5-coder:3b", "prompt": prompt, "stream": False,
                "options": {"temperature": 0.8, "num_predict": 200, "top_p": 0.95}
            }, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    text = result.get("response", "")
                    try:
                        s = text.find('{'); e = text.rfind('}') + 1
                        if s >= 0 and e > s:
                            data = json.loads(text[s:e])
                            return JSONResponse({"success":True,"response":data.get("response",text[:200]),
                                "translation":data.get("translation",""),"tip":data.get("tip",""),
                                "context":context,"image_url":image_url,"live_data_used":live_used})
                    except: pass
                    return JSONResponse({"success":True,"response":text.strip()[:200],"translation":"","tip":"",
                        "context":context,"image_url":image_url,"live_data_used":live_used})
    except Exception as e:
        logger.error(f"Ollama erro: {e}")
    
    return JSONResponse({"success":True,"response":f"I understand. Tell me more about {context}.",
        "translation":"Entendo. Conte mais.","tip":"","context":context,"image_url":"","live_data_used":False,"offline_fallback":True})


# ============================================================
# DIÁLOGOS - DINÂMICO (MODO HÍBRIDO)
# ============================================================

@app.post("/api/dialogs/dynamic")
async def dynamic_dialog(request: dict):
    """Diálogo dinâmico com IA generativa + dados online"""
    theme = request.get("theme", "casual conversation")
    role = request.get("role", "assistant")
    user_message = request.get("user_message", "")
    history = request.get("history", [])
    use_live = request.get("use_live_data", True)
    
    if not user_message: raise HTTPException(400, "user_message required")
    
    result = await dialog_engine.generate_response(
        theme=theme, role=role, conversation_history=history,
        user_message=user_message, use_live_data=use_live
    )
    return JSONResponse({"success": True, **result})


# ============================================================
# CONQUISTAS & UTILITÁRIOS
# ============================================================

@app.get("/api/user/achievements")
async def achievements(user_id: str = Query("default")):
    from ..data.database import db
    ach = await db.fetch_all("SELECT * FROM achievements WHERE user_id=? OR user_id='default' ORDER BY completed DESC, achievement_key", (user_id,))
    total = len(ach); unlocked = sum(1 for a in ach if a.get("completed"))
    return JSONResponse({"success":True,"total":total,"unlocked":unlocked,"progress":round(unlocked/total*100,1) if total>0 else 0,"achievements":ach})

@app.get("/api/stats/database")
async def db_stats():
    from ..data.database import db
    tables = ["categories","vocabulary","dialogs","user_progress","study_sessions","achievements"]
    st = {}
    for t in tables:
        c = await db.fetch_one(f"SELECT COUNT(*) as count FROM {t}")
        st[t] = c["count"] if c else 0
    sz = Path("english_teacher.db").stat().st_size if Path("english_teacher.db").exists() else 0
    return JSONResponse({"success":True,"database_size_mb":round(sz/1024/1024,2),"tables":st})


# ============================================================
# EXCEÇÕES
# ============================================================

@app.exception_handler(404)
async def not_found(request: Request, exc: HTTPException):
    return JSONResponse({"success":False,"error":"Endpoint não encontrado","path":str(request.url.path)}, status_code=404)

@app.exception_handler(500)
async def internal_error(request: Request, exc: HTTPException):
    logger.error(f"Erro: {exc}", exc_info=True)
    return JSONResponse({"success":False,"error":"Erro interno"}, status_code=500)