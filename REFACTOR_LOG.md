# Refactor Log

## Goal

Gradually refactor the Cookie Clicker bot toward clearer SOLID/OOP structure and modern Python conventions while keeping the bot runnable throughout the migration.

## Agent handoff (read this first)

Use this section to orient before editing. Repository conventions and commands are also summarized in [`AGENTS.md`](AGENTS.md).

### Commands

| Action | Command |
|--------|---------|
| Run the bot | `python main.py` (canonical entrypoint) |
| Run all tests | `python -m pytest -q` |
| Run one test module | `python -m pytest -q tests/test_dom_loop.py` |
| Working tree | `git status --short` |

Tests live under [`tests/`](tests/); [`pytest.ini`](pytest.ini) sets `testpaths = tests` and `pythonpath = .` so imports resolve from the repo root.

### Repository map

| Area | Role |
|------|------|
| [`main.py`](main.py) | Delegates to `clicker_bot.app.main()`. |
| [`clicker_bot/app.py`](clicker_bot/app.py) | `BotApplication`: hotkeys, `sync_mod_files`, launch/focus game, builds dashboard via `clicker.start_dashboard()`, runs Tk main loop. Takes the **`clicker` legacy module** as `legacy_module` (see `build_default_application`). |
| [`clicker.py`](clicker.py) | **Large legacy module**: globals, feature wiring, `dom_loop()`, `click_loop()`, `start_dashboard()`, toggles, feed I/O, Win32/game interaction. **Goal is to shrink and eventually replace** with thin wiring; new logic belongs in `clicker_bot/` or feature modules, not new sprawling code here. |
| [`clicker_bot/`](clicker_bot/) | New shell: runtime, controls, activation, lifecycle, `dom_loop.py`, `dom_loop_services.py`, policies (`reserve_policy`, `pause_policy`, `startup_policy`), diagnostics, dashboard factory. **Prefer adding code here** when extracting from `clicker.py`. |
| Top-level `*_controller.py`, `stock_trader.py`, etc. | Feature logic (garden, stock, buildings, spells, …). Keep behavior stable; integrate behind clearer interfaces over time. |
| [`hud_gui.py`](hud_gui.py) | **Tkinter HUD** (`BotDashboard`). Built through [`clicker_bot/dashboard.py`](clicker_bot/dashboard.py) (`DashboardCallbacks` → `build_dashboard`). Planned migration to **PySide6** (separate epic below). |

### Architecture snapshot

```
main.py
  → clicker_bot.app.BotApplication(legacy_module=clicker)
       → register_hotkeys / initialize_runtime (calls into clicker)
       → clicker.start_dashboard()  → build_dashboard(...) → hud_gui.BotDashboard
clicker.dom_loop()  → clicker_bot.dom_loop_services + dom_loop coordinator (legacy globals exported each cycle)
```

**Dependency direction to preserve:** `clicker_bot` must not import `clicker` except where explicitly intentional (today only `app.build_default_application` does `import clicker` for wiring). New modules should stay import-clean at load time per `AGENTS.md`.

### How to pick a task

1. **Shrink `clicker.py` (default track):** Find self-contained helpers still in `clicker.py` that are mostly pure or have a small set of global dependencies; extract to `clicker_bot/` with explicit parameters; keep thin wrappers in `clicker.py` until callers are migrated. Add or extend tests under `tests/` against the new module (avoid new AST-based tests that parse `clicker.py`).
2. **HUD / PySide6 (parallel epic):** Preserve `DashboardCallbacks` and `get_dashboard_state()` contract; replace Tk `BotDashboard` implementation; audit `lifecycle.py` for thread vs GUI thread rules.
3. **Never in one PR:** giant `dom_loop` rewrites + full HUD rewrite + behavior changes. Ship incremental diffs; keep **`python -m pytest -q` green**.

### Git workflow and branching

Use this workflow for **all** refactor work so parallel agents do not collide and history stays reviewable.

| Concept | Convention |
|---------|------------|
| **Integration branch** | `master` (this repository’s default). Keep it **green**: full `python -m pytest -q` before merge. |
| **Branch lifetime** | **Short-lived** topic branches only. Do not accumulate long-running “mega” refactor branches. |
| **One vertical slice** | One branch = one coherent extract/test/log update (matches **Guardrails**). If scope grows, **split** into a follow-up branch. |
| **Parallel epics** | Use a **prefix** so merges stay obvious: **`refactor/core-…`** for A-track (`clicker.py` / `dom_loop` / policies) vs **`refactor/hud-…`** for B-track (PySide6 / dashboard). Never mix core loop extraction and full HUD rewrites in one PR. |
| **Naming pattern** | `refactor/<track>-<short-slug>` in `kebab-case`, e.g. `refactor/core-a1-ui-owner-gating`, `refactor/hud-b1-callback-contract`. |
| **Start of work** | `git checkout master` → `git pull` (or rebase onto latest `master` if you already had a branch) → `git checkout -b refactor/…`. |
| **Integration** | Open a PR (or merge locally if solo) **into `master`**. Rebase or merge from `master` often if the branch lives more than a day. |
| **Doc in the same change** | When a phase completes, add the **Phase N** bullet under **Completed** on the **same** branch/PR as the code, per **Definition of done**. |
| **Conflicts** | Prefer **rebasing** your topic branch onto `master` before merge when history is linear; if the team uses merge commits, stay consistent with existing repo practice. |

**For other agents:** read **Current State**, **Remaining Refactor Plan**, and **pick a slice** that does not overlap an in-flight branch (check open PRs or ask). Claim work by **branch name + short intent** in your PR description or commit message body.

### Completed-phase note

Phases **0–31** were documented before tests moved to `tests/` (Phase 32). Older bullets may reference `test_*.py` at repo root; those files now live under [`tests/`](tests/).

## Principles

- Prefer incremental, behavior-preserving changes over rewrites.
- Keep `clicker.py` launch-compatible until the new application structure is fully established.
- Move side effects and orchestration behind explicit boundaries before rewriting feature logic.
- Preserve test coverage and keep the suite green after each phase.

## Completed

### Phase 0: Baseline Stabilization

- Added [`pytest.ini`](/C:/Users/blake/Desktop/Repo/clicker/pytest.ini:1) to make test discovery deterministic.
- Configured pytest to:
  - only collect `test_*.py`
  - ignore temp/cache directories in the repo root
  - disable the pytest cache plugin that was colliding with the local `.pytest_cache` state
- Verified the suite runs cleanly with:
  - `python -m pytest -q`

### Phase 1: Entrypoint Extraction

- Added canonical entrypoint [`main.py`](/C:/Users/blake/Desktop/Repo/clicker/main.py:1).
- Converted [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:5049) into a compatibility wrapper exposing `main()`.
- Removed import-time startup behavior from `clicker.py`:
  - hotkey registration
  - mod sync
  - game launch/focus
  - dashboard startup

### Phase 2: Initial Application Shell

- Added package [`clicker_bot`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/__init__.py:1).
- Added [`clicker_bot/app.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/app.py:1) with:
  - `BotApplication`
  - explicit hotkey binding registration
  - startup/runtime initialization
  - dashboard launch wiring
- Added [`clicker_bot/config.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/config.py:1) with initial `AppConfig`.
- Added [`test_app.py`](/C:/Users/blake/Desktop/Repo/clicker/test_app.py:1) covering:
  - app shell startup flow
  - idempotent hotkey registration

### Phase 3: Runtime State Extraction

- Added [`clicker_bot/runtime.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/runtime.py:1) with:
  - `RuntimeConfig`
  - `RuntimeStore`
- Moved runtime/dashboard state ownership, recent-event buffering, feed buffering, and latest big-cookie snapshot storage behind the runtime store.
- Added [`test_runtime.py`](/C:/Users/blake/Desktop/Repo/clicker/test_runtime.py:1) for runtime store behavior.

### Phase 4: Dashboard and Lifecycle Extraction

- Added [`clicker_bot/dashboard.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dashboard.py:1) to build the Tk dashboard from injected callbacks.
- Added [`clicker_bot/lifecycle.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/lifecycle.py:1) with:
  - `BotLifecycle`
  - `BotLifecycleState`
- Moved dashboard construction and loop-thread start/restart decisions out of `clicker.py`.
- Added:
  - [`test_dashboard_factory.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dashboard_factory.py:1)
  - [`test_lifecycle.py`](/C:/Users/blake/Desktop/Repo/clicker/test_lifecycle.py:1)

### Phase 5: Control and Activation Extraction

- Added [`clicker_bot/controls.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/controls.py:1) with `BotControls`.
- Moved feature toggles, horizon updates, building-cap changes, and wrinkler mode cycling behind the control layer.
- Added [`clicker_bot/activation.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/activation.py:1) with `BotActivationController`.
- Moved bot on/off transition orchestration out of `clicker.py`:
  - active-state flips
  - shimmer reset
  - game window attach/launch/focus
  - lifecycle start/stop
- Added:
  - [`test_controls.py`](/C:/Users/blake/Desktop/Repo/clicker/test_controls.py:1)
  - [`test_activation.py`](/C:/Users/blake/Desktop/Repo/clicker/test_activation.py:1)

### Phase 6: Event and Dashboard-State Extraction

- Added [`clicker_bot/events.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/events.py:1) with `BotEventRecorder`.
- Added [`clicker_bot/dashboard_state.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dashboard_state.py:1) with `DashboardStateBuilder`.
- Moved:
  - feed/recent-event recording
  - dashboard payload assembly
  out of `clicker.py`.
- Added:
  - [`test_events.py`](/C:/Users/blake/Desktop/Repo/clicker/test_events.py:1)
  - [`test_dashboard_state.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dashboard_state.py:1)

### Phase 7: Pre-existing Regression Fix

- Fixed garden-open gating in [`garden_controller.py`](/C:/Users/blake/Desktop/Repo/clicker/garden_controller.py:368).
- The garden controller now refuses to open the minigame when it cannot prove the current plan is actionable:
  - no open target
  - no viable plan
  - missing required seed costs
  - layout cost unknown
  - insufficient cookies for the current plan

### Phase 8: `dom_loop()` Snapshot and Diagnostic Extraction

- Added [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1) with:
  - `DomSnapshotPreparer`
  - `DomDiagnosticsBuilder`
  - structured loop data objects for prepared snapshots, bank-diag cache, and build options
- Moved the non-action setup stages out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3294):
  - feed snapshot loading and top-level snapshot decoration
  - diagnostic assembly for garden, lump, building, ascension, upgrade, dragon, golden-cookie, stock, wrinkler, combo, and spell state
  - reserve/pause/defer calculations
  - runtime/HUD publication payload assembly
  - feed-signature construction for debug logging
- Kept the existing priority/action execution chain in `clicker.py` unchanged for this phase.
- Added [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) covering:
  - snapshot preparation and snapshot flag decoration
  - diagnostic decoration and runtime publication
  - stock bank-diag cache reuse behavior

### Phase 9: Early `dom_loop()` Action Execution Extraction

- Extended [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1) with `DomActionExecutor`.
- Moved these action-execution blocks out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3294) while keeping action selection and priority order in place:
  - sugar lump harvest
  - notification dismissal
  - combo action execution
  - spell action execution
  - garden action execution
- Removed the duplicated combo execution body in `clicker.py` by routing both combo phases through the shared executor.
- Expanded [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) to cover:
  - lump execution side effects
  - spell execution gating
  - combo scroll execution
  - garden execution and UI-owner claiming

### Phase 10: Remaining `dom_loop()` Action Execution Extraction

- Extended [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1) so `DomActionExecutor` now also handles:
  - upgrade store preparation and upgrade clicks/focus actions
  - wrinkler clicks
  - dragon actions
  - ascension-prep store actions
  - stock-trading actions
  - building store actions
  - minigame store access preparation
- Reduced [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3294) further so these paths now delegate execution and side effects while `clicker.py` still owns:
  - action planning
  - cooldown and blocker decisions
  - candidate/tracker state setup before execution
- Expanded [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) to cover:
  - stock-trade execution
  - upgrade focus execution and returned focus state
  - building execution and attempt-tracker updates

### Phase 11: Early Priority Coordination

- Added `DomActionCoordinator` and `DomLoopActionOutcome` to [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1).
- Replaced the first inline portion of the post-shimmer priority chain in [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3294) with explicit staged coordination for:
  - sugar lump harvest
  - notification dismissal
  - pending combo execution
  - spell execution
  - opportunistic combo execution
  - garden execution
- This phase keeps stage planning logic in `clicker.py`, but the ordering is now expressed as a coordinator-driven stage list instead of a hand-written `if/continue` ladder.
- Expanded [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) to cover coordinator ordering and fallthrough behavior.

### Phase 12: Remaining Priority Coordination

- Moved the rest of the post-garden priority chain in [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3294) onto the same `DomActionCoordinator` path.
- The coordinator-driven late-stage ordering now covers:
  - upgrade store prep, upgrade execution, and upgrade blocker logging
  - wrinkler actions
  - dragon actions
  - ascension-prep store actions
  - stock-trading actions
  - building store actions, including stuck-signature backoff handling
  - minigame store access preparation
- This phase keeps planning logic in `clicker.py`, but the full post-shimmer priority sequence is now expressed as staged coordinator passes instead of a mixed coordinator-plus-inline ladder.
- Re-ran the targeted loop/regression coverage for:
  - [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1)
  - [`test_clicker_upgrade_attempt_tracking.py`](/C:/Users/blake/Desktop/Repo/clicker/test_clicker_upgrade_attempt_tracking.py:1)
  - [`test_clicker_building_attempt_tracking.py`](/C:/Users/blake/Desktop/Repo/clicker/test_clicker_building_attempt_tracking.py:1)

### Phase 13: Late-Stage Planning Extraction

- Added `DomActionPlanner` to [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1) with focused planning helpers for:
  - upgrade store reset/buy planning
  - wrinkler action planning
  - dragon action planning
  - ascension-prep store planning
  - stock-trading action planning
  - building/store planning and blocked-signature decoration
  - minigame store access planning
- Reduced the remaining inline planning code inside [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3294) so the late-stage coordinator mostly delegates candidate/store-action assembly to the planner layer.
- Kept execution, cooldowns, attempt tracking, and blocker logging behavior in `clicker.py` for this phase.
- Expanded [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) with direct planner coverage for:
  - upgrade store reset planning
  - dragon action planning without aura-planning priority
  - building plan blocked-signature decoration
  - minigame store-access plan wrapping

### Phase 14: Attempt-Tracking Policy Extraction

- Added `DomAttemptTracker` to [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1) to centralize:
  - candidate attempt-tracker synchronization
  - blocked-signature state checks
  - upgrade blocker-signature logging and deduplication
- Reduced [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3294) further so upgrade/building attempt-state maintenance now delegates to the extracted helper.
- Replaced the AST-only tracking tests with direct unit coverage in [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) for:
  - tracker synchronization across unchanged and changed signatures
  - active blocked-signature checks
  - deduplicated upgrade blocker logging

### Phase 15: Late-Stage Gate Policy Extraction

- Added `DomStagePolicy` to [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1) to centralize late-stage `dom_loop()` gating and cooldown checks for:
  - upgrade planning eligibility
  - upgrade blocker reason assembly
  - wrinkler gating
  - dragon gating and aura cooldown allowance
  - ascension-prep gating
  - trade gating
  - building gating
- Reduced [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3294) further so the late-stage coordinator now delegates most gate-condition evaluation to the extracted policy helper.
- Expanded [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) with direct policy coverage for:
  - upgrade planning cooldown gates
  - upgrade blocker reason assembly
  - wrinkler post-upgrade cooldown gating
  - trade/building pause and cooldown gates

### Phase 16: Stage-Closure Extraction

- Added `DomLoopStageRunner` plus explicit early/late stage context models to [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1).
- Moved the remaining inline stage-closure assembly out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3263):
  - early priority stages for lumps, note dismissal, combo/spell actions, and garden actions
  - late priority stages for upgrade/wrinkler/dragon/ascension/trade/building/minigame actions
- Kept existing planners, executors, cooldowns, and feature-module decision logic intact; this phase only moved stage wiring/orchestration.
- Expanded [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) with direct runner coverage for:
  - early note-stage execution
  - late upgrade-blocker signature propagation
  - late building-stage dispatch

### Phase 17: Late-Stage Preflight Extraction

- Added `DomLoopLateStagePreparer` and `DomLoopLateStagePreparation` to [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1).
- Moved the remaining late-stage preflight bookkeeping out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3263):
  - upgrade attempt-tracker synchronization before stage execution
  - upgrade signature/backoff-state derivation
  - stock-deferral gating for pending upgrade candidates
  - upgrade reserve affordability checks
  - initial upgrade-plan assembly before the late-stage runner executes
- Kept late-stage execution, planner behavior, and feature-specific decisions unchanged; this phase only moved preflight state assembly.
- Expanded [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) with direct preparer coverage for:
  - blocked-signature detection
  - defer-stock propagation
  - upgrade-plan preparation when the policy gate is open

### Phase 18: Outcome-Application Extraction

- Added `DomLoopOutcomeHandler` plus explicit early/late stage state models to [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1).
- Moved the remaining post-stage bookkeeping out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3263):
  - early-stage outcome update merging
  - late-stage outcome update merging
  - idle no-action profile/sleep fallthrough handling
- Kept loop control flow and action behavior unchanged; this phase only moved state-application/orchestration code.
- Expanded [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) with direct outcome-handler coverage for:
  - early outcome state merging
  - late outcome state merging
  - idle fallthrough profiling and sleep behavior

### Phase 19: Shimmer Orchestration Extraction

- Added `DomShimmerHandler` plus explicit shimmer context/result models to [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1).
- Moved the remaining shimmer-path orchestration out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3263):
  - active shimmer cleanup across click/retry/pending-result state
  - pending shimmer resolution and wrath-gate logging
  - planned shimmer click dispatch for pending Hand of Fate targets
  - scan-based shimmer click dispatch and retry bookkeeping
  - shimmer-path profiling/sleep behavior
- Kept the lower-level shimmer decision helpers and telemetry interpretation intact; this phase only moved orchestration/state handling.
- Expanded [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) with direct shimmer-handler coverage for:
  - pending-result resolution
  - planned shimmer click dispatch and attempt tracking
  - no-click shimmer profiling behavior

### Phase 20: Cycle-Setup and Feed-Logging Extraction

- Added `DomLoopCyclePreparer`, `DomLoopFeedLogger`, and `DomLoopCycleState` to [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1).
- Moved the remaining top-of-loop bookkeeping out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3263):
  - snapshot extraction timing
  - diagnostics build timing and runtime publication
  - per-cycle `now` capture and value-action clot pause state derivation
  - feed-signature change detection and debug logging
- Kept diagnostic content and feed-signature semantics unchanged; this phase only moved setup/orchestration code.
- Expanded [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) with direct coverage for:
  - cycle preparation and profile timing
  - feed logger signature-change behavior
  - feed logger no-op behavior when the signature is unchanged

### Phase 21: Per-Cycle Coordinator Extraction

- Added `DomLoopCoordinator` and `DomLoopState` to [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1).
- Moved the remaining per-cycle orchestration out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3296):
  - cycle preparation and feed logging handoff
  - shimmer-path dispatch handoff
  - early-stage execution and outcome application handoff
  - late-stage preflight, execution, and idle fallthrough handoff
- Reduced `clicker.py` so `dom_loop()` now mostly owns:
  - the thread loop and exception boundary
  - feature-toggle snapshotting for each cycle
  - synchronization of returned loop state back onto legacy globals
- Expanded [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) with direct coordinator coverage for:
  - shimmer-handled early return
  - early/late stage update propagation through one cycle

### Phase 22: Loop-State Bridge Extraction

- Added `DomLoopStateBridge` to [`clicker_bot/dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop.py:1).
- Reduced the remaining legacy state marshalling in [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3296) so `dom_loop()` now delegates:
  - initial structured loop-state creation
  - pre-cycle external click-suppression reconciliation
  - post-cycle export back onto legacy globals
- Kept loop behavior and the existing global compatibility surface unchanged; this phase only extracted the remaining state-bridge plumbing around the coordinator.
- Expanded [`test_dom_loop.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop.py:1) with direct bridge coverage for:
  - initial state construction
  - pre-cycle suppression synchronization
  - export of legacy update values

### Phase 23: `dom_loop()` Service-Wiring Extraction

- Added [`clicker_bot/dom_loop_services.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dom_loop_services.py:1) with `DomLoopServiceFactory` plus a default builder for the extracted `dom_loop()` service graph.
- Moved the remaining lazy-construction and singleton-caching shell out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:3263) for:
  - snapshot preparation and diagnostics builders
  - cycle/feed/shimmer/coordinator services
  - planner/executor/policy/tracker helpers
  - stage runner, late-stage preparer, outcome handler, and state bridge wiring
- Reduced `clicker.py` further so the compatibility layer now delegates `dom_loop()` service access through one shared factory instead of owning a long series of per-service singleton getters.
- Added [`test_dom_loop_services.py`](/C:/Users/blake/Desktop/Repo/clicker/test_dom_loop_services.py:1) covering:
  - lazy service caching
  - dependency sharing across the service graph
  - default wiring of the coordinator/feed/state-bridge path

### Phase 24: Upgrade Candidate-Diagnostic Extraction

- Added [`clicker_bot/upgrade_diagnostics.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/upgrade_diagnostics.py:1) with `build_upgrade_diag()`.
- Moved the remaining inline upgrade candidate-selection shell out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:2551):
  - horizon-budget assembly
  - payback sweep selection
  - cheap cash-sweep selection
  - affordable fallback selection
  - final upgrade-diagnostic payload assembly
- Reduced `clicker.py` further so `_extract_upgrade_diag()` now delegates to the extracted helper while preserving the existing metric helpers and thresholds.
- Replaced the AST-only upgrade diagnostic coverage with direct unit tests in [`test_upgrade_diagnostics.py`](/C:/Users/blake/Desktop/Repo/clicker/test_upgrade_diagnostics.py:1) for:
  - horizon candidate selection
  - no-candidate horizon behavior
  - affordable fallback behavior
  - cash-sweep and payback-sweep ordering
  - toggle/tech pool exclusion

### Phase 25: Minigame Store-Access Planning Extraction

- Added [`clicker_bot/minigame_access.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/minigame_access.py:1) with `plan_minigame_store_access()`.
- Moved the remaining inline minigame/store-access candidate assembly out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:2409):
  - grimoire closed-state gating
  - bank/garden closed-state candidate selection
  - ordered fallback across minigame owners
  - focus-action probing for each candidate
- Reduced `clicker.py` further so `_plan_minigame_store_access()` now delegates to the extracted helper while preserving the existing building-store focus behavior.
- Added [`test_minigame_access.py`](/C:/Users/blake/Desktop/Repo/clicker/test_minigame_access.py:1) covering:
  - grimoire-first ordering when no open target exists
  - fallback to bank when grimoire already has an open target
  - fallback to later candidates when an earlier focus action is unavailable
  - no-plan behavior when no candidate can be opened

### Phase 26: Stock Helper Extraction

- Added [`clicker_bot/stock_helpers.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/stock_helpers.py:1).
- Moved the remaining stock-support helper shell out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:559):
  - stock trade deferral gating for pending upgrade buys
  - reserve-affordability checks shared with stock gating
  - disabled bank-diagnostic payload assembly
  - stock trade-management activity checks
  - stock buy-control fallback payload assembly
- Reduced `clicker.py` further so these paths now delegate through thin compatibility wrappers.
- Replaced the AST-based stock-gate test with direct unit coverage in [`test_clicker_stock_gate.py`](/C:/Users/blake/Desktop/Repo/clicker/test_clicker_stock_gate.py:1) for:
  - upgrade deferral gating
  - reserve affordability
  - disabled bank diagnostics
  - stock management active-state detection

### Phase 27: Snapshot Extractor Extraction

- Added [`clicker_bot/snapshot_extractors.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/snapshot_extractors.py:1).
- Moved the remaining feed/snapshot shaping helpers out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:2192):
  - generic snapshot target normalization
  - big-cookie target extraction
  - spell target extraction
  - shimmer list extraction
  - buff list extraction
- Reduced `clicker.py` further so these paths now delegate through thin compatibility wrappers used by the existing loop and diagnostics shell.
- Added [`test_snapshot_extractors.py`](/C:/Users/blake/Desktop/Repo/clicker/test_snapshot_extractors.py:1) covering:
  - click-vs-center target normalization
  - big-cookie extraction
  - spell extraction
  - shimmer extraction with invalid-entry filtering
  - spellbook buff fallback extraction

### Phase 28: Dragon Diagnostic Extraction

- Added [`clicker_bot/dragon_diagnostics.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/dragon_diagnostics.py:1) with `build_dragon_diag()`.
- Moved the remaining dragon snapshot-diagnostic assembly out of [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:2474):
  - dragon availability/unlock gating
  - actionable-state and blocker-reason selection
  - building-sacrifice floor validation
  - dragon UI target extraction for open/action/close and aura controls
  - aura prompt choice normalization
- Reduced `clicker.py` further so `_extract_dragon_diag()` now delegates through a thin compatibility wrapper.
- Replaced the AST-based dragon diagnostic test shell with direct unit coverage in [`test_clicker_dragon_diag.py`](/C:/Users/blake/Desktop/Repo/clicker/test_clicker_dragon_diag.py:1) for:
  - affordable cookie-cost dragon stages
  - affordable building-sacrifice stages
  - blocked building-sacrifice floor behavior
  - mismatched affordability flag handling when the sacrifice floor is not met

### Phase 29: Reserve Policy Extraction

- Added [`clicker_bot/reserve_policy.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/reserve_policy.py:1) with:
  - `ReservePolicy`
  - `apply_building_burst_purchase_goal()`
- Routed the active reserve-policy compatibility surface in [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:2661) through the extracted module for:
  - lucky reserve multiplier scaling and throttled logging state
  - hard/live lucky reserve calculation
  - building-buff burst-window detection
  - global reserve budget assembly
  - burst-driven building purchase-goal override
- Replaced the AST-based reserve-policy test shell with direct unit coverage in [`test_clicker_lucky_reserve.py`](/C:/Users/blake/Desktop/Repo/clicker/test_clicker_lucky_reserve.py:1) for:
  - hard-vs-live lucky reserve calculation
  - burst-window activation from buffs and pixies readiness
  - global reserve behavior when lucky reserve is enabled or disabled
  - burst purchase-goal override behavior
  - ascension-based lucky reserve multiplier scaling

### Phase 30: Startup Policy Extraction

- Added [`clicker_bot/startup_policy.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/startup_policy.py:1) with:
  - startup/attach timing constants
  - `should_launch_new_game_process()`
- Reduced [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:1846) further so the launch-gate compatibility helper now delegates through the extracted startup policy module.
- Replaced the remaining AST-based startup/launch tests with direct unit coverage in:
  - [`test_clicker_launch_gate.py`](/C:/Users/blake/Desktop/Repo/clicker/test_clicker_launch_gate.py:1)
  - [`test_clicker_startup_window.py`](/C:/Users/blake/Desktop/Repo/clicker/test_clicker_startup_window.py:1)

### Phase 31: Pause and Garden Gate Policy Extraction

- Added [`clicker_bot/pause_policy.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/pause_policy.py:1) with:
  - click-buff name extraction
  - positive/long-buff detection
  - buff-only pause classification
  - non-click pause allowance policy
  - garden-action gating policy
- Reduced [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:571) further so these remaining pause/garden helper paths now delegate through the extracted policy module while preserving current behavior.
- Replaced the AST-based garden-gate policy test shell with direct unit coverage in [`test_clicker_garden_gate.py`](/C:/Users/blake/Desktop/Repo/clicker/test_clicker_garden_gate.py:1) for:
  - garden-action gating around click buffs
  - direct click-buff classification
  - positive/long buff detection from spellbook fallback data
  - buff-only pause classification
  - current non-click pause behavior remaining conservative

### Phase 32: Test layout cleanup

- Added a dedicated [`tests/`](/C:/Users/blake/Desktop/Repo/clicker/tests/) package directory for all `test_*.py` modules (replacing repo-root test files) to keep the top level focused on runtime modules and `clicker_bot/`.
- Pointed [`pytest.ini`](/C:/Users/blake/Desktop/Repo/clicker/pytest.ini:1) `testpaths` at `tests` and set `pythonpath = .` (repo root) so discovery stays deterministic, top-level packages like `clicker_bot` import reliably, and running pytest from `tests/` still resolves the application modules.
- Adjusted tests that assumed repo-root working paths (`clicker.py` reads, SQLite temp files in `.`) so they resolve against the repository root or the system temp directory instead of the invocation directory.

### Phase 33: Garden reserve extraction and dead-code removal

- Moved `get_garden_cookie_reserve()` into [`clicker_bot/stock_helpers.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker_bot/stock_helpers.py:1) with an explicit `garden_automation_enabled` flag so reserve behavior is unit-testable without reading [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:1).
- Reduced [`clicker.py`](/C:/Users/blake/Desktop/Repo/clicker/clicker.py:1) so `_get_garden_cookie_reserve()` delegates to the extracted helper.
- Removed an accidental duplicate block of pre-extraction lucky/burst/global reserve implementations that were fully shadowed by later `ReservePolicy` delegations (dead code only).
- Replaced the AST-based scrape in [`tests/test_clicker_garden_reserve.py`](/C:/Users/blake/Desktop/Repo/clicker/tests/test_clicker_garden_reserve.py:1) with direct imports plus coverage for disabled garden automation.

### Phase 34: Contributor Git workflow documentation

- Added **Git workflow and branching** guidance under **Agent handoff** in this file: integration on `master`, short-lived `refactor/<track>-<slug>` branches, **`refactor/core-…`** vs **`refactor/hud-…`** prefixes for parallel epics, and coordination notes for other agents.
- Linked the same guidance from [`AGENTS.md`](AGENTS.md) under **Commit & Pull Request Guidelines** so contributors who start from repo rules still land on the workflow.

## Current State

- `main.py` is the intended entrypoint.
- `clicker.py` remains a compatibility shim.
- Startup, runtime state, activation, controls, dashboard wiring, event recording, dashboard-state assembly, and substantial `dom_loop()` orchestration now live under `clicker_bot/`.
- Core game decision logic and feature-specific planning still live in `clicker.py`, but one full `dom_loop()` cycle plus its legacy state bridge now route through extracted services in `clicker_bot/dom_loop.py`.
- The full cycle setup, feed logging, shimmer orchestration, post-shimmer action priority ordering, late-stage candidate/store-action planning, attempt/blocker bookkeeping helpers, late-stage preflight setup, late-stage gate policy, stage-outcome application, per-cycle loop coordination, and loop-state bridging now all live under `clicker_bot/dom_loop.py`.
- The remaining `dom_loop()` helper construction/caching shell now also lives under `clicker_bot/dom_loop_services.py`, leaving `clicker.py` with only a thin compatibility adapter for the shared loop-service factory.
- Upgrade candidate-diagnostic assembly now also lives under `clicker_bot/upgrade_diagnostics.py`, reducing one more inline decision path in `clicker.py`.
- Minigame store-access candidate planning now also lives under `clicker_bot/minigame_access.py`, reducing another explicit candidate-assembly path in `clicker.py`.
- Stock gating/support helpers now also live under `clicker_bot/stock_helpers.py`, reducing another small policy/diagnostic slice in `clicker.py`.
- Snapshot shaping helpers now also live under `clicker_bot/snapshot_extractors.py`, reducing another pure helper slice in `clicker.py`.
- Dragon snapshot-diagnostic assembly now also lives under `clicker_bot/dragon_diagnostics.py`, reducing another pure helper/diagnostic slice in `clicker.py`.
- Reserve-policy calculation now also lives under `clicker_bot/reserve_policy.py`, reducing another planner-support policy slice in `clicker.py`.
- Startup timing and launch gating now also live under `clicker_bot/startup_policy.py`, reducing another compatibility-only helper slice in `clicker.py`.
- Pause/garden action gating helpers now also live under `clicker_bot/pause_policy.py`, reducing another pure policy slice in `clicker.py`.
- The test suite is currently green.
- **Contributor workflow:** use the **Git workflow and branching** section above for all new refactor slices (one topic branch per vertical slice, merge to `master`).

## Remaining Refactor Plan

Work below is **ordered by dependency** (do earlier items before later ones when in doubt). **Two parallel epics** are intentional: **(A) core refactor** and **(B) HUD toolkit**. Do not merge both into a single huge change set.

### A1. `dom_loop()` / `clicker.py` decomposition (primary track)

**Objective:** Move remaining orchestration and pure-ish helpers out of [`clicker.py`](clicker.py); leave thin delegation until call sites inject dependencies directly.

| Step | Deliverable | Hints |
|------|-------------|--------|
| A1.1 | Smaller `clicker.py` | Identify blocks that only need `log`, `time`, snapshot dicts, or a few toggles; extract to `clicker_bot/` with explicit parameters. |
| A1.2 | Explicit planning vs dispatch | Where `clicker.py` still mixes “build candidate” with “execute click”, split along existing `dom_loop` coordinator patterns. |
| A1.3 | Loop startup / globals | Reduce the “compatibility adapter” surface in `clicker.py` toward a small set of factories or a future `LegacyRuntime` object (see long-term). |

**Files often involved:** [`clicker.py`](clicker.py), [`clicker_bot/dom_loop.py`](clicker_bot/dom_loop.py), [`clicker_bot/dom_loop_services.py`](clicker_bot/dom_loop_services.py), tests under [`tests/test_dom_loop.py`](tests/test_dom_loop.py) / [`tests/test_dom_loop_services.py`](tests/test_dom_loop_services.py).

### A2. Loop orchestration and models

**Objective:** Fewer ad-hoc dict passes through the priority chain; clearer stage inputs/outputs where it reduces bugs.

- Introduce or extend **internal dataclasses / typed structures** for loop stage context **only where** it clarifies existing behavior (no big speculative type system).
- **Centralize cross-feature gating** still inlined in `clicker.py` into policy helpers or `dom_loop` collaborators.

### A3. Shared policy extraction (incremental)

Much of reserve/pause already lives under `clicker_bot`; this item means **finish** moving remaining UI/loop gating out of `clicker.py`:

- **UI ownership** (`_claim_ui_owner`, throttle, conflicts) → dedicated small module or expand existing helpers.
- **Cooldown / action gating** scattered in `clicker.py` → align with `DomStagePolicy` / similar patterns in [`clicker_bot/dom_loop.py`](clicker_bot/dom_loop.py).

### A4. Feature integration cleanup (later)

**Objective:** Feature modules (`stock_trader`, `garden_controller`, …) called through **consistent planner/service interfaces**, not ad-hoc `clicker` globals.

- Buildings, upgrades, spells, stock, garden, wrinklers, combo/dragon/ascension: **one slice at a time**, with tests.

### A5. Legacy cleanup and end state

- **No new AST-based tests** that parse `clicker.py`; replace any remaining pattern with imports from `clicker_bot` or feature modules.
- **`clicker.py` removal** only when [`clicker_bot/app.py`](clicker_bot/app.py) no longer needs `import clicker` and all wiring lives behind a narrow runtime API.

---

### B. HUD: Tkinter → PySide6 (parallel epic)

**Objective:** Replace [`hud_gui.py`](hud_gui.py) (Tk `BotDashboard`) with a **PySide6** implementation while **keeping** [`clicker_bot/dashboard.py`](clicker_bot/dashboard.py) `DashboardCallbacks` + `build_dashboard(...)` as the stable boundary.

| Step | Deliverable | Notes |
|------|-------------|--------|
| B1 | **Contract doc** (short, in this file or `AGENTS.md`) | List every `DashboardCallbacks` field and the shape of `get_dashboard_state()` return value; note refresh interval and threading expectations. |
| B2 | **Dependency** | Add `PySide6` to [`requirements.txt`](requirements.txt); document larger install footprint vs stdlib Tk. |
| B3 | **Qt implementation** | New module (e.g. `hud_qt.py` or `clicker_bot/qt_dashboard.py`) constructing the same behavior as current `BotDashboard`; `build_dashboard` returns the Qt window class. |
| B4 | **Lifecycle / threads** | Review [`clicker_bot/lifecycle.py`](clicker_bot/lifecycle.py) and `start_dashboard` in `clicker.py`: Qt **must** be tickled from the GUI thread; DOM/click threads should not call widget APIs directly. |
| B5 | **Tests** | Update [`tests/test_dashboard_factory.py`](tests/test_dashboard_factory.py) (and related) to mock the new class or use a `QApplication` fixture where needed. |

**Coupling goal (overlaps A):** Push more of `get_dashboard_state()` toward **structured data** (dataclass / clear dict schema) so the Qt view does not reach into `clicker` globals.

---

### C. HUD and runtime reporting (cross-cutting)

- **Structured runtime for HUD:** extend [`clicker_bot/dashboard_state.py`](clicker_bot/dashboard_state.py) / runtime store so the dashboard is a **consumer** of snapshots, not a reader of arbitrary globals.
- **Reduce `clicker.py` ↔ dashboard coupling:** new HUD code must not `import clicker`; only callbacks passed at construction.

---

### Definition of done (every PR)

1. **`python -m pytest -q`** passes (full suite).
2. **Manual smoke (when UI or loop touched):** bot starts, dashboard opens, toggle still responds (document what you ran in PR/commit message if non-obvious).
3. **REFACTOR_LOG:** add a short **Phase N** bullet under **Completed** describing what moved and why (keep it factual).
4. **No silent behavior change** unless explicitly agreed and tested.

## Guardrails

- No large rewrite of the feature logic in one pass.
- No behavioral redesign unless explicitly planned and tested.
- Keep startup and runtime behavior stable from the user’s perspective.
- End every phase with a green test suite.
- **Agents:** default to **one vertical slice** per change (extract + test + log update). If scope creeps, split PRs. Do not leave the suite red “to fix in a follow-up.”

## Last Verified

- Date: 2026-04-12
- Command: `python -m pytest -q`
- Result: `223 passed` (suite under `tests/`)
