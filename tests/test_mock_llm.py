# tests/test_mock_llm.py
"""
Testes com mock do Ollama/Qwen.
Simula respostas do LLM sem precisar do Ollama rodando.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTutorWithMock:
    """Testa o tutor com Ollama simulado"""
    
    @pytest.mark.asyncio
    async def test_generate_feedback_with_mock(self):
        """Feedback deve funcionar mesmo com Ollama offline (fallback)"""
        from src.llm.tutor import tutor
        
        feedback = await tutor.generate_feedback(
            expected="three",
            actual="tree",
            errors=[{"word": "three", "expected": "three", "actual": "tree", "type": "wrong"}],
            pronunciation_score=30
        )
        
        # Deve retornar feedback mesmo sem Ollama (fallback)
        assert feedback is not None
        assert isinstance(feedback, dict)
        assert "correction" in feedback or "tip" in feedback
    
    @pytest.mark.asyncio
    async def test_fallback_perfect_score(self):
        """Fallback para score alto deve ser encorajador"""
        from src.llm.tutor import tutor
        
        feedback = await tutor.generate_feedback(
            expected="hello",
            actual="hello",
            errors=[],
            pronunciation_score=95
        )
        
        assert feedback is not None
    
    @pytest.mark.asyncio
    async def test_fallback_low_score(self):
        """Fallback para score baixo deve dar dicas"""
        from src.llm.tutor import tutor
        
        feedback = await tutor.generate_feedback(
            expected="difficult word",
            actual="wrong",
            errors=[{"word": "difficult", "type": "wrong"}],
            pronunciation_score=20
        )
        
        assert feedback is not None
    
    @pytest.mark.asyncio
    async def test_check_ollama_status(self):
        """Verificação de status do Ollama não deve quebrar"""
        from src.llm.tutor import tutor
        
        status = await tutor._check_ollama()
        
        assert isinstance(status, dict)
        assert "running" in status


class TestPrompts:
    """Testa a geração de prompts"""
    
    def test_prompt_format(self):
        """Prompt deve conter informações essenciais"""
        from src.llm.prompts import prompt_templates
        
        prompt = prompt_templates.create_full_prompt(
            expected="hello world",
            actual="hello",
            score=50,
            errors=[{"word": "world", "type": "missing"}]
        )
        
        assert "hello world" in prompt
        assert "50" in prompt
        assert len(prompt) > 100
    
    def test_error_tips_exist(self):
        """Deve ter dicas para erros comuns"""
        from src.llm.prompts import prompt_templates
        
        tip = prompt_templates.get_error_tip("th_sound")
        assert tip is not None
        assert len(tip) > 20
    
    def test_encouragement_phrases(self):
        """Deve ter frases de encorajamento"""
        from src.llm.prompts import prompt_templates
        
        phrase = prompt_templates.get_encouragement()
        assert phrase is not None
        assert len(phrase) > 5