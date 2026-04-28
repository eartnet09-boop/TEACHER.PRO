# src/main.py
"""
English Teacher Agent - Entrypoint Principal
Inicia o servidor FastAPI com todas as verificações necessárias
"""
import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# ============================================================
# CONFIGURAÇÃO INICIAL
# ============================================================

# Adiciona diretório raiz ao PYTHONPATH
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Configura logging básico até carregar configurações
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================
# FUNÇÕES DE VERIFICAÇÃO
# ============================================================

def print_banner():
    """Exibe banner do sistema"""
    banner = """
    ╔══════════════════════════════════════════════════════╗
    ║            🎧 ENGLISH TEACHER AGENT v3.0            ║
    ║         Professor de Inglês por IA - Offline        ║
    ╚══════════════════════════════════════════════════════╝
    """
    print(banner)


def check_python_version():
    """Verifica versão do Python"""
    required = (3, 10)
    current = sys.version_info[:2]
    
    if current < required:
        logger.error(f"Python {required[0]}.{required[1]} ou superior necessário")
        logger.error(f"Versão atual: {current[0]}.{current[1]}")
        sys.exit(1)
    
    logger.info(f"✅ Python {current[0]}.{current[1]}")


def check_directories():
    """Verifica e cria diretórios necessários"""
    from src.config import TEMP_DIR, MODELS_DIR, STATIC_DIR
    
    directories = {
        "TEMP_DIR": TEMP_DIR,
        "MODELS_DIR": MODELS_DIR,
        "STATIC_DIR": STATIC_DIR,
    }
    
    for name, dir_path in directories.items():
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ {name}: {dir_path}")
        except Exception as e:
            logger.error(f"❌ Erro ao criar {name}: {e}")
            sys.exit(1)


def check_ffmpeg():
    """Verifica se FFmpeg está instalado"""
    import subprocess
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            logger.info(f"✅ FFmpeg: {version_line[:60]}...")
            return True
    except FileNotFoundError:
        logger.error("❌ FFmpeg não encontrado!")
        logger.error("   Instale com: winget install ffmpeg")
        logger.error("   Ou: https://ffmpeg.org/download.html")
        return False
    except Exception as e:
        logger.warning(f"⚠️ FFmpeg: {e}")
        return False


def check_ollama():
    """Verifica conexão com Ollama"""
    import aiohttp
    
    async def _check():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://localhost:11434/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [m["name"] for m in data.get("models", [])]
                        logger.info(f"✅ Ollama: {len(models)} modelo(s) disponível(is)")
                        for model in models[:3]:
                            logger.info(f"   - {model}")
                        return True
        except aiohttp.ClientError:
            logger.warning("⚠️ Ollama não está rodando!")
            logger.warning("   Inicie com: ollama serve")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Ollama: {e}")
            return False
    
    loop = asyncio.new_event_loop()
    result = loop.run_until_complete(_check())
    loop.close()
    return result


def check_models():
    """Verifica se modelos estão disponíveis"""
    from src.config import MODELS_DIR
    
    models_path = Path(MODELS_DIR)
    if not models_path.exists():
        logger.warning("⚠️ Diretório de modelos não encontrado")
        return
    
    # Lista modelos baixados
    model_dirs = list(models_path.glob("models--*"))
    
    if model_dirs:
        logger.info(f"✅ Modelos encontrados: {len(model_dirs)}")
        for m in model_dirs:
            logger.info(f"   - {m.name}")
    else:
        logger.warning("⚠️ Nenhum modelo encontrado em models/")
        logger.warning("   Execute: python download_models.py")


def check_gpu():
    """Verifica disponibilidade de GPU"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            logger.info(f"✅ GPU: {gpu_name} ({gpu_mem:.1f} GB)")
        else:
            logger.info("ℹ️  GPU não disponível - usando CPU")
    except ImportError:
        logger.info("ℹ️  PyTorch não instalado - usando CPU")


# ============================================================
# VERIFICAÇÕES DE IMPORTAÇÃO
# ============================================================

def check_imports():
    """Verifica se todos os módulos podem ser importados"""
    modules = [
        ("config", "src.config"),
        ("audio.processor", "src.audio.processor"),
        ("audio.recorder", "src.audio.recorder"),
        ("transcription.chall_model", "src.transcription.chall_model"),
        ("pronunciation.wavlm_analyzer", "src.pronunciation.wavlm_analyzer"),
        ("pronunciation.scorer", "src.pronunciation.scorer"),
        ("pronunciation.aligner", "src.pronunciation.aligner"),
        ("llm.tutor", "src.llm.tutor"),
        ("llm.prompts", "src.llm.prompts"),
        ("tts.speaker", "src.tts.speaker"),
        ("web.session_manager", "src.web.session_manager"),
        ("web.app", "src.web.app"),
    ]
    
    failed = []
    
    for name, module_path in modules:
        try:
            __import__(module_path)
            logger.debug(f"✅ {name}")
        except Exception as e:
            logger.error(f"❌ {name}: {e}")
            failed.append((name, str(e)))
    
    if failed:
        logger.error(f"\n{'='*50}")
        logger.error(f"FALHA EM {len(failed)} MÓDULO(S):")
        for name, error in failed:
            logger.error(f"  - {name}: {error}")
        logger.error(f"{'='*50}")
        return False
    
    logger.info(f"✅ Todos os {len(modules)} módulos importados")
    return True


# ============================================================
# PRÉ-CARREGAMENTO DE MODELOS (OPCIONAL)
# ============================================================

def preload_models():
    """Pré-carrega modelos para primeira execução mais rápida"""
    preload = os.getenv("PRELOAD_MODELS", "false").lower() == "true"
    
    if not preload:
        logger.info("ℹ️  Pré-carregamento desativado (configure PRELOAD_MODELS=true no .env)")
        return
    
    logger.info("🔄 Pré-carregando modelos...")
    
    try:
        # Whisper
        logger.info("   Carregando Whisper tiny...")
        import whisper
        model = whisper.load_model("tiny", download_root="./models")
        logger.info("   ✅ Whisper carregado")
    except Exception as e:
        logger.warning(f"   ⚠️ Whisper: {e}")
    
    try:
        # WavLM
        logger.info("   Carregando WavLM...")
        from transformers import WavLMModel
        model = WavLMModel.from_pretrained("microsoft/wavlm-base-plus", cache_dir="./models")
        logger.info("   ✅ WavLM carregado")
    except Exception as e:
        logger.warning(f"   ⚠️ WavLM: {e}")


# ============================================================
# INICIALIZAÇÃO DO SERVIDOR
# ============================================================

def start_server():
    """Inicia o servidor Uvicorn"""
    from src.config import SERVER_CONFIG
    import uvicorn
    
    host = SERVER_CONFIG["host"]
    port = SERVER_CONFIG["port"]
    
    print(f"""
    ╔══════════════════════════════════════════════════════╗
    ║  🚀 SERVIDOR INICIADO                              ║
    ╠══════════════════════════════════════════════════════╣
    ║  🌐 Interface: http://{host}:{port}                  ║
    ║  ❤️  Health:   http://{host}:{port}/api/health         ║
    ║  📊 API Docs: http://{host}:{port}/docs               ║
    ╠══════════════════════════════════════════════════════╣
    ║  Pressione Ctrl+C para parar                       ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    try:
        uvicorn.run(
            "src.web.app:app",
            host=host,
            port=port,
            reload=False,
            log_level="info",
            access_log=True,
            timeout_keep_alive=30,
        )
    except KeyboardInterrupt:
        print("\n\n👋 Servidor parado. Até logo!")
    except Exception as e:
        logger.error(f"❌ Erro fatal no servidor: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# ============================================================
# MÓDULO DE TESTE RÁPIDO
# ============================================================

def run_diagnostics():
    """Executa diagnóstico completo do sistema"""
    print("\n" + "=" * 60)
    print("🔍 DIAGNÓSTICO DO SISTEMA")
    print("=" * 60 + "\n")
    
    print("📋 VERIFICAÇÕES BÁSICAS:")
    check_python_version()
    check_directories()
    
    print("\n🔧 FERRAMENTAS EXTERNAS:")
    check_ffmpeg()
    check_ollama()
    check_gpu()
    
    print("\n📦 MODELOS:")
    check_models()
    
    print("\n📚 MÓDULOS:")
    all_ok = check_imports()
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ DIAGNÓSTICO CONCLUÍDO - SISTEMA PRONTO!")
    else:
        print("⚠️  DIAGNÓSTICO CONCLUÍDO - HÁ PROBLEMAS A RESOLVER")
    print("=" * 60 + "\n")


# ============================================================
# ENTRYPOINT
# ============================================================

def main():
    """Função principal"""
    # Banner
    print_banner()
    
    # Argumentos de linha de comando
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "diagnose":
            run_diagnostics()
            return
        
        elif command == "check":
            print("🔍 Verificação rápida do sistema...\n")
            check_python_version()
            check_ffmpeg()
            check_ollama()
            check_imports()
            print("\n✅ Verificação concluída!")
            return
        
        elif command == "preload":
            print("🔄 Pré-carregando modelos...")
            preload_models()
            print("✅ Pré-carregamento concluído!")
            return
        
        elif command in ["help", "--help", "-h"]:
            print("""
            Uso: python -m src.main [comando]
            
            Comandos:
              (sem args)  Inicia o servidor
              diagnose    Executa diagnóstico completo
              check       Verificação rápida
              preload     Pré-carrega modelos
              help        Esta mensagem
            """)
            return
    
    # Inicia servidor (comportamento padrão)
    print("🔍 Verificando sistema...\n")
    
    # Verificações essenciais
    check_python_version()
    check_directories()
    
    # Verificações não-bloqueantes
    check_ffmpeg()
    check_ollama()
    check_models()
    
    print()
    
    # Inicia servidor
    start_server()


if __name__ == "__main__":
    main()