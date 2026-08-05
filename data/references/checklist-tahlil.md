# Page « Tahlil » (تحليل) — Checklist de l'analyse complète

Objectif : une page qui, pour un mot d'un verset, produit l'analyse intégrale **+ le تعليل par niveau + le تركيب / القيمة الزائدة** (niveau de l'exemple يُسارعون). Elle **réutilise** tout ce que QLisan a déjà, et ajoute la couche générative.

Légende : `[x]` = déjà bâti (réutilisable) · `[ ]` = à construire.

---

## Principe fondateur (cadre l'ancrage de tout le sens)

**تفسير القرآن بالقرآن — comprendre le Coran par lui‑même.** Pas de tafsīr ni de commentaire externe. Le sens est ancré sur trois piliers internes/linguistiques :

1. **الحروف** — la valeur sémantique de chaque lettre de la racine (phono‑sémantique).
2. **الاستعمال القرآني** — l'usage propre du Coran : les نظائر (toutes les occurrences de la racine/du mot) servent de **preuve empirique** et de garde‑fou contre l'arbitraire.
3. **(à décider)** références purement linguistiques du sens‑noyau de racine — Maqāyīs (Ibn Fāris), Rāghib (المفردات) — considérées comme *lexicales*, pas exégétiques (voir §J).

Conséquence : les niveaux **صوتي** et **دلالي** sont refondus ci‑dessous.

---

## A. Acquis réutilisables (depuis QLisan)

- [x] Sélecteur verset + clic mot, clé `sourate:verset:mot`, alignement rasm/chakl
- [x] **صرفي (faits)** : القسم, الجذر, اللفظ, البنية الصرفية, traits (زمن/حالة/شخص/جنس/عدد)
- [x] **الوزن/الميزان durci** : إعلال, إبدال, جموع التكسير, مضاعف ; باب I–X ; `available=False` honnête
- [x] **النظائر** filtrées par lemme — **pilier central du nouveau دلالي**
- [x] **نحوي (faits)** : الموقع الإعرابي, العلامة, المتعلَّق depuis QAC
- [x] Discipline faits/interprétation : badge « معطى محقّق », coverage log, gold sets, mesure
- [x] Stack : loader QAC, `mizan.py`, `mizan_patterns.json`, assembleur FastAPI, frontend, Qdrant + BGE‑M3 + BM25 + reranker + Qwen

---

## B. Niveau صوتي — refondu en **phono‑sémantique de la racine**

> On abandonne tajwīd / madd / prosodie. On garde uniquement : séparer les lettres de la racine, donner le sens de chacune, puis synthétiser.

- [ ] **Table des معاني الحروف** : valeur sémantique de chaque lettre arabe, sourcée sur une œuvre théorique nommée (ex. حسن عباس « خصائص الحروف »), versionnée, avec provenance — **badge تأويلي, jamais محقّق**
- [ ] (support) Tables **ṣifāت** par lettre (شدّة/رخاوة, جهر/همس, تكرار…) comme *justification articulatoire* du sens attribué à la lettre
- [ ] Décomposition de la racine en lettres (س + ر + ع)
- [ ] Attribution du sens à chaque lettre (depuis la table)
- [ ] **Synthèse du sens‑noyau** de la racine = composition/somme des sens des lettres
- [ ] **Validation contre l'usage coranique** : le sens synthétisé colle‑t‑il aux نظائر réelles ? Sinon → marquer faible/تأويلي, logger

## C. Niveau دلالي — refondu en **self‑référentiel (sans tafsīr)**

- [ ] **Sens‑noyau** hérité de la synthèse des lettres (B) + Maqāyīs/Rāghib si retenus (§J)
- [ ] **الاستعمال القرآني** : agréger toutes les occurrences de la racine/mot (نظائر) → dégager le comportement sémantique réel dans le Coran
- [ ] **Sens سياقي** inféré **du Coran seul** : contexte du verset (relations Zero) + نظائر parallèles, **pas** de commentaire externe
- [ ] **الحقل الدلالي** via l'**ontologie QAC** (dérivée du Coran lui‑même — compatible avec le principe) ; Arabic WordNet optionnel
- [ ] Relations : ترادف / تضاد à partir des emplois coraniques
- [ ] Collection Qdrant : `quran_usage` (occurrences + contextes) — **pas** de collection tafsīr
- [ ] Asbāb al‑nuzūl : **exclu** (externe au texte) — sauf décision contraire

## D. Bases de connaissances « دلالة des formes » (NOUVEAU)

Petites tables curées, versionnées, qui rendent le تعليل morpho/syntaxe possible.

- [ ] **دلالة الوزن/الباب** : المفاعلة → مشاركة/مبالغة ; استفعال → طلب ; تفعيل → تكثير…
- [ ] **دلالة الزمن/الصيغة النحوية** : مضارع → تجدّد/استمرار ; ماضٍ → ثبوت ; أمر → طلب…
- [ ] **دلالة الصيغة الصرفية** : اسم فاعل → حدوث ; مبالغة → كثرة ; مصدر → حدث مجرّد…
- [ ] Provenance citée par entrée (source صرف/نحو/بلاغة)

## E. Couche générative تعليل + تركيب (LE CŒUR)

- [ ] **تعليل par niveau** (وصف → تعليل) :
  - [ ] صوتي (لتّ) → sens de chaque lettre + synthèse racine (تأويلي, validé usage)
  - [ ] صرفي → دلالة الصيغة contextuelle + contrastif (« أبلغ من X »)
  - [ ] نحوي → دلالة الزمن/الإعراب + relation Zero (السبب)
  - [ ] دلالي → sens‑noyau + désambiguïsation par l'usage coranique + حقل + نظائر
- [ ] **تركيب / القيمة الزائدة** : synthèse des niveaux en une thèse (« اجتمع سرّ الحروف + صيغة المفاعلة + المضارع لتصوير… »)
- [ ] Raisonnement contrastif ancré sur les نظائر (« يتعذّر لو قيل يفعلون الخير »)
- [ ] **Ancrage obligatoire** : chaque affirmation renvoie à une lettre (table), une نظيرة coranique, ou une règle de forme — sinon omise
- [ ] **3 badges** : محقّق (fait QAC) / مُولَّد (généré ancré sur نظائر+formes) / **تأويلي** (lettres, « أبلغ من », phono‑sémantique)
- [ ] Sortie : JSON structuré + prose arabe selon le gabarit

## F. Génération & infra

- [ ] Prompt = le **gabarit** (`gabarit-تحليل-لساني-لكلمة-قرآنية.md`)
- [ ] Génération Qwen (Claude en secours)
- [ ] Récupération sur `quran_usage` (نظائر/contextes) + tables lettres/formes ; **pas** de RAG tafsīr
- [ ] Anti‑hallucination : *cite‑or‑omit* ; séparation محقّق / مُولَّد / تأويلي
- [ ] On‑the‑fly vs pré‑calcul + cache (§J)
- [ ] Coverage/quality log (affirmations non ancrées, synthèses non validées par l'usage)

## G. Évaluation & qualité

- [ ] **Jeu gold d'exemplars experts** (~30 mots, façon يُسارعون) = référence
- [ ] Métriques : fidélité (chaque affirmation ancrée sur lettre/نظيرة/forme ?), cohérence synthèse↔usage coranique, couverture
- [ ] **Inspection par échantillon et par source** (leçon الله : un تعليل fluide‑mais‑faux est invisible dans l'agrégat)
- [ ] Champ `reviewed` + revue experte (human‑in‑the‑loop)

## H. Page Tahlil (UI)

- [ ] Route/onglet **Tahlil** (à côté de QLisan)
- [ ] Sélecteur verset + clic mot (réutiliser QLisan)
- [ ] Blocs : **الحروف/الصوتي** (décomposition + sens par lettre + synthèse) / صرفي / نحوي / دلالي (usage coranique) / **تركيب**
- [ ] Badges : محقّق / مُولَّد / **تأويلي** / قيد الإعداد
- [ ] Affichage des **نظائر‑preuves** (liens vers les versets sources) sous les affirmations dérivées de l'usage
- [ ] Bascule prose ↔ structuré

## I. Gouvernance & données

- [ ] Provenance + licence tracées (Tanzil, QAC GPL, **table des معاني الحروف** = source théorique nommée)
- [ ] Versionnage prompts + KB (lettres, formes)
- [ ] Journalisation du modèle générateur

---

## J. Décisions à trancher avant le spec

1. **Références lexicales** : Maqāyīs / Rāghib retenues comme sources *linguistiques* du sens‑noyau, ou exclues aussi (pure racine‑lettres + usage coranique) ?
2. **Source de la table des معاني الحروف** : quelle œuvre fait autorité (حسن عباس ? autre ?) — c'est le socle du niveau صوتي refondu.
3. **Langue de sortie** : arabe seul ou bilingue AR/FR ?
4. **On‑the‑fly vs pré‑calcul** de la génération + cache.
5. **Human‑in‑the‑loop** : systématique sur le مُولَّد/تأويلي, ou revue a posteriori ?
6. **تركيب** : capability à part ou volet du chantier دلالي.
7. **Granularité Tahlil** : mot seul, verset entier, ou les deux.

---

*Voir : `gabarit-تحليل-لساني-لكلمة-قرآنية.md`, `roadmap-couche-analyse-linguistique-mot.md`, `sources-datasets-qlisan.md`.*