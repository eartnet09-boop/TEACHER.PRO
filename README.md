# 🎧 English Teacher Agent

**Professor de Inglês por IA - 100% Offline e Privado**

![Version](https://img.shields.io/badge/version-3.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-orange)
![Status](https://img.shields.io/badge/status-stable-brightgreen)

---

## 📖 Sobre

O **English Teacher Agent** é um tutor de pronúncia de inglês que utiliza inteligência artificial para avaliar e corrigir a pronúncia de alunos brasileiros. Totalmente offline, preserva sua privacidade e funciona sem internet.

### ✨ Funcionalidades

- 🎤 **Gravação de áudio** diretamente no navegador
- 📝 **Transcrição que preserva erros** (não auto-corrige)
- 🔊 **Análise fonética** palavra por palavra
- 🤖 **Feedback personalizado** via IA local (Ollama + Qwen)
- 📊 **Scores detalhados** por palavra e geral
- 🎯 **Dicas físicas** de pronúncia (posição da língua, lábios)
- 📚 **Exercícios práticos** baseados nos erros
- 🔒 **100% offline** - seus dados nunca saem do seu computador

---

## 🏗️ Arquitetura
Usuário → [Browser] → [FastAPI] → [Pipeline de IA]
├── Whisper (Transcrição)
├── WavLM (Análise Fonética)
├── Wav2Vec2 (Alinhamento)
└── Qwen 2.5 (Feedback)
 
 
### Tecnologias

| Componente | Tecnologia | Função |
|-----------|-----------|--------|
| **Backend** | FastAPI + Uvicorn | Servidor web |
| **Transcrição** | OpenAI Whisper tiny | Preserva erros |
| **Análise Fonética** | Microsoft WavLM | Embeddings de áudio |
| **Alinhamento** | Facebook Wav2Vec2 | Timestamps |
| **Tutor IA** | Qwen 2.5 Coder 3B | Feedback em português |
| **TTS** | Edge TTS | Áudio de referência |
| **Áudio** | librosa + noisereduce | Processamento |

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.11+
- FFmpeg
- Ollama
- Git (opcional)

### Passo a Passo

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/english-teacher-agent.git
cd english-teacher-agent

# 2. Crie o ambiente virtual
python -m venv venv

# 3. Ative o ambiente
# Windows:
venv\Scripts\Activate.ps1
# Linux/Mac:
source venv/bin/activate

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Instale o Whisper
pip install openai-whisper

# 6. Configure as variáveis de ambiente
cp .env.example .env

# 7. Baixe os modelos
python download_models.py

# 8. Inicie o Ollama (em outro terminal)
ollama serve

# 9. Baixe o modelo Qwen
ollama pull qwen2.5-coder:3b

# 10. Execute o diagnóstico
python -m src.main diagnose

# 11. Inicie o servidor
python -m src.main
Acesse: http://localhost:8000

📊 Diagnóstico
bash
# Verificação rápida
python -m src.main check

# Diagnóstico completo
python -m src.main diagnose

# Pré-carregar modelos
python -m src.main preload
🎯 Como Usar
Abra http://localhost:8000

Clique em "Gravar" e leia a frase exibida

Aguarde o processamento (3-5 segundos)

Veja seu score e feedback personalizado

Siga as dicas e pratique com os exercícios

Clique em "Ouvir" para escutar a pronúncia correta

Use "Próxima" para avançar para outra frase

📁 Estrutura do Projeto
text
english-teacher-agent/
├── src/
│   ├── web/                    # Interface e servidor
│   │   ├── app.py              # FastAPI
│   │   ├── session_manager.py  # Sessões
│   │   └── static/
│   │       └── index.html      # Frontend
│   ├── audio/                  # Processamento de áudio
│   │   ├── processor.py        # Pipeline profissional
│   │   └── recorder.py         # Gravação
│   ├── transcription/          # Transcrição
│   │   └── chall_model.py      # Whisper
│   ├── pronunciation/          # Análise
│   │   ├── wavlm_analyzer.py   # WavLM
│   │   ├── scorer.py           # Pontuação
│   │   └── aligner.py          # Alinhamento
│   ├── llm/                    # Tutor IA
│   │   ├── tutor.py            # Ollama
│   │   └── prompts.py          # Templates
│   ├── tts/                    # Síntese de voz
│   │   └── speaker.py          # Edge TTS
│   ├── config.py               # Configurações
│   └── main.py                 # Entrypoint
├── requirements.txt            # Dependências
├── download_models.py          # Download de modelos
├── .env.example                # Template de config
├── .gitignore                  # Arquivos ignorados
└── README.md                   # Documentação
🔧 Comandos Úteis
bash
# Servidor
python -m src.main              # Iniciar
python -m src.main diagnose     # Diagnosticar
python -m src.main check        # Verificar

# Direto com uvicorn
uvicorn src.web.app:app --reload --port 8000

# Ollama
ollama list                     # Modelos instalados
ollama pull qwen2.5-coder:3b   # Baixar modelo
ollama serve                    # Iniciar servidor

# Modelos
python download_models.py       # Baixar modelos
🐛 Solução de Problemas
Problema	Solução
ModuleNotFoundError	Ative o venv: venv\Scripts\Activate.ps1
Ollama não conecta	Execute ollama serve em outro terminal
FFmpeg não encontrado	winget install ffmpeg
Porta 8000 em uso	Altere a porta no .env
Score muito baixo	Fale mais próximo ao microfone
Erro no PyTorch	pip install torch --index-url https://download.pytorch.org/whl/cpu
🤝 Contribuindo
Contribuições são bem-vindas! Siga os passos:

Fork o projeto

Crie uma branch (git checkout -b feature/nova-funcionalidade)

Commit suas mudanças (git commit -m 'Adiciona funcionalidade X')

Push para a branch (git push origin feature/nova-funcionalidade)

Abra um Pull Request

📄 Licença
Este projeto está sob a licença MIT. Veja o arquivo LICENSE para mais detalhes.

🙏 Agradecimentos
OpenAI Whisper

Microsoft WavLM

Meta Wav2Vec2

Alibaba Qwen

Ollama