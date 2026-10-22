<!--
PR title: Conventional Commits form carrying the task id on roadmap slices,
e.g. feat(pkgs): KA-12.1 — ART: pin + Shape-1 derivation
(A CI gate checks the title form on every PR.) One logical change per PR.

Writing: the new prose follows ASD-STE100. One thought per sentence, at or under 20 words, active voice, no idioms.
-->
## What

<!-- what changed, one paragraph -->

## Why

<!-- the KA-XX issue this implements; the plan section in the issue body is the design source -->

Closes #__

## Verification

<!-- how you proved the change: watched RED output, GREEN output, flake check / build evidence -->

- [ ] `nix flake check --all-systems` green
- [ ] relevant gate/manifest evidence linked
- [ ] The new prose follows ASD-STE100: one thought per sentence, at or under 20 words, active voice, no idioms.
