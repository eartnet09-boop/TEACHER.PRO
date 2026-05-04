"""
Motor de melhorias online - modo híbrido.
Ativa recursos da internet quando disponível, 
mantém funcionamento offline quando não.
"""
from .web_services import WebServices
from .context_engine import ContextEngine

__all__ = ['WebServices', 'ContextEngine']