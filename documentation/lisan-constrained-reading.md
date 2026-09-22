# Lecture des lettres contrainte par le noyau de la racine (« تحليل اللسان »)

Ce document décrit le pipeline de la page `/lexical` **après l'inversion** : d'où vient le
noyau sémantique attesté d'une racine, comment il sélectionne un sens parmi le faisceau de
sens d'une lettre, ce que le système fait quand il ne sait pas, et comment enrichir la
curation.

Tout ce chemin est **déterministe, hors-ligne, sans LLM ni modèle d'aucune sorte**. Ce
n'est pas une préférence de style : la synthèse Lisan a déjà été dé-LLMisée une fois parce
qu'un modèle local produisait une prose fluide *contredisant* le sens attesté, et `/madar`
est en quarantaine pour la même raison. Un modèle placé dans l'étape de *sélection*
reconstruirait cette panne un étage plus bas, là où elle est plus difficile à voir.

---

## 1. Le défaut que ce pipeline remplace

Avant, `letter_lexicon.describe()` renvoyait **une** glose figée par lettre
(`abbas_meaning_ar`) et `synthesis_template` les enchaînait dans l'ordre de la racine.
Rien dans ce chemin ne savait ce que la racine signifiait, donc rien ne pouvait préférer
un sens de la lettre à un autre — il n'y en avait qu'un en fichier.

Sur `خ-ي-ر`, le résultat était :

> « القذارة والخشونة والخواء … فساد »

alors qu'Ibn Fāris écrit :

> « الخاء والياء والراء **أصله العطف والميل**، ثم يحمل عليه »

Le bug n'est pas une mauvaise ligne dans un CSV. **C'est le sens du pipeline.** La même خ
est légitimement « خشونة/خبث » dans `خ-ب-ث` (« أصل واحد يدل على خلاف الطيب ») et
légitimement « رقة/نضارة » dans `خ-ي-ر`. Toute conception incapable de produire les deux
lectures à partir de la même lettre, c'est le bug actuel avec un schéma neuf.

---

## 2. Le pipeline inversé

```
Frontend (/lexical)
        │  POST /lisan/analyze
        ▼
api/routers/lisan.py   →   linguistics/lisan/lisan_service.py
        │
        ├─ 1. mot → racine            (LexicalRetriever, échelle QAC puis lenient)
        │
        ├─ 2. racine → noyau(x) attesté(s)     root_core_store.py
        │        clé = graphie CANONIQUE de la racine QAC (jamais le fold)
        │
        ├─ 3. POUR CHAQUE noyau : sélection par lettre     sense_selection.py
        │        éligibilité (≥1 axe partagé, 0 axe antonyme)
        │        puis tri par (axes partagés, position, confiance, ordre)
        │
        ├─ 4. synthèse par noyau      synthesis_template.py
        │        ouvre sur la citation, ne nomme que les lettres sélectionnées
        │
        └─ 5. garde de divergence par noyau     sense_selection.detect_divergence
                 DÉTECTE, ne corrige jamais
```

Les lettres ne sont lues **qu'après** que le noyau est en main. C'est la seule propriété
qui distingue ce pipeline du précédent.

---

## 3. Les trois datasets

Tous trois sont dans `data/references/` (érudition curée), chacun avec sa constante dans
`quran_data/paths.py`, son loader caché dans `quran_data/loaders.py` et son entrée dans
`quran_data/manifest.py` — `tests/test_quran_data.py` échoue sinon. Un quatrième fichier
les accompagne sans être un dataset : `letter_senses.lock.json` **gèle** le troisième à une
version (§8.1).

### 3.1 `semantic_axes.json` — le vocabulaire **fermé**

```json
{ "id": "atf", "label_ar": "العطف والرقة واللين والرأفة", "antonym": "qaswa" }
```

47 axes. Les deux autres datasets ne référencent des axes que **par `id`**.

Pourquoi fermé ? Parce que la sélection est une **intersection d'ensembles** entre les axes
du noyau et ceux d'un sens. Avec des axes en texte libre, « ميل » et « الميل والانعطاف »
ne s'intersectent pas, et l'accord devient un accident de formulation : le mécanisme aurait
l'air de fonctionner et échouerait de façon imprévisible.

Le lien `antonym` est **symétrique** (validé) et c'est lui qui transforme « ces deux-là ne
partagent rien » en « ces deux-là sont opposés » — la différence entre les motifs de rejet
`no-shared-axis` et `conflicting-axis`.

> **Granularité.** Trop grossier, tout s'apparie ; trop fin, rien ne s'apparie. Un axe
> utilisé par un seul noyau ou un seul sens est un signal d'alerte.
>
> Le cas à justifier est `atf`, qui regroupe « العطف والرقة واللين والرأفة ». Ibn Fāris
> emploie عطف dans deux emplois que le français sépare : *pencher vers* (« العطف والميل »,
> l'aṣl de `خير`) et *se pencher sur*, la tendresse (« الرقة والعطف والرأفة », l'aṣl de
> `رحم`). **On les tient sous un seul axe parce que عطف signifie littéralement « plier,
> infléchir », et que les deux emplois en dérivent** : plier *vers* quelque chose est
> l'inclination, se plier *sur* quelqu'un est la compassion. Ce n'est pas une homonymie
> que l'axe écraserait, c'est une seule image qui se ramifie — et l'axe nomme l'image.
>
> Ce qui ne justifie **pas** ce regroupement : le fait que le séparer viderait la lecture
> de `خير`. Une conséquence sur un résultat n'est pas un argument sur la langue, et
> l'accepter comme tel serait la curation circulaire du §8 déplacée au niveau du
> vocabulaire — un cran plus haut, donc un cran plus difficile à voir. Si une lecture
> d'Ibn Fāris montrait que les deux emplois sont étrangers l'un à l'autre, l'axe devrait
> être scindé **et** `خير` devrait alors ne rien apparier.

### 3.2 `root_cores.json` — le noyau attesté, cité

```json
"خير": [{
  "gloss":    "العطف والميل",
  "verbatim": "الخاء والياء والراء أصله العطف والميل، ثم يحمل عليه",
  "axes":     ["atf", "mayl"],
  "polarity": "neutral",
  "source":   "ابن فارس، معجم مقاييس اللغة",
  "edition":  "Harun_DarAlFikr"
}]
```

- **`verbatim` est byte-identique** au segment correspondant de `maqayis_asl.csv`. Le
  validateur le vérifie. Seuls `gloss`, `axes` et `polarity` relèvent de la curation :
  la moitié « citation » ne peut donc pas dériver.
  Précision sur ce que « les mots d'Ibn Fāris » signifie exactement ici : la chaîne est
  *Maqāyīs → édition OpenITI → `scripts/build_maqayis_dataset.py` → `maqayis_asl.csv`*, et ce
  dernier est **dévocalisé** (le texte y porte «تعديا», non «تعدياً»). Le `verbatim` est donc
  fidèle à l'octet près **au dataset livré**, qui est lui-même un parse d'une édition — pas à
  un manuscrit. La garantie porte sur le dernier maillon, et c'est le seul qu'un test puisse
  tenir.
- **La valeur est une LISTE.** `ظلم` a deux aṣl (« خلاف الضياء والنور » ‖ « وضع الشيء غير
  موضعه تعديا »). Ils ne sont **jamais fusionnés** et leurs axes ne sont **jamais mis en
  commun** : mettre en commun rendrait presque n'importe quel sens éligible et
  reconstruirait le mélange indifférencié que ce changement supprime.
- **`polarity` décrit l'aṣl TEL QUE CITÉ**, et vaut `neutral` dès que l'aṣl est descriptif.
  C'est ce qui rend le cas `ك-ف-ر` traitable : Ibn Fāris donne « الستر والتغطية », qui est
  descriptif ; la charge négative de la racine est un fait d'**usage coranique**, pas
  d'étymologie. Enregistrer cette charge d'usage comme polarité de l'*aṣl* ferait du dataset
  un lexique de sentiment, et la garde se déclencherait sur toute racine dont l'usage et
  l'étymologie divergent — c'est-à-dire beaucoup.

#### ⚠️ Le piège de la clé

Les clés sont la **graphie canonique de la racine QAC** — la graphie exacte, porteuse de
hamza, que renvoie `LexicalRetriever._canon` — et **jamais** la forme repliée par
`normalize_root` sur laquelle `maqayis_asl.csv` est indexé.

C'est le raccourci plausible qui produit un dataset n'appariant ~0 racine hamzée et
dégradant en « pas de noyau », ce qui ressemble exactement au comportement normal d'une
racine non couverte. **La panne est silencieuse.** Le validateur vérifie que chaque clé est
une vraie clé de racine QAC ; c'est ce qui la rend bruyante.

Le script de semis peut *replier* une clé pour **trouver** la ligne Maqāyīs — il stocke
toujours la graphie canonique.

### 3.3 `letter_senses.csv` — une lettre porte un faisceau

Une ligne par **(lettre, sens)** :

| colonne | rôle |
|---|---|
| `letter` | le glyphe de base (les supports de hamza se replient sur `ء`) |
| `sense_id` | identifiant stable, unique **dans** la lettre |
| `gloss_ar` | le sens, en arabe |
| `pole` | `positive` / `negative` / `neutral` |
| `axes` | ids d'axes, séparés par `;` |
| `position` | `initial` / `medial` / `final` / `any` |
| `gesture_ar` | le geste articulatoire dont le sens est lu |
| `source` + `page` | l'autorité citée et sa page — **obligatoires** |
| `confidence` | `verified` / `high` / `summary` |

59 sens sur les 28 lettres de base, transcrits de Ḥasan ʿAbbās, *خصائص الحروف العربية
ومعانيها* (1998), avec la page. Le rang de `confidence` mesure **la force de l'attestation,
pas la justesse du sens** :

- `verified` — la valeur de tête de la lettre (`core_meaning`). Chaque lettre en a
  exactement une.
- `high` — une tendance que l'auteur énonce sous condition : soit dépendante de la position
  (`position_notes`), soit dépendante de la réalisation (« إن رُقّقت… وإن خُنخنت… » pour ن).
- `summary` — une observation marginale, y compris un **contre-exemple**. Le sens
  «الستر والاختفاء» de ر en relève : l'auteur y relève dix mots qui *contredisent* la
  caractéristique de la lettre («عشرةُ مصادرَ تناقض خاصية الظهور»). C'est plus faible qu'une
  tendance, et le rang le dit — mais le sens reste sélectionnable, et c'est le seul que `كفر`
  apparie. La formulation de la source voyage jusqu'à l'écran, entre parenthèses.

Le `pole` est une propriété de **la glose**, jamais de la racine qui la sélectionne : une
glose descriptive («الشدة والقساوة», «الظلام والسواد») est `neutral` même quand la racine qui
la retient est négative. Seules les gloses véritablement évaluatives — خسة/قذارة, نتانة,
عيوب/يأس d'un côté ; رقة/جمال/صفاء/نضارة de l'autre — portent un pôle.

**Un sens sans source ni page est refusé à la validation.** Le moteur Tahlīl refuse déjà de
publier une prose générée qu'il ne peut pas citer (`linguistics/tahlil/citations.py`) ; on
tient l'érudition curée au même seuil. Sans cette barrière, l'étape de sélection devient une
machine à produire le sens qui *fait marcher* la racine — c'est-à-dire le bug actuel avec
plus d'étapes.

`arabic_letters_dataset.csv` garde en face les 28 lignes d'identité et de phonétique et a
**perdu** `abbas_meaning*` / `abbas_keywords*`. Un CSV dénormalisé unique répéterait
`makhraj_ar` sur chaque ligne de sens et les laisserait diverger.

**Ce fichier est gelé** (`letter_senses.lock.json`, v1.0.0) : les racines se curent contre
une feuille de lettres fixe, et une lettre ne change que par une nouvelle version sourcée.
Le pourquoi et le comment sont au §8.1 — ils appartiennent à la procédure de curation, pas
à la description du format.

---

## 4. L'algorithme de sélection

Pour chaque lettre de la racine, avec **un** noyau (`sense_selection.select_for_letter`) :

1. **Éligibilité.** Garder les sens qui partagent ≥ 1 id d'axe avec le noyau **et** ne
   portent **aucun** axe déclaré antonyme d'un axe du noyau. L'ordre compte : un sens
   portant un axe en conflit est rejeté `conflicting-axis` **quels que soient** ses autres
   recouvrements. Sans conflit et sans axe partagé → `no-shared-axis`.
2. **Tri** des éligibles, du plus fort au plus faible, par le tuple fixe :

   ```
   (nombre d'axes partagés, ajustement de position, rang de confiance, −index de déclaration)
   ```

   *ajustement de position* = 1 si la `position` du sens vaut celle de la lettre dans la
   racine (`initial`/`medial`/`final`) **ou `any`**, sinon 0. `any` vaut donc 1, pas 0 : c'est
   la valeur par défaut du dataset (Ḥasan ʿAbbās n'énonce pas de position pour chaque sens) et
   la pénaliser reviendrait à traiter « l'auteur n'a rien précisé » comme « ne s'applique pas
   ici ». En revanche `selection_rule` ne vaut `axis-match+position` que si le sens a nommé la
   position **réelle** de la lettre — sinon il revendiquerait une preuve que la citation n'a
   pas donnée. *(La note R7 de `design.md` dit « `any` contribue 0 » ; c'est elle qui est
   périmée — la Requirement du spec et le code disent 1.)* Confiance : `verified` > `high` >
   `summary`. Le dernier terme fait trancher les ex æquo par **l'ordre du curateur**, jamais
   par l'ordre d'itération d'un dict.
3. Le premier gagne. Les éligibles battus sont marqués `outranked`.

Le tuple est **total**, donc le résultat est reproductible : même mot, même processus ou
processus neuf, mêmes sélections (`tests/test_lisan_regression.py` le mesure dans un
sous-processus).

### Ce qui n'a pas été retenu, et pourquoi

- **Un score numérique pondéré** — les poids seraient inventés et devraient être réglés
  contre les exemples mêmes qu'ils sont censés juger.
- **Des embeddings entre la glose et l'aṣl** — plausible, intraçable, et cela ferait
  dépendre la lecture d'un modèle de 1,1 Go sur une page qui ne coûte aujourd'hui rien
  (`HybridSearch` est paresseux précisément pour que les pages lexicales ne détiennent
  aucune mémoire modèle).
- **Toujours prendre le sens le plus fiable** — cela ignore le noyau, qui est tout le
  changement.

---

## 5. Ce que le système fait quand il ne sait pas

### 5.1 Une lettre sans sens éligible

`selection_rule: "unmatched"`, `selected: null`, **aucun** sens de repli. Tous ses sens
apparaissent en `discarded` avec `no-shared-axis` (ou `conflicting-axis`), et la synthèse
ne lui attribue aucun sens. Une lecture partiellement contrainte est quand même renvoyée et
marquée comme telle : **la lecture partielle honnête est le produit** ; combler le trou en
silence est le comportement qu'on supprime.

### 5.2 Une racine sans noyau

`constrained: false`, un `warning` en arabe, **aucune synthèse**. Les sens des lettres sont
renvoyés dans `inventory` — le faisceau entier, rien de sélectionné, explicitement étiqueté
non contraint.

Le coût est assumé et énoncé : **au plus 1 290 des 1 656 racines QAC** (77,9 %) peuvent
avoir un noyau Maqāyīs, et l'ensemble curé démarre bien plus bas — **5 racines, 6 noyaux
(0,3 %)** à la fusion de ce changement.

> Le plan initial annonçait un plafond de 1 149. Ce chiffre est celui du **repli seul** :
> `maqayis_asl.csv` est indexé sur la forme repliée, mais le store *et* le validateur
> essaient en plus le **pont géminé** (`اب` ↔ `ابب`), ce qui atteint 141 racines de plus.
> `python scripts/validate_lisan_datasets.py` recalcule les deux chiffres depuis les
> fichiers livrés et n'en lit jamais un en dur. C'est un résultat normal pour une
grande minorité de racines, pas un cas limite — et c'est préférable à conserver pour elles
la lecture qui a produit le bug `خ-ي-ر`.

**Il n'existe aucun drapeau restaurant l'ancienne concaténation.** Un drapeau qui
restaurerait le bug `خ-ي-ر` est précisément ce que ce changement existe pour retirer.

---

## 6. La garde de divergence

Après la sélection, la polarité agrégée des sens **sélectionnés** est comparée à la
`polarity` du noyau. Si les deux sont non neutres et se contredisent, la lecture porte un
objet `divergence` (polarité du noyau, polarité de la lecture, lettres concernées, message
arabe) et l'UI l'affiche.

**La garde ne relance pas la sélection, ne re-trie pas, ne retire ni ne substitue aucun
sens.** Une garde corrective — re-trier jusqu'à ce que les pôles s'accordent — rendrait
l'outil incapable de *jamais* être en désaccord avec l'aṣl : il aurait donc toujours l'air
d'avoir raison. C'est exactement l'inquiétude que soulève le cas `ك-ف-ر` : une contrainte
qui force la réponse.

Un déclenchement est une information sur **les données** (sens de lettres, axes du noyau ou
polarité mal curés) et se traite par la curation, jamais en affaiblissant la vérification.

> **Corollaire à écrire noir sur blanc : une garde qui ne se déclenche jamais est un signal
> d'alerte, pas un succès.** Cela suggérerait que les sens de lettres ont été curés pour
> coller aux noyaux (§8).

Un noyau `neutral` ne lève **jamais** de divergence sur le seul terrain de la polarité.

> **État à la fusion : la garde ne s'est jamais déclenchée.** Sur les 6 noyaux curés, trois
> sont `neutral` (la garde sort tôt, par conception) et les trois évaluatifs s'accordent avec
> leur lecture. Par son propre corollaire, ce n'est pas un succès : c'est le déclencheur
> d'audit que la conception demandait de surveiller, et il est actuellement tiré. Avec un
> ensemble curé de 5 racines c'est attendu ; il faudra le relire au premier vrai lot de
> curation. `tests/test_lisan_regression.py::test_no_curated_root_diverges_today` consigne
> l'état — ce test n'est pas un invariant du mécanisme, c'est un enregistrement : s'il se met
> à échouer, ce sont les données qu'il faut auditer, pas la vérification. Le seuil au-delà
> duquel ce silence cesse d'être excusable est désormais chiffré et imprimé : **50 racines**
> (§8.3).

---

## 7. Ce que produit l'ensemble curé actuel

| racine | noyau | lettre sélectionnée | résultat |
|---|---|---|---|
| `خير` | « أصله العطف والميل » (neutral) | **خ** → « الرقة والنضارة » (positive), via l'axe `atf` | ي et ر `unmatched` ; le sens « الخسة والقذارة » est **rejeté et affiché** |
| `خبث` | « خلاف الطيب » (negative) | **خ** → « الرداءة والخسة والقذارة » (negative), via `khubth` | ب et ث `unmatched` |
| `كفر` | « الستر والتغطية » (neutral) | **ر** → « الستر والاختفاء » (neutral), via `satr` | ك et ف `unmatched` ; aucune évaluation positive ni négative |
| `ظلم` | deux aṣl | noyau 1 : **aucune lettre** appariée ; noyau 2 : **ظ** → « الشدة والقساوة » via `qaswa` | sous le noyau 2, «الليونة» de ل et م est rejetée `conflicting-axis` (عطف est l'antonyme déclaré de قساوة) ; leurs autres sens le sont en `no-shared-axis` |
| `رحم` | « الرقة والعطف والرأفة » (positive) | **ح** et **م** → sens positifs via `atf` | ر `unmatched` ; `outranked` exercé sur les autres sens de ح |

**La paire minimale `خ-ي-ر` / `خ-ب-ث` est le test décisif** : même lettre, deux noyaux, deux
sens différents. Un mécanisme incapable de produire les deux n'a pas corrigé le défaut, il
l'a réétiqueté.

### Une honnêteté à consigner

Sur `خ-ي-ر`, la خ est appariée par l'axe **`atf` (العطف)**, pas par `mayl` (الميل). Aucune
autorité au niveau de la lettre n'attribue ميل à خ : Ḥasan ʿAbbās donne pour la خ adoucie
« الرقة والنضارة » (p. 173-179). Le noyau cite « العطف **و**الميل » : l'appariement se fait
sur la moitié qui est attestée des deux côtés, et elle l'est parce que عطف nomme le
**pli** dont l'inclination et la tendresse sont les deux versants (§3.1).

Écrire un sens « ميل » pour خ afin de faire coller `خ-ي-ر` aurait été exactement la curation
circulaire que le §8 interdit — et ce n'est plus seulement une consigne : le gel du §8.1
rend cette édition rouge à la validation. La mutation a été exercée, avec la ligne
`خ,mayl_invented,الميل والانعطاف,…` ajoutée au CSV : le validateur sort en 1.

Il reste que cet appariement tient à **un seul tag** sur **un seul sens**. Retirer `atf` de
`خ/riqqa` fait de `خ-ي-ر` une lecture vide. Ce n'est pas un argument pour le garder — c'est
la raison de l'avoir écrit ici, pour qu'un futur curateur sache ce qu'il déplace.

---

## 8. Curer une nouvelle racine

### 8.1 Le dataset des lettres est GELÉ

`letter_senses.csv` est figé à une version, et `letter_senses.lock.json` la porte : un
`version` sémantique, le **sha256 des octets du CSV**, ses compteurs, et un `history` dont
chaque entrée cite la raison **et** l'autorité qui la justifie. Version gelée initiale :
**1.0.0**, 59 sens sur 28 lettres.

Le gel ne protège pas contre une faute de frappe — il protège contre un mode d'échec qui
*ressemble à un succès*. Un curateur rencontre une racine qui n'apparie rien ; il ajoute un
sens à l'une de ses lettres ; la racine « marche » désormais. Rien dans les données ne
consigne que la preuve a été écrite pour coller à la conclusion. C'est la curation
circulaire R1, et elle est invisible après coup. Un digest la rend rouge.

Les quatre règles, dans l'ordre où elles mordent :

1. **Le dataset des lettres ne bouge pas** pendant une campagne de curation de racines.
2. **Une racine qui n'apparie rien est un RÉSULTAT.** On le consigne — le rapport le nomme
   (`ظلم#0` aujourd'hui) — on ne retouche pas une lettre pour le faire disparaître.
3. **Une lettre ne change que par une nouvelle version**, justifiée par une autorité *au
   niveau de la lettre* avec sa page. Jamais par une racine qui ne marchait pas. Le
   validateur refuse une entrée d'historique sans `source`.
4. **Le semeur ne touche jamais au dataset des lettres.** `build_root_cores_seed.py`
   n'écrit que `root_cores.json` ; deux tests l'épinglent — l'un lit son source, l'autre
   vérifie que le digest du CSV survit à un `write()`.

Changer une lettre reste légitime : ce n'est pas une interdiction, c'est un passage obligé
par une version datée et sourcée. Le message d'échec du validateur ne nomme que ces deux
issues — annuler, ou versionner — et jamais « ajouter le sens ».

### 8.2 La procédure

1. **Semer** — `python scripts/build_root_cores_seed.py` remplit `verbatim`, `source`,
   `edition` et la clé canonique depuis `maqayis_asl.csv`, en laissant `axes` vide et
   `polarity` à `null`. Il n'invente **jamais** d'axes ni de polarité, et **re-lancer le
   script ne réécrit aucune curation existante** — c'est pourquoi `root_cores.json` est
   enregistré comme *non régénérable* au manifeste bien qu'il ait un producteur.
2. **Curer** `axes` et `polarity` en lisant le `verbatim`, et **seulement** lui.
3. **Ne pas toucher aux lettres.** Si aucun sens n'est éligible, la racine se lit
   `unmatched` et c'est le résultat qu'on garde.
4. **Valider** — `python scripts/validate_lisan_datasets.py`. Une entrée à moitié curée
   (`axes` vide ou `polarity` nulle) est un **échec** : un fichier inachevé ne peut pas
   partir en production. Un CSV de lettres modifié sous une version gelée aussi.

### 8.3 L'indicateur de méthode

Le validateur imprime deux taux à chaque exécution, calculés en faisant tourner **l'étape
de sélection réelle** sur l'ensemble curé — pas une seconde implémentation, qui ne
mesurerait qu'elle-même :

| taux | lecture |
|---|---|
| **unmatched** | part des créneaux-lettres qu'aucun sens n'a pu remplir. Élevé quand la couverture est mince, et c'est **sain** : c'est le système qui s'abstient. |
| **divergence** | part des lectures dont le pôle agrégé contredit la polarité de leur propre noyau. C'est la **sonde de falsifiabilité**. |

Au 2026-09-22 : **66,7 %** d'unmatched (12/18 créneaux), **0 %** de divergence (0/6
lectures), 5 racines curées.

Le verdict est imprimé en clair, et il y a un seuil :

- **< 50 racines** — « not yet testable ». Cinq racines ne peuvent pas exercer une
  contradiction ; 0 % ne dit rien, ni dans un sens ni dans l'autre.
- **≥ 50 racines et 0 % de divergence** — « **NOT FALSIFIABLE** ». La garde détecte et ne
  corrige jamais ; si elle n'a jamais rien vu sur un ensemble large, c'est que les sens de
  lettres s'accordent avec tous les noyaux qu'ils rencontrent — exactement la silhouette
  qu'aurait une curation des lettres faite pour coller aux racines. Le rapport le dit à
  haute voix plutôt que de laisser lire un 0 % comme un bon bulletin de santé.

Ces taux ne valent que comme **tendance** entre deux campagnes. C'est pourquoi le rapport
les imprime même sur une exécution propre : une campagne qui fait monter la couverture sans
laisser ses chiffres derrière elle ne laisse rien à comparer.

### 8.4 Les deux règles qui protègent la curation

- **R1 — curation circulaire.** Si un curateur écrit les sens de خ *en regardant* `خ-ي-ر`,
  l'appariement est tautologique et ne prouve rien. Les garde-fous : chaque sens cite une
  autorité **au niveau de la lettre** avec une page ; l'ensemble des sens se cure **par
  lettre**, jamais par racine ; le gel du §8.1 rend la retouche opportuniste rouge ; et une
  garde durablement silencieuse est un signal d'audit, désormais imprimé comme verdict
  (§8.3). Ce risque ne s'élimine pas par un mécanisme, il se garde visible.
- **R5 — deux datasets peuvent désormais se contredire.** Un noyau mal curé corrompt
  **toutes** les lettres de cette racine. D'où la vérification byte-à-byte du `verbatim` :
  seule la moitié « opinion » (axes, polarité) peut dériver, et la garde surveille la
  polarité.

---

## 9. Le contrat HTTP

`POST /lisan/analyze` publie **la contrainte, pas seulement la conclusion** : `cores`,
`constrained`, une entrée de `readings` par noyau (chacune avec, par lettre, `selected` /
`discarded` / `selection_rule` / `matched_axes`, sa `synthesis` et sa `divergence`),
`inventory`, `axis_labels`, `warning` et le `disclaimer` interprétatif.

**Rupture assumée** : `sequential_reading` a disparu, et `letters[].meaning` n'existe plus
comme glose unique. Ces deux champs décrivent un pipeline qui n'existe plus ; le frontend
vit dans ce dépôt et `/lisan/analyze` n'a qu'un seul appelant, donc une couche de
compatibilité n'aurait préservé qu'une forme dont la sémantique est partie.

La validation d'entrée est inchangée : 422 sur entrée vide ou non arabe, 200 avec
`root: null` et un `message` arabe quand rien ne résout.

---

## 10. Hors périmètre

`linguistics/tahlil/huruf.py` continue de lire `arabic_letter_semantics_hasan_abbas.json`
**inchangé** ; `/madar` reste en quarantaine ; `ishtiqaq_akbar` (les تقاليب d'Ibn Jinnī)
reste la seule section non contrainte de la page ; aucun modèle n'est introduit nulle part.
