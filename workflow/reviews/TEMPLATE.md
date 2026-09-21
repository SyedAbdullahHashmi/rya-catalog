# Review template (qa → user)

Fill this in after reviewing a build. Put it in `reviews/<slug>.md`.

---

# Review: <slug>

**Build folder:** `builds/<slug>/`
**Plan:** `plans/<slug>.md`

## Plan vs built

[Does the build match what the plan said? Be specific:
- What matches
- What doesn't match
- What's missing
- What's extra (out of scope but included)]

## Findings

### Blockers
[List only issues that must be fixed before this ships. Explain why
each is a blocker — what breaks, what's wrong, what the risk is.]

- 

### Should fix
[List important issues that aren't strictly blockers but should be
addressed soon. Explain the impact of leaving them.]

- 

### Nits
[List minor improvements, style issues, or optional changes. Keep
this section short — don't pad it.]

- 

## Verdict

- [ ] **Ship** — build matches the plan, no blockers, ready to go
- [ ] **Send back to dev** — has blockers or significant gaps; dev
       needs to fix before this ships
- [ ] **Discuss** — unclear, needs a decision, or both dev and QA
       need to align before proceeding

## Notes for the user

[Any context the user needs: what QA checked, what wasn't checked,
what the main risks are, what the recommendation is and why.]
