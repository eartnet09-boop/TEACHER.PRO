# src/llm/dialog_engine.py
"""
Motor de Diálogos com IA - English Teacher Agent v4.2
Gera respostas naturais e contextualizadas usando Qwen via Ollama.
Suporte a modo híbrido com dados online em tempo real.
"""

import json
import logging
import aiohttp
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class DialogEngine:
    """
    Motor de geração de respostas para diálogos imersivos.
    
    Características:
    - Personagens realistas que mantêm o papel estritamente
    - Respostas SEMPRE em inglês (com instrução reforçada)
    - Integração com dados online (clima, cultura, cotação)
    - Fallback offline transparente
    - Correção sutil de erros do aluno
    - Respostas curtas e naturais (estilo conversação real)
    - Parse robusto de JSON com fallback inteligente
    """
    
    # Constantes
    OLLAMA_HOST = "http://localhost:11434"
    MODEL_NAME = "qwen2.5-coder:3b"
    MAX_HISTORY_MESSAGES = 12
    TEMPERATURE = 0.6
    NUM_PREDICT = 200
    TOP_P = 0.92
    REPEAT_PENALTY = 1.15
    TIMEOUT_SECONDS = 20
    MAX_RESPONSE_LENGTH = 250
    
    def __init__(self):
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
        # 1. Formata histórico
        history_text = self._format_history(conversation_history)
        
        # 2. Busca dados online (modo híbrido)
        live_context_prompt, live_data_used = await self._fetch_live_context(
            theme, use_live_data
        )
        
        # 3. Constrói prompt otimizado
        prompt = self._build_prompt(
            theme=theme,
            role=role,
            history_text=history_text,
            user_message=user_message,
            live_context_prompt=live_context_prompt
        )
        
        # 4. Gera resposta via Ollama
        result = await self._call_ollama(prompt)
        
        # 5. Valida e sanitiza resposta
        result = self._validate_response(result)
        
        # 6. Adiciona metadados
        result["live_data_used"] = live_data_used
        
        logger.debug(
            f"📝 Resposta gerada | tema={theme} | "
            f"live={'sim' if live_data_used else 'não'} | "
            f"tamanho={len(result.get('response',''))} caracteres"
        )
        
        return result
    
    # ================================================================
    # FORMATAÇÃO DE HISTÓRICO
    # ================================================================
    
    def _format_history(self, history: list) -> str:
        """
        Formata histórico da conversa para o prompt.
        Mantém apenas as últimas N mensagens para contexto.
        """
        if not history:
            return "(new conversation - no prior messages)"
        
        lines = []
        for msg in history[-self.MAX_HISTORY_MESSAGES:]:
            role_label = "Agent" if msg.get("role") == "agent" else "Student"
            text = msg.get("text", "").strip()
            if text:
                lines.append(f"{role_label}: {text}")
        
        return "\n".join(lines) if lines else "(empty conversation)"
    
    # ================================================================
    # CONTEXTO ONLINE (MODO HÍBRIDO)
    # ================================================================
    
    async def _fetch_live_context(self, theme: str, use_live_data: bool) -> Tuple[str, bool]:
        """
        Busca dados online para enriquecer o contexto do diálogo.
        
        Returns:
            Tuple[str, bool]: (prompt_text, data_was_used)
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
                    f"\n🌐 REAL-TIME CONTEXT (incorporate naturally):\n"
                    f"{context.contextual_prompt}\n"
                )
                logger.info(f"📡 Dados online integrados ao diálogo '{theme}'")
                return prompt, True
            
        except Exception as e:
            logger.warning(f"⚠️ Falha ao obter dados online: {e}")
        
        return "", False
    
    # ================================================================
    # CONSTRUÇÃO DO PROMPT
    # ================================================================
    
    def _build_prompt(
        self,
        theme: str,
        role: str,
        history_text: str,
        user_message: str,
        live_context_prompt: str
    ) -> str:
        """
        Constrói o prompt para o Ollama com instruções reforçadas.
        O prompt é projetado para:
        1. Garantir resposta em INGLÊS (nunca português)
        2. Manter o personagem estritamente no papel
        3. Gerar respostas naturais e curtas
        """
        is_start = user_message.upper() == "START"
        user_line = "" if is_start else f'Student just said: "{user_message}"'
        start_instruction = (
            "INITIATE the conversation naturally as this character would in a real situation. "
            "Greet the student appropriately for the context."
            if is_start else ""
        )
        
        return f"""SYSTEM: You are an AI roleplaying as a {role}.
This is a language learning exercise for a Brazilian student.

CRITICAL RULES - VIOLATION IS UNACCEPTABLE:
1. LANGUAGE: You MUST respond in ENGLISH only. Portuguese is STRICTLY FORBIDDEN in your "response" field.
2. CHARACTER: You ARE a {role}. Never break character under any circumstances.
3. REALISM: Speak EXACTLY as this person would in real life.
4. BREVITY: Keep responses between 8 and 25 words maximum.
5. RELEVANCE: React directly to what the student just said.
6. CORRECTION: If the student makes an error, subtly use the correct form in YOUR response.
7. CONTEXT: Stay within the {theme} context - do NOT change topics.
8. CONTINUITY: NEVER restart or re-greet unless the student explicitly leaves and comes back.

CONTEXT: {theme}
{live_context_prompt}
CONVERSATION HISTORY:
{history_text}
{user_line}
{start_instruction}

IMPORTANT: Your "response" field MUST be in ENGLISH. The "translation" field should be in Portuguese.

Respond ONLY with a valid JSON object (no other text, no markdown, no code blocks):
{{"response": "your in-character ENGLISH response here", "translation": "sua tradução em PORTUGUÊS aqui", "tip": "brief correction tip ONLY if student made a clear error, otherwise leave empty"}}"""

    # ================================================================
    # CHAMADA À API OLLAMA
    # ================================================================
    
    async def _call_ollama(self, prompt: str) -> dict:
        """
        Chama a API do Ollama para gerar resposta.
        Inclui timeout, tratamento de erros e fallback offline.
        """
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.TEMPERATURE,
                        "num_predict": self.NUM_PREDICT,
                        "top_p": self.TOP_P,
                        "repeat_penalty": self.REPEAT_PENALTY
                    }
                }
                
                async with session.post(
                    f"{self.OLLAMA_HOST}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.TIMEOUT_SECONDS)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        text = result.get("response", "")
                        logger.debug(f"Ollama respondeu em {len(text)} caracteres")
                        return self._parse_response(text)
                    else:
                        logger.error(f"❌ Ollama retornou HTTP {resp.status}")
                        
        except aiohttp.ClientError as e:
            logger.warning(f"🔌 Ollama indisponível: {e}")
        except aiohttp.ServerTimeoutError:
            logger.error("⏰ Timeout ao chamar Ollama")
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao chamar Ollama: {e}")
        
        return self._fallback_response()
    
    # ================================================================
    # PARSE DA RESPOSTA
    # ================================================================
    
    def _parse_response(self, text: str) -> dict:
        """
        Extrai JSON da resposta do Ollama.
        Lida com casos onde o modelo retorna:
        - JSON puro
        - JSON dentro de markdown (```json ... ```)
        - Texto fora do JSON
        - Campos ausentes
        """
        # Tenta extrair JSON da resposta
        try:
            # Remove markdown code blocks se existirem
            clean_text = text.strip()
            if clean_text.startswith("```"):
                clean_text = clean_text.split("```")[1]
                if clean_text.startswith("json"):
                    clean_text = clean_text[4:]
                clean_text = clean_text.strip()
            
            start = clean_text.find('{')
            end = clean_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                data = json.loads(clean_text[start:end])
                
                response = data.get("response", "").strip()
                translation = data.get("translation", "").strip()
                tip = data.get("tip", "").strip()
                
                # Se a resposta veio em português, tenta extrair algo útil
                if response and not self._is_english(response):
                    logger.warning(f"⚠️ Resposta não está em inglês: '{response[:50]}...'")
                    # Usa a resposta como tradução e gera fallback
                    return {
                        "response": "I understand. How can I help you?",
                        "translation": response[:self.MAX_RESPONSE_LENGTH],
                        "tip": tip[:200] if tip else ""
                    }
                
                return {
                    "response": response[:self.MAX_RESPONSE_LENGTH],
                    "translation": translation[:self.MAX_RESPONSE_LENGTH] if translation else "",
                    "tip": tip[:200] if tip else ""
                }
                
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            logger.warning(f"⚠️ Falha ao parsear JSON: {e}")
        
        # Fallback: usa o texto como resposta
        cleaned = text.strip()
        for char in ['`', '{', '}', '"', '\\']:
            cleaned = cleaned.replace(char, '')
        cleaned = cleaned.replace('json', '').strip()
        
        if cleaned and self._is_english(cleaned):
            return {
                "response": cleaned[:self.MAX_RESPONSE_LENGTH],
                "translation": "",
                "tip": ""
            }
        
        return self._fallback_response()
    
    def _is_english(self, text: str) -> bool:
        """
        Verifica se o texto está em inglês usando heurísticas simples.
        """
        if not text:
            return False
        
        # Palavras comuns em português que NÃO deveriam aparecer
        portuguese_markers = [
            'você', 'para', 'como', 'uma', 'aqui', 'isso', 'não', 'mais',
            'muito', 'bem', 'bom', 'boa', 'dia', 'noite', 'olá', 'oi',
            'obrigado', 'obrigada', 'por favor', 'prazer', 'tchau'
        ]
        
        text_lower = text.lower()
        for marker in portuguese_markers:
            if marker in text_lower:
                return False
        
        # Se tem mais de 3 palavras e nenhuma em português, assume inglês
        return True
    
    def _validate_response(self, result: dict) -> dict:
        """
        Valida e sanitiza a resposta final.
        Garante que a resposta está em inglês.
        """
        response = result.get("response", "")
        
        # Se a resposta está vazia ou em português
        if not response or not self._is_english(response):
            logger.warning("⚠️ Resposta inválida detectada, usando fallback")
            fallback = self._fallback_response()
            fallback["translation"] = response if response else fallback["translation"]
            return fallback
        
        return result
    
    # ================================================================
    # FALLBACK
    # ================================================================
    
    def _fallback_response(self) -> dict:
        """
        Resposta de fallback quando Ollama falha.
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