"""
Gerenciador de sessões de usuário
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """Estados possíveis da sessão"""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


@dataclass
class UserSession:
    """Dados de sessão de um usuário"""
    session_id: str
    created_at: datetime
    last_activity: datetime
    state: SessionState = SessionState.IDLE
    task_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    
    # Histórico de análises
    history: list = field(default_factory=list)
    max_history: int = 10
    
    # Lock para evitar concorrência
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    
    def is_expired(self, max_idle_minutes: int = 30) -> bool:
        """Verifica se sessão expirou"""
        return datetime.now() - self.last_activity > timedelta(minutes=max_idle_minutes)
    
    def add_to_history(self, analysis_result: Dict[str, Any]):
        """Adiciona análise ao histórico"""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "result": analysis_result
        })
        
        # Mantém apenas últimas N análises
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_progress(self) -> Dict[str, Any]:
        """Calcula progresso do aluno"""
        if not self.history:
            return {"average_score": 0, "sessions": 0, "trend": "new"}
        
        scores = [h["result"].get("pronunciation_score", 0) for h in self.history]
        avg_score = sum(scores) / len(scores)
        
        # Tendência (últimas 3 vs anteriores)
        if len(scores) >= 4:
            recent_avg = sum(scores[-3:]) / 3
            older_avg = sum(scores[:-3]) / (len(scores) - 3)
            trend = "improving" if recent_avg > older_avg else "declining"
        else:
            trend = "learning"
        
        return {
            "average_score": round(avg_score, 1),
            "sessions": len(self.history),
            "trend": trend,
            "last_score": scores[-1] if scores else 0
        }


class SessionManager:
    """Gerencia sessões de usuários"""
    
    def __init__(self, cleanup_interval: int = 300):
        self.sessions: Dict[str, UserSession] = {}
        self.cleanup_interval = cleanup_interval
        self._cleanup_task = None
    
    async def start(self):
        """Inicia o gerenciador de sessões"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("SessionManager iniciado")
    
    async def stop(self):
        """Para o gerenciador"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("SessionManager parado")
    
    async def create_session(self) -> UserSession:
        """Cria nova sessão"""
        session_id = uuid.uuid4().hex[:12]
        session = UserSession(
            session_id=session_id,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            state=SessionState.IDLE
        )
        self.sessions[session_id] = session
        logger.info(f"Sessão criada: {session_id}")
        return session
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """Recupera sessão existente"""
        session = self.sessions.get(session_id)
        if session:
            if session.is_expired():
                await self.delete_session(session_id)
                return None
            session.last_activity = datetime.now()
        return session
    
    async def delete_session(self, session_id: str):
        """Remove sessão"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Sessão removida: {session_id}")
    
    async def _cleanup_loop(self):
        """Loop de limpeza de sessões expiradas"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                expired = [
                    sid for sid, session in self.sessions.items()
                    if session.is_expired()
                ]
                for sid in expired:
                    await self.delete_session(sid)
                if expired:
                    logger.info(f"Limpeza: {len(expired)} sessões expiradas removidas")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro na limpeza de sessões: {e}")


# Instância global
session_manager = SessionManager()