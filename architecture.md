# Quran RAG — Architecture Technique

## Vue d'ensemble

Le système est une application RAG (Retrieval-Augmented Generation) construite autour de quatre couches indépendantes et découplées : ingestion des données, vectorisation et indexation, retrieval et génération, interface utilisateur. Chaque couche communique avec la suivante via des interfaces définies, ce qui permet de remplacer un composant (ex. : changer de LLM ou de vector store) sans refactorer le reste.

```
┌─────────────────────────────────────────────────────────────┐
│                     INTERFACE UTILISATEUR                    │
│              Next.js 14 + TailwindCSS (port 3000)           │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP / WebSocket
┌─────────────────────▼───────────────────────────────────────┐
│                        API BACKEND                           │
│              FastAPI + Python 3.11 (port 8000)              │
│         /chat  /search  /lexical  /themes  /verse           │
└──────┬──────────────┬──────────────────┬────────────────────┘
       │              │                  │
┌──────▼──────┐ ┌─────▼──────┐ ┌────────▼────────┐
│   QDRANT    │ │  MORPHO    │ │      LLM        │
│ Vector DB   │ │  INDEX     │ │ Qwen2.5 / API   │
│ (port 6333) │ │ PostgreSQL │ │ (Ollama/Claude) │
└─────────────┘ └────────────┘ └─────────────────┘
```

---

## Structure du projet

```
quran-rag/
├── README.md
├── docker-compose.yml
├── .env.example
│
├── ingestion/                        # Pipeline de traitement des données
│   ├── __init__.py
│   ├── parser.py                     # Parsing du fichier .txt source
│   ├── normalizer.py                 # Normalisation texte arabe
│   ├── morphology.py                 # Extraction racines arabes (camel-tools)
│   ├── enricher.py                   # Ajout métadonnées (thèmes, période...)
│   ├── chunker.py                    # Stratégie de chunking par verset
│   └── run_pipeline.py               # Script principal d'ingestion
│
├── indexing/                         # Vectorisation et indexation
│   ├── __init__.py
│   ├── embedder.py                   # Génération des embeddings
│   ├── qdrant_store.py               # Wrapper Qdrant
│   ├── bm25_index.py                 # Index sparse BM25 (rank-bm25)
│   ├── hybrid_search.py              # Fusion dense + sparse (RRF)
│   └── build_index.py                # Script de construction de l'index
│
├── retrieval/                        # Pipeline RAG
│   ├── __init__.py
│   ├── query_processor.py            # Analyse et expansion de la query
│   ├── retriever.py                  # Retrieval hybride principal
│   ├── reranker.py                   # Cross-encoder reranking
│   ├── hyde.py                       # Hypothetical Document Embedding
│   └── lexical_retriever.py          # Retrieval spécialisé recherche lexicale
│
├── generation/                       # Génération LLM
│   ├── __init__.py
│   ├── llm_client.py                 # Abstraction LLM (Ollama / Anthropic API)
│   ├── prompts.py                    # Tous les prompts système et utilisateur
│   ├── chat_engine.py                # Moteur de conversation avec historique
│   └── lexical_analyzer.py           # Analyse linguistique d'un mot/racine
│
├── api/                              # Backend FastAPI
│   ├── __init__.py
│   ├── main.py                       # Application FastAPI + CORS + routes
│   ├── routers/
│   │   ├── chat.py                   # POST /chat
│   │   ├── search.py                 # GET /search?q=...
│   │   ├── lexical.py                # POST /lexical (définition mot)
│   │   ├── themes.py                 # GET /themes
│   │   └── verse.py                  # GET /verse/{sourate}/{ayet}
│   ├── models/                       # Pydantic models (request/response)
│   │   ├── chat.py
│   │   ├── verse.py
│   │   └── lexical.py
│   └── middleware.py                 # Rate limiting, logging, auth future
│
├── frontend/                         # Interface Next.js
│   ├── package.json
│   ├── next.config.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx              # Page principale (chatbot)
│   │   │   ├── search/page.tsx       # Recherche avancée
│   │   │   ├── lexical/page.tsx      # Recherche lexicale
│   │   │   └── themes/page.tsx       # Exploration thématique
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx     # Interface de chat principale
│   │   │   ├── VerseCard.tsx         # Affichage d'un verset avec métadonnées
│   │   │   ├── LexicalResult.tsx     # Résultat analyse lexicale
│   │   │   ├── ThemeMap.tsx          # Carte thématique interactive
│   │   │   └── ArabicText.tsx        # Composant texte arabe (RTL, font)
│   │   └── lib/
│   │       ├── api.ts                # Client API backend
│   │       └── types.ts              # Types TypeScript partagés
│   └── public/
│       └── fonts/                    # Police arabe (Amiri ou Scheherazade)
│
├── data/
│   ├── raw/
│   │   └── quran.txt                 # Fichier source (à placer ici)
│   ├── processed/
│   │   ├── verses.json               # Versets parsés avec métadonnées
│   │   └── morphology.json           # Index morphologique (racines → versets)
│   └── translations/
│       ├── fr_hamidullah.json        # Traduction française
│       └── en_sahih.json             # Traduction anglaise (Sahih International)
│
├── tests/
│   ├── test_ingestion.py
│   ├── test_retrieval.py
│   ├── test_lexical.py
│   └── eval/
│       ├── qa_dataset.json           # Dataset de questions/réponses de référence
│       └── evaluate.py               # Script d'évaluation qualité RAG
│
├── scripts/
│   ├── setup.sh                      # Installation de l'environnement
│   ├── ingest.sh                     # Lancement pipeline ingestion
│   └── start_dev.sh                  # Démarrage en développement
│
└── requirements.txt
```

---

## Couche 1 — Ingestion & prétraitement

### 1.1 Parsing du fichier source

**Fichier** : `ingestion/parser.py`

Le parser lit le fichier `.txt` et produit une liste de versets structurés. La structure cible pour chaque verset est :

```python
{
    "id": "2:255",                         # sourate:verset (clé unique)
    "surah_number": 2,
    "surah_name_ar": "البقرة",
    "surah_name_fr": "La Vache",
    "surah_name_en": "Al-Baqarah",
    "ayah_number": 255,
    "text_ar": "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ...",  # avec harakat
    "text_ar_clean": "الله لا إله إلا هو...",          # sans harakat
    "translation_fr": "Allah ! Point de divinité...",
    "translation_en": "Allah - there is no deity...",
    "transliteration": "Allahu la ilaha illa huwa...",
    "period": "madani",                     # makkiyya ou madani
    "juz": 3,                               # numéro de juz (1-30)
    "page": 42,                             # page du Mushaf standard
    "themes": [],                           # à enrichir
    "roots": []                             # à remplir par morphology.py
}
```

### 1.2 Normalisation du texte arabe

**Fichier** : `ingestion/normalizer.py`

Opérations de normalisation appliquées avant l'embedding :

```python
# Librairie : camel-tools ou pyarabic
# Opérations :
# 1. Suppression des harakat (diacritiques) pour la version "clean"
# 2. Normalisation des alifs (أ إ آ → ا)
# 3. Normalisation du ya (ى → ي)
# 4. Normalisation du ta marbuta (ة → ه pour la recherche)
# 5. Suppression des tatweel (ـ)
# 6. Unicode NFC normalization
```

### 1.3 Index morphologique

**Fichier** : `ingestion/morphology.py`

C'est l'index critique pour la fonctionnalité de recherche lexicale (F2). Il mappe chaque racine arabe à tous les versets où elle apparaît.

```python
# Librairie : camel-tools (CamelMorphAnalyzer)
# Sortie : morphology.json
{
    "ر-ح-م": {
        "root": "ر-ح-م",
        "forms_found": ["رَحْمَة", "رَحِيم", "رَحْمَن", "يَرْحَم", "مَرْحَمَة"],
        "verses": ["1:1", "1:3", "2:64", "2:143", ...],  # 114+ occurrences
        "count": 114
    },
    "ع-ل-م": { ... },
    ...
}
```

**Dépendance** : `pip install camel-tools` + téléchargement des modèles morphologiques CAMeL.

### 1.4 Stratégie de chunking

**Fichier** : `ingestion/chunker.py`

Le verset est l'unité de base (pas de chunking arbitraire par tokens). Cependant, pour les très longs versets (ex. : 2:282, le verset de la dette), un chunking en deux parties avec overlap peut être nécessaire.

Règle : si `len(text_ar) > 500 caractères`, split en deux chunks avec overlap de 50 caractères.

Pour la recherche contextuelle, les 3 versets précédents et suivants sont inclus dans le contexte envoyé au LLM (pas dans l'index, mais au moment de la génération).

---

## Couche 2 — Vectorisation & indexation

### 2.1 Modèle d'embedding

**Fichier** : `indexing/embedder.py`

Deux stratégies selon la langue de la query et du texte :

```python
# Modèle principal (arabe + multilingue)
# Nom HuggingFace : "intfloat/multilingual-e5-large-instruct"
# Dimension : 1024
# Alternative arabe pur : "CAMeL-Lab/bert-base-arabic-camelbert-mix"
# Alternative légère : "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
# Dimension : 768

# Le texte envoyé à l'embedder est la concaténation :
# f"passage: {text_ar_clean} {translation_fr}"
# → Permet les queries en français ET en arabe
```

### 2.2 Base vectorielle — Qdrant

**Fichier** : `indexing/qdrant_store.py`

```python
# Collection Qdrant : "quran_verses"
# Configuration :
{
    "vectors": {
        "size": 1024,
        "distance": "Cosine"
    },
    "sparse_vectors": {
        "bm25": {}  # Pour la recherche hybride dense+sparse
    }
}

# Payload indexé pour filtrage :
# - surah_number (int)    → filter: surah_number == 2
# - period (keyword)      → filter: period == "makkiyya"
# - juz (int)             → filter: juz == 30
# - themes (list[str])    → filter: themes contains "miséricorde"
```

### 2.3 Index BM25 sparse

**Fichier** : `indexing/bm25_index.py`

```python
# Librairie : rank-bm25
# Corpus : texte arabe sans harakat + traduction française (concaténés)
# Tokenizer arabe : split sur les espaces après normalisation
# Stockage : sérialisé en JSON dans data/processed/bm25_index.pkl
```

### 2.4 Fusion hybride — Reciprocal Rank Fusion

**Fichier** : `indexing/hybrid_search.py`

```python
# Algorithme : RRF (Reciprocal Rank Fusion)
# Score final = 1/(k + rank_dense) + 1/(k + rank_sparse)
# k = 60 (paramètre standard)
# Le score dense et sparse sont fusionnés avant le reranking
```

---

## Couche 3 — Retrieval & génération

### 3.1 Traitement de la query

**Fichier** : `retrieval/query_processor.py`

```python
class QueryProcessor:
    def process(self, query: str) -> ProcessedQuery:
        # 1. Détection de langue (langdetect)
        # 2. Si question sur un mot arabe → extraction de la racine
        # 3. Expansion de query : génération de synonymes et termes liés
        # 4. Si arabe : normalisation et extraction des racines présentes
        return ProcessedQuery(
            original=query,
            language="fr",           # "ar", "fr", "en"
            is_lexical=True,         # Si c'est une demande de définition
            arabic_root="ر-ح-م",    # Si détecté
            expanded_terms=["rahma", "rahima", "rahman", "rahim"],
            filters={}               # Filtres Qdrant si mentionnés dans la query
        )
```

### 3.2 HyDE (Hypothetical Document Embedding)

**Fichier** : `retrieval/hyde.py`

```python
# Pour les questions complexes ou abstraites :
# 1. Envoyer la query au LLM en lui demandant de générer
#    un "verset hypothétique" qui répondrait à la question
# 2. Embedder ce verset hypothétique
# 3. Utiliser cet embedding pour la recherche vectorielle
# → Améliore significativement le recall sur les questions abstraites

HYDE_PROMPT = """
Tu es un expert du Coran. Un utilisateur cherche des versets coraniques 
sur le sujet suivant : {query}

Génère un extrait de texte qui ressemblerait à un verset coranique 
traitant de ce sujet. Texte en arabe suivi de sa traduction française.
Ne cite pas de vrais versets, génère un texte hypothétique.
"""
```

### 3.3 Reranking

**Fichier** : `retrieval/reranker.py`

```python
# Modèle : cross-encoder/ms-marco-MiniLM-L-6-v2 (léger, multilingue partiel)
# Alternative arabe : fine-tuner un cross-encoder sur des paires arabe
# Input : (query, verset concaténé avec traduction)
# Top-K avant reranking : 20 versets
# Top-K après reranking : 5 à 7 versets envoyés au LLM
```

### 3.4 Retrieval spécialisé — Recherche lexicale

**Fichier** : `retrieval/lexical_retriever.py`

```python
class LexicalRetriever:
    def retrieve_by_root(self, root: str) -> LexicalResult:
        # 1. Lookup dans morphology.json → liste de verse_ids
        # 2. Récupération des versets depuis Qdrant par IDs
        # 3. Groupement par forme grammaticale (nom, verbe, adj...)
        # 4. Sélection des versets les plus représentatifs par groupe
        # 5. Retour d'une structure complète pour l'analyse LLM
        pass
```

### 3.5 Abstraction LLM

**Fichier** : `generation/llm_client.py`

```python
class LLMClient:
    """
    Abstraction permettant de switcher entre :
    - Ollama local (Qwen2.5:72b, Jais-30b)
    - Anthropic API (claude-sonnet-4-6)
    - OpenAI API (gpt-4o) — fallback
    """
    def __init__(self, provider: str = "ollama"):
        # provider: "ollama" | "anthropic" | "openai"
        ...

    async def generate(self, system: str, messages: list, stream: bool = True):
        ...
```

**Configuration** (`.env`) :
```
LLM_PROVIDER=ollama           # ou "anthropic"
OLLAMA_MODEL=qwen2.5:72b
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
```

### 3.6 Prompts système

**Fichier** : `generation/prompts.py`

```python
SYSTEM_PROMPT_CHAT = """
Tu es un assistant spécialisé dans l'étude du Coran. 
Tu réponds aux questions en te basant UNIQUEMENT sur les versets coraniques 
fournis dans le contexte. 

Règles strictes :
1. Cite toujours la référence exacte : Sourate {nom} ({numéro}), Verset {numéro}
2. Si aucun verset fourni ne répond à la question, dis-le explicitement
3. Ne génère JAMAIS de citation de verset qui ne figure pas dans le contexte
4. Distingue clairement le texte coranique de ton analyse
5. Reste neutre sur les questions théologiques controversées
6. Tu peux répondre en arabe, français ou anglais selon la langue de la question

Format de réponse :
- Réponse synthétique (3-5 phrases)
- Versets clés cités avec référence
- Contexte complémentaire si pertinent
"""

SYSTEM_PROMPT_LEXICAL = """
Tu es un linguiste spécialisé en arabe coranique.
On te donne la liste de TOUTES les occurrences d'une racine arabe dans le Coran,
avec leurs versets et contextes.

Tu dois fournir :
1. La définition de la racine (sens premier, champ sémantique)
2. Les différentes formes grammaticales trouvées et leur sens spécifique
3. L'évolution du sens selon le contexte (mécanique, spirituel, éthique...)
4. Les 3-5 versets les plus illustratifs avec explication du choix
5. Ce que l'ensemble des occurrences révèle sur la conception coranique de ce concept

Cite chaque verset avec sa référence exacte.
"""
```

---

## Couche 4 — API Backend

### 4.1 Routes principales

**Fichier** : `api/main.py`

```
POST /chat
    Body: { messages: [...], session_id: str }
    Response: { answer: str, sources: [Verse], session_id: str }
    Streaming: Server-Sent Events (SSE)

POST /chat/stream
    Body: { message: str, history: [...], filters: {} }
    Response: SSE stream de tokens + sources finales

POST /lexical
    Body: { word: str, language: "ar"|"fr"|"en" }
    Response: { root: str, forms: [...], analysis: str, key_verses: [Verse] }

GET /search
    Params: q=str, surah=int?, period=str?, limit=int
    Response: { results: [Verse], total: int }

GET /verse/{surah_number}/{ayah_number}
    Response: { verse: Verse, context: [Verse], translations: {...} }

GET /themes
    Response: { themes: [{ name: str, count: int, representative_verses: [...] }] }

GET /surah/{number}
    Response: { surah: Surah, verses: [Verse] }

GET /health
    Response: { status: "ok", qdrant: bool, llm: bool }
```

### 4.2 Modèles de données

**Fichier** : `api/models/verse.py`

```python
from pydantic import BaseModel

class Verse(BaseModel):
    id: str                    # "2:255"
    surah_number: int
    surah_name_ar: str
    surah_name_fr: str
    ayah_number: int
    text_ar: str
    translation_fr: str
    translation_en: str
    period: str
    relevance_score: float | None = None

class ChatMessage(BaseModel):
    role: str                  # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    session_id: str | None = None
    filters: dict = {}

class ChatResponse(BaseModel):
    answer: str
    sources: list[Verse]
    session_id: str

class LexicalRequest(BaseModel):
    word: str
    language: str = "ar"

class LexicalResponse(BaseModel):
    word: str
    root: str
    forms: list[str]
    occurrences_count: int
    analysis: str
    key_verses: list[Verse]
```

---

## Couche 5 — Interface utilisateur

### 5.1 Stack Frontend

```
Next.js 14 (App Router)
TailwindCSS 3
Lucide React (icônes)
Zustand (state management)
```

### 5.2 Pages

- `/` — Chatbot principal (page d'accueil)
- `/search` — Recherche avancée avec filtres (sourate, période, thème)
- `/lexical` — Outil de définition de mots arabes
- `/surah/[number]` — Affichage complet d'une sourate
- `/themes` — Carte d'exploration thématique

### 5.3 Considérations RTL

```css
/* Le texte arabe est toujours RTL */
.arabic-text {
    direction: rtl;
    font-family: 'Amiri', 'Scheherazade New', serif;
    font-size: 1.5rem;
    line-height: 2.5;
}

/* L'interface globale reste LTR (fr/en) */
/* Chaque VerseCard gère le RTL localement */
```

### 5.4 Police arabe recommandée

Amiri (Google Fonts) — spécialisée pour le texte coranique, supporte toutes les formes de diacritiques arabes.

```html
<link href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
```

---

## Infrastructure & déploiement

### Variables d'environnement

```bash
# .env.example

# LLM
LLM_PROVIDER=ollama              # "ollama" | "anthropic"
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:72b
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-6

# Vector DB
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=quran_verses

# Embedding
EMBEDDING_MODEL=intfloat/multilingual-e5-large-instruct
EMBEDDING_DEVICE=cpu             # "cpu" | "cuda" | "mps"

# App
BACKEND_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=INFO
```

### Docker Compose

```yaml
# docker-compose.yml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_storage:/qdrant/storage

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    # Pour GPU : ajouter deploy: resources: reservations: devices: [driver: nvidia...]

  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    env_file: .env
    depends_on:
      - qdrant
      - ollama

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000

volumes:
  qdrant_storage:
  ollama_models:
```

### Requirements Python

```
# requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
pydantic==2.8.0
python-dotenv==1.0.1

# RAG & LLM
langchain==0.3.0
langchain-community==0.3.0
anthropic==0.34.0
ollama==0.3.0

# Embeddings
sentence-transformers==3.1.0
torch==2.4.0

# Vector DB
qdrant-client==1.11.0

# BM25
rank-bm25==0.2.2

# Reranking
transformers==4.44.0

# NLP Arabe
camel-tools==1.5.4
pyarabic==0.6.15
langdetect==1.0.9

# Utils
httpx==0.27.0
aiofiles==24.1.0
structlog==24.4.0
```

---

## Ordre de développement recommandé pour Claude Code

Voici l'ordre optimal pour bootstrapper le projet. Chaque étape produit quelque chose de fonctionnel et testable avant de passer à la suivante.

**Étape 1** — Setup initial
```
1. Créer la structure de dossiers complète
2. Configurer docker-compose.yml (Qdrant + Ollama)
3. Créer requirements.txt et .env.example
4. Vérifier que Qdrant démarre et est accessible
```

**Étape 2** — Pipeline d'ingestion
```
1. ingestion/parser.py → parser le quran.txt, produire verses.json
2. ingestion/normalizer.py → normalisation texte arabe
3. ingestion/morphology.py → index morphologique (morphology.json)
4. Test : python ingestion/run_pipeline.py
   → Vérifier que les 6236 versets sont bien parsés
```

**Étape 3** — Indexation
```
1. indexing/embedder.py → tester les embeddings sur 10 versets
2. indexing/qdrant_store.py → créer la collection et insérer les versets
3. indexing/bm25_index.py → construire l'index sparse
4. Test : requête directe sur Qdrant, vérifier les résultats
```

**Étape 4** — Pipeline RAG de base
```
1. retrieval/retriever.py → retrieval hybride basique
2. generation/llm_client.py → connexion Ollama/Anthropic
3. generation/prompts.py → prompts système
4. generation/chat_engine.py → pipeline question → retrieval → génération
5. Test CLI : poser une question et vérifier la réponse
```

**Étape 5** — API Backend
```
1. api/main.py → app FastAPI avec /health
2. api/routers/chat.py → endpoint /chat avec streaming SSE
3. api/routers/search.py → endpoint /search
4. Test : curl ou Postman sur les endpoints
```

**Étape 6** — Recherche lexicale
```
1. retrieval/lexical_retriever.py → lookup par racine
2. generation/lexical_analyzer.py → analyse LLM des occurrences
3. api/routers/lexical.py → endpoint /lexical
4. Test : définition du mot "رحمة" (rahma)
```

**Étape 7** — Frontend
```
1. Setup Next.js dans frontend/
2. ChatInterface.tsx → interface de chat basique
3. VerseCard.tsx → affichage d'un verset avec texte arabe
4. Connexion à l'API backend
5. Test end-to-end complet
```

**Étape 8** — Qualité RAG
```
1. retrieval/reranker.py → cross-encoder reranking
2. retrieval/hyde.py → HyDE pour les questions abstraites
3. retrieval/query_processor.py → expansion de query
4. Évaluation sur qa_dataset.json
```

---

## Points d'attention critiques

**1. Format du fichier quran.txt** : avant de commencer le développement, analyser manuellement le format exact du fichier source (séparateurs, encoding, structure des lignes) et adapter `parser.py` en conséquence. C'est la première chose à faire.

**2. Diacritiques arabes** : toujours maintenir deux versions du texte — avec harakat (pour l'affichage) et sans harakat (pour l'indexation et la recherche). Un mot avec et sans harakat ne doit pas être traité comme deux mots différents.

**3. Performance des embeddings** : l'ingestion de 6236 versets avec un modèle d'embedding peut prendre 10 à 30 minutes selon le hardware. Prévoir un script de reprise en cas d'interruption (checkpoint sur le dernier verset indexé).

**4. Streaming LLM** : utiliser Server-Sent Events (SSE) pour streamer la réponse du LLM token par token. Ne jamais attendre la réponse complète avant de l'envoyer au frontend — l'expérience utilisateur en dépend.

**5. Contexte des versets** : quand le LLM génère une réponse, inclure toujours dans le contexte les versets précédent et suivant le verset récupéré. Le sens d'un verset dépend souvent de son contexte immédiat.
