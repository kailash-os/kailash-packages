# 0001 — ASD-STE100: the overlay's writing standard

Status: accepted

## Context

The overlay carries written surfaces the reader meets directly: the CLI
help, usage, and error strings; the `cli/README.md`; and the issue and PR
bodies written here. The register differs between those surfaces. The
printed strings also sit inside recorded quotes: the README examples, the
release notes, and the check assertions all carry the printed output.

## Decision

The operator's directive (2026-10-20) sets the standard. The org record is
[`kailash-os` ADR 0004](https://github.com/kailash-os/kailash-os/blob/master/docs/adr/0004-asd-ste100-standard.md);
this record adopts the same rule set for this repo's written output.

Every written text in the overlay follows ASD-STE100 Simplified Technical
English:

1. One thought per sentence. A sentence carries one fact or one instruction.
2. A sentence stays at or under 20 words.
3. The voice is active. The tense is present. Instructions sit in the imperative.
4. A non-approved verb takes one fixed approved substitution.
5. One word carries one meaning, on every surface.
6. Fixed technical names stay exact: tool ids, flag names, layer names, gate names.
7. Numbers use digits, with units adjacent.
8. Rendered text carries no idioms, no slang, and no first or second person.
9. No invented facts. A claim states its basis. A measured number cites the record that measured it.
10. Historical records keep their filed tense and wording.

The scope, and the boundary:

- `cli/README.md`, `AGENTS.md`, and the CLI help, usage, and error strings
  follow the rule set.
- A printed-string change is a code change. It re-pins every recorded output
  line in the same change: the README examples, the release notes quotes,
  and the check assertions in `cli/check-kailash-cli.py`.

Enforcement:

- The conversion lane is [kailash-packages#68](https://github.com/kailash-os/kailash-packages/issues/68).
- Every change rides a leaf branch, a signed Conventional Commit, and a PR.
- Every PR keeps the repo gates green: `flake-check`, `pr-title-gate`, and
  `pre-commit.ci`.

## Consequences

- Strings written after this record follow the rule set from the merge day on.
- The standing README and `AGENTS.md` prose converts through the conversion lane.
- A recorded output line never drifts silently: the re-pin rides the string
  change, and the check pair proves the pair.
