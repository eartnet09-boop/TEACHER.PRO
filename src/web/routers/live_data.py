"""
Endpoints para dados online em tempo real.
Modo híbrido: funciona com internet, tem fallback offline.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ...enhancements.context_engine import context_engine
from ...enhancements.web_services import web_services

router = APIRouter(prefix="/api/live", tags=["Live Data"])


@router.get("/context")
async def get_live_context(
    theme: str = Query(..., description="Tema da lição"),
    country: str = Query("United States", description="País para contexto"),
    city: str = Query("New York", description="Cidade para clima"),
    flight_number: str = Query("", description="Número do voo"),
    product_category: str = Query("clothing", description="Categoria do produto"),
    wiki_topic: str = Query("", description="Tópico para artigo")
):
    """
    Constrói contexto enriquecido com dados online.
    Busca automaticamente informações relevantes baseadas no tema.
    """
    context = await context_engine.build_context(
        theme=theme,
        country=country,
        city=city,
        flight_number=flight_number,
        product_category=product_category,
        wiki_topic=wiki_topic
    )
    
    return JSONResponse({
        "success": True,
        "context": context.model_dump()
    })


@router.get("/weather")
async def get_weather(
    city: str = Query("New York", description="Nome da cidade"),
    lat: float = Query(40.7128, description="Latitude"),
    lon: float = Query(-74.0060, description="Longitude")
):
    """Busca clima atual de uma cidade"""
    weather = await web_services.get_weather(city, lat, lon)
    
    return JSONResponse({
        "success": True,
        "weather": weather.model_dump()
    })


@router.get("/country")
async def get_country(
    name: str = Query("United States", description="Nome do país em inglês")
):
    """Busca informações culturais de um país"""
    country = await web_services.get_country_info(name)
    
    return JSONResponse({
        "success": True,
        "country": country.model_dump()
    })


@router.get("/currency")
async def get_currency(
    base: str = Query("USD", description="Moeda base"),
    target: str = Query("BRL", description="Moeda alvo")
):
    """Busca taxa de câmbio atual"""
    currency = await web_services.get_currency_rate(base, target)
    
    return JSONResponse({
        "success": True,
        "currency": currency.model_dump()
    })


@router.get("/flight")
async def get_flight(
    flight_number: str = Query("", description="Número do voo (ex: AA100)")
):
    """Busca informações de voo para simulação"""
    flight = await web_services.get_flight_info(flight_number)
    
    return JSONResponse({
        "success": True,
        "flight": flight.model_dump()
    })


@router.get("/product")
async def get_product(
    category: str = Query("clothing", description="Categoria do produto")
):
    """Busca produto de exemplo para lições de compras"""
    product = await web_services.get_product_example(category)
    
    return JSONResponse({
        "success": True,
        "product": product.model_dump()
    })


@router.get("/wiki")
async def get_wiki(
    topic: str = Query(..., description="Tópico para busca")
):
    """Busca artigo educacional do Wikibooks"""
    article = await web_services.get_wiki_article(topic)
    
    return JSONResponse({
        "success": True,
        "article": article.model_dump()
    })


@router.get("/image")
async def get_image(
    theme: str = Query("restaurant", description="Tema para imagem")
):
    """Retorna URL de imagem contextual"""
    image_url = await context_engine.get_image_for_theme(theme)
    
    return JSONResponse({
        "success": True,
        "image_url": image_url,
        "theme": theme
    })


@router.get("/status")
async def live_status():
    """Verifica disponibilidade dos serviços online"""
    import aiohttp
    
    services = {
        "restcountries": False,
        "open_meteo": False,
        "exchange_rate": False,
        "fakestore": False,
        "wikibooks": False,
        "picsum": False,
    }
    

@router.get("/time")
async def get_world_time(timezone: str = Query("America/New_York")):
    """Busca hora atual em qualquer fuso horário"""
    result = await web_services.get_world_time(timezone)
    return JSONResponse({"success": True, **result})


@router.get("/number-fact")
async def get_number_fact(number: int = Query(7, ge=0, le=9999)):
    """Busca curiosidade sobre um número"""
    result = await web_services.get_number_fact(number)
    return JSONResponse(result)


@router.get("/radio-stations")
async def get_radio_stations(country: str = Query("united states", description="País em inglês")):
    """Busca estações de rádio de um país"""
    stations = await web_services.get_radio_stations(country)
    return JSONResponse({"success": True, "stations": stations, "country": country})

    try:
        async with aiohttp.ClientSession() as session:
            # Testa REST Countries
            try:
                async with session.get("https://restcountries.com/v3.1/name/usa", timeout=aiohttp.ClientTimeout(total=3)) as r:
                    services["restcountries"] = r.status == 200
            except:
                pass
            
            # Testa Open-Meteo
            try:
                async with session.get("https://api.open-meteo.com/v1/forecast?latitude=40.71&longitude=-74.00&current_weather=true", timeout=aiohttp.ClientTimeout(total=3)) as r:
                    services["open_meteo"] = r.status == 200
            except:
                pass
            
            # Testa ExchangeRate
            try:
                async with session.get("https://open.er-api.com/v6/latest/USD", timeout=aiohttp.ClientTimeout(total=3)) as r:
                    services["exchange_rate"] = r.status == 200
            except:
                pass
            
            # Testa FakeStore
            try:
                async with session.get("https://fakestoreapi.com/products?limit=1", timeout=aiohttp.ClientTimeout(total=3)) as r:
                    services["fakestore"] = r.status == 200
            except:
                pass
            
            # Testa Wikibooks
            try:
                async with session.get("https://en.wikibooks.org/w/api.php?action=query&list=search&srsearch=English&format=json", timeout=aiohttp.ClientTimeout(total=3)) as r:
                    services["wikibooks"] = r.status == 200
            except:
                pass
            
            # Testa Picsum
            try:
                async with session.get("https://picsum.photos/10/10", timeout=aiohttp.ClientTimeout(total=3)) as r:
                    services["picsum"] = r.status == 200
            except:
                pass
    except:
        pass
    
    online_count = sum(1 for v in services.values() if v)
    
    return JSONResponse({
        "success": True,
        "services": services,
        "online_count": online_count,
        "total_services": len(services),
        "mode": "hybrid" if online_count > 0 else "offline"
    })