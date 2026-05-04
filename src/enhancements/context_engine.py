"""
Motor de Contexto Inteligente.
Analisa o tema da lição e busca dados relevantes da internet
para enriquecer a experiência do aluno.
"""
import logging
from typing import Optional

from .web_services import WebServices, web_services
from ..models.live_data import LiveContext

logger = logging.getLogger(__name__)


class ContextEngine:
    """
    Orquestrador que decide quais dados online buscar
    baseado no tema da lição ou diálogo.
    """
    
    def __init__(self):
        self.services: WebServices = web_services
        
        # Mapeamento: tema → dados relevantes
        self.theme_mapping = {
            "restaurant": ["country", "currency", "image"],
            "restaurante": ["country", "currency", "image"],
            "airport": ["flight", "country", "weather", "image"],
            "aeroporto": ["flight", "country", "weather", "image"],
            "hotel": ["country", "weather", "image"],
            "shopping": ["product", "currency", "image"],
            "compras": ["product", "currency", "image"],
            "weather": ["weather", "image"],
            "clima": ["weather", "image"],
            "transport": ["weather", "image"],
            "transporte": ["weather", "image"],
            "pharmacy": ["image"],
            "farmacia": ["image"],
            "job interview": ["wiki", "image"],
            "professions": ["wiki", "image"],
            "casual conversation": ["country", "weather", "image"],
        }
    
    async def build_context(
        self,
        theme: str,
        country: str = "United States",
        city: str = "New York",
        flight_number: str = "",
        product_category: str = "clothing",
        wiki_topic: str = ""
    ) -> LiveContext:
        """
        Constrói um contexto enriquecido baseado no tema.
        Busca dados online automaticamente.
        
        Args:
            theme: Tema da lição
            country: País para contexto cultural
            city: Cidade para clima
            flight_number: Número de voo (aeroporto)
            product_category: Categoria de produto (compras)
            wiki_topic: Tópico para artigo educacional
            
        Returns:
            LiveContext com todos os dados relevantes
        """
        theme_lower = theme.lower()
        services_to_call = self.theme_mapping.get(theme_lower, ["country", "image"])
        
        context = LiveContext(theme=theme)
        prompts = []
        
        # Busca informações do país
        if "country" in services_to_call:
            country_info = await self.services.get_country_info(country)
            context.country_info = country_info
            
            if country_info.cultural_tip:
                prompts.append(f"Cultural context: {country_info.cultural_tip}")
            prompts.append(
                f"The student is learning about {country_info.name}. "
                f"Capital: {country_info.capital}. Languages: {', '.join(country_info.languages[:3])}."
            )
        
        # Busca clima
        if "weather" in services_to_call:
            weather = await self.services.get_weather(city)
            context.weather_info = weather
            prompts.append(
                f"Current weather in {city}: {weather.condition}, {weather.temperature_c}°C."
            )
        
        # Busca cotação
        if "currency" in services_to_call:
            currency = await self.services.get_currency_rate("USD", "BRL")
            context.currency_info = currency
            prompts.append(
                f"Exchange rate: {currency.example_conversion}. "
                f"This helps the student understand real prices."
            )
        
        # Busca voo
        if "flight" in services_to_call:
            flight = await self.services.get_flight_info(flight_number)
            context.flight_info = flight
            prompts.append(
                f"Flight {flight.flight_number}: {flight.origin} → {flight.destination}. "
                f"Gate {flight.gate}, {flight.status}. "
                f"Use these details naturally in the conversation."
            )
        
        # Busca produto
        if "product" in services_to_call:
            product = await self.services.get_product_example(product_category)
            context.product_info = product
            prompts.append(
                f"Product: {product.name} - ${product.price}. "
                f"Description: {product.description}. "
                f"Use this product as an example in the shopping conversation."
            )
        
        # Busca artigo educacional
        if "wiki" in services_to_call and wiki_topic:
            article = await self.services.get_wiki_article(wiki_topic)
            context.wiki_article = article
            prompts.append(
                f"Educational content about {article.title}: {article.summary[:200]}. "
                f"Use this to create a mini-lesson or quiz."
            )
        
        # Monta prompt contextual
        context.contextual_prompt = "\n".join(prompts) if prompts else ""
        
    
                     # Conta quantas fontes de dados foram obtidas
        data_sources = [
            context.country_info,
            context.weather_info,
            context.currency_info,
            context.product_info,
            context.flight_info,
            context.wiki_article
        ]
        active_sources = sum(1 for x in data_sources if x is not None)
        
        logger.info(
            f"Contexto construido para '{theme}': "
            f"{active_sources} fontes de dados"
        )
        
        return context
    
    async def get_image_for_theme(self, theme: str) -> str:
        """Retorna URL de imagem para o tema"""
        return await self.services.get_context_image(theme)
    
    async def close(self):
        """Fecha serviços"""
        await self.services.close()


# Instância global
context_engine = ContextEngine()