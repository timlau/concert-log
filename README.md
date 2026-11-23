# Concert Log

A small desktop journal for the concerts you have been to: who played, when,
where, who else was on the bill, and whatever you want to remember about the
night.

Python and SQLite do the storage; the interface is QML (Qt Quick) through
PySide6. The app picks up your active **Omarchy theme** at launch, so it matches
the rest of the desktop.

## Features

- Master/detail layout: shows grouped by year on the left, full details on the right.
- Log the headliner, event/festival, start and optional end date, venue, city,
  support acts, free-form notes, and a setlist photo.
- Setlist photos are imported from a file picker, resized to at most 1024 px
  high (aspect ratio kept), stored beside the database, and opened full-size in
  a popup when clicked.
- Export the whole log to one `.zip`, then import it on another computer to
  keep the two lists in sync (photos included).
- Multi-day events: give a show an end date and it displays as a date range.
- Future shows are marked automatically: an accent `UPCOMING` badge plus a hint
  such as `In 42 days` or `Tomorrow`; a show happening today or during a
  multi-day run gets a green `TODAY` / `ONGOING` badge with `Happening now`,
  `Ends today`, or `Ends 17 Jun`.
- Concert list grouped by year and month, with a separator for each.
- Search across bands, events, venues, cities, notes, and support acts as you type.
- Artist manager for adding, renaming, and removing bands, with show counts.
- Autocomplete for band names, venues, and cities already in the log.
- Inline calendar for picking a date, plus a keyboard-friendly `YYYY-MM-DD` field.
- "Google Calendar" button on a show opens a prefilled all-day event with the
  lineup, event, notes, and venue as the location (multi-day shows included).
- Colors, surfaces, and font follow the current Omarchy theme.

## Requirements

- Linux with Qt 6 / PySide6 (tested with PySide6 6.12 on Python 3.14).
- Python 3.10 or newer.
- [`uv`](https://docs.astral.sh/uv/) to create the virtual environment
  (`sudo pacman -S uv` on Arch/Omarchy).

## Run

```bash
cd ~/udv/github/concert-log
uv sync
uv run main.py
```

`uv sync` creates `.venv` and installs the pinned dependencies from
`uv.lock`. `uv run main.py` keeps the environment in sync automatically, so
`./run.sh` is a convenience wrapper around it.

To run with a different database:

```bash
uv run main.py --db /path/to/concerts.db
```

### Desktop launcher

`./install.sh` creates a launcher that points at the checkout it lives in, using
`run.sh` and `assets/concert-log.svg`, and installs it into
`$XDG_DATA_HOME/applications` (default `~/.local/share/applications`):

```bash
./install.sh
```

The launcher uses absolute paths as desktop entries require, so run the script
again after moving the checkout to refresh it.

## Data

The database lives at:

```
$XDG_DATA_HOME/concert-log/concerts.db
```

which defaults to `~/.local/share/concert-log/concerts.db`. The directory is
created on first launch. Override the location with either:

```bash
CONCERT_LOG_DB=/path/to/concerts.db ./run.sh
uv run main.py --db /path/to/concerts.db
```

Back it up by copying that single `.db` file.

Setlist photos live in a `setlists/` folder next to the database, so back that
up together with the `.db` file. Rows store only the image filename; deleting or
replacing a photo removes the old file.

## Syncing two computers

Click **Sync** in the app to export or import an archive.

1. On computer A, choose **Export…** and save the generated `.zip` somewhere
   both machines can reach (a Nextcloud folder, USB stick, etc.).
2. On computer B, choose **Import…**, pick that `.zip`, and confirm the result
   shown in the dialog.
3. Repeat in the other direction when you have made changes on B.

The archive is a zip containing `concert-log.json` plus every setlist photo in
`setlists/`. Import **merges** rather than replaces:

- Shows are identified by a stable sync ID stored in each row. Older databases
  get IDs automatically on first launch, and shows with the same band, date,
  event, venue, and city are also recognised as the same show.
- New shows and artists are added. When both copies exist, the one with the
  newer edit time wins; re-importing the same archive changes nothing.
- Renamed artists and removed setlist photos follow their show.
- Deleting a show or artist is **not** propagated — imports never remove local
  data. Delete it on both machines if you want it gone from both.

Backups made before sync IDs existed still import; their shows are matched by
content instead.

## Importing Obsidian notes

`import_obsidian.py` reads the YAML frontmatter of the concert notes in the
Obsidian vault and imports them into the database. The default folder is:

```
~/Nextcloud/Documents/Notes/Obsidian/Tim Notes/2. Areas/Koncerter/Datoer
```

Preview first, then import:

```bash
.venv/bin/python import_obsidian.py --dry-run --verbose
.venv/bin/python import_obsidian.py
```

Use any other folder or database with `SOURCE` and `--db`:

```bash
.venv/bin/python import_obsidian.py "/path/to/notes" --db /path/to/concerts.db
```

How the frontmatter maps to the app:

| Note field    | Concert Log field                              |
| ------------- | ---------------------------------------------- |
| `Dato`        | start date (must be `YYYY-MM-DD`)              |
| `SlutDato`    | optional end date for multi-day events          |
| `Band`        | headliner; extra list items become support acts |
| `Andre Bands` | support acts                                   |
| `Spillested`  | venue                                           |
| `Arrangement` | event / festival name                           |
| `Deltaget`    | `False` notes are skipped once the show is over; upcoming planned shows are still imported |

Only the contents of the notes are used; the filename is never a fallback for
the date or band. Attended notes need a valid `Dato` and a `Band`; anything
missing either is skipped and reported.

The import is idempotent: shows already present with the same date and
headliner are skipped, so the script is safe to run again after adding notes.
Notes marked `Deltaget: False` are treated as plans while their date is today or
later, so upcoming shows appear in the app; once the show is over they are
skipped. Use `--include-not-attended` to import those past notes as well.

## Schema

Exactly two tables:

```sql
bands (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    uid        TEXT NOT NULL DEFAULT '',      -- stable id used for sync
    name       TEXT NOT NULL COLLATE NOCASE UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
)

concerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uid         TEXT NOT NULL DEFAULT '',      -- stable id used for sync
    band_id     INTEGER NOT NULL REFERENCES bands(id) ON DELETE RESTRICT,
    event       TEXT NOT NULL DEFAULT '',   -- festival / tour / event name
    date        TEXT NOT NULL,              -- start date, YYYY-MM-DD
    end_date    TEXT NOT NULL DEFAULT '',   -- optional last day, YYYY-MM-DD
    venue       TEXT NOT NULL DEFAULT '',
    city        TEXT NOT NULL DEFAULT '',
    other_bands TEXT NOT NULL DEFAULT '[]', -- JSON array of band ids
    notes       TEXT NOT NULL DEFAULT '',
    setlist_image TEXT NOT NULL DEFAULT '',  -- filename in setlists/
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
)
```

An optional `end_date` turns a show into a multi-day event (for example a
festival); it must be on or after `date`, and a same-day end date is stored as
an empty value.

Support acts are stored as a JSON array of ids in `concerts.other_bands`, so the
bands table stays the single source of band names without needing a third
junction table. Every band in that array must already exist in `bands` (the app
creates new names as you type them).

Deleting a band is refused while it headlines a show. If it only appears as a
support act, it is removed from those lineups first.

## Theme

On startup the app reads the live Omarchy palette from the first file that
exists:

1. `$CONCERT_LOG_COLORS` (for testing or a custom palette)
2. `$XDG_STATE_HOME/omarchy/current/theme/colors.toml`
   (default `~/.local/state/omarchy/current/theme/colors.toml`)
3. `~/.config/omarchy/current/theme/colors.toml`
4. The theme named in `theme.name`, looked up under
   `~/.config/omarchy/themes/<name>/` and `/usr/share/omarchy/themes/<name>/`
5. Built-in Ethereal palette

Colors are used for the window, panels, inputs, accent, danger/success states,
and the calendar. Prefer `CaskaydiaMono Nerd Font` when installed, then other
monospace fonts, then the system default. Theme changes apply on the next
launch.

`tests/render_preview.py` can save offscreen screenshots against a scratch
database:

```bash
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
    .venv/bin/python tests/render_preview.py /tmp/preview-list.png list
```

Modes are `list`, `detail`, `add`, `bands`, `setlist`, `sync`, and `date` (opens
the add form with the calendar visible).

## Keyboard shortcuts

| Shortcut | Action                     |
| -------- | -------------------------- |
| `Ctrl+N` | Add a show                 |
| `Ctrl+F` | Focus the search field     |
| `Ctrl+E` | Edit the selected show     |
| `Esc`    | Close an open dialog       |
| `Enter`  | Pick from an autocomplete suggestion / open the date picker from the date field |

## Tests

```bash
cd ~/udv/github/concert-log
uv run python -m unittest discover -s tests -v
```

The suite covers database CRUD, search, validation, band/lineup handling,
setlist photos, export/import merging, theme loading/fallback, and the Obsidian
importer.

To check that the QML loads cleanly without opening a window:

```bash
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software uv run main.py --check
```

## Layout

```
main.py                     entry point, palette, QML engine
concert_log/database.py     schema, queries, validation
concert_log/backend.py      QML-facing properties and slots
concert_log/theme.py        Omarchy colors.toml loading and palette derivation
concert_log/setlist.py      setlist photo import, 1024 px resize, file cleanup
concert_log/transfer.py     zip export and merge-on-import with sync IDs
qml/Main.qml                window, show list, detail pane, shortcuts
qml/components/             buttons, text fields, chips, date picker
qml/dialogs/                add/edit show, artists, sync, confirmation
import_obsidian.py          Obsidian markdown frontmatter importer
tests/                      database, theme, and importer tests; preview renderer
run.sh                      launcher that runs the app through uv
install.sh                  installs a desktop launcher for this checkout
```
