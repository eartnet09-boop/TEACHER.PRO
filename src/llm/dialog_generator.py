# src/llm/dialog_generator.py (NOVO)
"""
Gerador de diálogos dinâmicos usando Qwen via Ollama
"""
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DialogGenerator:
    """
    Gera respostas dinâmicas para diálogos usando o LLM local.
    Mantém a estrutura do tema mas varia as falas do agente.
    """
    
    def __init__(self):
        self.tutor = None  # Será injetado
        
    async def generate_agent_response(
        self,
        theme: str,
        role: str,
        context: List[Dict],
        user_response: str = None
    ) -> Dict:
        """
        Gera a próxima fala do agente baseado no contexto da conversa.
        
        Args:
            theme: Tema do diálogo (Restaurante, Aeroporto, etc.)
            role: Papel do agente (Garçom, Atendente, etc.)
            context: Histórico da conversa (últimas 5 falas)
            user_response: Última resposta do usuário
            
        Returns:
            Dict com a fala do agente e tradução
        """
        # Constrói o contexto da conversa
        context_text = ""
        for msg in context[-6:]:  # Últimas 6 mensagens
            context_text += f"{msg['role']}: {msg['text']}\n"
        
        prompt = f"""Você é um {role} em um {theme} nos Estados Unidos. 
Você está conversando com um cliente que está aprendendo inglês.

CONTEXTO DA CONVERSA:
{context_text}

O cliente acabou de dizer: "{user_response}"

REGRAS:
1. Responda APENAS em inglês (natural, como um nativo falaria)
2. Use frases curtas (máximo 15 palavras)
3. Seja educado e profissional
4. Se o cliente cometer um erro de inglês, sutilmente use a forma correta na sua resposta
5. Mantenha a conversa fluindo naturalmente
6. Adicione uma pequena variação, não repita sempre as mesmas frases

RESPONDA APENAS COM UM JSON:
{{
  "line": "Sua resposta em inglês aqui",
  "translation": "Tradução em português aqui",
  "correction": "Se o aluno errou algo, corrija sutilmente aqui (ou deixe vazio)"
}}
"""
        
        # Usa o Ollama para gerar resposta
        try:
            from .tutor import tutor
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "qwen2.5-coder:3b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,  # Mais criatividade
                        "num_predict": 150,
                        "top_p": 0.9
                    }
                }
                
                async with session.post(
                    "http://localhost:11434/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result.get("response", "")
                        
                        # Extrai JSON da resposta
                        try:
                            start = response_text.find('{')
                            end = response_text.rfind('}') + 1
                            if start >= 0 and end > start:
                                return json.loads(response_text[start:end])
                        except json.JSONDecodeError:
                            pass
                        
                        # Fallback: usa a resposta como linha
                        return {
                            "line": response_text.strip()[:150],
                            "translation": "",
                            "correction": ""
                        }
        except Exception as e:
            logger.warning(f"Erro ao gerar resposta dinâmica: {e}")
        
        # Fallback: resposta padrão
        return {
            "line": "How can I help you today?",
            "translation": "Como posso ajudá-lo hoje?",
            "correction": ""
        }
    
    async def generate_daily_phrases(
        self,
        situation: str,
        count: int = 5
    ) -> List[Dict]:
        """
        Gera frases úteis para situações do dia a dia.
        
        Args:
            situation: Situação (ex: "pedindo café", "no táxi", "na farmácia")
            count: Número de frases
            
        Returns:
            Lista de frases com tradução
        """
        prompt = f"""Gere {count} frases em inglês que um brasileiro usaria na seguinte situação nos Estados Unidos:
"{situation}"

REGRAS:
1. Frases REALMENTE úteis e comuns
2. Inglês natural do dia a dia
3. Inclua variações (formal e informal)
4. Cada frase deve ter no máximo 12 palavras

RESPONDA APENAS COM UM JSON:
{{
  "phrases": [
    {{"english": "frase em inglês", "portuguese": "tradução", "context": "quando usar"}}
  ]
}}
"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "qwen2.5-coder:3b",
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.8, "num_predict": 500}
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
                                return data.get("phrases", [])
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            logger.warning(f"Erro ao gerar frases: {e}")
        
        return []