# src/llm/tutor.py
"""
Tutor IA usando Ollama + Qwen2.5-Coder
"""
import json
import logging
import aiohttp
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class Tutor:
    """Tutor de pronúncia usando LLM local via Ollama"""
    
    def __init__(self):
        self.ollama_host = "http://localhost:11434"
        self.model_name = "qwen2.5-coder:3b"
        self.temperature = 0.3
        self.max_tokens = 300
        
    async def _check_ollama(self) -> Dict:
        """Verifica se Ollama está rodando"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.ollama_host}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [m["name"] for m in data.get("models", [])]
                        return {
                            "running": True,
                            "models": models,
                            "has_qwen": self.model_name in models
                        }
        except aiohttp.ClientError:
            pass
        except Exception as e:
            logger.warning(f"Ollama check error: {e}")
        
        return {"running": False, "models": [], "has_qwen": False}
    
    async def generate_feedback(
        self,
        expected: str,
        actual: str,
        errors: List[Dict],
        pronunciation_score: float
    ) -> Dict[str, str]:
        """
        Gera feedback personalizado para o aluno
        
        Args:
            expected: Texto esperado
            actual: Texto transcrito (com erros)
            errors: Lista de erros detectados
            pronunciation_score: Score geral (0-100)
            
        Returns:
            Dict com correção, dica e exercício
        """
        # Primeiro verifica se Ollama está disponível
        ollama_status = await self._check_ollama()
        
        if not ollama_status["running"]:
            return self._fallback_feedback(expected, actual, errors, pronunciation_score)
        
        # Constrói prompt
        prompt = self._build_prompt(expected, actual, errors, pronunciation_score)
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    }
                }
                
                async with session.post(
                    f"{self.ollama_host}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result.get("response", "")
                        
                        # Tenta extrair JSON da resposta
                        feedback = self._parse_response(response_text)
                        return feedback
        
        except aiohttp.ClientError as e:
            logger.error(f"Erro na comunicação com Ollama: {e}")
        except Exception as e:
            logger.error(f"Erro ao gerar feedback: {e}")
        
        # Fallback se algo der errado
        return self._fallback_feedback(expected, actual, errors, pronunciation_score)
    
    def _build_prompt(
        self,
        expected: str,
        actual: str,
        errors: List[Dict],
        score: float
    ) -> str:
        """Constrói prompt para o LLM"""
        errors_text = self._format_errors(errors)
        
        prompt = f"""Você é um tutor de pronúncia de inglês para brasileiros. 
Analise o seguinte e responda APENAS com um JSON válido.

Frase esperada: "{expected}"
Frase falada pelo aluno: "{actual}"
Score de pronúncia: {score}/100
Erros detectados: {errors_text}

Responda EXATAMENTE neste formato JSON (sem texto adicional):
{{
  "correction": "✅ [uma frase apontando o erro principal]",
  "tip": "💡 [uma dica física/mecânica em português]",
  "exercise": "📝 [um exercício curto para praticar]"
}}

Regras:
- Responda SEMPRE em português do Brasil
- Máximo 150 caracteres por campo
- Seja encorajador
- Compare sons com o português quando possível
"""
        return prompt
    
    def _format_errors(self, errors: List[Dict]) -> str:
        """Formata erros para o prompt"""
        if not errors:
            return "Nenhum erro específico detectado"
        
        formatted = []
        for i, error in enumerate(errors[:5], 1):
            word = error.get("word", "")
            expected_w = error.get("expected", "")
            actual_w = error.get("actual", "")
            error_type = error.get("type", "unknown")
            
            if error_type == "missing":
                formatted.append(f"{i}. Palavra '{expected_w}' não foi falada")
            elif error_type == "extra":
                formatted.append(f"{i}. Palavra extra: '{actual_w}'")
            else:
                formatted.append(f"{i}. Falou '{actual_w}' em vez de '{expected_w}'")
        
        return "; ".join(formatted)
    
    def _parse_response(self, text: str) -> Dict[str, str]:
        """Tenta extrair JSON da resposta do LLM"""
        try:
            # Procura por JSON na resposta
            start = text.find('{')
            end = text.rfind('}') + 1
            
            if start >= 0 and end > start:
                json_str = text[start:end]
                result = json.loads(json_str)
                
                # Valida campos esperados
                return {
                    "correction": result.get("correction", ""),
                    "tip": result.get("tip", ""),
                    "exercise": result.get("exercise", ""),
                }
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Erro ao parsear resposta do LLM: {e}")
        
        # Se não conseguir parsear, usa o texto bruto
        return {
            "correction": text[:200] if text else "Análise não disponível",
            "tip": "Tente pronunciar mais claramente cada palavra.",
            "exercise": "Repita a frase lentamente, palavra por palavra.",
        }
    
    def _fallback_feedback(
        self,
        expected: str,
        actual: str,
        errors: List[Dict],
        score: float
    ) -> Dict[str, str]:
        """Feedback de fallback quando Ollama não está disponível"""
        
        if not actual or actual == "[Não foi possível transcrever]":
            return {
                "correction": "✅ Não foi possível detectar sua fala. Tente novamente.",
                "tip": "💡 Fale mais próximo ao microfone e articule bem as palavras.",
                "exercise": "📝 Ouça a pronúncia modelo e tente imitar."
            }
        
        if score >= 85:
            return {
                "correction": f"✅ Excelente! Sua pronúncia está muito boa ({score:.0f}/100).",
                "tip": "💡 Continue praticando para aperfeiçoar os detalhes.",
                "exercise": f"📝 Tente falar mais rápido mantendo a clareza: '{expected}'"
            }
        elif score >= 60:
            errors_list = [e.get("expected", "") for e in errors if e.get("type") == "wrong"]
            focus_words = ", ".join(errors_list[:3]) if errors_list else "algumas palavras"
            return {
                "correction": f"✅ Bom esforço! Preste atenção em: {focus_words}",
                "tip": "💡 Tente pronunciar cada sílaba separadamente antes de juntar.",
                "exercise": f"📝 Repita devagar: '{expected}' - 3 vezes."
            }
        else:
            return {
                "correction": f"✅ Continue tentando! Foque em pronunciar cada palavra claramente.",
                "tip": "💡 Não se preocupe com a velocidade. Clareza é mais importante que rapidez.",
                "exercise": f"📝 Pratique palavra por palavra: {expected}"
            }


# Instância global
tutor = Tutor()