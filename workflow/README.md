# Workflow README

## Three-profile team: planner → developer → qa

### Shared workspace
`~/Desktop/html catalogger/workflow/`

```
workflow/
├── plans/       — planner drops approved plans here
├── builds/      — developer drops built results here
└── reviews/     — qa drops review reports here
```

### How a job flows

1. **You** give an idea to **planner** (Telegram or CLI)
2. **Planner** writes a plan to `plans/<slug>.md` and asks for your sign-off
3. **You** approve → planner tells **developer** to build
4. **Developer** builds, writes result + handoff note to `builds/<slug>/`
5. **Developer** flags "ready for review"
6. **QA** picks up the build, reviews against the plan, writes report to `reviews/<slug>.md`
7. **QA** flags findings (blocker / should-fix / nit)
8. **You** decide: ship it, send back to dev, or discuss

### File conventions

- Plan files: `plans/<descriptive-slug>.md`
- Build folders: `builds/<slug>/` (contains the output + `handoff.md`)
- Review files: `reviews/<slug>.md`

### Roles

| Profile | Telegram bot | Job |
|---------|-------------|-----|
| planner | `@plannerbot` (8859201981) | Turn ideas into plans |
| developer | `@developerbot` (8958797858) | Build from plans |
| qa | `@qabot` (8624360395) | Review builds against plans |

### Handoff note format (developer → qa)

```markdown
# Build: <slug>

## What was built
[brief description]

## Plan followed
[yes / mostly / deviations — list any deviations from the plan]

## How to test
[steps to verify the build works]

## What's in this folder
- [file list with brief description of each]

## Known issues / concerns
[anything the dev is unsure about]
```

### Review report format (qa → user)

```markdown
# Review: <slug>

## Plan vs built
[does the build match what the plan said?]

## Findings

### Blockers
- [must fix before shipping]

### Should fix
- [important, fix soon]

### Nits
- [optional improvements]

## Verdict
- [Ship / Send back to dev / Discuss]
```
