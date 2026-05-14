# 🎧 TEACHER.PRO v4.2

**Tutor de Inglês com Inteligência Artificial — 100% Offline e Privado**

![Version](https://img.shields.io/badge/version-4.2.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![Status](https://img.shields.io/badge/status-stable-brightgreen)
![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)
![AI Models](https://img.shields.io/badge/AI%20Models-4-orange)
![Tests](https://img.shields.io/badge/tests-47%20passing-success)

---

## 📖 Sobre

O **TEACHER.PRO** é um tutor de inglês completo que utiliza **4 modelos de inteligência artificial** rodando 100% no seu computador. Diferente de aplicativos como Duolingo ou ELSA Speak, ele funciona **totalmente offline** — seus dados de voz, progresso e conversas nunca saem do seu dispositivo.

Ideal para brasileiros que querem praticar pronúncia, vocabulário e conversação com feedback personalizado e privacidade total.

### ✨ Funcionalidades Principais

| Modo | Descrição |
|:---|:---|
| 📖 **Vocabulário** | 320+ palavras em 13 categorias com pronúncia, tradução e scoring |
| 🗣️ **Diálogos com IA** | Conversas realistas com personagens (garçom, recepcionista, médico) |
| 💬 **Conversa Livre** | Chat aberto com tutor IA sobre qualquer tema |
| 🔢 **Números** | Cardinais, ordinais, horas, preços e medidas |
| 🎤 **Pronúncia** | Frases completas com análise fonética detalhada |
| 📻 **Rádio em Inglês** | Estações ao vivo dos EUA/UK para imersão auditiva |

### 🧠 Motores de IA Integrados

| Modelo | Criador | Função |
|:---|:---|:---|
| **Whisper Tiny** | OpenAI | Transcrição de fala (preserva erros do aluno) |
| **WavLM Base Plus** | Microsoft | Análise fonética por embedding acústico |
| **Qwen 2.5 Coder 3B** | Alibaba | Tutor IA generativa para diálogos e feedback |
| **Wav2Vec2 Base** | Meta | Alinhamento temporal de áudio |

---

## 🏗️ Arquitetura
Usuário (Navegador) → [FastAPI] → Pipeline de IA → Feedback
│
┌───────────────────┼───────────────────┐
▼ ▼ ▼
🎤 Whisper 🔊 WavLM 🤖 Qwen 2.5
Transcrição Análise Fonética Tutor IA
│ │ │
└───────────────────┼───────────────────┘
▼
📊 SQLite + Gamificação

text

### Tecnologias

| Categoria | Tecnologia | Função |
|:---|:---|:---|
| **Backend** | FastAPI + Uvicorn | Servidor web local |
| **Frontend** | HTML5 + CSS3 + JavaScript | Interface dark premium |
| **Banco de Dados** | SQLite + Repository Pattern | Progresso e conteúdo |
| **Áudio** | librosa + noisereduce + pyloudnorm | Pipeline profissional |
| **Voz** | Edge TTS | Síntese de voz neural gratuita |
| **Segurança** | PyArmor + PyInstaller | Código ofuscado e empacotado |

---

## 📥 Instalação (Usuário Final)

### ✅ Método Recomendado: Instalador .exe

1. **Baixe** o instalador da [página de Releases](https://github.com/eartnet09-boop/TEACHER.PRO/releases)
2. **Execute** como Administrador
3. **Marque** "Instalar IA" para baixar FFmpeg + Ollama + Qwen
4. **Aguarde** ~10 minutos (download do Qwen: 1.9 GB)
5. **Clique** em "Iniciar TEACHER.PRO"
6. **Acesse** http://localhost:8000

### ⚙️ Requisitos Mínimos

| Componente | Mínimo |
|:---|:---|
| **Sistema** | Windows 10/11 (64-bit) |
| **RAM** | 4 GB |
| **Disco** | 5 GB livres |
| **Internet** | Apenas na 1ª instalação (baixar modelos) |

---

## 🔧 Instalação (Desenvolvedor)

```bash
# 1. Clone o repositório
git clone https://github.com/eartnet09-boop/TEACHER.PRO.git
cd TEACHER.PRO

# 2. Crie o ambiente virtual
python -m venv venv

# 3. Ative o ambiente (Windows)
.\venv\Scripts\Activate.ps1

# 4. Instale as dependências
pip install -r requirements.txt
pip install openai-whisper pyarmor pyinstaller

# 5. Configure o ambiente
cp .env.example .env

# 6. Inicie o Ollama e baixe o Qwen
ollama serve
ollama pull qwen2.5-coder:3b

# 7. Execute
python -m src.main
📊 Comandos Úteis
bash
# Diagnóstico do sistema
python -m src.main diagnose

# Verificação rápida
python -m src.main check

# Executar testes (47 testes)
pytest tests/ -v

# Compilar executável
pyinstaller --clean --noconfirm teachpro.spec
📁 Estrutura do Projeto
text
TEACHER.PRO/
├── src/
│   ├── web/                    # Servidor e interface
│   │   ├── app.py              # FastAPI (25+ endpoints)
│   │   ├── session_manager.py  # Gerenciamento de sessões
│   │   ├── routers/            # Rotas modulares (/api/live/*)
│   │   └── static/
│   │       └── index.html      # Frontend completo (5 abas)
│   ├── audio/                  # Pipeline de áudio
│   │   └── processor.py        # Noise reduction + LUFS normalization
│   ├── transcription/          # Transcrição de fala
│   │   └── chall_model.py      # Whisper com preservação de erros
│   ├── pronunciation/          # Análise fonética
│   │   ├── wavlm_analyzer.py   # WavLM embeddings
│   │   ├── scorer.py           # Sistema de pontuação 0-100
│   │   └── aligner.py          # Wav2Vec2 forced alignment
│   ├── llm/                    # Inteligência Artificial
│   │   ├── dialog_engine.py    # Motor de diálogos com personagens
│   │   ├── tutor.py            # Feedback personalizado
│   │   └── prompts.py          # Templates de prompt otimizados
│   ├── tts/                    # Síntese de voz
│   │   └── speaker.py          # Edge TTS
│   ├── data/                   # Banco de dados
│   │   ├── database.py         # Gerenciador SQLite
│   │   ├── seeder.py           # 320 palavras, 82 diálogos
│   │   └── repository.py       # Repository Pattern
│   ├── enhancements/           # Modo híbrido
│   │   ├── web_services.py     # 9 APIs externas gratuitas
│   │   └── context_engine.py   # Orquestrador de contexto
│   ├── models/                 # Modelos Pydantic
│   ├── config.py               # Configuração centralizada
│   └── main.py                 # Entrypoint
├── tests/                      # 47 testes automatizados
├── hooks/                      # Hooks do PyInstaller
├── teachpro.spec               # Configuração de build
├── requirements.txt            # Dependências
└── README.md                   # Esta documentação
🐛 Solução de Problemas
Problema	Solução
ModuleNotFoundError	Ative o venv: .\venv\Scripts\Activate.ps1
Ollama não conecta	Execute ollama serve em outro terminal
FFmpeg não encontrado	winget install ffmpeg
Porta 8000 em uso	Feche outras instâncias ou mude a porta no .env
Index.html não encontrado	Recompile com pyinstaller --clean teachpro.spec
Erro numba ou fastapi.middleware	Verifique o teachpro.spec (hiddenimports)
📄 Licença
Este projeto é proprietário. Todos os direitos reservados a Expedito Anderson Rufino.

Veja o arquivo LICENSE para mais detalhes.

👨‍💻 Desenvolvedor
Expedito Anderson Rufino

GitHub: @eartnet09-boop

Repositório: TEACHER.PRO

🙏 Agradecimentos
OpenAI Whisper

Microsoft WavLM

Meta Wav2Vec2

Alibaba Qwen

Ollama

FastAPI

PyInstaller

Inno Setup

⭐ Se este projeto te ajudou, deixe uma estrela!

text

---

## ✅ Melhorias Implementadas

| Seção | Antes | Depois |
|:---|:---|:---|
| **Nome** | English Teacher Agent | TEACHER.PRO v4.2 |
| **Badges** | 4 básicos | 6 com testes, plataforma, IA |
| **Funcionalidades** | Texto corrido | Tabela com 6 modos + ícones |
| **Modelos IA** | Lista simples | Tabela com criador e função |
| **Instalação** | Só desenvolvedor | Usuário final PRIMEIRO |
| **Estrutura** | Desatualizada | Completa com 15 pastas |
| **Comandos** | Básicos | Inclui testes e build |
| **Licença** | MIT | Proprietária (correto!) |
| **Desenvolvedor** | Não tinha | Seção dedicada |
| **Requisitos** | Não tinha | Tabela com mínimo |
