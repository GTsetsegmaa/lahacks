# Claude Code Rules of Engagement

You are working on the SupplyMind project. Read PROJECT.md before any task.

## Core principles

1. **Stay in scope.** PROJECT.md defines what is being built. Do not add features, agents, pages, or capabilities beyond what is listed there. If you think something is missing, ASK before adding.

2. **One slice at a time.** When asked to build something, build the smallest working version first. Do not add error handling, logging, or polish until the basic version works end-to-end.

3. **Respect the contract.** `shared/contracts.py` is the source of truth for data shapes. Never edit it without explicit instruction. Always import from it; never redefine types locally.

4. **No silent refactors.** If you need to change a file outside the one you're working on, STOP and tell me what you want to change and why. Do not refactor "for cleanliness."

5. **Demo external calls are strictly limited.** During a demo run, the only permitted external service calls are: (1) the LLM — Gemma via local Ollama on the GX10, or a hosted LLM API as fallback; and (2) ElevenLabs for voice narration. Everything else — ERP systems, commodity price APIs, news feeds, carrier APIs — must use static local mock data. The Market Intelligence Agent reads from `shared/mock_data/external_signals.json`, not a live API. Do not add any new external service calls without explicit instruction.

6. **Verify before claiming done.** After writing code, explain what you would do to test it. Do not say "this should work" — say "to verify, run X and expect output Y."

7. **Fail loudly.** If a piece of the spec is ambiguous, ask. Do not guess and proceed. If you don't know how a Fetch.ai API works, say so — do not invent method signatures.

## Specific anti-patterns to avoid

- DON'T generate 500+ lines in one response. Break it up.
- DON'T add features I didn't ask for ("I also added authentication for security").
- DON'T rewrite working code to be "cleaner" unless I asked for refactoring.
- DON'T use placeholder values like `# TODO` or `pass` in code that's supposed to work — implement it or tell me you can't.
- DON'T import libraries that aren't in `requirements.txt` / `package.json` without asking me to add them first.
- DON'T assume Fetch.ai SDK behavior — if I haven't pasted the docs in, ask me to.

## How to ask for help

When you're stuck or uncertain, format your response as:

> **Status**: Stuck on X.
> **What I tried**: Y.
> **What I need**: Either docs for Z, a decision on W, or permission to do V.

## When generating code

- Use type hints in Python (Pydantic models, function signatures).
- Use TypeScript strictly in the dashboard (no `any` unless I say so).
- Match the existing code style in the file you're editing.
- Write docstrings for agents and orchestration code; skip docstrings for trivial functions.
- Prefer composition over inheritance.
- Keep functions under 50 lines where possible.

## File operations

- Always show me the full file path you're editing.
- For new files, show the full content.
- For edits to existing files, use precise string-replace operations rather than rewriting the whole file.
- Commit working code as you go — suggest a commit message after each meaningful unit of work.
