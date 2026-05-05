# src/llm/dialog_engine.py
"""
Motor de Diálogos com IA - English Teacher Agent v4.1
Gera respostas naturais e contextualizadas usando Qwen via Ollama.
Suporte a modo híbrido com dados online em tempo real.
"""

import json
import logging
import aiohttp
from typing import Optional

logger = logging.getLogger(__name__)


class DialogEngine:
    """
    Motor de geração de respostas para diálogos imersivos.
    
    Características:
    - Personagens realistas que mantêm o papel estritamente
    - Integração com dados online (clima, cultura, cotação)
    - Fallback offline transparente
    - Correção sutil de erros do aluno
    - Respostas curtas e naturais (estilo conversação real)
    """
    
    def __init__(self):
        self.ollama_host = "http://localhost:11434"
        self.model = "qwen2.5-coder:3b"
        self._context_engine: Optional[object] = None
        self._context_engine_loaded: bool = False
    
    @property
    def context_engine(self) -> Optional[object]:
        """
        Carrega ContextEngine sob demanda (lazy loading).
        Evita import circular e falha silenciosa se módulo não existir.
        """
        if not self._context_engine_loaded:
            self._context_engine_loaded = True
            try:
                from ..enhancements.context_engine import context_engine
                self._context_engine = context_engine
                logger.info("✅ ContextEngine carregado - modo híbrido disponível")
            except ImportError:
                logger.info("ℹ️ ContextEngine não disponível - modo apenas offline")
                self._context_engine = None
        return self._context_engine
    
    # ================================================================
    # GERAÇÃO PRINCIPAL
    # ================================================================
    
    async def generate_response(
        self,
        theme: str,
        role: str,
        conversation_history: list,
        user_message: str,
        use_live_data: bool = True
    ) -> dict:
        """
        Gera resposta natural do agente para diálogo imersivo.
        
        Args:
            theme: Tema do diálogo (restaurant, airport, hotel, etc.)
            role: Papel do agente (ex: "friendly waiter at an Italian restaurant")
            conversation_history: Histórico da conversa [{"role":"agent/user","text":"..."}]
            user_message: Última mensagem do aluno (ou "START" para iniciar)
            use_live_data: Se True, busca dados online para enriquecer contexto
            
        Returns:
            dict: {
                "response": "resposta em inglês",
                "translation": "tradução em português",
                "tip": "dica de correção (ou string vazia)",
                "live_data_used": bool
            }
        """
        # --- 1. Constrói histórico formatado ---
        history_text = self._format_history(conversation_history)
        
        # --- 2. Busca dados online (modo híbrido) ---
        live_context_prompt, live_data_used = await self._fetch_live_context(
            theme, use_live_data
        )
        
        # --- 3. Constrói prompt otimizado ---
        prompt = self._build_prompt(
            theme=theme,
            role=role,
            history_text=history_text,
            user_message=user_message,
            live_context_prompt=live_context_prompt
        )
        
        # --- 4. Gera resposta via Ollama ---
        result = await self._call_ollama(prompt)
        
        # --- 5. Adiciona metadados ---
        result["live_data_used"] = live_data_used
        
        logger.debug(
            f"Resposta gerada para '{theme}' | "
            f"live_data={'sim' if live_data_used else 'não'} | "
            f"tamanho={len(result.get('response',''))} caracteres"
        )
        
        return result
    
    # ================================================================
    # MÉTODOS AUXILIARES PRIVADOS
    # ================================================================
    
    def _format_history(self, history: list) -> str:
        """Formata histórico da conversa para o prompt"""
        if not history:
            return "(new conversation)"
        
        lines = []
        for msg in history[-12:]:  # Últimas 8 mensagens
            prefix = "Agent" if msg.get("role") == "agent" else "Student"
            lines.append(f"{prefix}: {msg.get('text', '')}")
        
        return "\n".join(lines)
    
    async def _fetch_live_context(self, theme: str, use_live_data: bool) -> tuple:
        """
        Busca dados online para enriquecer o contexto.
        
        Returns:
            tuple: (context_prompt: str, live_data_used: bool)
        """
        if not use_live_data:
            return "", False
        
        if self.context_engine is None:
            return "", False
        
        try:
            context = await self.context_engine.build_context(
                theme=theme,
                country="United States",
                city="New York"
            )
            
            if context and context.contextual_prompt:
                prompt = (
                    f"\n🌐 REAL-TIME DATA (incorporate naturally):\n"
                    f"{context.contextual_prompt}\n"
                )
                logger.info(f"📡 Dados online integrados ao diálogo '{theme}'")
                return prompt, True
            
        except Exception as e:
            logger.warning(f"⚠️ Falha ao obter dados online: {e}")
        
        return "", False
    
    def _build_prompt(
        self,
        theme: str,
        role: str,
        history_text: str,
        user_message: str,
        live_context_prompt: str
    ) -> str:
        """
        Constrói o prompt para o Ollama com instruções detalhadas.
        O prompt é projetado para manter o personagem estritamente no papel.
        """
        # Determina se é início de conversa
        is_start = user_message.upper() == "START"
        user_line = "" if is_start else f'Student just said: "{user_message}"'
        start_instruction = (
            "Start the conversation naturally as this character would in a real situation."
            if is_start else ""
        )
        
        return f"""You are ROLEPLAYING as a {role}.

CONTEXT: {theme}
{live_context_prompt}
CONVERSATION HISTORY:
{history_text}
{user_line}
{start_instruction}

CHARACTER RULES (MUST FOLLOW):
1. You ARE a {role}. Never break character.
2. Speak EXACTLY as this person would in real life.
3. Use common phrases and vocabulary a real {role} uses daily.
4. Respond in English ONLY (10-25 words maximum).
5. React directly to what the student said.
6. If the student makes a grammar or vocabulary error, subtly use the correct form in your response (do NOT explicitly correct them unless they ask).
7. Stay within the {theme} context - do NOT change topics randomly.
8. NEVER restart the conversation or re-greet the guest unless they explicitly leave and come back.

CONVERSATION FLOW:
- If this is the start, greet the student as a real {role} would.
- After your response, naturally invite the student to respond.
- Keep the conversation moving forward logically.

Respond ONLY with a valid JSON object:
{{"response": "your in-character English response", "translation": "Brazilian Portuguese translation of your response", "tip": "brief correction tip ONLY if student made a clear error, otherwise empty string"}}"""

    async def _call_ollama(self, prompt: str) -> dict:
        """
        Chama a API do Ollama para gerar resposta.
        Inclui timeout, retry e fallback offline.
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.6,   # Equilíbrio entre criatividade e consistência
                        "num_predict": 180,    # Suficiente para resposta + JSON
                        "top_p": 0.92,
                        "repeat_penalty": 1.1  # Evita repetições
                    }
                }
                
                async with session.post(
                    f"{self.ollama_host}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        text = result.get("response", "")
                        return self._parse_response(text)
                    else:
                        logger.error(f"Ollama retornou HTTP {resp.status}")
                        
        except aiohttp.ClientError as e:
            logger.warning(f"🔌 Ollama indisponível: {e}")
        except Exception as e:
            logger.error(f"❌ Erro ao chamar Ollama: {e}")
        
        # Fallback offline total
        return self._fallback_response()
    
    def _parse_response(self, text: str) -> dict:
        """
        Extrai JSON da resposta do Ollama.
        Lida com casos onde o modelo retorna texto fora do JSON.
        """
        # Tenta extrair JSON da resposta
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                data = json.loads(text[start:end])
                
                # Valida campos obrigatórios
                return {
                    "response": data.get("response", "").strip()[:250],
                    "translation": data.get("translation", "").strip()[:250],
                    "tip": data.get("tip", "").strip()[:200]
                }
        except (json.JSONDecodeError, KeyError, AttributeError):
            pass
        
        # Se não conseguiu extrair JSON, usa o texto como resposta
        cleaned = text.strip()
        # Remove caracteres não-JSON comuns
        for char in ['`', '{', '}', '"']:
            cleaned = cleaned.replace(char, '')
        
        return {
            "response": cleaned[:200] if cleaned else "I understand. How can I help you?",
            "translation": "",
            "tip": ""
        }
    
    def _fallback_response(self) -> dict:
        """
        Resposta de fallback quando tudo falha.
        Mantém o tom profissional e encorajador.
        """
        return {
            "response": "I understand. How can I help you with that?",
            "translation": "Entendo. Como posso ajudar com isso?",
            "tip": ""
        }


# ================================================================
# INSTÂNCIA GLOBAL
# ================================================================

dialog_engine = DialogEngine()