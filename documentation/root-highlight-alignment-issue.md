# Issue — surlignage du mot dans « Word in Verses » (RÉSOLU)

> **Statut : résolu.** `_match_indices` ne décide plus du surlignage : `retrieval/
> verse_lookup.py` lit désormais les **positions** que QAC connaît déjà (`root_graph` ×
> `word_index`), exactement le §« Le fix recommandé » ci-dessous, mais **au runtime** —
> la colonne vertébrale d'alignement existait déjà, il n'y avait plus rien à construire
> au build. Mesures après correction en fin de document.
>
> Le diagnostic et les trois tentatives sont conservés tels quels : ils expliquent
> pourquoi le matching par sous-chaîne ne pouvait pas être rustiné, et ce repli existe
> toujours pour les cas que la colonne vertébrale ne couvre pas (noms propres, racine
> absente du graphe, mot non aligné).

## Symptôme

Dans l'onglet *Verse Study → Word in Verses*, certains mots ne sont **pas surlignés**
alors que le verset est bien listé. Exemple : recherche `فتى` → le verset 12:30 apparaît
mais `فَتَاهَا` n'est pas surligné (idem `لِفَتَاهُ` en 18:60/62). Seul `فَتًى` (21:60),
graphie identique à la forme stockée, est surligné.

## Cause racine

Le surlignage (`retrieval/verse_lookup.py::_match_indices`) compare une **forme stockée**
(normalisée) à chaque **token du verset** (normalisé) par **sous-chaîne**. Il échoue sur
l'**alternance de lettre faible** (لام معتلّة) et les écarts d'orthographe QAC vs mushaf :

| Forme / token | `_norm_match` |
|---|---|
| forme stockée `فَتَىٰ` | `فتيا` |
| token `فَتَاهَا` (12:30) | `فتاها` |

`normalize_search` folde `ى → ي`, donc la forme devient `فت**ي**…`, tandis que la surface
avec pronom attaché s'écrit avec un **alif plène** `فت**ا**ها`. La 3ᵉ lettre diffère → pas
de sous-chaîne → pas de surlignage. Touche **tous** les mots à finale faible (دعا/يدعو,
رمى, هدى…), pas seulement فتى. Ampleur mesurée : **737 occurrences non surlignées** sur
46 026 (~1,6 %).

## Tentatives (et pourquoi elles échouent)

### Tentative 1 — normalisation plus agressive (folder la famille alif) ❌

Folder `ى` et le dagger `ٰ` vers `ا` puis collapser les alifs doublés, dans `_norm_match`.

**Régresse** : trous 737 → **953**, et **374 régressions** (casse les mots à `ي` genuine :
`أُمِّيّ`, `بَرِيء`…). Le matching par sous-chaîne sur forme normalisée est structurellement
fragile ; on ne peut pas le rustiner proprement.

### Tentative 2 — surlignage par **position de mot** (index QAC) ⚠️

QAC fournit `sourate:aya:mot:segment` et la racine de chaque mot. Idée : ne plus matcher de
texte, mais surligner le **N-ᵉ mot** du verset. Émettre `data/derived/word_occurrences.json`
= `{verset: [{w, root, lemma}]}` / `[{w, pn}]`, et mapper « mot QAC N » → « N-ᵉ token réel »
(en sautant les tokens de waqf `ۖ ۗ …` que le CSV chakl émet séparément).

- Sur `فتى` : **corrige** (12:30 → token 7 `فَتَاهَا` surligné ✓).
- Trous globaux : 737 → **1** (le seul restant : `يَا ابْنَ أُمَّ` 20:94, mot fusionné, cf. ci-dessous).

**MAIS** — piège découvert : le comptage positionnel suppose « mot QAC N = N-ᵉ token
d'affichage ». Faux pour **460 versets** (`max mot QAC ≠ nb tokens réels`). Un décalage
produit un **mauvais** token (non vide), donc **non détecté par le comptage des trous**.

Source du décalage : QAC englobe des **particules proclitiques** (`يَا`, …) et des **mots
fusionnés** dans un seul mot, que le CSV vocalisé écrit **détachés**. Répartition des
premiers tokens des versets désalignés :

```
158  يَا      (vocatif : QAC « يٰأيها » = 1 mot ; affichage « يَا أَيُّهَا » = 2 tokens)
 93  بِسْمِ
 25  قَالَ      22  قَالُوا     16  قُلْ
 10  وَإِذْ     10  وَيَا       10  وَقَالَ
  … + mots fusionnés type « يبنؤم » (ابن+أم) = 1 mot QAC, 3 tokens affichés
```

Effet : pour un verset commençant par `يَا`, **tout mot après** est décalé de +1 → surlignage
du token précédent. Non livrable en l'état.

### Tentative 3 — **alignement** glouton mot-QAC ↔ tokens ⚠️ (incomplet)

La bonne approche : **aligner** les mots QAC aux tokens d'affichage. Clé — le **mot QAC =
concaténation de TOUS ses segments** (racine + clitiques + pronom) doit égaler le token
affiché après normalisation. Ex. `آباؤكم` = segments `آباء`+`كم` → `اباوكم` = token affiché.

Algo testé : glouton, pour chaque mot QAC accumuler les tokens d'affichage jusqu'à égalité
(normalisée). Résultat : **33 % d'échec** — l'égalité stricte bute sur des différences
d'orthographe **résiduelles** entre QAC et mushaf, non foldées identiquement :

| mot QAC (normalisé) | token affiché (normalisé) | écart |
|---|---|---|
| `الصلواة` | `الصلاة` | `ة` vs `ه` non appliqué des deux côtés + `و` médial |
| `وبالءاخرة` | `وبالآخرة` | `ءا` vs madda `آ` |
| `يومنون` (`يُؤْمِنُونَ`) | `يومنون` | OK |

## Le fix recommandé (à faire)

1. **Alignement au build**, une fois, dans `ingestion/qac_morphology.py` :
   - charger le CSV chakl (`quran_data.corpus.chakl_by_ref`),
   - reconstruire chaque **mot QAC = concat de tous ses segments** (y compris particules et
     pronoms — actuellement les segments sans racine/PN sont *skippés* et leur forme est
     perdue),
   - aligner par **égalité après un fold FORT** (matching de mots entiers, donc un fold
     agressif est sûr ici) : NFC, retrait harakat/tatweel/waqf, `ٰ`(dagger)→`ا`, `ى→ا`,
     `ة→ه`, madda `آ`→`ا` (et `ءا`→`ا`), hamza foldée — jusqu'à ~100 % d'alignement,
   - stocker dans `word_occurrences.json` l'**index de token d'affichage** résolu (`t`),
     pas seulement `w`.
2. **`retrieval/verse_lookup.py`** : lire `t` directement (union des `t` des occurrences
   filtrées par lemme/nom propre). Plus aucun comptage ni logique waqf au lookup. Même
   forme de sortie (`match_indices`) → **aucun changement frontend**. Fallback substring
   (`_match_indices`) conservé pour les versets où l'alignement échoue.
3. Rebuild : `python -m ingestion.qac_morphology`.

### Cas limites connus

- **Mots fusionnés** (`يبنؤم` = ابن+أم, ~2 versets : 7:150, 20:94) : 1 mot QAC → plusieurs
  tokens d'affichage, portant potentiellement **deux racines**. L'alignement les mappe à
  l'ensemble de tokens du mot ; il faut choisir de surligner tout le mot fusionné.
- La **déduplication `(verset, mot)`** utilisée en tentative 2 supprimait à tort la 2ᵉ
  racine d'un mot fusionné — à ne pas refaire (dédupliquer par `(verset, mot, racine)`).

## Mesures de référence

- Occurrences totales à surligner : **46 026**.
- Trous (substring actuel) : **737** ; (tentative 1) : 953 ; (tentative 2 comptage) : 1.
- Versets à alignement non trivial : **460 / 6 216**.
- Alignement glouton (égalité stricte, tentative 3) : **66 % réussite** — insuffisant,
  à améliorer via le fold fort ci-dessus.

Harness de validation : ne PAS utiliser l'oracle « la forme est sous-chaîne du token »
pour valider — il échoue sur exactement les cas qu'on répare (`آباءكم` jugé « faux » à
tort). Valider par l'alignement lui-même (taux de réussite) et par inspection ciblée.

## Depuis la rédaction : la colonne vertébrale d'alignement existe

> Ajouté après coup, sans rien retirer du diagnostic ci-dessus — **le bug, lui, n'est
> toujours pas corrigé** : `retrieval/verse_lookup.py::_match_indices` fait encore du
> matching par sous-chaîne.

Ce que « Le fix recommandé » §1 demande — un alignement calculé **au build**, une fois — a
depuis été construit par `ingestion/qac_treebank.py` (Stage 5), pour un autre besoin
(QLisan). Il produit `data/derived/word_index.json` : `s:a:w` →
`{uthmani, imlaai, chakl_char_start, chakl_char_end, aligned}`, soit **77 429 mots QAC
alignés sur 77 429** (couverture 1,00) par décalage de caractères dans la ligne chakl.

Deux différences avec le plan d'origine, à prendre en compte avant de s'en servir :

- l'ancrage est un **décalage de caractères**, pas un indice de token d'affichage (`t`) ;
- ces décalages sont calculés sur les lignes chakl **Basmala incluse**, alors que
  `_verse_row` retire le préfixe avant `_match_indices`. Il faut donc rebaser, sans quoi
  tout se décale des quatre mots de la Basmala.

## Voir aussi

- [`root-lookup.md`](root-lookup.md) — pipeline « Word in Verses » et construction des index
  QAC (§5.1 y décrit déjà la fragilité du surlignage).
- `quran_data/manifest.py` — la fiche de `WORD_INDEX_JSON` et de tout autre dataset cité ici.

## Résolution (livrée)

Le surlignage se lit maintenant, et ne se devine plus.

`VerseLookup._indices` interroge d'abord la **colonne vertébrale d'alignement** :

- `root_graph.json` — racine → les références de mots `s:a:w` qui la portent, lecture
  primaire **et** alternante (donc ٱلنَّاس est joignable sous `أنس` comme sous `نوس`) ;
- `word_index.json` — pour ce mot, sa **tranche de caractères** dans la ligne chakl.

Trois points de mise en œuvre, chacun couvert par un test dans `tests/test_verse_lookup.py` :

1. **Rebasage Basmala.** `word_index` mesure ses décalages sur la ligne chakl *brute*,
   Basmala comprise — c'est délibéré, la fiche QLisan tranche par ces décalages. Or
   `_verse_row` retire le préfixe avant de surligner. Sans rebasage, tout verset en
   Basmala décale de quatre mots (10:1 surlignait `تِلْكَ` au lieu de `آيَاتُ`).
2. **Mots fusionnés.** On retient **tous** les tokens que la tranche du mot recoupe, pas
   celui où tombe son premier caractère : QAC compte `يٰأبت` pour un mot là où la ligne
   chakl écrit `يَا أَبَتِ`. S'ancrer sur le début surlignait la particule et laissait le
   nom nu — 282 occurrences. C'est le cas limite annoncé plus haut, traité comme
   recommandé : on surligne le mot fusionné en entier.
3. **Trois états, pas deux.** Verset *avec* position → on l'utilise ; verset où la racine
   est absente → on ne surligne **rien** ; racine hors du graphe, ou mot non aligné → repli
   sur `_match_indices`. Confondre les deux derniers transformerait « je ne sais pas » en
   « il n'y a rien ».

### Mesures après correction

Vérification sans pliage : pour chaque occurrence, la tranche `[chakl_char_start,
chakl_char_end)` est-elle exactement couverte par les tokens surlignés ?

| | avant | après |
|---|---|---|
| occurrences vérifiées | 50 343 | 50 343 |
| tokens surlignés reproduisant le mot QAC | — | **50 343 (100,00 %)** |
| occurrences non surlignées (« trous ») | 737 | **0** |
| faux positifs (token surligné sans rapport) | 4 928 — **9,0 %** des surlignages | **0** |

`فتى` → 12:30 surligne `فَتَاهَا`, 18:60/62 `لِفَتَاهُ`, 21:60 `فَتًى`. Le cas d'origine de
ce document est clos.

### Deuxième passe : du niveau RACINE au niveau LEMME

La première livraison surlignait au niveau **racine** : `root_graph` sait quels mots
portent أيي, pas lequel relève de `آيَة` plutôt que de `أَيّ`. Dans les versets qui portent
les deux, **les deux cartes surlignaient les mêmes mots** — 40:81
«وَيُرِيكُمْ آيَاتِهِ فَأَيَّ آيَاتِ اللَّهِ تُنْكِرُونَ» allumait les trois mots dans chacune.
Ampleur : **2 505 lignes affichées sur 46 097 (5,4 %)**.

Croiser les deux chaînes sur la clé de lemme est **impossible** : elles ne s'accordent que
sur 1 186 racines sur 1 654 (chaîne A dit `اي / اية` pour أيي, chaîne B `ءاية / اى / ايها /
ايتها`). La correction se fait donc **dans la chaîne A**, qui construit déjà les lemmes et
possède déjà `seg.word_ref` : `lemma_index.json` (et `proper_nouns.json`) portent désormais
`word_refs` — les refs `s:a:w` de chaque occurrence — à côté de `verses`.

Au runtime, `verse_lookup.py` a trois niveaux, du plus précis au plus grossier :

1. `word_refs` du lemme → positions exactes de **ce** lemme ;
2. `root_graph` → positions de la racine (corpus construit avant `word_refs`) ;
3. `_match_indices` → sous-chaîne (dernier recours).

Effets mesurés après cette passe, sur les 46 097 lignes affichées :

| | valeur |
|---|---|
| tokens surlignés | 50 626 |
| n'appartenant pas au lemme de la carte | **0** (avant : 5,4 % des lignes touchées) |
| lignes sans aucun surlignage | **0** |
| lignes retombées sur le repli sous-chaîne | **0** |

Bénéfice collatéral : les **noms propres** (rootless, donc absents de `root_graph`) portent
eux aussi des `word_refs`. Ils quittent le repli sous-chaîne — le dernier chemin qui
l'utilisait encore — et deviennent comptables (`عدد المواضع`).

Reconstruction nécessaire : `python -m ingestion.qac_morphology` (≈ 1 s). Seuls
`lemma_index.json` (1,7 → 2,9 Mo) et `proper_nouns.json` (23 → 39 Ko) changent ;
`morphology.json`, `qac_resolution.json` et `verses_final.json` restent identiques au
bit près.

### Troisième passe : ne pas surligner la particule

Couvrir « tout le mot QAC » débordait dans l'autre sens : QAC compte `يٰأيها` pour un mot,
l'affichage écrit deux tokens, et l'on marquait `يَا` — une particule sans racine — en plus
de `أَيُّهَا`. Parmi les tokens qu'un mot recouvre, on ne garde donc que ceux qui portent sa
partie lexicale, en comparant aux formes du lemme. Ce test de sous-chaîne est sûr **ici** et
ne l'était pas dans `_match_indices` : il s'applique à l'intérieur d'une tranche que
l'alignement a déjà validée, il peut donc restreindre mais jamais dériver, et au pire il
garde tout.

283 tokens en trop retirés, 0 régression. Le cas le plus dur passe : 20:94 «يَا ابْنَ أُمَّ»
est **un** mot QAC de trois tokens portant **deux** racines — la carte ابْن marque `ابْنَ`,
la carte أُمّ marque `أُمَّ`, et `يَا` n'est marqué nulle part.

### Ce que ce document a fait gagner

Les tentatives 1 et 2 ont été **évitées** grâce à lui : la tentative 1 (normalisation plus
agressive) régressait, et la tentative 2 (comptage positionnel) était déjà connue pour
casser sur 460 versets. Le décalage Basmala et les mots fusionnés étaient tous deux écrits
ici avant d'être rencontrés.
