"""
Templates de prompts para o tutor IA (Qwen2.5-Coder)
Sistema de prompts estruturados para diferentes cenários de feedback
"""
from typing import Dict, List, Optional
from enum import Enum


class FeedbackType(Enum):
    """Tipos de feedback disponíveis"""
    CORRECTION = "correction"
    TIP = "tip"
    EXERCISE = "exercise"
    ENCOURAGEMENT = "encouragement"


class PromptTemplates:
    """
    Gerencia templates de prompts para o tutor de pronúncia.
    Cada template é otimizado para o Qwen2.5-Coder 3B,
    com restrições fortes de formato e idioma.
    """
    
    SYSTEM_PROMPT = """<<SYS>>
VOCÊ É UM TUTOR DE PRONÚNCIA DE INGLÊS PARA BRASILEIROS.
SUA FUNÇÃO É CORRIGIR E ENSINAR, NUNCA DESANIMAR.

REGRAS ABSOLUTAS (VIOLAÇÃO = FALHA):
1. Responda SOMENTE em português do Brasil
2. Use APENAS 3 frases curtas (máximo 150 caracteres por frase)
3. NUNCA repita o erro do aluno sem explicar
4. NUNCA use termos técnicos complexos (ex: "fricativa dental surda")
5. SEMPRE dê uma dica FÍSICA (posição da língua, lábios, etc.)
6. SEMPRE compare com sons do português brasileiro
7. Se o score for < 30: FOCO em UMA única correção principal
8. Se o score for > 70: FOCO em refinamento e fluência
9. JAMAIS minta sobre a pronúncia. Se o áudio não foi captado, diga.
10. Use EMOJIS: ✅ para acertos, 💡 para dicas, 📝 para exercícios

ESTRUTURA DE RESPOSTA (JSON):
{
  "correction": "✅ [O que foi identificado]",
  "tip": "💡 [Dica física + comparação com português]",
  "exercise": "📝 [Exercício prático rápido]"
}

EXEMPLOS DE REFERÊNCIA:

Exemplo 1 (som 'th'):
{
  "correction": "✅ Você falou 'tree' (árvore), o correto é 'three' (três). O som 'th' não existe em português.",
  "tip": "💡 Coloque a ponta da língua entre os dentes e assopre levemente. É como falar 'f' mas com a língua para fora.",
  "exercise": "📝 Repita: 'th-th-three'. Depois tente: 'I think three things'."
}

Exemplo 2 (som 'r' americano):
{
  "correction": "✅ O 'r' em 'car' não é como o 'r' de 'carro'. Você usou som de 'r' forte.",
  "tip": "💡 Enrole a língua para trás sem encostar no céu da boca. Parece o 'r' do sotaque caipira em 'porta'.",
  "exercise": "📝 Pratique: 'car... far... star...' alongando o som final."
}

Exemplo 3 (vogal longa vs curta):
{
  "correction": "✅ 'Ship' e 'sheep' têm sons diferentes. Você falou os dois iguais.",
  "tip": "💡 Para 'sheep', estique os lábios como um sorriso forçado. Para 'ship', relaxe os lábios. É como 'i' de 'vida' vs 'i' de 'pipa'.",
  "exercise": "📝 Repita: 'ship (curto) - sheep (longo)... hit - heat... bit - beat'."
}
<</SYS>>"""

    USER_PROMPT_TEMPLATE = """[INST]
ANÁLISE DO ALUNO:
- Frase esperada: "{expected}"
- O que o aluno falou: "{actual}"
- Score de pronúncia: {score}/100
- Principais erros detectados: {errors}

Forneça feedback estruturado em JSON seguindo as regras do sistema.
[/INST]"""

    USER_PROMPT_NO_SPEECH = """[INST]
O sistema não detectou fala na gravação do aluno.
Frase esperada: "{expected}"

Forneça feedback encorajador para tentar novamente, em JSON.
[/INST]"""

    USER_PROMPT_PERFECT = """[INST]
ANÁLISE DO ALUNO:
- Frase esperada: "{expected}"
- O que o aluno falou: "{actual}"
- Score de pronúncia: {score}/100 (PRONÚNCIA EXCELENTE!)

Forneça feedback de reconhecimento e dê uma nova frase desafio, em JSON.
[/INST]"""

    def __init__(self):
        """Inicializa templates de prompts"""
        self.templates = {
            "default": self.USER_PROMPT_TEMPLATE,
            "no_speech": self.USER_PROMPT_NO_SPEECH,
            "perfect": self.USER_PROMPT_PERFECT,
        }
        
        # Frases de reforço positivo para intercalar
        self.encouragement_phrases = [
            "Você está melhorando a cada tentativa! 🌟",
            "Errar faz parte do aprendizado. Continue! 💪",
            "Muito bem por tentar! Vamos refinar mais um pouco. 🎯",
            "Sua dedicação é incrível! Pequenos ajustes farão diferença. ✨",
        ]
        
        # Dicas por tipo de erro comum
        self.common_errors_tips = {
            "th_sound": "Coloque a língua entre os dentes e assopre. O som 'th' (como em 'think') não existe em português, mas parece um 'f' com a língua para fora.",
            "r_sound": "Para o 'r' americano, enrole a língua para trás sem tocar no céu da boca. Não é como o 'r' forte do português.",
            "ed_ending": "O final '-ed' tem 3 sons: /t/ (walked), /d/ (played), /ɪd/ (wanted). Não é 'édi', é um som bem curto.",
            "short_long_vowels": "Vogais curtas (ship, bit) vs longas (sheep, beat). Nas longas, alongue o som como se tivesse dois pontos (shi:p).",
            "dark_l": "O 'L' no final (well, call) é diferente. A parte de trás da língua sobe. Não solte a língua no final.",
        }
    
    def get_system_prompt(self) -> str:
        """Retorna o prompt de sistema base"""
        return self.SYSTEM_PROMPT
    
    def get_user_prompt(
        self,
        expected: str,
        actual: str,
        score: float,
        errors: List[Dict],
        feedback_type: str = "default"
    ) -> str:
        """
        Monta prompt do usuário baseado no cenário
        
        Args:
            expected: Texto esperado
            actual: Texto transcrito (com erros preservados)
            score: Score de pronúncia (0-100)
            errors: Lista de erros detectados
            feedback_type: Tipo de template a usar
            
        Returns:
            Prompt formatado para o modelo
        """
        # Seleciona template
        if feedback_type == "no_speech" or actual == "[Não foi possível transcrever]":
            template = self.templates["no_speech"]
        elif score >= 95:
            template = self.templates["perfect"]
        else:
            template = self.templates["default"]
        
        # Formata erros
        if errors:
            errors_str = self._format_errors(errors)
        else:
            errors_str = "Nenhum erro específico detectado"
        
        # Preenche template
        prompt = template.format(
            expected=expected,
            actual=actual,
            score=int(score),
            errors=errors_str
        )
        
        return prompt
    
    def _format_errors(self, errors: List[Dict]) -> str:
        """Formata lista de erros para o prompt"""
        if not errors:
            return "Nenhum erro específico detectado"
        
        formatted = []
        for i, error in enumerate(errors[:5], 1):  # Máximo 5 erros
            word = error.get("word", "")
            expected = error.get("expected", "")
            actual = error.get("actual", "")
            error_type = error.get("type", "pronunciation")
            
            if error_type == "missing":
                formatted.append(f"{i}. PALAVRA FALTANDO: '{expected}' não foi falada")
            elif error_type == "extra":
                formatted.append(f"{i}. PALAVRA EXTRA: '{actual}' foi adicionada")
            elif error_type == "wrong":
                formatted.append(f"{i}. TROCA: falou '{actual}' em vez de '{expected}'")
            else:
                formatted.append(f"{i}. '{word}': esperado '{expected}', falado '{actual}'")
        
        return "\n".join(formatted) if formatted else "Erros não especificados"
    
    def get_error_tip(self, error_type: str) -> Optional[str]:
        """Retorna dica específica para tipo de erro"""
        return self.common_errors_tips.get(error_type)
    
    def get_encouragement(self) -> str:
        """Retorna frase de encorajamento aleatória"""
        import random
        return random.choice(self.encouragement_phrases)
    
    def create_full_prompt(
        self,
        expected: str,
        actual: str,
        score: float,
        errors: List[Dict],
        include_encouragement: bool = False
    ) -> str:
        """
        Cria prompt completo (sistema + usuário)
        
        Returns:
            String completa para enviar ao modelo
        """
        system = self.get_system_prompt()
        user = self.get_user_prompt(expected, actual, score, errors)
        
        if include_encouragement and score > 0:
            encouragement = f"\n\n[Nota: {self.get_encouragement()}]"
            user += encouragement
        
        return system + "\n\n" + user


# Instância global
prompt_templates = PromptTemplates()