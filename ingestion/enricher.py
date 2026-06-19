"""
enricher.py — Stage 3 of the ingestion pipeline.

Adds static metadata to each verse using mappings embedded in code:
  - revelation period (makkiyya | madani)
  - English and French surah names
  - Juz number (1–30)

Saves to `data/processed/verses_enriched.json`.

Note: French surah names are intentional application data (the project is a
trilingual ar/fr/en Quran app), not French authoring — they are kept on
purpose. Arabic surah names come from the source CSV.
"""
from __future__ import annotations

import bisect
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / "data" / "processed" / "verses_enriched.json"

# Revelation period: "makkiyya" (Meccan) or "madani" (Medinan), per scholarly
# consensus. Keyed by surah number (1–114).
SURAH_PERIOD = {
    1: "makkiyya", 2: "madani", 3: "madani", 4: "madani", 5: "madani",
    6: "makkiyya", 7: "makkiyya", 8: "madani", 9: "madani", 10: "makkiyya",
    11: "makkiyya", 12: "makkiyya", 13: "madani", 14: "makkiyya", 15: "makkiyya",
    16: "makkiyya", 17: "makkiyya", 18: "makkiyya", 19: "makkiyya", 20: "makkiyya",
    21: "makkiyya", 22: "madani", 23: "makkiyya", 24: "madani", 25: "makkiyya",
    26: "makkiyya", 27: "makkiyya", 28: "makkiyya", 29: "makkiyya", 30: "makkiyya",
    31: "makkiyya", 32: "makkiyya", 33: "madani", 34: "makkiyya", 35: "makkiyya",
    36: "makkiyya", 37: "makkiyya", 38: "makkiyya", 39: "makkiyya", 40: "makkiyya",
    41: "makkiyya", 42: "makkiyya", 43: "makkiyya", 44: "makkiyya", 45: "makkiyya",
    46: "makkiyya", 47: "madani", 48: "madani", 49: "madani", 50: "makkiyya",
    51: "makkiyya", 52: "makkiyya", 53: "makkiyya", 54: "makkiyya", 55: "madani",
    56: "makkiyya", 57: "madani", 58: "madani", 59: "madani", 60: "madani",
    61: "madani", 62: "madani", 63: "madani", 64: "madani", 65: "madani",
    66: "madani", 67: "makkiyya", 68: "makkiyya", 69: "makkiyya", 70: "makkiyya",
    71: "makkiyya", 72: "makkiyya", 73: "makkiyya", 74: "makkiyya", 75: "makkiyya",
    76: "madani", 77: "makkiyya", 78: "makkiyya", 79: "makkiyya", 80: "makkiyya",
    81: "makkiyya", 82: "makkiyya", 83: "makkiyya", 84: "makkiyya", 85: "makkiyya",
    86: "makkiyya", 87: "makkiyya", 88: "makkiyya", 89: "makkiyya", 90: "makkiyya",
    91: "makkiyya", 92: "makkiyya", 93: "makkiyya", 94: "makkiyya", 95: "makkiyya",
    96: "makkiyya", 97: "makkiyya", 98: "madani", 99: "madani", 100: "makkiyya",
    101: "makkiyya", 102: "makkiyya", 103: "makkiyya", 104: "makkiyya", 105: "makkiyya",
    106: "makkiyya", 107: "makkiyya", 108: "makkiyya", 109: "makkiyya", 110: "madani",
    111: "makkiyya", 112: "makkiyya", 113: "makkiyya", 114: "makkiyya",
}

# English and French surah names, keyed by surah number.
SURAH_NAMES = {
    1:   {"en": "The Opening",                      "fr": "L'Ouverture"},
    2:   {"en": "The Cow",                          "fr": "La Vache"},
    3:   {"en": "Family of Imran",                  "fr": "La Famille d'Imran"},
    4:   {"en": "The Women",                        "fr": "Les Femmes"},
    5:   {"en": "The Table Spread",                 "fr": "La Table Servie"},
    6:   {"en": "The Cattle",                       "fr": "Les Bestiaux"},
    7:   {"en": "The Heights",                      "fr": "Les Murailles"},
    8:   {"en": "The Spoils of War",                "fr": "Le Butin"},
    9:   {"en": "The Repentance",                   "fr": "Le Repentir"},
    10:  {"en": "Jonah",                            "fr": "Jonas"},
    11:  {"en": "Hud",                              "fr": "Hud"},
    12:  {"en": "Joseph",                           "fr": "Joseph"},
    13:  {"en": "The Thunder",                      "fr": "Le Tonnerre"},
    14:  {"en": "Abraham",                          "fr": "Abraham"},
    15:  {"en": "The Rocky Tract",                  "fr": "Al-Hijr"},
    16:  {"en": "The Bee",                          "fr": "Les Abeilles"},
    17:  {"en": "The Night Journey",                "fr": "Le Voyage Nocturne"},
    18:  {"en": "The Cave",                         "fr": "La Caverne"},
    19:  {"en": "Mary",                             "fr": "Marie"},
    20:  {"en": "Ta-Ha",                            "fr": "Ta-Ha"},
    21:  {"en": "The Prophets",                     "fr": "Les Prophètes"},
    22:  {"en": "The Pilgrimage",                   "fr": "Le Pèlerinage"},
    23:  {"en": "The Believers",                    "fr": "Les Croyants"},
    24:  {"en": "The Light",                        "fr": "La Lumière"},
    25:  {"en": "The Criterion",                    "fr": "Le Discernement"},
    26:  {"en": "The Poets",                        "fr": "Les Poètes"},
    27:  {"en": "The Ant",                          "fr": "Les Fourmis"},
    28:  {"en": "The Stories",                      "fr": "Le Récit"},
    29:  {"en": "The Spider",                       "fr": "L'Araignée"},
    30:  {"en": "The Romans",                       "fr": "Les Romains"},
    31:  {"en": "Luqman",                           "fr": "Luqman"},
    32:  {"en": "The Prostration",                  "fr": "La Prosternation"},
    33:  {"en": "The Combined Forces",              "fr": "Les Coalisés"},
    34:  {"en": "Sheba",                            "fr": "Saba"},
    35:  {"en": "The Originator",                   "fr": "Le Créateur"},
    36:  {"en": "Ya-Sin",                           "fr": "Ya-Sin"},
    37:  {"en": "Those Who Set the Ranks",          "fr": "Les Rangés"},
    38:  {"en": "Sad",                              "fr": "Sad"},
    39:  {"en": "The Troops",                       "fr": "Les Groupes"},
    40:  {"en": "The Forgiver",                     "fr": "Le Pardonneur"},
    41:  {"en": "Explained in Detail",              "fr": "Les Versets Détaillés"},
    42:  {"en": "The Consultation",                 "fr": "La Consultation"},
    43:  {"en": "The Ornaments of Gold",            "fr": "L'Ornement"},
    44:  {"en": "The Smoke",                        "fr": "La Fumée"},
    45:  {"en": "The Crouching",                    "fr": "L'Agenouillée"},
    46:  {"en": "The Wind-Curved Sandhills",        "fr": "Al-Ahqaf"},
    47:  {"en": "Muhammad",                         "fr": "Muhammad"},
    48:  {"en": "The Victory",                      "fr": "La Victoire Éclatante"},
    49:  {"en": "The Rooms",                        "fr": "Les Appartements"},
    50:  {"en": "Qaf",                              "fr": "Qaf"},
    51:  {"en": "The Winnowing Winds",              "fr": "Qui Éparpillent"},
    52:  {"en": "The Mount",                        "fr": "Le Mont"},
    53:  {"en": "The Star",                         "fr": "L'Étoile"},
    54:  {"en": "The Moon",                         "fr": "La Lune"},
    55:  {"en": "The Beneficent",                   "fr": "Le Tout Miséricordieux"},
    56:  {"en": "The Inevitable",                   "fr": "L'Événement"},
    57:  {"en": "The Iron",                         "fr": "Le Fer"},
    58:  {"en": "The Pleading Woman",               "fr": "La Discussion"},
    59:  {"en": "The Exile",                        "fr": "L'Exode"},
    60:  {"en": "She That Is to Be Examined",       "fr": "L'Éprouvée"},
    61:  {"en": "The Ranks",                        "fr": "Le Rang"},
    62:  {"en": "Friday",                           "fr": "Le Vendredi"},
    63:  {"en": "The Hypocrites",                   "fr": "Les Hypocrites"},
    64:  {"en": "The Mutual Disillusion",           "fr": "La Grande Perte"},
    65:  {"en": "The Divorce",                      "fr": "Le Divorce"},
    66:  {"en": "The Prohibition",                  "fr": "L'Interdiction"},
    67:  {"en": "The Sovereignty",                  "fr": "La Royauté"},
    68:  {"en": "The Pen",                          "fr": "La Plume"},
    69:  {"en": "The Reality",                      "fr": "Celle Qui Montre la Vérité"},
    70:  {"en": "The Ascending Stairways",          "fr": "Les Voies d'Ascension"},
    71:  {"en": "Noah",                             "fr": "Noé"},
    72:  {"en": "The Jinn",                         "fr": "Les Djinns"},
    73:  {"en": "The Enshrouded One",               "fr": "L'Enveloppé"},
    74:  {"en": "The Cloaked One",                  "fr": "Le Revêtu d'un Manteau"},
    75:  {"en": "The Resurrection",                 "fr": "La Résurrection"},
    76:  {"en": "Man",                              "fr": "L'Homme"},
    77:  {"en": "The Emissaries",                   "fr": "Les Envoyés"},
    78:  {"en": "The Tidings",                      "fr": "La Nouvelle"},
    79:  {"en": "Those Who Drag Forth",             "fr": "Les Anges Qui Arrachent"},
    80:  {"en": "He Frowned",                       "fr": "Il S'est Renfrogné"},
    81:  {"en": "The Overthrowing",                 "fr": "L'Obscurcissement"},
    82:  {"en": "The Cleaving",                     "fr": "La Rupture"},
    83:  {"en": "The Defrauding",                   "fr": "Les Fraudeurs"},
    84:  {"en": "The Sundering",                    "fr": "La Déchirure"},
    85:  {"en": "The Mansions of the Stars",        "fr": "Les Constellations"},
    86:  {"en": "The Nightcomer",                   "fr": "L'Astre Nocturne"},
    87:  {"en": "The Most High",                    "fr": "Le Très-Haut"},
    88:  {"en": "The Overwhelming",                 "fr": "L'Enveloppante"},
    89:  {"en": "The Dawn",                         "fr": "L'Aube"},
    90:  {"en": "The City",                         "fr": "La Cité"},
    91:  {"en": "The Sun",                          "fr": "Le Soleil"},
    92:  {"en": "The Night",                        "fr": "La Nuit"},
    93:  {"en": "The Morning Hours",                "fr": "Le Jour Montant"},
    94:  {"en": "The Relief",                       "fr": "La Consolation"},
    95:  {"en": "The Fig",                          "fr": "Le Figuier"},
    96:  {"en": "The Clot",                         "fr": "L'Adhérence"},
    97:  {"en": "The Power",                        "fr": "La Destinée"},
    98:  {"en": "The Clear Proof",                  "fr": "La Preuve"},
    99:  {"en": "The Earthquake",                   "fr": "La Secousse"},
    100: {"en": "The Courser",                      "fr": "Les Coursiers"},
    101: {"en": "The Calamity",                     "fr": "Le Fracas"},
    102: {"en": "The Rivalry in World Increase",    "fr": "La Course aux Richesses"},
    103: {"en": "The Declining Day",                "fr": "Le Temps"},
    104: {"en": "The Traducer",                     "fr": "Les Calomniateurs"},
    105: {"en": "The Elephant",                     "fr": "L'Éléphant"},
    106: {"en": "Quraysh",                          "fr": "Quraysh"},
    107: {"en": "The Small Kindnesses",             "fr": "L'Ustensile"},
    108: {"en": "The Abundance",                    "fr": "L'Abondance"},
    109: {"en": "The Disbelievers",                 "fr": "Les Infidèles"},
    110: {"en": "The Divine Support",               "fr": "Le Secours"},
    111: {"en": "The Palm Fiber",                   "fr": "Les Fibres"},
    112: {"en": "The Sincerity",                    "fr": "Le Monothéisme Pur"},
    113: {"en": "The Daybreak",                     "fr": "L'Aube Naissante"},
    114: {"en": "Mankind",                          "fr": "Les Hommes"},
}

# Juz boundaries: the (surah, ayah) where each of the 30 juz begins.
JUZ_START = [
    (1, 1), (2, 142), (2, 253), (3, 93), (4, 24),
    (4, 148), (5, 82), (6, 111), (7, 88), (8, 41),
    (9, 93), (11, 6), (12, 53), (15, 1), (17, 1),
    (18, 75), (21, 1), (23, 1), (25, 21), (27, 56),
    (29, 46), (33, 31), (36, 28), (39, 32), (41, 47),
    (46, 1), (51, 31), (58, 1), (67, 1), (78, 1),
]

# Flattened sortable keys for fast juz lookup via binary search.
_JUZ_KEYS = [s * 1000 + a for (s, a) in JUZ_START]


def juz_for(surah_number: int, ayah_number: int) -> int:
    """Return the juz number (1–30) for a given verse."""
    key = surah_number * 1000 + ayah_number
    # bisect_right - 1 gives the index of the last start <= key.
    idx = bisect.bisect_right(_JUZ_KEYS, key) - 1
    return max(1, idx + 1)


def enrich_verse(verse: dict) -> dict:
    """Enrich a single verse in place with static metadata."""
    sn = verse["surah_number"]
    names = SURAH_NAMES.get(sn, {"en": "", "fr": ""})
    verse["surah_name_en"] = names["en"]
    verse["surah_name_fr"] = names["fr"]
    verse["period"] = SURAH_PERIOD.get(sn, "")
    verse["juz"] = juz_for(sn, verse["ayah_number"])
    return verse


def run(verses: list[dict]) -> list[dict]:
    """Enrich every verse and report any gaps in the static mappings."""
    missing_names = set()
    missing_period = set()
    for v in verses:
        enrich_verse(v)
        if not v["surah_name_en"]:
            missing_names.add(v["surah_number"])
        if not v["period"]:
            missing_period.add(v["surah_number"])

    msg = f"  enricher   : {len(verses)} verses enriched (period, names, juz)"
    if missing_names:
        msg += f", ⚠️ missing names for surahs {sorted(missing_names)}"
    if missing_period:
        msg += f", ⚠️ missing period for surahs {sorted(missing_period)}"
    print(msg)

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(verses, f, ensure_ascii=False, indent=2)
    return verses


if __name__ == "__main__":
    for surah, ayah, expected in [(1, 1, 1), (2, 142, 2), (2, 253, 3), (78, 1, 30)]:
        got = juz_for(surah, ayah)
        flag = "ok" if got == expected else "MISMATCH"
        print(f"juz({surah}:{ayah}) = {got} (expected {expected}) [{flag}]")
