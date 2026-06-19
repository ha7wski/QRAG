# Quran RAG — Project Summary

## Vision

Construire un système RAG (Retrieval-Augmented Generation) sur le corpus intégral du Coran, accessible via un chatbot conversationnel. L'objectif est de permettre à tout utilisateur — croyant, chercheur, étudiant ou curieux — d'explorer le texte coranique de manière intelligente : comprendre un mot dans son contexte linguistique et théologique, trouver toutes les occurrences d'un concept, comparer des versets thématiquement liés, et obtenir des réponses sourcées directement depuis le texte sacré.

Le système ne se substitue pas à l'interprétation savante (tafsir), mais offre un premier niveau d'exploration rigoureux, transparent sur ses sources, et multilingue (arabe, français, anglais).

---

## Corpus source

- **Format initial** : fichier `.txt` contenant le Coran complet
- **Structure cible après parsing** : chaque verset (āyah) est une unité atomique avec les métadonnées suivantes :
  - Numéro de sourate (1–114)
  - Nom de la sourate (arabe + translittération + traduction)
  - Numéro de verset
  - Texte arabe original (avec et sans harakat/diacritiques)
  - Traduction(s) — au minimum français et anglais
  - Translittération phonétique _(champ présent mais laissé vide — hors scope jusqu'à F5, voir ROADMAP)_
  - Période de révélation : Makkiyya (mecquoise) ou Madaniyya (médinoise)
  - Thème(s) principal(aux) du verset (à enrichir progressivement)
  - Racines arabes présentes dans le verset (index morphologique)

---

## Fonctionnalités à implémenter

### F1 — Chatbot Q&A (MVP)

L'utilisateur pose une question en langage naturel (arabe, français ou anglais). Le système :
1. Analyse et reformule la question pour optimiser le retrieval
2. Recherche les versets les plus pertinents dans la base vectorielle
3. Génère une réponse synthétique et nuancée
4. Cite systématiquement les versets sources avec leur référence (Sourate X, Verset Y)
5. Propose des versets complémentaires si pertinent

**Exemples de questions attendues :**
- "Que dit le Coran sur la patience ?"
- "Quelles sont les qualités du croyant ?"
- "Comment le Coran décrit-il la création du monde ?"
- "Quel est le sens du mot rahma (رحمة) ?"

---

### F2 — Recherche lexicale et définition de mots (priorité haute)

C'est une fonctionnalité centrale et distinctive du projet. Quand un utilisateur demande la définition ou le sens d'un mot arabe :

1. **Extraction de la racine** : le système identifie la racine trilitère (ou quadrilitère) du mot (ex. : *rahma* → racine `ر-ح-م`)
2. **Récupération exhaustive** : toutes les occurrences de cette racine dans le Coran sont récupérées depuis l'index morphologique
3. **Analyse contextuelle** : le LLM analyse le contexte de chaque occurrence pour dégager les nuances sémantiques
4. **Réponse structurée** :
   - Définition linguistique de la racine
   - Champ sémantique dans le Coran (comment le sens évolue selon les contextes)
   - Formes dérivées présentes (nom, verbe, adjectif, pluriel...)
   - Versets clés illustrant chaque nuance, avec citation et référence

**Particularité technique** : cette fonctionnalité nécessite un index morphologique arabe (basé sur `camel-tools` ou `pyarabic`) en complément de la recherche vectorielle pure.

---

### F3 — Exploration thématique

Permet de naviguer le Coran par thèmes et concepts :
- Carte thématique des sourates avec clustering sémantique
- Recherche par thème : "versets sur la miséricorde", "versets sur la justice sociale"
- Comparaison de versets traitant d'un même sujet
- Visualisation de la répartition d'un thème entre période mecquoise et médinoise

---

### F4 — Comparaison de traductions — ⛔ retirée du scope (2026-06-19)

_Retirée du périmètre produit._ Les traductions FR (Hamidullah) et EN (Sahih) restent ingérées,
indexées et affichées en ligne sous chaque verset (`VerseCard`, page `/verse/[surah]/[ayah]`),
mais aucune vue de comparaison côte à côte dédiée n'est prévue.

_Idée initiale : pour un verset donné, afficher et comparer plusieurs traductions existantes côte à côte._

---

### F5 — Mode étude et mémorisation

- Sélection de versets à mémoriser
- Flashcards générées automatiquement avec la translittération
- Quiz basé sur le contexte : "Quel est le verset précédent/suivant ?"
- Suivi de progression

---

### F6 — Export et partage

- Copie d'une citation formatée (verset arabe + traduction + référence)
- Export PDF d'une session de recherche
- Partage de résultats via lien

---

## Contraintes et principes directeurs

### Respect du texte sacré
- Le système cite toujours la source exacte (sourate + numéro de verset)
- Les réponses générées distinguent clairement ce qui vient du texte coranique et ce qui est une analyse du LLM
- Aucune hallucination ne doit être tolérée sur les citations — si le LLM ne trouve pas de verset pertinent, il le dit explicitement
- Le système ne prend pas position sur des questions théologiques controversées

### Multilinguisme
- Interface et réponses disponibles en arabe, français et anglais
- Les questions peuvent être posées dans n'importe laquelle de ces langues
- Le texte arabe est toujours affiché en écriture arabe originale, jamais uniquement en translittération

### Open source en priorité
- Privilégier les outils et modèles open source pour la souveraineté des données et la pérennité
- Le LLM doit pouvoir tourner localement (Qwen2.5-72B via Ollama) ou via API (Claude Sonnet 4.6) selon les ressources disponibles

### Performance et précision
- Le retrieval hybride (dense + sparse) est obligatoire pour combiner recherche sémantique et recherche exacte sur les racines
- Le reranking est obligatoire avant la génération pour garantir la pertinence des versets sélectionnés
- Temps de réponse cible : < 5 secondes pour une question standard

---

## Phases de développement

### Phase 1 — Infrastructure & MVP (priorité absolue)
- [ ] Parsing et nettoyage du fichier .txt source
- [ ] Construction de la pipeline d'ingestion (chunking, enrichissement métadonnées)
- [ ] Normalisation du texte arabe (diacritiques, Unicode)
- [ ] Index morphologique pour les racines arabes
- [ ] Setup Qdrant + index hybride (dense + BM25 sparse)
- [ ] Embedding avec CAMeL-BERT ou gte-multilingual
- [ ] Pipeline RAG de base avec LangChain ou LlamaIndex
- [ ] Chatbot Q&A (F1) — interface minimale
- [ ] Recherche lexicale (F2) — version basique

### Phase 2 — Qualité & fonctionnalités
- [ ] Reranking avec cross-encoder
- [ ] HyDE (Hypothetical Document Embedding) pour améliorer le retrieval
- [ ] Expansion de query par racines arabes
- [ ] Exploration thématique (F3)
- [ ] Comparaison de traductions (F4)
- [ ] Interface utilisateur complète (Next.js)

### Phase 3 — Enrichissement & polish
- [ ] Mode étude/mémorisation (F5)
- [ ] Export et partage (F6)
- [ ] Analytics et feedback utilisateur
- [ ] Optimisations de performance
- [ ] Tests de régression sur la qualité des réponses

---

## KPIs de qualité

- **Précision du retrieval** : les versets retournés sont-ils pertinents à la question ? (évaluation humaine sur un jeu de test)
- **Exactitude des citations** : 0% d'hallucination sur les références (sourate/verset)
- **Couverture lexicale** : toutes les occurrences d'une racine sont-elles bien retrouvées ?
- **Satisfaction utilisateur** : feedback intégré (👍/👎 sur chaque réponse)
- **Temps de réponse** : P95 < 5 secondes

---

## Références et ressources utiles

- Corpus Coran : tanzil.net (source de référence pour le texte arabe versionné)
- Morphologie arabe : camel-tools (Carnegie Mellon Arabic NLP toolkit)
- Tafsir de référence : Tafsir Ibn Kathir, Al-Jalalayn (pour validation des réponses)
- Benchmarks NLP arabe : AraBench, ALUE (Arabic Language Understanding Evaluation)
