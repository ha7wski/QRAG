# Vendored typefaces

Two faces, two roles (design D6): **Amiri** is reserved for Qurʾānic text, **IBM Plex Sans
Arabic** carries the interface chrome. Keeping them apart is what preserves the visual
boundary between the revealed text and the software commenting on it.

## Why the files are here and not fetched at runtime

The three `<link>` tags this replaces fetched from `fonts.googleapis.com` in the reader's
browser, which fails silently offline and falls back to a serif that is not Amiri.

`next/font/google` was rejected: it does not remove the network dependency, it moves it to
**build time**, where the failure is fatal rather than silent — the fetch error is swallowed
into a fallback only when `isDev`, and re-thrown under `next build`. `local-dev/start.sh`
wipes `.next` before every rebuild, so webpack's font cache never survives a source change.
Offline, that turns a degraded font into a build that does not complete.

## Why plain `@font-face` and not `next/font/local`

`next/font/local` takes **one file per (weight, style)** and offers no `unicode-range`.
Google serves these faces **per subset** — a separate woff2 for `arabic` and for `latin` —
so through `next/font/local` the choice would be:

- declare only the `arabic` file, and let every Western digit, every `2:255` and every Latin
  technical tag fall through to a system font — the exact failure D6 rejects Noto Kufi for; or
- declare both under the same weight, where Next emits two identical `@font-face` rules with
  no `unicode-range`, the browser keeps the first, and the second is dead weight.

Hand-written `@font-face` with `unicode-range` in `../globals.css` reaches D6's actual goal —
self-hosted, no network at build time — and keeps the subsets, so a page with no Latin never
downloads the Latin file.

The files stay under `src/app/` rather than `public/` deliberately: referenced relatively
from `globals.css`, webpack emits them into `.next/static/media/`, which
`frontend/Dockerfile` already copies. `public/` does not exist in this project and the
Dockerfile does not copy it, so fonts placed there would 404 in the container image.

## Provenance

Downloaded from `fonts.gstatic.com` via the Google Fonts CSS API, `arabic` and `latin`
subsets only. `latin` (U+0000–00FF) carries the ASCII digits the numeral policy keeps
Western and the accented characters of the French translation field, so `latin-ext` and the
Cyrillic subsets are not vendored. 388 KB over 10 files.

| File | Face | Weight | Subset |
|---|---|---|---|
| `amiri-400-arabic.woff2` | Amiri | 400 | arabic |
| `amiri-400-latin.woff2` | Amiri | 400 | latin |
| `amiri-700-arabic.woff2` | Amiri | 700 | arabic |
| `amiri-700-latin.woff2` | Amiri | 700 | latin |
| `plexarabic-400-arabic.woff2` | IBM Plex Sans Arabic | 400 | arabic |
| `plexarabic-400-latin.woff2` | IBM Plex Sans Arabic | 400 | latin |
| `plexarabic-500-arabic.woff2` | IBM Plex Sans Arabic | 500 | arabic |
| `plexarabic-500-latin.woff2` | IBM Plex Sans Arabic | 500 | latin |
| `plexarabic-600-arabic.woff2` | IBM Plex Sans Arabic | 600 | arabic |
| `plexarabic-600-latin.woff2` | IBM Plex Sans Arabic | 600 | latin |

The replaced `<link>` also requested Amiri italic (`ital,wght@1,400`). It is not vendored:
Arabic has no italic, and no rule in this project applies italics to Arabic text.

## Licensing

Both families are SIL Open Font License 1.1, so redistributing the files with the app is
permitted provided the licence travels with them:

- `OFL-Amiri.txt` — Copyright 2010-2022 The Amiri Project Authors
- `OFL-IBMPlexSansArabic.txt` — Copyright © 2017 IBM Corp., Reserved Font Name "Plex"

Neither font is renamed, so the Reserved Font Name clause is satisfied.
