# Ask DeepSeek Procedure

Use this procedure when Blake says something like "ask deepseek about <issue>" in this repository.

DeepSeek is an advisory reviewer in this workflow. The active Codex agent owns
all repo inspection, edits, test runs, and final judgment unless Blake
explicitly asks otherwise.

## Installed CLI

`opencode` is installed as the `opencode-ai` Node CLI. In PowerShell, the `opencode.ps1` shim may be blocked by execution policy. If that happens, invoke the package entrypoint directly:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Microsoft\VisualStudio\NodeJs\node.exe' 'C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Microsoft\VisualStudio\NodeJs\node_modules\opencode-ai\bin\opencode' run --model deepseek/deepseek-reasoner --dir . "<prompt>"
```

Known DeepSeek model IDs from the local install:

- `deepseek/deepseek-chat`
- `deepseek/deepseek-reasoner`

Prefer `deepseek/deepseek-reasoner` for architecture, debugging, design review, and hard tradeoff questions.

## Useful Flags

Top-level flags observed on `opencode` 1.4.3:

- `-h, --help`: show help.
- `-v, --version`: show version.
- `--print-logs`: print logs to stderr.
- `--log-level DEBUG|INFO|WARN|ERROR`: choose log detail.
- `--pure`: run without external plugins.
- `--port <number>` and `--hostname <host>`: server binding.
- `--mdns`, `--mdns-domain <domain>`, `--cors <domain>`: server discovery/CORS.
- `-m, --model <provider/model>`: choose model.
- `-c, --continue`: continue last session.
- `-s, --session <id>`: continue a specific session.
- `--fork`: fork a continued session.
- `--prompt <prompt>`: prompt to use for TUI.
- `--agent <agent>`: choose opencode agent.

Useful `opencode run` flags:

- `opencode run [message..]`: run non-interactively with a prompt.
- `--command <name>`: run a configured command, using message as args.
- `-m, --model <provider/model>`: use `deepseek/deepseek-reasoner`.
- `--variant <variant>`: provider-specific reasoning effort, for example `high`, `max`, or `minimal`.
- `-f, --file <path>`: attach one or more files.
- `--dir <path>`: run in a specific directory.
- `--format default|json`: choose formatted output or raw JSON events.
- `--thinking`: show thinking blocks if available.
- `--title <title>`: name the session.
- `-c, --continue`, `-s, --session <id>`, `--fork`: session controls.
- `--share`: share the session.
- `--attach <url>` and `-p, --password <password>`: attach to an existing opencode server.
- `--dangerously-skip-permissions`: auto-approve permissions. Avoid this unless Blake explicitly authorizes it.

## Procedure

1. Clarify the target question from Blake's wording. Do not ask a follow-up unless the request is genuinely ambiguous.
2. Gather focused local context before calling DeepSeek:
   - Run `git status --short`.
   - Use `rg` or `rg --files` to find the relevant modules, tests, docs, configs, or logs.
   - Read only the files needed to frame the issue.
   - Note any dirty worktree changes that may affect the answer.
3. Build a self-contained prompt for DeepSeek. Include:
   - The exact question Blake asked.
   - Repository context: this is the Cookie Clicker auto-clicker project.
   - Relevant file paths and short code excerpts or summaries.
   - Current symptoms, failing commands, traceback snippets, or test output.
   - Constraints: preserve user changes, avoid broad rewrites, follow local project patterns.
   - The kind of answer needed: diagnosis, implementation options, risk review, test ideas, etc.
   - A read-only instruction such as:

```text
You are reviewing only. Do not edit files, write patches, run tests, run shell
commands, install dependencies, or change repository state. Base your answer on
the prompt and any attached files. Return concise advice, risks, and test ideas.
```

4. Prefer attaching files with `--file` when the relevant set is small. For broader questions, include concise excerpts in the prompt instead of dumping unrelated files.
5. Run DeepSeek through `opencode run`, usually with a prompt that explicitly says this is a read-only review:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Microsoft\VisualStudio\NodeJs\node.exe' 'C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Microsoft\VisualStudio\NodeJs\node_modules\opencode-ai\bin\opencode' run --model deepseek/deepseek-reasoner --variant high --dir . --title "DeepSeek: <short topic>" "<self-contained prompt>"
```

6. Await the response. If the command fails because `opencode` needs network access or access to its state directory, rerun with the normal escalation approval flow. Do not use `--dangerously-skip-permissions` unless Blake explicitly authorizes it.
7. Treat DeepSeek's answer as advice, not authority. Reconcile it against the actual codebase before making changes.
8. If DeepSeek output suggests it may have edited files or run tools beyond reading, immediately run `git status --short` and inspect any unexpected changes before continuing. Do not keep DeepSeek-authored edits unless Blake explicitly asked for them and Codex has reviewed them.
9. Report back with:
   - What was asked.
   - DeepSeek's key points.
   - Your assessment of which points are actionable.
   - Any proposed edits or tests.

## Subagent Use

Do not put this procedure behind a Codex subagent by default. The active agent should gather context, call `opencode run`, and interpret the response directly.

Use a Codex subagent only when Blake explicitly asks for subagents, delegation, or parallel agent work in that same request. If a subagent is used, assign it a narrow side task such as collecting relevant files or independently reviewing DeepSeek's answer. The actual `opencode run` call should stay with the active agent unless Blake specifically asks otherwise.
