"""
Serviços web para enriquecer lições com dados reais.
Todas as APIs usadas são gratuitas (sem API key).
Fallback offline para cada serviço.
"""
import aiohttp
import logging
import random
from typing import Optional
from datetime import datetime

from ..models.live_data import (
    CountryInfo, WeatherInfo, CurrencyInfo,
    ProductInfo, FlightInfo, WikiArticle
)

logger = logging.getLogger(__name__)


class WebServices:
    """
    Cliente para APIs externas gratuitas.
    Cada método tem timeout curto e fallback offline.
    """
    
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=8)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session
    
    # ================================================================
    # CULTURA E GEOGRAFIA - REST Countries API (Grátis, sem key)
    # ================================================================
    
    async def get_country_info(self, country_name: str) -> CountryInfo:
        """
        Busca informações culturais de um país.
        API: https://restcountries.com (grátis, sem autenticação)
        """
        try:
            session = await self._get_session()
            url = f"https://restcountries.com/v3.1/name/{country_name}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = (await response.json())[0]
                    
                    cultural_tips = {
                        "United States": "In the US, tipping 15-20% is expected at restaurants.",
                        "Brazil": "In Brazil, a 10% service charge is usually included in the bill.",
                        "Japan": "In Japan, tipping is considered rude. Service is excellent by default.",
                        "France": "In France, service is included ('service compris') but leaving small change is appreciated.",
                        "Italy": "In Italy, 'coperto' (cover charge) is common, and tipping is optional.",
                        "United Kingdom": "In the UK, a 12.5% service charge is often added to the bill.",
                        "Germany": "In Germany, round up the bill by 5-10% as a tip.",
                        "Spain": "In Spain, leave small change or up to 5% for good service.",
                    }
                    
                    return CountryInfo(
                        name=data["name"]["common"],
                        capital=data.get("capital", ["Unknown"])[0],
                        region=data.get("region", "Unknown"),
                        population=data.get("population", 0),
                        languages=list(data.get("languages", {}).values()),
                        currencies=list(data.get("currencies", {}).keys()),
                        cultural_tip=cultural_tips.get(data["name"]["common"], ""),
                        flag_emoji=data.get("flag", "🏳️")
                    )
        except Exception as e:
            logger.warning(f"Falha ao buscar país '{country_name}': {e}")
        
        # Fallback offline
        return CountryInfo(
            name=country_name,
            capital="Unknown",
            region="Unknown",
            population=0,
            languages=["English"],
            currencies=["USD"],
            cultural_tip="In many countries, it's polite to learn basic phrases in the local language.",
            flag_emoji="🏳️"
        )
    
    # ================================================================
    # CLIMA - Open-Meteo API (Grátis, sem key)
    # ================================================================
    
    async def get_weather(self, city: str, lat: float = 40.7128, lon: float = -74.0060) -> WeatherInfo:
        """
        Busca clima atual de uma cidade.
        API: https://open-meteo.com (grátis, sem autenticação)
        """
        try:
            session = await self._get_session()
            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    current = data.get("current_weather", {})
                    
                    condition_map = {
                        0: ("Clear sky", "☀️"),
                        1: ("Mainly clear", "🌤️"),
                        2: ("Partly cloudy", "⛅"),
                        3: ("Overcast", "☁️"),
                        45: ("Foggy", "🌫️"),
                        51: ("Light drizzle", "🌦️"),
                        61: ("Rain", "🌧️"),
                        80: ("Rain showers", "⛈️"),
                    }
                    
                    code = current.get("weathercode", 0)
                    condition, icon = condition_map.get(code, ("Unknown", "🌤️"))
                    
                    return WeatherInfo(
                        city=city,
                        country="",
                        temperature_c=current.get("temperature", 20),
                        condition=condition,
                        humidity=0,
                        wind_speed_kmh=current.get("windspeed", 0),
                        description=f"It's {condition.lower()} and {current.get('temperature', 20)}°C in {city}.",
                        icon=icon
                    )
        except Exception as e:
            logger.warning(f"Falha ao buscar clima '{city}': {e}")
        
        # Fallback offline
        conditions = ["sunny", "cloudy", "rainy", "windy", "hot", "cold"]
        temps = [15, 20, 25, 30, 10, 5]
        return WeatherInfo(
            city=city,
            country="",
            temperature_c=random.choice(temps),
            condition=random.choice(conditions),
            humidity=60,
            wind_speed_kmh=10,
            description=f"The weather in {city} is typical for this time of year.",
            icon="🌤️"
        )
    
    # ================================================================
    # CONVERSÃO DE MOEDA - ExchangeRate API (Grátis, sem key)
    # ================================================================
    
    async def get_currency_rate(self, base: str = "USD", target: str = "BRL") -> CurrencyInfo:
        """
        Busca taxa de câmbio atual.
        API: https://open.er-api.com (grátis, sem autenticação)
        """
        try:
            session = await self._get_session()
            url = f"https://open.er-api.com/v6/latest/{base}"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    rate = data["rates"].get(target, 5.0)
                    
                    return CurrencyInfo(
                        base_currency=base,
                        target_currency=target,
                        rate=rate,
                        last_updated=data.get("time_last_update_utc", ""),
                        example_conversion=f"${100} = {target} {100 * rate:.2f}"
                    )
        except Exception as e:
            logger.warning(f"Falha ao buscar cotação {base}/{target}: {e}")
        
        # Fallback offline
        fallback_rates = {"BRL": 5.0, "EUR": 0.92, "GBP": 0.79, "JPY": 150.0, "CAD": 1.35}
        rate = fallback_rates.get(target, 1.0)
        
        return CurrencyInfo(
            base_currency=base,
            target_currency=target,
            rate=rate,
            last_updated=datetime.now().isoformat(),
            example_conversion=f"${100} = {target} {100 * rate:.2f}"
        )
    
    # ================================================================
    # IMAGENS - Picsum Photos (Grátis, placeholder)
    # ================================================================
    
    async def get_context_image(self, theme: str, width: int = 400, height: int = 300) -> str:
        """
        Retorna URL de imagem placeholder relacionada ao tema.
        API: https://picsum.photos (grátis, sem autenticação)
        """
        # Mapeia temas para seeds consistentes (mesma imagem para mesmo tema)
        seed_map = {
            "restaurant": 1, "airport": 2, "hotel": 3, "shopping": 4,
            "pharmacy": 5, "cafe": 6, "weather": 7, "animals": 8,
            "transport": 9, "clothes": 10
        }
        
        seed = seed_map.get(theme.lower(), random.randint(1, 100))
        return f"https://picsum.photos/seed/{theme.lower()}{seed}/{width}/{height}"
    
    # ================================================================
    # PRODUTOS - Fake Store API (Grátis, dados de exemplo)
    # ================================================================
    
    async def get_product_example(self, category: str = "clothing") -> ProductInfo:
        """
        Busca produto de exemplo para lições de compras.
        API: https://fakestoreapi.com (grátis, dados fictícios)
        """
        try:
            session = await self._get_session()
            
            # Mapeia categorias
            category_map = {
                "clothing": "men's clothing",
                "electronics": "electronics",
                "jewelry": "jewelery",
            }
            
            api_category = category_map.get(category, "men's clothing")
            url = f"https://fakestoreapi.com/products/category/{api_category}?limit=3"
            
            async with session.get(url) as response:
                if response.status == 200:
                    products = await response.json()
                    if products:
                        product = random.choice(products)
                        return ProductInfo(
                            name=product["title"],
                            price=product["price"],
                            currency="USD",
                            description=product["description"][:150],
                            image_url=product["image"],
                            category=product["category"]
                        )
        except Exception as e:
            logger.warning(f"Falha ao buscar produto '{category}': {e}")
        
        # Fallback offline
        products_fallback = {
            "clothing": ProductInfo(
                name="Classic Blue Shirt", price=29.99, currency="USD",
                description="A comfortable cotton shirt, perfect for casual and business wear.",
                image_url="https://picsum.photos/seed/shirt/400/400", category="clothing"
            ),
            "electronics": ProductInfo(
                name="Wireless Headphones", price=79.99, currency="USD",
                description="Noise-cancelling headphones with 30-hour battery life.",
                image_url="https://picsum.photos/seed/headphones/400/400", category="electronics"
            ),
        }
        return products_fallback.get(category, products_fallback["clothing"])
    
    # ================================================================
    # VOOS - AviationStack (dados de exemplo gratuitos)
    # ================================================================
    
    async def get_flight_info(self, flight_number: str = "") -> FlightInfo:
        """
        Gera informações de voo para simulações.
        Usa dados realistas como fallback (APIs de voo requerem key).
        """
        # Dados de exemplo realistas (principais rotas)
        sample_flights = [
            FlightInfo(
                flight_number="AA100", airline="American Airlines",
                origin="New York (JFK)", destination="London (LHR)",
                departure_time="08:00 AM", arrival_time="08:00 PM",
                gate="B12", terminal="8", status="On Time"
            ),
            FlightInfo(
                flight_number="UA200", airline="United Airlines",
                origin="Los Angeles (LAX)", destination="Tokyo (NRT)",
                departure_time="11:30 AM", arrival_time="3:00 PM (+1)",
                gate="G45", terminal="7", status="Boarding"
            ),
            FlightInfo(
                flight_number="DL300", airline="Delta Airlines",
                origin="Atlanta (ATL)", destination="Paris (CDG)",
                departure_time="05:15 PM", arrival_time="07:30 AM (+1)",
                gate="D22", terminal="5", status="On Time"
            ),
            FlightInfo(
                flight_number="LA400", airline="LATAM Airlines",
                origin="São Paulo (GRU)", destination="Miami (MIA)",
                departure_time="10:00 PM", arrival_time="05:00 AM (+1)",
                gate="C10", terminal="3", status="On Time"
            ),
        ]
        
        if flight_number:
            for flight in sample_flights:
                if flight.flight_number == flight_number:
                    return flight
        
        return random.choice(sample_flights)
    
    # ================================================================
    # WIKIBOOKS - Conteúdo educacional gratuito
    # ================================================================
    
    async def get_wiki_article(self, topic: str) -> WikiArticle:
        """
        Busca artigo educacional do Wikibooks.
        API: https://en.wikibooks.org (grátis, sem autenticação)
        """
        try:
            session = await self._get_session()
            url = f"https://en.wikibooks.org/w/api.php?action=query&list=search&srsearch={topic}&format=json&srlimit=1"
            
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get("query", {}).get("search", [])
                    
                    if results:
                        result = results[0]
                        return WikiArticle(
                            title=result["title"],
                            summary=result.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", ""),
                            url=f"https://en.wikibooks.org/wiki/{result['title'].replace(' ', '_')}",
                            key_terms=[topic],
                            difficulty_level="intermediate"
                        )
        except Exception as e:
            logger.warning(f"Falha ao buscar artigo '{topic}': {e}")
        
        # Fallback offline
        return WikiArticle(
            title=topic.capitalize(),
            summary=f"Learning about {topic} is an important part of your English journey. This topic includes key vocabulary and real-world applications.",
            url="",
            key_terms=[topic],
            difficulty_level="beginner"
        )
    
    # ================================================================
    # LIMPEZA
    # ================================================================
    
    async def close(self):
        """Fecha sessão HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()


# Instância global
web_services = WebServices()