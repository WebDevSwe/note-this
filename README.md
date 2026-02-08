# NoteThis

En enkel anteckningsapp i Python (Tkinter) med fokus pa snabb textinmatning, mallar och trygg sparning.

## Funktioner

- Skapa ny anteckning fran mall (`templates/`)
- Oppna och radera sparade anteckningar (`notes/`)
- Spara och "Spara som.."
- Autosparning var 5:e minut med `.bak`-backup
- Sokfalt med markering av traffar i texten
- Enkel Markdown-stod for rubriker (`#`, `##`, `###`, `####`)
- Smart Enter-hantering for listor:
  - `- [ ]` fortsatter som ny checkbox-rad
  - `1.` fortsatter som numrerad lista
  - `-` fortsatter som punktlista
- Infoga tidsstampel (knapp: `🕒`)
- Zoomlage: 100%, 150%, 200% (knapp: `+`)
- Dark mode / light mode (knapp: `🌙` / `☀`)
- About-dialog med innehall fran `settings/about_notethis.md`

## Krav

- Python 3.10+ rekommenderas
- Tkinter (brukar inga i vanlig Python-installation pa Windows)

## Kom igang

1. Gå till projektmappen.
2. Starta appen:

```powershell
python NoteThis.py
```

## Struktur

- `NoteThis.py`: huvudapp
- `settings/tokens.json`: token-konfiguration
- `settings/tooltips.json`: tooltips pa knappar/falt
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

Da kan du snabbt skapa en ny TODO-anteckning direkt via "Ny anteckning".

## Felsokning

- Om appen inte startar: kontrollera att Python ar installerat och finns i PATH.
- Om inga mallar visas: kontrollera att `.md`-filer finns i `templates/`.
- Om tooltips saknas: kontrollera `settings/tooltips.json` och att `enabled` ar `true`.
