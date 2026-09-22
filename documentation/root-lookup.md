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

2. **Récupération** — pour chaque racine, on lit ses occurrences dans l'index. Le lemme
   (`lemma_index.json`) reste l'**entrée interne** : il fournit les `word_refs` et les
   `forms_found` dont le surligneur a besoin. Mais il ne sort plus : le regroupement
   affiché se fait par **لفظ**, la forme écrite (§ 2 bis).

3. **Découpage par لفظ** — chaque occurrence est rangée sous la graphie de son mot.
   `سمو` ne répond plus « 2 lemmes » mais 17 ألفاظ (`سماء`, `سماوات`, `أسماء`, `اسمه`…).
   La dérivation est décrite en § 2 bis.

4. **Affichage vocalisé** — le texte vocalisé (chakl) vient de `data/source/quran_chakl.csv`
   via `quran_data.corpus.chakl_by_ref()` (le corpus dérivé `text_ar` n'a **pas** de
   harakat). Regroupé par لفظ puis par sourate, avec le mot **surligné** — par sa
   **position**, lue dans `root_graph.json` × `word_index.json` (voir
   [`root-highlight-alignment-issue.md`](root-highlight-alignment-issue.md)), et non plus
   par matching de texte. `_match_indices` ne sert plus que de repli. Le surlignage est
   **limité au لفظ du bloc** : en 40:81, `آيَاتِ` est marqué dans le bloc `آيات` et
   `آيَاتِهِ` dans le bloc `آياته`. Une آية portant deux ألفاظ est donc listée deux fois —
   19 des 353 آيات de `أيي`, soit 373 lignes pour 353 آيات distinctes.

5. **Cas nom propre** — `لوط`, `موسى`, `إبراهيم`… sont **sans racine dans QAC** → résolus
   via `proper_nouns.json`, découpés par لفظ comme le reste (`لوط` → 2 ألفاظ : `لوط`,
   `لوطا`), avec racine vide, `is_proper_noun: true`, et le nom vocalisé porté par le
   champ de tête `proper_noun_display`.

### 2 bis. Le لفظ : comment une forme écrite est dérivée

Un **لفظ** est le mot *tel que le muṣḥaf l'écrit*, pas une entrée de dictionnaire.
`آيات`, `آياتنا` et `آياته` sont trois ألفاظ du seul lemme `آيَة`. Pour une occurrence :

1. **le dernier token affiché** que le surligneur marque. QAC soude une particule
   proclitique au mot qu'elle régit (`يحسرتى` pour les deux tokens `يَا حَسْرَتَا`) et
   l'arabe écrit la particule d'abord : la tête lexicale est donc la dernière. Une seule
   occurrence sur 50 045 marque encore deux tokens après `_narrow` — c'est exactement
   celle-là.
2. **`arabic_text.bare()` et rien d'autre.** Ce repli **supprime** l'alef suscrit U+0670,
   ce que veut une forme écrite : `مُوسَىٰ` → `موسى`. Le replier en alef plein donnerait
   `موسىا`, une graphie qui n'existe nulle part, et scinderait les 136 occurrences du nom.
3. **retrait des proclitiques que QAC déclare**, lus dans `word_prefixes.json`. Jamais
   déduits des lettres initiales : une regex qui pèle un `و`/`ب`/`ك` initial transformerait
   `وَلَد` en `لد` et `كِتَاب` en `تاب`. Le préfixe n'est retiré que si le token commence
   réellement par lui ; ce garde-fou se déclenche sur 156 occurrences sur 50 045 et a
   raison à chaque fois (le `يٰ` vocatif est un token d'affichage séparé ; une hamza
   interrogative fondue dans `آللَّهُ` ne peut pas sortir sans réécrire le mot).

Les suffixes pronominaux **font partie** du لفظ (`آياتنا` ≠ `آيات`) ; les proclitiques non
(`بِآيَاتِنَا` et `آيَاتِنَا` sont un seul لفظ).

**Pourquoi un fichier dédié plutôt que `qac_words.json`** — qui porte pourtant la même
segmentation : parce qu'il coûte **248 Mo résidents** contre 64 Mo pour `word_index.json`,
et que le chemin de la requête ne payait ni l'un ni l'autre. `word_prefixes.json` en extrait
les 0,5 Mo utiles : 26 001 refs, 108 chaînes de préfixe distinctes.

Les blocs sont émis dans l'ordre de **première occurrence, globalement, toutes racines
confondues**. Le tri par racine seul plaçait `مأكول` (105:5) avant `كلما` (2:20) sur la
requête homographe `كل` ; le client départage ses égalités sur l'ordre reçu, donc un mauvais
ordre ne se voit pas comme un ordre faux mais comme un ordre arbitraire.

### Normalisation : le bon normaliseur au bon endroit

Trois normaliseurs coexistent dans le projet, à ne pas confondre. Ils vivent désormais
**côte à côte dans `arabic_text/`**, précisément pour que le choix soit visible au moment
où on le fait ; le tableau comparatif de `arabic_text/__init__.py` fait autorité :

- **`arabic_text.normalize_root`** — pour les **racines** : folde les porteurs de hamza
  mais **ne supprime jamais** la hamza. Utilisé par la résolution.
- **`arabic_text.normalize_search`** — hamza-safe (folde ى/ة, retire les
  marques de waqf) : pour BM25 et pour le **repli** de surlignage.
- **`arabic_text.fold_madda`** — replie le digraphe `ءا` (et lui seul) en `ا`, pour
  faire se rencontrer la graphie othmanienne des formes QAC (`ءايات`) et celle que
  l'utilisateur tape (`آيات`, `ايات`). Ce n'est **pas** une suppression de hamza : une
  hamza isolée reste une lettre (`جزاء` ne devient pas `جزا`).
- **`arabic_text.normalize_text`** — **supprime** la hamza (أَرْض → رض) : **jamais** pour le
  matching de racines (over-matcherait عرض/مرض/فرض).

Le **repli** de surlignage (`_match_indices` + `_norm_match`) utilise `normalize_search`
avec en plus le **dagger alef** (U+0670) replié en alif plène, pour réconcilier `بَقَرَٰت`
(QAC) et `بَقَرَات` (mushaf vocalisé). Le chemin principal n'en a plus besoin : il compare
des positions, pas des graphies.

**Le piège de la graphie othmanienne.** QAC écrit le ā long à la manière du muṣḥaf — hamza
isolée + alif (`ءَا`) — là où l'utilisateur tape la madda `آ` ou un simple `ا`.
`normalize_root` conserve la hamza isolée, comme il le doit, si bien que la clé stockée
`ءايات` et la clé tapée `ايات` ne pouvaient **jamais** se rencontrer : ni l'une ni l'autre
des deux plis hamza ne les réconcilie (`fold_blind` donne `اايات`, alif doublé). La
résolution échouait donc, puis le repli « lenient » retirait des alifs jusqu'à tomber sur
`ايت` — une clé réelle mais ambiguë, qui répond `أتي` (venir) avant `أيي` (signe). D'où
`الايات` → racine `أتي`, 988 versets, dont aucun ne contenait le mot cherché.
`fold_madda`, appliqué **des deux côtés** aux étapes FORM et lemme de l'échelle, ferme le
trou : 27 formes `ءا` sur 27 résolvent maintenant vers la bonne racine (5 avant, 3 fausses,
19 sans réponse).

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

Le Stage 5 (`ingestion/qac_treebank.py`) en produit deux autres que ce chemin lit :

| Fichier | Contenu | Rôle |
|---|---|---|
| **`data/derived/word_function.json`** | `s:a:w` → أداة نداء / استفهام / شرط | les 297 mots qui servent d'**outil grammatical** : filtrés, jamais listés ni comptés |
| **`data/derived/word_prefixes.json`** | `s:a:w` → chaîne des segments PREFIX | les proclitiques à retirer pour obtenir le لفظ (26 001 refs, 0,5 Mo, 108 chaînes distinctes) |

Ces deux-là sont des **extraits** de `qac_words.json`, écrits par l'étape qui le produit
déjà. Ils existent pour une raison mesurée et pas par goût de la découpe :
`qac_words.json` coûte **248 Mo résidents** contre 64 Mo pour `word_index.json`, et le
chemin de la requête n'en a besoin que de quelques kilo-octets.

Ces chemins ne sont jamais écrits à la main dans le code : ils viennent des constantes de
`quran_data/paths.py`, et se lisent via les loaders paresseux de `quran_data/loaders.py`.

### Reconstruire les index

```bash
python -m ingestion.qac_morphology     # Stage 4 : morphology / lemma_index / proper_nouns
python -m ingestion.qac_treebank       # Stage 5 : word_index / root_graph / word_function /
                                       #           word_prefixes  (autonome lui aussi)
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

### 5.1. Stocker la racine *par occurrence* — ✅ fait, et le surlignage en a vécu

`morphology.json` enregistre `racine → {formes, versets}` **au niveau racine seulement** —
jamais « quelle forme / quelle racine dans quel verset ». Deux conséquences étaient
annoncées ici ; la première est réglée, la seconde reste ouverte.

- ~~**Surlignage reconstruit à la main**~~ — **résolu.** La racine par occurrence existe
  bien (`roots_resolved.json`, exposée par racine dans `root_graph.json`) et l'alignement
  mot ↔ ligne chakl aussi (`word_index.json`, 77 429/77 429). `verse_lookup.py` croise les
  deux : surlignage exact, 100 % des 50 343 occurrences, zéro faux positif — là où le
  matching par sous-chaîne se trompait sur 9,0 % des tokens surlignés. Détail et mesures :
  [`root-highlight-alignment-issue.md`](root-highlight-alignment-issue.md).
- ~~**Lemme non identifié dans le verset**~~ — **résolu.** `lemma_index.json` porte
  maintenant `word_refs` (`s:a:w`) par lemme, si bien que chaque carte surligne le mot de
  SON lemme et non ceux de ses voisins de racine (40:81 = `آيَاتِهِ` pour آيَة, `فَأَيَّ` pour
  أَيّ). `proper_nouns.json` en porte aussi, ce qui retire les noms propres du repli
  sous-chaîne. Reconstruction : `python -m ingestion.qac_morphology`.
- **Et un troisième usage, non prévu ici** — la même donnée a rendu possible le
  regroupement par **لفظ** (§ 2 bis). Savoir *quel token* d'un verset est marqué, c'est
  aussi savoir *comment il est écrit* ; il ne manquait que les proclitiques, que
  `word_prefixes.json` fournit. Aucune information nouvelle n'a dû être produite. À noter
  pour la suite : ce que cette section appelle « stocker la racine par occurrence » s'est
  révélé plus rentable que son intitulé ne le laissait croire.

### 5.1 bis. La fonction grammaticale, et pas seulement la racine

Porter une racine ne suffit pas à être une occurrence du **sens** de cette racine. Dans
«يَٰٓأَيُّهَا ٱلنَّاسُ», le segment `أَيُّ` porte bien `ROOT:أيي`, mais le mot est une formule
d'appel — le lister sous آية comme s'il s'agissait du nom « signe » est du bruit.

`word_function.json` (étape 5) nomme les mots qui servent d'**outil** :

| classe | occurrences | où |
|---|---|---|
| `أداة نداء` | 154 | أيي — «يا أيها» **et** «أيها» sans particule |
| `أداة استفهام` | 138 | كيف (80), أيي (58) |
| `أداة شرط` | 5 | أيي (3), حيث (2) |

**297 sur 50 342 (0,59 %)**, concentrées sur trois racines. Le classement vient de ce que
QAC annote, jamais d'une liste de mots écrite à la main, et il faut les **deux** couches :
la morphologie marque `INTG`/`COND` et le suffixe `ATT` ; le treebank rattrape les
interrogatifs qu'elle laisse nus (كيف est `INTG` sur 30 segments mais حرف استفهام sur 80).

**Le critère du vocatif est `ATT` (حرف تنبيه), et lui seul.** Sur un mot porteur de racine
il apparaît 154 fois et chacune est `أَيّ`, jamais un nom : il identifie donc exactement le
vocatif postiche. La particule d'appel `يا` n'est **pas** le critère — elle est facultative
(«إِنْ يَشَأْ يُذْهِبْكُمْ أَيُّهَا ٱلنَّاسُ» n'en a pas, et exiger `VOC` en laissait 10 passer), et
elle ne suffit pas non plus, puisque QAC la colle au nom qu'elle appelle : «يَٰقَوْمِ» est
`VOC` lui aussi, mais قوم signifie « peuple », et filtrer sur `VOC` emporterait **143
occurrences authentiques**.

Conséquence pour أيي : **la totalité** du lemme `أَيّ` est fonctionnelle (154 + 58 + 3 = 215),
donc le lemme disparaît et «الآيات» ne répond plus que `آيَة` — 382 مواضع, 353 آيات, 59 سور.

**Ces occurrences sont retirées des résultats** — ni listées, ni surlignées, ni comptées.
Les quatre statistiques de l'en-tête (`عدد المواضع`, `عدد الآيات`, `عدد السور`,
`عدد الألفاظ`) décrivent toutes le **même ensemble filtré** : أيي passe de 597 مواضع /
562 آيات à **382 / 353 / 59 سور / 1 لفظ**.

Attention, le **mode de comptage n'est pas uniforme**, par décision : `عدد المواضع` (mots),
`عدد الآيات` et `عدد الألفاظ` sont des décomptes **distincts** sur toute la racine, tandis
que `عدد السور` est la **somme des cartes**, pour que l'en-tête s'additionne avec ce que le
lecteur voit. شجر affiche donc 13 + 7 = 20 alors que la sourate 56 porte les deux lemmes
(56:72 `شَجَرَتَهَا`, 56:52 `شَجَرٍ`) et que seules 19 sourates contiennent la racine. Coût
assumé : قوم, avec ses 18 lemmes, annonce 225 sourates sur les 114 existantes.

Le filtre porte sur l'**occurrence**, jamais sur le verset. 40:81 contient `آيَاتِهِ`
(lexical) et `فَأَيَّ` (outil) : le verset reste, seule l'occurrence d'outil disparaît.
Supprimer l'āya entière perdrait un vrai résultat آيات parce qu'un outil s'y trouvait.

**Le coût, assumé et épinglé par un test** : sur كيف, 80 occurrences sur 83 sont des
أدوات استفهام — la racine ne rend plus que 3 versets. Aucune racine n'est vidée entièrement.

- **Homographes non désambiguïsés** — **toujours ouvert** : `كل` renvoie `اكل` / `كلل` /
  `كيل` sans savoir lequel est réellement dans tel verset. La donnée pour trancher est
  pourtant là, dans `roots_resolved.json` ; c'est la résolution (`resolve_roots`) qui ne la
  consulte pas, seul le surlignage le fait.

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
