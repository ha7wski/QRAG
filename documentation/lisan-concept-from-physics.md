# Le مفهوم engendré depuis la physique des lettres

Ce document décrit le **second** moteur de `/lexical` : celui qui compose le concept d'une
racine à partir de la description tajwīdique mesurable de ses lettres — مخرج et صفات — et
qui ne rencontre Ibn Fāris qu'**après**, comme épreuve et non comme entrée.

Il coexiste avec le moteur *core-first* décrit dans
[`lisan-constrained-reading.md`](lisan-constrained-reading.md). Aucun des deux n'est déclaré
correct ici. Le présent document publie ce que la mesure a donné, et elle est négative.

> ## ⛔ EXPÉRIENCE CLOSE
>
> **`k / 40 = 0`.** Le chantier est clos, la spec archivée, et **rien n'est réparé** : pas
> d'élargissement du vocabulaire de traits, pas de découpage du حلق, pas de fenêtre retouchée.
> L'échec n'est **pas paramétrique** — 162 des 176 manques sont `imported`, donc la notion
> manquante n'est pas une affaire de granularité. La route `POST /lisan/concept` reste montée et
> le مفهوم reste affiché, étiqueté comme une expérience close, avec son nombre et sa réserve à
> côté : un résultat négatif retiré de l'écran devient un résultat invérifiable.
>
> La décision et sa justification complète : **§10.6**. La portée exacte de ce qui est conclu —
> et de ce qui ne l'est **pas** : **§10.1–10.5**.
>
> **Mesure sœur.** La table *publiée* de Samer Islambouli, transcrite et non curée, a été
> passée au même harnais sur un lot témoin neuf : **`k / 40 = 0`** également, 28 attestations
> couvertes sur 379. Résultat, réserves et protocole :
> [`lisan-islambouli-table.md`](lisan-islambouli-table.md).

---

## 0. Le résultat, d'abord

> ## **k / 40 = 0**
>
> Aucune des 40 racines témoins n'a un concept couvrant **toutes** ses attestations gelées.
> Répartition déclarée avant la mesure : **0 / 25** pour les racines portant une lettre à
> signature (`ر ش ض ل ص ز س`), **0 / 15** pour celles qui n'en portent pas.
>
> **RÉSERVE, publiée avec le nombre et non ailleurs.** La règle de composition n'est **pas
> entièrement pré-enregistrée**. La fenêtre réalisée — combien d'أصول par position
> atteignent la phrase — a été fixée à **deux**, puis élargie à **trois** *après* une mesure
> revenue négative sur `ضرب`, le cas de développement déclaré. Les positions, l'ordre de
> rareté et le départage ont été fixés avant d'être éprouvés ; **la fenêtre, non**. Ce qui
> contient cette exposition : les 40 racines témoins n'ont jamais été lues au moment où la
> fenêtre a changé, et `ضرب` est exclue de `k`. Ce que cela n'efface pas : un paramètre libre
> de la règle a été réglé en regardant un résultat, et **un lecteur qui décote `k / 40` pour
> ce motif lit correctement**.

Sur 183 attestations gelées, **7 sont couvertes**. Les 176 manques se classent ainsi :

| classe | n | ce qui a échoué |
|---|---|---|
| `imported` | 162 | la glose exige une notion absente du vocabulaire de traits |
| `direction` | 8 | l'ordre positionnel contredit la glose |
| `inert` | 6 | les أصول sont compatibles avec la glose et n'en disent rien |

**C'est cette distribution qui est le résultat, pas le zéro.** Le moteur ne manque pas ses
attestations en disant une chose fausse, ni en la disant dans le mauvais ordre : il les
manque parce que la notion n'est **pas dans le vocabulaire**. `عقل` demande إدراك. `خوف`
demande un affect. `نصر` demande deux parties. `قول` demande la parole — et comme tous les
أصول décrivent *comment* un son est produit, « parole » est précisément la notion que ce
vocabulaire ne peut jamais affirmer sans circularité. C'est la frontière la plus nette que
la méthode ait tracée autour d'elle-même.

Les cinq racines témoins ayant au moins une attestation couverte : `قعد`, `مسك`, `دخل`,
`رجع`, `رود`. Elles ont en commun de désigner un mouvement ou une tenue **sans domaine
externe** — s'asseoir, retenir, entrer, revenir, aller lentement. Dès qu'une glose nomme
Dieu, le péché, l'eau, la prière, un organe ou une catégorie juridique, ce domaine est
importé et l'attestation tombe.

`ضرب`, cas de développement, est publiée et comptée dans aucune moitié : **1 / 5**, partielle
— exactement ce que §D9 avait prédit. `الضرب باليد` est atteint ; `ضرب المثل` ne l'est pas,
et §D6 avait déjà écrit qu'il ne le serait pas.

---

## 1. Pourquoi un second moteur

Le moteur *core-first* a corrigé un vrai défaut : une lettre porte un **faisceau** de sens et
rien ne sélectionnait parmi eux. Mais cette correction a une conséquence que sa propre
spécification n'avait pas anticipée — **l'أصل entre en amont, donc rien en aval ne peut dire
quoi que ce soit que l'أصل ne dise déjà**. Un sens survit à la sélection en partageant un axe
avec le noyau : la lecture publiée est structurellement une paraphrase du noyau.

Un moteur qui ne peut qu'être d'accord avec son entrée ne lit pas les lettres ; il reformule
une entrée de dictionnaire avec des étapes en plus.

Ce moteur-ci inverse la direction une seconde fois : le concept est engendré **en aveugle**
depuis la phonétique mesurable de chaque lettre, et Ibn Fāris devient le **test**.

---

## 2. La couche objective, et elle seule

Lues : les colonnes `makhraj_ar` et `sifat` de `data/references/arabic_letters_dataset.csv`,
pour les 28 lettres. Rien n'y est curé pour ce moteur et rien n'y est ajouté.

**Bannies : les colonnes `ibn_jinni_note*` du même fichier.** Ce sont une glose interprétative
figée par lettre — exactement l'artefact que toute l'histoire de `/lexical` cherche à
éliminer. Les lire ici reconstruirait le défaut d'origine sous un autre nom.
`tests/test_physical_primitives.py` vérifie qu'aucun module du moteur ne les nomme.

### La réduction à un vocabulaire fermé

Les chaînes brutes ne sont pas utilisables telles quelles :

- **19 valeurs de صفة** dont plusieurs ne distinguent rien. Une صفة portée par 24 lettres sur
  28 n'est pas une information. Règle : seul le membre **marqué** d'une paire opposée produit
  un trait ; le membre non marqué (`انفتاح`, `استفال`) est l'état par défaut. Les صفات
  privatives, équipollentes, لا ضد لها et contestées suivent la même règle de réduction.
- **18 valeurs de مخرج** pour 28 lettres, ce qui est un glossaire par lettre déguisé. Elles
  s'effondrent sur les **cinq zones classiques** : حلق · أقصى اللسان · وسط اللسان ·
  طرف اللسان · شفتان.

Le résultat est **21 traits**, dans `linguistics/lisan/concept/features.py`.

---

## 3. La table gelée

`data/references/physical_primitives.csv` — une ligne par (trait, أصل), **20 أصول** sur 21
lignes, fermée. `physical_primitives.lock.json` porte la version, la date de gel et le sha256
des octets : `a9fa94d162f6…`, v1.0.0.

**Chaque ligne déclare un `status`.** `attested` exige une autorité nommée et des pages
réelles ; `hypothesis` est une revendication du projet, portant le fait tajwīdique
incontesté comme `physical_basis` et citant des appuis sans leur emprunter d'autorité.

> **Toutes les lignes de la table livrée sont `hypothesis`.** Aucune source ne tabule les
> صفات en une correspondance générale qualité → notion : Ibn Jinnī illustre le principe sur
> des cas particuliers, Ḥasan ʿAbbās donne des sens par lettre. La table est la construction
> du projet et le dit. C'est précisément ce qui rend `k / 40` capable de la falsifier — et
> `k / 40 = 0` est cette falsification.

La table ne bouge que par une nouvelle version de lock justifiée par une autorité **au niveau
du trait**, avec page. Jamais parce qu'une racine se lit mal.

---

## 4. La composition

**Règle positionnelle, posée une fois et jamais adaptée** : la 1ʳᵉ radicale **ouvre** l'action,
la 2ᵉ en est le **corps**, la 3ᵉ la **conclut**. Aucun chemin de code n'en assigne d'autres, et
il n'existe pas de mécanisme d'exception par racine où en ajouter une.

**Ordre dans une position** : par **couverture croissante** — l'أصل porté par le moins de
lettres d'abord — départage par ordre de déclaration dans la table. `ظُهور` est porté par 17
lettres sur 28 et ne vaut presque rien ; `تَكرار` est porté par une seule et est presque sa
signature. La règle démote les أصول quasi universels sans cas particulier.

**Fenêtre réalisée : trois par position.** Le reste est retourné en `carried`, affiché sous la
phrase, jamais jeté. **Ce nombre est le seul de cette section à avoir changé après une
mesure** — voir §6.

### Les cas que la règle ne couvre pas

| cas | n | règle |
|---|---|---|
| porteurs de hamza `أ ؤ ئ آ` | 138 racines | repliés sur `ء` par une table explicite porteur→hamza. **Pas** `arabic_text.fold_carrier`, qui replie vers le *porteur* et supprime la hamza — il résoudrait les 139 positions vers une lettre absente de la feuille et les rendrait « muettes » avec une raison plausible au lieu de lever. |
| `ا` nu dans la clé (`اني`, `اول`, `هاء`, `هات`) | 4 racines | `ا` n'est pas dans la feuille des 28 et n'a pas de مخرج propre : **aucun أصل**, position muette, concept `partial`, lettre nommée. Aucun repli, aucun drapeau qui en restaure un. |
| quadrilitères | 43 racines | **aucun concept**, avec raison énoncée. La règle à trois positions n'est pas étirée à quatre : adapter la règle au cas est ce que cette conception interdit. Une règle à quatre positions serait un changement futur, posé d'avance. |
| radicales faibles `و`/`ي` | — | **aucune exception.** Ce sont des consonnes dans la feuille et la table s'applique mécaniquement. 16 des 40 racines témoins en portent une : le choix est mesuré, pas supposé. |

---

## 5. La sonde de collision — une porte dure, franchie deux fois

La table projette 28 lettres sur un nombre fini de profils. Si deux lettres sont
indiscernables, deux racines qui n'en diffèrent que par elles reçoivent le **même** concept,
et la méthode ne lit alors pas la racine. §D13 a fait de cette vérification une **porte**,
courue avant toute curation.

**Passe 1 — sur le brouillon ṣifāt seules (18 profils pour 28 lettres) : COLLISION CONFIRMÉE,
5 sur 5.** `حرب` = `حرج` = `حرد` · `تبر` = `كبر` · `كود` = `كيد`. Aucun `order-distinct`,
aucun `distinct`. Structurel, pas un bug du compositeur.

Le repli **déclaré à l'avance** a joué : cartographier les cinq zones classiques devient la
**v1.0.0** de la table — un remplacement, pas une incrémentation. Le sha du brouillon
supplanté est dans `history[0]` du lock.

**Passe 2 — sur la v1.0.0 : 5 `distinct` sur 5.** Les trois classes mandatées discriminent,
seule issue qui autorisait d'élargir.

**Élargissement — 130 paires minimales, balayées exhaustivement.** Échantillon fixé par une
règle mécanique d'énumération (toute paire existante dont les deux racines ont une ligne
`has_asl`, moins les 13 déjà dépensées) : ni tirage, ni classement, ni troncature, donc aucun
choix ne reste à faire en regardant les données. Résultat : **117 `distinct`, 0
`order-distinct`, 13 `identical` — et les 13 tombent sur la seule paire `ح`/`ه`**. 12 portent
des أصول divergents et sont des collisions confirmées ; `فرح`~`فره` est classée non
qualifiante sous la règle d'ensemble conservatrice.

L'élargissement est **d'un cran plus faible comme preuve** que la sonde mandatée — ses verdicts
d'أصل ont été lus après les résultats — et le dossier le dit et publie chaque أصل verbatim.

### Le résidu `ح`/`ه` est accepté, et voici la condition de réouverture

`ح` et `ه` partagent la zone `الحلق` et le profil `رخاوة` + `همس` : cinq zones ne peuvent pas
les séparer. Une sixième zone, ou un découpage en trois du حلق, ramènerait le compte à zéro en
une après-midi — et ce zéro ne voudrait rien dire, parce qu'il serait la table ajustée jusqu'à
ce que la mesure lui donne raison. **12 collisions sur 130 paires, publiées et chiffrées,
valent mieux qu'un zéro obtenu en ajustant la table.**

Le moment légitime pour rouvrir la granularité est la **mesure mandatée**, et la condition a
été écrite avant que le nombre existe : les échecs par collision doivent représenter
**strictement plus de la moitié** des racines en échec, classés sur les raisons déjà commitées,
la racine en collision identifiée par le critère `identical` de la sonde et une divergence
d'أصل sous la règle d'ensemble.

> **Mesuré : 1 racine en échec sur 40 est une collision** (`هجر` ~ `حجر`, أصول divergents).
> La condition n'est pas remplie, et de très loin. **Le résidu `ح`/`ه` ne coûte rien à cette
> mesure**, et découper le حلق ne changerait `k / 40` en rien.

---

## 6. La réserve sur la fenêtre, et d'où elle vient

Quand les zones sont entrées dans la table, la v1.0.0 a donné **27 profils distincts sur 28**
— seuls `ح` et `ه` restaient fusionnés. Mais à une fenêtre de **deux**, la phrase ne voyait
que les deux premiers أصول, et là la table ne donnait que **25 paires réalisées distinctes** :

- `و`/`ي` — tous deux ouvrent `لِين(2) · مَدّ(2)` ; la zone qui les sépare, `بُرُوز(4)` contre
  `وَسَط(3)`, est **troisième** et n'arrivait jamais.
- `خ`/`غ` — pire : ils étaient **distincts** à deux sur le brouillon ṣifāt seules. Ajouter
  `غَوْر` en tête a poussé leur séparateur hors de la fenêtre. Les zones ont **créé** cette
  collision.

Des zones cartographiées mais invisibles au lecteur n'ont pas été cartographiées en un sens qui
compte. À **trois**, les triplets réalisés sont **27 sur 28** — exactement le compte de profils.
À quatre, toujours 27 : rien de plus à acheter.

**Ce que cela ne change pas :** la décision a été prise contre la **feuille des lettres**, pas
contre une racine. 18, 25, 27 sont des propriétés de `arabic_letters_dataset.csv` et de
`physical_primitives.csv` et de rien d'autre. Aucune racine témoin n'a été lue, aucun أصل
consulté, le holdout est intact. Et la fenêtre était **fixée et commitée avant** que la seconde
sonde tourne, donc cette sonde reste un vrai test.

**Ce que cela change :** « la règle a été fixée avant d'être éprouvée » vaut encore pour les
positions, l'ordre de rareté et le départage. Elle ne vaut plus pour la fenêtre. C'est pourquoi
la réserve est attachée au **nombre**, en §0 de ce document, dans le rapport du validateur et
dans la réponse de l'API — et non reléguée à la note de conception.

### Ce que la fenêtre a coûté en lisibilité

Trois positions × trois أصول = **neuf notions** dans une phrase qui en budgétait six. Le مفهوم
de `ضرب` :

> «امتِدادٌ وضَخامةٌ وطَرَفٌ، ثُمَّ تَكرارٌ وتَمَهُّلٌ وطَرَفٌ، حتَّى بُرُوزٌ وارتِدادٌ وقَطْعٌ»

Neuf مصادر liés par و et deux adverbes de séquence. C'est de l'arabe grammatical, et ce n'est
pas une phrase qu'on appellerait un مفهوم : cela **énumère**. L'échange est donc littéral —
chaque zone qui atteint le lecteur a été payée d'une notion qu'il doit tenir.

**Le و n'est pas en cause et ne sera pas retiré.** La juxtaposition nue — «امتِدادٌ ضَخامةٌ» —
n'est pas une liste en arabe : elle se lit comme un نعت, ce qui **affirmerait** que la ضخامة
*est* l'امتداد. La composition n'autorise pas cette affirmation : ce sont deux أصول coordonnés
d'une même lettre. Le و coûte une syllabe et interdit une affirmation.

**La fenêtre ne revient pas à deux.** Elle a bougé une fois, après une mesure ; la faire bouger
une seconde fois parce que le résultat *se lit mal* serait un second ajustement — et deux
ajustements, chacun défendable isolément, sont la façon dont une règle pré-enregistrée devient
une règle réglée.

**C'est la présentation qui change, et elle seule.** La chaîne déterministe reste la vérité
terrain : c'est ce que `compose()` renvoie, ce que la confrontation juge, ce que le dossier
stocke et ce sur quoi `k / 40` est mesuré. La page `/lexical` rend les mêmes neuf أصول en
**trois groupes positionnels** — يفتَح / جسَد / يختِم — lisibles comme trois lectures de trois
lettres, et affiche la chaîne enregistrée telle quelle à côté.

---

## 7. Le protocole de confrontation

L'ordre porte tout le poids. Si les attestations sont écrites **après** lecture du concept,
« est-ce qu'il les couvre » est élastique : la liste se façonne silencieusement et de bonne foi
autour de ce que la phrase dit.

Pour chaque racine témoin, dans cet ordre :

1. **Geler les attestations d'abord.** Depuis la liste d'occurrences de `morphology.json` et le
   `verbatim` de l'أصل, et rien d'autre. Chaque entrée : une glose, une référence de verset
   tirée de la liste d'occurrences **de cette racine** (vérifié mécaniquement, 0 violation).
   **Commitée avant que le concept existe** — c'est le commit `6b2a6be`, 40 racines, 183
   attestations, tous les verdicts `not_judged`.
2. **Engendrer le concept**, en aveugle.
3. **Juger chaque attestation** : `covered` / `not_covered`, avec une ligne de raison.
4. **Consigner le désaccord comme résultat.** Jamais comme motif d'ajouter une ligne, de
   reglossier un أصل ou de réordonner quoi que ce soit.

### La cécité est une arête du graphe d'imports

Un protocole qui dit « engendrer d'abord, regarder ensuite » est tenu par celui qui l'exécute,
et personne ne peut vérifier après coup qu'il l'a été. Une arête d'import est tenue par le build.

Les modules de `linguistics/lisan/concept/` ne peuvent atteindre — ni directement ni
transitivement — `root_core_store`, `sense_selection`, `qlisan_data`, ni aucun lecteur de
`root_cores.json` / `maqayis_asl.csv` / `letter_senses.csv` / `semantic_axes.json`. Ils ne
peuvent pas même **nommer** ces fichiers : `quran_data` est un import légal pour toutes les
couches et contient tous les jeux de données, donc `loaders.<un jeu sémantique>()` serait
atteignable sans importer un seul module de la liste.

`confront.py` est l'unique exemption, écrite dans le test **avant** que le fichier existe.
Il importe le **résultat** du compositeur ; le compositeur ne l'importe jamais.

### Un test ne peut pas composer une racine témoin

Pendant le gel, un test de `confront.__main__` a composé `قوم` — une racine témoin. Son concept
n'a jamais été enregistré, ni affiché, ni lu par le curateur, et l'incident est consigné
verbatim dans `concept_attestation.json`. Mais une note dans un bloc `meta` ne protège de rien.

`linguistics/lisan/concept/witness_guard.py` lève désormais depuis la première ligne de
`compose()` sous un lanceur de tests, sans mode avertissement et sans drapeau. **Treize tests
composaient des racines du holdout** quand la garde a tourné la première fois — aucun
délibérément : chacun voulait une racine trilitère et en a pris une. C'est tout l'argument.

La route livrée n'est pas concernée (un lecteur ne sait pas que le holdout existe) et le chemin
d'enregistrement prend une sanction explicite et grepable.

---

## 8. Le critère de couverture

§D9 disait « juger la couverture » sans dire ce qu'est la couverture. Un juge sans critère écrit
en applique un quand même, le découvre en jugeant, et dérive vers le nombre qu'il attendait à
moitié — dans un sens ou dans l'autre. Le critère a donc été commité **seul** (`ec3a807`), sans
un seul verdict dans l'arbre.

> Une attestation est **couverte** quand un lecteur à qui l'on donne **uniquement** les أصول
> réalisés, dans leur ordre positionnel, et à qui l'on ne dit **rien** de la racine,
> reconnaîtrait la notion de cette attestation comme quelque chose que la lecture dit.

Trois tests, tous nécessaires :

1. **Rien d'importé.** Chaque notion de contenu de la glose remonte à au moins un أصل réalisé.
2. **Pas seulement inerte.** Les أصول doivent faire plus que ne pas contredire la glose. Neuf
   notions sont compatibles avec presque tout, donc « ne contredit pas » est exactement le mode
   de défaillance auquel cette lecture est la plus exposée. Au moins un أصل réalisé doit porter
   la notion **centrale** de la glose.
3. **La direction tient.** ouvre → corps → conclut fait partie de la revendication.

**L'interdit qui rend le critère utilisable : le juge ne peut pas se servir de ce qu'il sait de
la racine pour construire le pont.** Savoir que `قوم` est la station fait ressembler
«أَصْل · ظُهور» à un socle. Cela n'y ressemble que pour qui a déjà la réponse.

Chaque manque nomme sa classe en premier mot de sa raison — `imported`, `inert`, `direction`,
`collision` — et le validateur refuse un manque non classé. Ce vocabulaire n'est pas de la
tenue de registre : la condition de réouverture de §5 est un **compte** sur ces classes, et une
raison en texte libre ne peut être comptée après coup sans être relue et re-décidée, ce qui
mettrait la condition entre les mains de qui veut rouvrir.

`collision` est **calculée**, pas jugée, et calculée **après** l'écriture des verdicts, sur
toutes les racines trilitères du corpus — pour que savoir qu'une racine entre en collision ne
puisse ni adoucir ni durcir la lecture de ses attestations.

---

## 9. L'audit est **possible**, pas **effectué**

Il n'y a pas de second juge et cette note ne prétend pas le contraire : les verdicts sont ceux
du curateur. Ce qui est commité — les attestations gelées, le concept engendré, le verdict et sa
raison, pour les 40 — est tout ce dont un lecteur qui clone le dépôt a besoin pour **refaire le
jugement et être en désaccord**. Aucun texte, ici ou ailleurs, n'affirme qu'une relecture
indépendante a eu lieu.

Pour refaire la mesure :

```bash
python scripts/validate_concept_datasets.py        # imprime k / 40 avec la réserve
python scripts/record_concept_verdicts.py worksheet # les 40 lectures en regard de leurs attestations
```

---

## 10. Conclusion — et la portée exacte de ce qui est conclu

### 10.1 Ce qui est établi

> **Le sens d'une racine n'est pas récupérable depuis les propriétés articulatoires de ses
> lettres** — sous **ce** vocabulaire (20 أصول dérivés des مخارج et صفات), **cette** règle de
> composition (trois positions, ordre de rareté, fenêtre de trois), **ce** critère de couverture
> (§8), sur **40 racines témoins tirées d'avance** et jamais lues pendant la construction.

Quatre qualificatifs, et ils sont tous portants. Retirez-en un et l'énoncé devient plus large que
ce qui a été mesuré.

### 10.2 Ce qui n'est **pas** établi

**La tradition des معاني الحروف n'est pas réfutée.** Ce document ne l'atteint pas, et ne prétend
pas l'atteindre.

Ce qui a échoué est **une formalisation**, parmi beaucoup de formalisations possibles : une table
de 20 أصول écrite par ce projet, appliquée mécaniquement, sans exception par racine, sous un
critère de couverture strict. Ibn Jinnī n'a jamais proposé une table ; il illustre un principe sur
des cas particuliers. Ḥasan ʿAbbās ne dérive pas un sens de racine ; il donne des faisceaux de sens
par lettre. Ni l'un ni l'autre n'a affirmé ce que `k / 40` a testé.

Un lecteur qui tirerait d'ici « les lettres n'ont pas de sens » lirait plus large que la mesure.
Ce qui est mesuré, c'est qu'**une** correspondance physique → notion, fixée d'avance et appliquée
sans exception, ne reconstitue pas les emplois coraniques des 40 racines témoins.

### 10.3 Le meilleur constat du run

> **Puisque toute صفة décrit *comment* un son est produit, « la parole » — la notion même que porte
> `قول` — est une chose que ce vocabulaire ne peut jamais affirmer sans circularité.**

Les أصول sont `جَرَيان`, `قَطْع`, `خَفاء`, `ظُهور` : des descriptions du passage de l'air et de la
position des organes. Décrire la production d'un son avec ces termes, puis en conclure « ceci parle »,
c'est se servir du fait que l'on est en train de parler comme prémisse. Ce n'est pas une limite de
*cette* table : c'est une limite de toute table construite sur ce vocabulaire, et elle est visible
sur une racine, `قول`, qui fait partie du lot tiré d'avance.

### 10.4 Les réserves qui restent attachées au nombre

Elles ne s'annulent pas parce que le résultat est négatif — un résultat négatif obtenu par une
procédure faible reste faible.

1. **La fenêtre a été fixée après coup sur `ضرب`** (§6). Une partie de la règle de composition n'est
   pas pré-enregistrée. Et `ضرب` **plafonne elle-même à 1 / 5** : le cas sur lequel la fenêtre a été
   réglée n'atteint pas non plus ses propres attestations, donc l'ajustement n'a même pas acheté ce
   pour quoi il a été fait.
2. **Juge unique.** Les 188 verdicts sont ceux du curateur. Aucune relecture indépendante n'a eu
   lieu, et aucun texte de ce dépôt n'affirme le contraire.
3. **L'audit est possible, pas effectué.** Les attestations gelées, le concept engendré, le verdict
   et sa raison sont commités pour les 41 racines : c'est de quoi refaire le jugement et être en
   désaccord. Ce n'est pas la même chose qu'un désaccord ayant eu lieu.
4. **Les verdicts d'أصل de l'élargissement ont été lus après les résultats** (§5). Cette partie-là
   de la preuve est d'un cran plus faible que la sonde mandatée, et le dossier le dit à l'endroit
   où il la publie.

### 10.5 La conclusion croisée sur les deux moteurs

Les deux moteurs ont été construits, montés, et mesurés autant que chacun pouvait l'être.

- Le moteur **core-first** produit une lecture — mais uniquement parce qu'il **emprunte l'أصل**. Le
  noyau attesté sélectionne le sens de chaque lettre, donc la sortie ne peut porter aucune
  information que le noyau ne portait pas déjà. Sur les racines où il produit un paragraphe, ce
  paragraphe est une reformulation de l'أصل.
- Le moteur **physics-first** n'emprunte rien — et **ne produit rien** : `k / 40 = 0`.

> **Pris ensemble : la couche « sens des lettres » n'apporte aucune information mesurable sur le
> sens d'une racine.** Quand elle est alimentée par l'أصل, elle restitue l'أصل. Quand on la coupe de
> l'أصل, elle ne restitue rien.

**Ce que cet énoncé n'est pas.** Ce n'est **pas une mesure du moteur core-first.** Celui-ci n'a pas
de métrique comparable — il n'y a pas de `k / 40` pour lui — et son défaut connu est l'inverse de
celui-ci : il ne peut pas être en désaccord avec son entrée, donc il ne peut pas non plus être
falsifié par elle. Ce qui est dit ci-dessus est une conclusion **par recoupement**, pas un second
résultat chiffré, et elle hérite de toutes les réserves de §10.4.

### 10.6 La décision : l'expérience est close

- La route `POST /lisan/concept` **reste montée** et la page continue d'afficher le مفهوم, étiqueté
  **EXPÉRIENCE CLOSE**, avec son nombre et sa réserve affichés à côté. Un résultat négatif retiré de
  l'écran devient un résultat que personne ne peut vérifier.
- **Aucune tentative de sauvetage.** Pas d'élargissement du vocabulaire de traits, pas de découpage
  du حلق, pas de fenêtre retouchée. Ce n'est pas de la discipline gratuite : **162 des 176 manques
  sont `imported`**, donc l'échec n'est **pas paramétrique** — la notion manquante n'est pas une
  affaire de granularité, et aucun réglage des paramètres existants ne l'atteint. La condition de
  réouverture de §5 a déjà répondu par l'évidence : **1 collision sur 40 racines en échec**, contre
  un seuil de strictement plus de la moitié.
- Ajouter un trait pour atteindre `إدراك` ou `عون` serait l'ajouter **parce que** la mesure a
  échoué. C'est exactement le geste que le gel de la table existe pour interdire, et le faire ici
  effacerait la seule chose que ce chantier a produite : un résultat.
- `/lexical` est **recentré sur l'attesté** — racine (QAC), أصل d'Ibn Fāris cité, occurrences,
  morphologie et syntaxe. La lecture par lettres reste affichée et sourcée, présentée comme un
  **مذهب** — ce que Ḥasan ʿAbbās et Ibn Jinnī disent d'une lettre — et jamais comme une définition
  dérivée.

---

## 11. Ce que ce document ne couvre pas


- **Il ne mesure pas le moteur core-first.** §10.5 tire une conclusion par recoupement sur les
  deux ; ce n'est pas un second nombre. Le moteur core-first n'a pas de métrique comparable, et son
  défaut connu est l'inverse de celui-ci — il ne peut pas être en désaccord avec son entrée, donc
  il ne peut pas non plus être falsifié par elle.
- **Il ne propose pas de correctif à la table.** Le résultat dit `imported` 162 fois : la
  notion manquante n'est pas une question de granularité de مخرج, et §5 le chiffre. Élargir le
  vocabulaire de traits pour atteindre `إدراك` ou `عون` serait l'ajouter *parce que* la mesure
  a échoué — précisément la manœuvre que le gel de la table interdit.
- **Le biais de signature reste mesuré, jamais corrigé.** Sept lettres possèdent une صفة
  qu'aucune autre ne porte et mènent donc toujours avec leur signature. Pondérer l'ordre sur
  autre chose que la table serait le premier pas vers une sélection par le sens — le défaut que
  ce moteur existe pour fuir. La répartition de §0 est ce qui l'expose ; ici elle sépare 0 de 0.
