# SIDEQUEST

> Print a quest. Leave the screen. Touch grass.

SIDEQUEST is a screenless-first AI project that generates small real-world quests designed to get people away from their screens and outside.

Instead of another app that asks for your attention, SIDEQUEST uses a local open-weight AI model to generate a personalized outdoor quest that can be printed as a physical receipt.

The current version is a web-based prototype of a future physical device: choose how much time you have and what kind of break you need, print your quest, and leave the screen behind.

## 🌱 Why?

Remote work, studying, and entertainment can make it surprisingly easy to spend an entire day in front of a screen.

Going outside sounds simple. Actually doing it isn't always.

SIDEQUEST turns:

> "I should go for a walk."

into:

> "I have a quest to complete."

## 🚧 Status

Currently in development for Hacktoberfest 2026 — Touch Grass Challenge.

## Run locally

SIDEQUEST stores generated quests and progress in `data/sidequest.db` relative to
the project root by default, regardless of the shell's current directory. Set
`SIDEQUEST_DB_PATH` to use a different SQLite file. Absolute override paths are
used as written; relative override paths are resolved from the project root.
The database directory is created automatically during application startup.

```powershell
ollama serve
uv run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/` in a browser. The database schema is initialized
once during application startup.

Daily streaks use the local calendar date of the device running SIDEQUEST. Keep
the device operating-system timezone configured for its physical location;
streak boundaries occur at local midnight rather than after an elapsed 24 hours.

Run the automated tests with:

```powershell
uv run pytest
node --test tests/frontend_progress.test.js
```
