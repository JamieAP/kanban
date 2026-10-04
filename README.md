# Kanban

A local CLI and Textual viewer for plans, tasks, notes, and document snapshots, stored in SQLite.

Task creation records available Git context: repository and worktree paths, branch, commit, and dirty state. Notes can also record the current commit and dirty state.

## Install

Requires Python 3.10 or newer.

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Use

```sh
kanban --help
kanban plan --help
kanban task --help
kanban note --help
kanban doc --help
kanban tui
```

The database path is selected in this order:

1. `--db PATH`
2. `KANBAN_DB`
3. `~/.kanban/kanban.db`

The CLI supports `--json` and `--quiet`. Task states are `todo`, `in_progress`, `blocked`, and `done`. Delete commands ask for confirmation unless `--yes` is supplied.

## Stored data and retention

The database stores descriptions, notes, timestamps, Git identifiers, and working directory, repository, and worktree paths.

`kanban doc link` copies the entire selected text file into the database, along with its absolute path and a relevance note. Later edits or deletion of the source file do not change that stored snapshot. The default size limit is 1 MiB; `--force` allows up to 10 MiB. Review files before linking them, especially credentials or private documents.

Delete commands mark records with `deleted_at` rather than erasing them. Record contents and linked documents remain in the database. There is no automatic expiry or secure purge function.

The application provides no data encryption or application-level access control. Treat databases, backups, and exports as private whenever their contents are private.

SQLite uses WAL mode. Its `-wal` and `-shm` sidecars may also contain data; close connections or use a consistent SQLite backup when copying a database. Git ignore rules cover common database names and sidecars, plus `exports/`, but do not cover arbitrary filenames. Keep live databases, journal files, and raw exports out of public repositories.

## Development

Source files are in `src/cli/`, `src/db.py`, `src/git.py`, and `src/tui/`. Tests use temporary or in-memory databases:

```sh
python -m pytest
```

Development commands use the active Python environment.

## License

Project code is licensed under [MIT](LICENSE). Third-party dependencies retain their own licenses. The license does not grant rights to documents or other content stored in a user's database.
