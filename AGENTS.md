# Repository Guidelines

The repository directory should be named **`auto_clicker_for_cookie_clicker`** (clone or rename the checkout to match). Python modules **`clicker.py`** and **`clicker_bot/`** keep their names for import compatibility.

## Project Structure & Module Organization

The bot is a Python project rooted at the repository top level. `main.py` is the current launch entrypoint, while `clicker.py` is a compatibility wrapper around the legacy runtime. Feature logic is still mostly split across top-level modules such as `stock_trader.py`, `garden_controller.py`, `spell_autocaster.py`, and `building_autobuyer.py`. New application-shell and orchestration support code lives under `clicker_bot/` (`app.py`, `runtime.py`, `controls.py`, `activation.py`, `dashboard.py`, `events.py`, `dom_loop.py`).

Unit tests live under `tests/` as `test_*.py` modules (see `pytest.ini`). The local Cookie Clicker mod files are in `cookie_shimmer_bridge_mod/`. Ongoing migration notes belong in `REFACTOR_LOG.md`.

## Build, Test, and Development Commands

- `python main.py`: run the bot through the canonical entrypoint.
- `python -m pytest -q`: run the full test suite.
- `python -m pytest -q tests/test_stock_trader.py`: run one test module during focused work.
- `git status --short`: check working tree changes before and after edits.

There is no separate build step. This is a Windows-focused runtime that interacts with the Steam Cookie Clicker client.

## Coding Style & Naming Conventions

Follow modern Python conventions with 4-space indentation and PEP 8 style. Prefer small classes, dataclasses, and explicit functions over adding more global state. Use `snake_case` for modules, functions, and variables; use `PascalCase` for classes; use `UPPER_SNAKE_CASE` for constants.

Keep behavior-preserving refactors incremental. Prefer extracting orchestration/helper logic into `clicker_bot/` or focused modules instead of expanding `clicker.py`. When touching `clicker.py`, bias toward delegation rather than adding new inline control flow.

## Testing Guidelines

Use `pytest`. Test files must be named `test_*.py`, and test names should describe observable behavior, for example `test_does_not_open_garden_when_plan_is_not_affordable`.

Add or update tests for every behavioral change. Keep the full suite green before ending a change set. Prefer direct unit tests over AST-based tests when moving logic out of `clicker.py`.

## Commit & Pull Request Guidelines

Commit messages in this repo use short imperative subjects, for example:
- `Fix stock market upgrade and broker gating`
- `Improve HUD controls and cap handling`

Pull requests should include a concise summary, the behavioral impact, tests run, and any runtime/manual validation steps. If UI or HUD behavior changes, include screenshots or a short description of what changed on screen.

For ongoing `clicker.py` / `clicker_bot` migration work, follow the **Git workflow and branching** table in [`REFACTOR_LOG.md`](REFACTOR_LOG.md) (topic branches into `master`, `refactor/core-…` vs `refactor/hud-…` prefixes).

## Architecture Notes

Do not introduce import-time side effects in new modules. Startup wiring belongs in `main.py` and `clicker_bot/app.py`. `clicker_bot/dom_loop.py` is the preferred home for loop orchestration, coordinators, and execution helpers extracted from `clicker.py`. Preserve the working bot while refactoring: prefer adapters, coordinators, and wrappers over rewrites. Update `REFACTOR_LOG.md` when a new refactor phase lands.
