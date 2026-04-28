# download_models.py (VERSÃO CORRIGIDA)
"""
Download dos modelos disponíveis
"""
import os
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

def download_whisper():
    """Whisper será baixado automaticamente na primeira execução"""
    print("📥 Whisper tiny será baixado automaticamente na primeira transcrição")
    print("   Tamanho: ~150MB")

def download_wavlm():
    """Baixa WavLM Base Plus"""
    print("\n📥 Baixando WavLM Base Plus...")
    try:
        from transformers import WavLMModel, Wav2Vec2FeatureExtractor
        
        model_name = "microsoft/wavlm-base-plus"
        
        print("  - Baixando feature extractor...")
        feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(
            model_name,
            cache_dir="./models"
        )
        
        print("  - Baixando modelo...")
        model = WavLMModel.from_pretrained(
            model_name,
            cache_dir="./models"
        )
        
        print("✅ WavLM Base Plus baixado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def download_wav2vec2():
    """Baixa Wav2Vec2 para alinhamento"""
    print("\n📥 Baixando Wav2Vec2 para alinhamento...")
    try:
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
        
        model_name = "facebook/wav2vec2-base-960h"
        
        print("  - Baixando processor...")
        processor = Wav2Vec2Processor.from_pretrained(
            model_name,
            cache_dir="./models"
        )
        
        print("  - Baixando modelo...")
        model = Wav2Vec2ForCTC.from_pretrained(
            model_name,
            cache_dir="./models"
        )
        
        print("✅ Wav2Vec2 baixado com sucesso!")
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("DOWNLOAD DE MODELOS - ENGLISH TEACHER AGENT")
    print("=" * 50)
    print()
    
    download_whisper()
    download_wavlm()
    download_wav2vec2()
    
    print("\n" + "=" * 50)
    print("✅ DOWNLOADS CONCLUÍDOS!")
    print("=" * 50)
    print(f"\nModelos salvos em: {os.path.abspath('./models')}")