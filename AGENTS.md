# AGENTS.md for eoapi-client

Rules for AI agents working in this repo. Follow them literally.

## Principles

- **Minimal changes.** Touch only what the request requires. No drive-by
  refactors, renames, reformatting or "while I'm here" fixes. If something
  adjacent looks wrong, mention it instead of changing it.
- **Concise code.** Prefer the shortest clear implementation. No speculative
  options, abstractions, or error handling for cases the request didn't raise.
  Small functions, plain data (`dict` / `bytes` / `str`) in and out.
- **Thin over eoAPI's HTTP APIs.** Mirror endpoint names, pass extra query
  parameters through as `**params`, and don't model every server option.
  Don't reimplement what a maintained library already covers (search →
  pystac-client, OGC Features → OWSLib).
- **Match the surrounding code**: naming, docstring style, comment density.
  Remove only what *your* change made unused.
- **If there's no existing pattern to follow, ask** before inventing one.

## Layout

| Path | What |
|---|---|
| `src/eoapi_client/_http.py` | Shared HTTP helpers and `EoApiError` |
| `src/eoapi_client/collections.py`, `assets.py` | STAC reads |
| `src/eoapi_client/transactions.py` | STAC Transactions (writes, behind stac-auth-proxy) |
| `src/eoapi_client/raster.py` | titiler-pgstac |
| `src/eoapi_client/vector.py` | tipg, via OWSLib (optional `vector` extra) |
| `src/eoapi_client/__init__.py` | Public API: export anything new here and in `__all__` |
| `tests/` | respx-mocked unit tests, one file per module |

## Rules

- **Credentials:** never send auth headers to a host other than the configured
  service. See `download_asset`'s same-host rule.
- **Errors:** failures raised by our own code are `EoApiError` (or a subclass)
  and carry `status_code` when there is a response.
- **Dependencies:** runtime deps stay minimal (`httpx`). Anything else goes
  behind an optional extra and is imported lazily, like `owslib` in
  `vector.py`. Ask before adding a dependency.
- **Public API changes** need a README update in the same change.
- **Python ≥ 3.11**, `from __future__ import annotations`, type hints on
  public functions.

## Testing

```bash
uv sync
uv run pytest                              # unit tests (respx, offline)
uv run pre-commit run --all-files          # ruff check + format, hooks, pytest
```

- Every behaviour change gets a respx test in the matching `tests/test_*.py`.
- Real-server checks: an eoapi-k8s deployment (`../k8s`, local cluster via
  `kubectl`) is served at `http://localhost` (`/stac`, `/raster`, `/vector`,
  `/multidim`). Writes to `/stac` need a token from the mock OIDC server:
  `POST http://localhost/mock-oidc/` with `username=...`. Clean up anything
  you create. Don't modify the cluster or the `../k8s` repo unless asked.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/). release-please
builds the changelog from them.

```
<type>(<scope>): <what and why>
```

- Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `build`.
- Scope is the module or area: `stac`, `transactions`, `raster`, `vector`,
  `http`, `docs`, `ci`.
- Breaking changes (pre-1.0 they're allowed): `feat!:` plus a
  `BREAKING CHANGE:` footer.
- One logical change per commit.

## Before finishing

- [ ] Every changed line traces to the request, and nothing extra was changed
- [ ] `uv run pre-commit run --all-files` passes
- [ ] New public API is exported, documented in the README, and tested
- [ ] No credentials in code, tests or fixtures
