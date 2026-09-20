"""One-off command-line tools that write the cached files under data/.

Each module here is run by a `pnpm data:…`, `pnpm check:routes` or `pnpm voice:goodbye` script and by
nothing else: no module in this package is imported by the API or by the dashboard.

Norma print() in production code: these are commands a person runs in a terminal, where stdout *is*
the interface — the progress of a download, the counts written, the OK/NOT OK a `--check` run is asked
for. A logger would add levels, a logger name and a configuration step to text that is already the
program's only output. So every module in this package prints; nothing else in the backend does, and
the rule stands everywhere else.
"""
