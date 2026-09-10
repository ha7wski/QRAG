# Issue — surlignage du mot dans « Word in Verses » (non résolu, reverté)

> **Statut : investigué, puis reverté au dernier commit.** Le fix propre (alignement
> mot-QAC ↔ token d'affichage au build) est **différé**. Ce document conserve le
> diagnostic complet et les mesures pour qui reprendra le sujet.

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
