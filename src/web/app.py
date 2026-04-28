# src/web/app.py
"""
Aplicação web FastAPI - Versão Profissional Refatorada
"""
import uuid
import logging
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydub import AudioSegment

from ..config import SERVER_CONFIG, TEMP_DIR
from .session_manager import session_manager, SessionState

logger = logging.getLogger(__name__)

# Cria app
app = FastAPI(
    title="English Teacher Agent",
    description="Professor de inglês por IA com preservação de erros",
    version="3.0.0"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Monta arquivos estáticos
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Importa os módulos (CORRIGIDO!)
from ..transcription.chall_model import transcriber
from ..pronunciation.wavlm_analyzer import analyzer  # ✅ CORRETO
from ..llm.tutor import tutor                        # ✅ CORRETO
from ..tts.speaker import speaker                    # ✅ CORRETO
from ..audio.processor import audio_processor        # ✅ CORRETO


@app.on_event("startup")
async def startup():
    """Inicializa serviços"""
    await session_manager.start()
    logger.info("✅ Servidor iniciado")


@app.on_event("shutdown")
async def shutdown():
    """Finaliza serviços"""
    await session_manager.stop()
    logger.info("✅ Servidor finalizado")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Página principal"""
    html_path = static_dir / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding='utf-8'))
    else:
        return HTMLResponse(content="<h1>Arquivo index.html não encontrado</h1><p>Execute o diagnóstico.</p>")


@app.post("/api/session")
async def create_session():
    """Cria nova sessão de usuário"""
    session = await session_manager.create_session()
    return JSONResponse({
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat()
    })


@app.post("/api/analyze")
async def analyze_audio(
    audio: UploadFile = File(...),
    expected: str = Form(""),
    session_id: Optional[str] = Form(None)
):
    """Analisa áudio do aluno com gerenciamento de sessão"""
    temp_files = []
    
    try:
        # Valida sessão
        session = None
        if session_id:
            session = await session_manager.get_session(session_id)
            if not session:
                session = await session_manager.create_session()
        else:
            session = await session_manager.create_session()
        
        # Verifica se sessão está livre
        async with session.lock:
            if session.state == SessionState.PROCESSING:
                return JSONResponse({
                    "success": False,
                    "error": "Sessão ocupada. Aguarde o processamento atual."
                }, status_code=409)
            session.state = SessionState.PROCESSING
        
        # 1. Salva áudio
        unique_id = uuid.uuid4().hex
        temp_webm = TEMP_DIR / f"recording_{unique_id}.webm"
        temp_wav = TEMP_DIR / f"recording_{unique_id}.wav"
        temp_processed = TEMP_DIR / f"processed_{unique_id}.wav"
        temp_files = [temp_webm, temp_wav, temp_processed]
        
        content = await audio.read()
        with open(temp_webm, "wb") as f:
            f.write(content)
        
        # 2. Converte WebM para WAV
        try:
            audio_segment = AudioSegment.from_file(str(temp_webm))
            audio_segment = audio_segment.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            audio_segment.export(str(temp_wav), format="wav")
        except Exception as e:
            logger.warning(f"pydub falhou, usando ffmpeg: {e}")
            import subprocess
            subprocess.run([
                "ffmpeg", "-i", str(temp_webm),
                "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
                "-y", str(temp_wav)
            ], capture_output=True, timeout=30)
        
        # 3. Processa áudio
        try:
            audio_array, metadata = audio_processor.process_pipeline(
                temp_wav,
                output_path=temp_processed,
                remove_noise=True,
                normalize=True,
                trim_silence=True
            )
        except Exception as e:
            logger.warning(f"Processamento falhou: {e}")
            temp_processed = temp_wav
        
        # 4. Transcrição
        transcription_result = transcriber.transcribe(temp_processed)
        actual_text = transcription_result.get("text", "")
        
        # 5. Comparação
        comparison = transcriber.compare_with_expected(actual_text, expected)
        
        # 6. Análise de pronúncia
        pronunciation_result = await analyzer.analyze(temp_processed, expected)
        
        # 7. Feedback do tutor
        feedback = await tutor.generate_feedback(
            expected=expected,
            actual=actual_text,
            errors=comparison.get("errors", []),
            pronunciation_score=pronunciation_result.get("overall_score", 0)
        )
        
        # 8. Resposta
        result = {
            "success": True,
            "transcription": actual_text if actual_text else "[Não foi possível transcrever]",
            "word_scores": pronunciation_result.get("word_scores", {}),
            "pronunciation_score": pronunciation_result.get("overall_score", 0),
            "errors": comparison.get("errors", []),
            "feedback": feedback,
            "session_id": session.session_id
        }
        
        session.add_to_history(result)
        session.state = SessionState.READY
        
        return JSONResponse(result)
        
    except Exception as e:
        logger.error(f"Erro na análise: {e}", exc_info=True)
        if session:
            session.state = SessionState.ERROR
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)
    
    finally:
        async def cleanup():
            await asyncio.sleep(30)
            for temp_file in temp_files:
                try:
                    if temp_file and temp_file.exists():
                        temp_file.unlink()
                except Exception:
                    pass
        asyncio.create_task(cleanup())


@app.post("/api/speak")
async def speak_text(request: dict):
    """Sintetiza voz do texto"""
    text = request.get("text", "")
    if not text:
        return JSONResponse({"error": "No text"}, status_code=400)
    
    audio_path = await speaker.speak(text)
    if audio_path and audio_path.exists():
        return FileResponse(audio_path, media_type="audio/wav")
    return JSONResponse({"error": "TTS not available"}, status_code=503)


@app.get("/api/health")
async def health():
    """Health check"""
    import torch
    ollama_status = await tutor._check_ollama()
    return {
        "status": "ok",
        "service": "English Teacher Agent",
        "version": "3.0.0",
        "ollama": ollama_status,
        "gpu_available": torch.cuda.is_available(),
        "active_sessions": len(session_manager.sessions)
    }