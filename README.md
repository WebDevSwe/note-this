# NoteThis

En enkel anteckningsapp i Python (Tkinter) med fokus på snabb textinmatning, mallar och trygg sparning.

## Funktioner

- Skapa ny anteckning från mall (`templates/`)
- Öppna och radera sparade anteckningar (`notes/`)
- Spara och "Spara som.."
- Autosparning var 5:e minut med `.bak`-backup
- Sökfalt med markering av träffar i texten
- Enkel Markdown-stöd for rubriker (`#`, `##`, `###`, `####`)
- Smart Enter-hantering for listor:
  - `- [ ]` fortsätter som ny checkbox-rad
  - `1.` fortsätter som numrerad lista
  - `-` fortsätter som punktlista
- Infoga tidsstämpel (knapp: `🕒`)
- Zoomlage: 100%, 150%, 200% (knapp: `+`)
- Dark mode / light mode (knapp: `🌙` / `☀`)
- About-dialog med innehall fran `settings/about_notethis.md`

## Krav

- Python 3.10+ rekommenderas
- Tkinter (brukar ingå i vanlig Python-installation på Windows)

## Kom igång

1. Gå till projektmappen.
2. Starta appen:

```powershell
python -m notethis
```

Alternativt fungerar fortfarande:

```powershell
python NoteThis.py
```

## Struktur

- `notethis/`: paket med appkod
- `notethis/app.py`: huvudapp
- `notethis/tokens.py`: token-hantering
- `NoteThis.py`: wrapper för bakåtkompatibel start
- `settings/tokens.json`: token-konfiguration
- `settings/tooltips.json`: tooltips påknappar/fält
- `settings/about_notethis.md`: texten i Om-rutan
- `templates/`: mallar for nya anteckningar
- `notes/`: sparade anteckningar
- `TODO.md`: gemensam att-gora-lista for framtida funktioner

## Kortkommandon

- `Ctrl+Z`: angra senaste andring
- `Enter`: smart fortsattning av listor/checkboxar

## Tokens i mallar

Vid sparning ersatts tokens som `[TODAY]`, `[NOW]`, `[NOTE_ID]`, `[CREATED_AT]`, `[UPDATED_AT]` enligt `settings/tokens.json`.

Exempel:

```md
Datum: [TODAY]
Tid: [NOW]
Anteckning: [NOTE_ID]
```

## Konfiguration

### `settings/tokens.json`

- `globals`: statiska textvarden
- `tokens`: dynamiska varden fran datum/tid/system/livscykel

### `settings/tooltips.json`

- `enabled`: `true/false` for att visa eller dolja tooltips
- `buttons`: text per knapp/falt

## Att-gora-lista

Projektets backlog finns i `TODO.md`.

I appen finns aven en mall for detta:

- `templates/05_Att-gora funktioner.md`

Då kan du snabbt skapa en ny TODO-anteckning direkt via "Ny anteckning".

## Felsökning

- Om appen inte startar: kontrollera att Python ar installerat och finns i PATH.
- Om inga mallar visas: kontrollera att `.md`-filer finns i `templates/`.
- Om tooltips saknas: kontrollera `settings/tooltips.json` och att `enabled` är `true`.
