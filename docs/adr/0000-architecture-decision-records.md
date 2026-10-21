# Kailash OS packages — Architecture Decision Records

This directory records the overlay repo's own decisions. A decision binds
written outputs this repo owns: the CLI help and output strings, the
`cli/README.md`, and the issue and PR bodies written here.

## Index

| Number | Title | Status |
| --- | --- | --- |
| [0001](0001-asd-ste100-standard.md) | ASD-STE100: the org writing standard (overlay adoption) | accepted |

## When this directory records a decision

The org's structural engineering decisions keep one record home:
[`kailash-os`](https://github.com/kailash-os/kailash-os/tree/master/docs/adr)
`docs/adr/` — [the process](https://github.com/kailash-os/kailash-os/blob/master/docs/adr/0000-architecture-decision-records.md),
[the record format](https://github.com/kailash-os/kailash-os/blob/master/docs/adr/0001-record-format.md).
Records that bind only this repo's prose and string surfaces live here, in
the same PR as the change they record.

Rules:

- Accepted records are immutable. A change that contradicts a record
  supersedes it with a new record.
- The record never invents discussion, deciders, or quotes. It cites
  permalinks, or it states "No substantive technical discussion recorded".
