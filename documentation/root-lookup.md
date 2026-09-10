# Root Lookup — « Word in Verses » (Verse Study)

Ce document décrit le pipeline de recherche par racine (« Word in Verses », onglet
*Verse Study*) : comment un mot arabe saisi remonte à tous ses versets, d'où viennent les
racines (quel dataset), comment les index sont construits, et les pistes d'amélioration.

Tout le code de ce chemin est **déterministe et sans LLM/ML au moment de la requête** :
la seule « intelligence » est pré-calculée une fois à l'ingestion.

---

## 1. Le pipeline « Word in Verses » (au moment de la requête)

Le flux part d'un **mot arabe saisi** et remonte à **tous les versets** qui partagent sa
racine :

```
Frontend (verse-study, onglet « Word in Verses »)
        │  POST /verse-lookup
        ▼
api/routers/verse_lookup.py   →   retrieval/verse_lookup.py (VerseLookup)
        │
        ├─ Résolution de la racine (LexicalRetriever)
        │     ordre : racine stricte → nom propre → « lenient » (clitiques/alif)
        │
        ├─ Récupération : pour chaque racine, toutes ses occurrences,
        │     groupées par lemme (sens dominant en premier)
        │
        └─ Affichage vocalisé : texte chakl depuis data/source/quran_chakl.csv,
              groupé par sourate, mot surligné (matching hamza-safe)
```

### Étapes détaillées (`retrieval/verse_lookup.py`)

1. **Résolution de la racine** — le mot passe par le résolveur QAC (`LexicalRetriever`).
   Ordre volontaire (`VerseLookup.lookup`) :
   - **racine stricte** (`resolve_roots`) : échelle QAC exacte,
   - sinon **nom propre** (`_resolve_proper_noun`) — placé *avant* le lenient pour qu'un
     nom comme `لوطًا` résolve le prophète `لوط`, et non une racine parasite obtenue en
     pelant son `ل` initial (`وطأ`),
   - sinon **lenient** (`resolve_roots_lenient`) : réessais sur variantes clitiques /
     alif plène.
   Les homographes renvoient **plusieurs** racines.

2. **Récupération** — pour chaque racine, on lit ses occurrences dans l'index, **groupées
   par lemme** (ex. `سمو` → `سماء` « ciel » / `اسم` « nom »).

3. **Affichage vocalisé** — le texte vocalisé (chakl) vient de `data/source/quran_chakl.csv`
   via `quran_data.corpus.chakl_by_ref()` (le corpus dérivé `text_ar` n'a **pas** de
   harakat). Regroupé par sourate, avec le mot **surligné** (`_match_indices`).

4. **Cas nom propre** — `لوط`, `موسى`, `إبراهيم`… sont **sans racine dans QAC** → résolus
   via `proper_nouns.json` et renvoyés comme un seul groupe avec racine vide et
   `is_proper_noun: true`.

### Normalisation : le bon normaliseur au bon endroit

Trois normaliseurs coexistent dans le projet, à ne pas confondre. Ils vivent désormais
**côte à côte dans `arabic_text/`**, précisément pour que le choix soit visible au moment
où on le fait ; le tableau comparatif de `arabic_text/__init__.py` fait autorité :

- **`arabic_text.normalize_root`** — pour les **racines** : folde les porteurs de hamza
  mais **ne supprime jamais** la hamza. Utilisé par la résolution.
- **`arabic_text.normalize_search`** — hamza-safe (folde ى/ة, retire les
  marques de waqf) : pour le **surlignage** et BM25.
- **`arabic_text.normalize_text`** — **supprime** la hamza (أَرْض → رض) : **jamais** pour le
  matching de racines (over-matcherait عرض/مرض/فرض).

Le surlignage (`_match_indices` + `_norm_match`) utilise `normalize_search` avec en plus
le **dagger alef** (U+0670) replié en alif plène, pour réconcilier `بَقَرَٰت` (QAC) et
`بَقَرَات` (mushaf vocalisé).

---

## 2. La source des racines : le Quranic Arabic Corpus (QAC)

Les racines **ne viennent pas d'un stemmer algorithmique** mais du **Quranic Arabic
Corpus**, en arabe natif et **vérifiées manuellement**.

- **Source brute** : `data/source/quran-morphology.txt` (fork *mustafa0x/quran-morphology*),
  lue **uniquement** via `quran_data/qac.py` — le lecteur unique de ce fichier, qui en avait
  quatre. Sa provenance complète est dans `quran_data/manifest.py`.
- Cela remplace l'ancien builder à base de tashaphyne (`ingestion/morphology.py`), qui
  mis-roote (ex. `كريم` → `ريم` au lieu de `كرم`). L'ancien builder est **laissé en place,
  inutilisé**, comme fallback optionnel derrière `QAC_STEMMER_FALLBACK=0` (off).

### Format du fichier brut

**Une ligne par segment morphologique** (pas par mot — QAC découpe les clitiques). Quatre
champs séparés par tabulation :

```
LOCATION        FORM        TAG        FEATURES
1:2:1:2         سْمِ         N          ...|ROOT:سمو|LEM:اسم|...
```

- `LOCATION` = `sourate:aya:mot:segment`
- `FEATURES` = tokens séparés par `|` ; la **racine** est un token `ROOT:<arabe>` qui peut
  se trouver à **n'importe quelle position** (d'où le scan par préfixe, jamais par indice
  de colonne). Le lemme est `LEM:<arabe>`.
- Beaucoup de lignes n'ont **pas de ROOT** (préfixes, DET, pronoms, particules, lettres
  isolées d'ouverture) → ignorées silencieusement.

---

## 3. La construction des index (`ingestion/qac_morphology.py`, Stage 4)

Le module lit le fichier brut ligne par ligne et, pour chaque segment porteur d'une racine :

1. **`parse_line`** extrait `(verse_id, form, root, lemma)`. Racine et lemme sont
   normalisés via `normalize_root`.
2. Il **accumule** : versets par racine, formes par racine, racines par verset, et des
   seaux `(racine, lemme)` pour le sous-découpage par sens.
3. **`parse_proper_noun`** rattrape les segments **sans ROOT mais taggés PN** (noms
   d'origine étrangère : `لوط`, `إبراهيم`, `موسى`…) — QAC ne leur donne pas de racine, donc
   ils vivent dans un index séparé, clé = lemme normalisé via `normalize_search`.

### Fichiers produits

| Fichier | Contenu | Rôle au lookup |
|---|---|---|
| **`data/derived/morphology.json`** | racine → `{root, forms_found, verses, count}` | index principal : toutes les occurrences d'une racine |
| **`data/derived/qac_resolution.json`** | `form_to_roots` + `lem_to_roots` | maps inverses : d'une **forme** ou d'un **lemme** on remonte à la/les racine(s) — résout le mot tapé |
| **`data/derived/lemma_index.json`** | racine → `[{lemma, lemma_display, forms_found, verses, count}]`, **sens dominant en premier** | sépare une racine en ses sens pour le groupement UI |
| **`data/derived/proper_nouns.json`** | lemme normalisé → `{lemma_display, forms_found, verses, count}` | trouve les noms propres sans racine |
| `data/derived/verses_final.json` | corpus + champ `roots` rempli par verset | (mis à jour au passage) |

Ces chemins ne sont jamais écrits à la main dans le code : ils viennent des constantes de
`quran_data/paths.py`, et se lisent via les loaders paresseux de `quran_data/loaders.py`.

### Reconstruire les index

```bash
python -m ingestion.qac_morphology     # rebuild autonome sur le corpus existant
# ou, dans le pipeline complet :
python ingestion/run_pipeline.py
```

Ces JSON sont lus **une fois au démarrage** par `LexicalRetriever` / `VerseLookup`.

---

## 4. La résolution mot → racine (`retrieval/lexical_retriever.py`)

L'échelle QAC (`_ladder`), par ordre de confiance, sur un token déjà normalisé :

1. le mot normalisé **est** déjà une clé de racine,
2. **FORM** de surface connue → racine(s) (`form_to_roots`),
3. **lemme** connu → racine(s) (`lem_to_roots`),
4. *(optionnel)* stemmer legacy — seulement si `QAC_STEMMER_FALLBACK=1`.

Deux points d'entrée :

- **`resolve_roots`** (strict) — pas de peeling de clitiques. Utilisé par l'expansion de
  requête du chat (dépend volontairement de ce comportement strict).
- **`resolve_roots_lenient`** — quand le mot exact échoue, réessaie sur des variantes
  **clitiques** (`_PROCLITICS` / `_ENCLITICS`, plus longs d'abord) et **alif plène →
  défective** (`_alif_variants`), en **n'acceptant qu'un stem qui donne une racine
  connue** (un peeling trop gourmand ne peut pas mis-résoudre). Utilisé par « Word in
  Verses ».

---

## 5. Pistes d'amélioration

Point de départ : **la donnée QAC est déjà le plafond de qualité** (vérifiée à la main).
On n'améliore donc pas la justesse des racines elles-mêmes, mais la **résolution**, la
**précision d'affichage** et la **couverture**. Classées du plus rentable au plus marginal.

### 5.1. Stocker la racine *par occurrence* (le plus gros levier)

Aujourd'hui `morphology.json` enregistre `racine → {formes, versets}` **au niveau racine
seulement** — jamais « quelle forme / quelle racine dans quel verset ». Deux conséquences :

- **Surlignage reconstruit à la main** (`_match_indices`) : matching par sous-chaîne,
  « imperfect for very short forms » — sur/sous-surligne.
- **Homographes non désambiguïsés** : `كل` renvoie `اكل` / `كلل` / `كيل` sans savoir lequel
  est réellement dans tel verset.

Or QAC connaît déjà la racine exacte de **chaque segment** (chaque ligne brute). En
stockant un mapping `verset → [(segment, forme, racine)]`, on obtient un surlignage
**exact** et une attribution racine **par occurrence**, sans plus jamais deviner. C'est un
enrichissement de `qac_morphology.py` + du format JSON.

### 5.2. Désambiguïser les homographes par fréquence (quick win)

`resolve_roots` renvoie **toutes** les racines d'un homographe, dans un ordre arbitraire.
Les **trier par nombre d'occurrences** (racine dominante d'abord) — déjà fait pour les
lemmes (`-g["count"]`), pas pour les racines — est trivial et améliore l'UX immédiatement.

### 5.3. Élargir prudemment la résolution « lenient »

`resolve_roots_lenient` ne tente que **clitiques + alif plène**. Manques possibles :

- **Incohérence de normaliseur** : la résolution utilise `normalize_root`, mais les noms
  propres `normalize_search` (ى→ي, ة→ه). Un mot tapé avec ة/ى finale peut rater côté
  racine alors qu'il matcherait côté nom propre → aligner les variantes finales.
- Variantes d'orthographe hamza au-delà de ce que `normalize_root` folde.

⚠️ À garder **hors du chemin chat** : `resolve_roots` strict reste volontairement strict
(décision P4 métriquée, non couplée à ce fix de lookup).

### 5.4. Couverture des mots hors-corpus

Aujourd'hui un mot non attesté dans le Coran ne résout rien (stemmer legacy
`QAC_STEMMER_FALLBACK=0`). Pour Verse Study c'est **voulu** (seuls les mots coraniques
comptent). Ne l'activer que si l'objectif change — le stemmer legacy mis-root
(`كريم` → `ريم`), donc ce serait une **régression** de qualité.

### 5.5. Mesurer avant/après

Aucune de ces pistes ne devrait être poussée sans un petit **gold set de résolution**
(mot → racine(s) attendue(s)), sur le modèle de `tests/eval/`. Sinon on améliore à
l'aveugle.

**Recommandation** : commencer par **5.1 (racine par occurrence)** — seul axe qui débloque
à la fois surlignage exact *et* désambiguïsation, et qui enrichit la donnée à la source.
**5.2** est un quick win à faire en même temps.
