# A small recording pilot

This is the practical handoff for H01–H03. It does not authorize a device connection, start a recorder, download videos, or train a model. The owner can supply this packet whenever convenient; independent offline development continues meanwhile.

## Start with what you already have

The proposed first packet is three to five short menu-decision segments, plus one unedited complete run if readily available. Segments may simply be approximate worksheet references into an unchanged original; no cutting or re-encoding is needed. These counts test the preparation workflow; they are not an estimate of how much data will train a successful agent. A smaller sample is still useful. Prefer an original recording over a recompressed or edited upload.

Useful first decisions include choosing a visible option on recruitment, route, or event menus, and bounded waiting. The schema's `stop` means ending the agent/replay session without another game interaction; it does not mean retreating, abandoning a run, quitting the game, or simply reaching the end of a recording. The current action schema cannot represent deployment, skills, retreating, or a complete battle. Preserve battle footage for a later schema extension; do not relabel it as menu actions.

Recordings with synchronized input logs are preferred. If only video exists, keep it: we can prepare it for manual review, but any recovered action starts as an inferred label. Missing inputs and uncertain timing stay unknown. A successful run alone does not tell us every input that produced it.

Use material you are entitled to supply for this project. Keep the originals and reports in private storage outside this public repository. Do not paste account identifiers, passwords, connection settings, or share links into public project files. Do not start a new unattended game run merely to fill this packet.

## A private packet layout

This layout is a suggestion, not a required machine-readable schema:

```text
private-pilot/
  INTAKE.md
  inventory-request.json
  originals/
    run-a.mp4
  input-logs/
    run-a.jsonl         (only if an original log actually exists)
  review-notes/
    decisions.md
```

Keep original files unchanged. Put annotations and any later redacted/derived media in separate files. If a source contains unrelated personal material, describe the issue privately and arrange an approved/redacted sample before giving the development agent access. Do not assume ignored files or local report folders are secure storage.

The byte-inventory request lists only files actually supplied. Paths are relative to the packet's top-level directory, which must be supplied explicitly as `--media-root`; locating the request file does not automatically select that root. For a video-only packet it would be:

```json
{
  "schema_version": 1,
  "assets": [
    {"asset_id": "recording-a", "path": "originals/run-a.mp4"}
  ]
}
```

An original input log can be listed as a second asset with its own ID/path. This selection establishes neither permission nor label acceptance; it merely selects files for byte hashing. Do not add URLs, absolute paths, or invented missing files. Related edits/uploads should later share a leakage group even when their hashes differ.

## Intake notes to supply privately

Copy these field names into the private `INTAKE.md`. Use `unknown` when information is missing; this worksheet is not consumed by a validator.

| Field | What to record |
| --- | --- |
| Target | Integrated Strategies theme, difficulty, intended ending, and representative roster |
| Source | Your own recording or another source you are entitled to supply; permission scope and any restrictions |
| Recording ID | An opaque ID, not an account name |
| Related sources | Other runs, edits, duplicate uploads, or views that must stay in the same evaluation partition |
| Capture context | Client language, known game version, capture resolution, and whether a cursor/touch marker is visible |
| Editing | Unedited, known cuts/speed changes/overlays, or unknown; preserve the original where available |
| Input log | Present or absent; which tool created it; requested inputs versus recorded human inputs; its documented clock |
| Timing evidence | Any reliable sync marker/clock mapping and its uncertainty, or unknown |
| Outcome | Clear, loss, abandonment, or unknown; specify which objective and the evidence, not just a filename saying “win” |
| Privacy | Account overlays, chat/notifications, or other information needing review before access |

Do not guess exact timing from a displayed progress bar or substitute a controller's reported success for the game outcome. The existing [collection plan](training-data-collection.md) explains the verified MAA/MaaFramework limitations.

## What happens after the packet is approved

1. Inventory explicitly selected file bytes and review size/hash duplicate candidates. This does not decode video or verify rights.
2. Use the separately implemented and tested media-indexing stage when available to retain actual frame timestamps and coordinate transforms. It is not implemented by byte inventory.
3. Prepare a few causal decision windows: only frames visible before the action may enter the policy input. Keep later outcome evidence separate.
4. Ask the owner to review candidate action labels and uncertain cases. Preserve `human`, `input_log`, or `inferred` origin after acceptance; never turn an inferred label into a logged input.
5. Validate reviewed demonstration declarations, assign whole leakage groups to partitions, and inspect the eligibility report. Empty evaluation partitions stay empty. A report does not certify training readiness.

For the first review, a plain private worksheet is enough: recording ID, approximate place to inspect, visible decision, proposed label, label origin, supporting evidence, timing uncertainty, and review result. Approximate places are navigation hints, not authoritative frame timestamps or ready-to-import manifest rows. Stop at ambiguous or unsupported actions instead of inventing labels.

## Expand only after the pilot works

Once the workflow preserves timing, inputs, provenance, and reviews, collect broader conditions: different rosters/stages and examples of mistakes, recovery, failed runs, and human corrections alongside clears. Track what is actually covered and keep related recordings together. Do not count synthetic fixtures as coverage of gameplay.

No specific volume or model performance is promised yet. Dataset sizing, model-specific export, GPU preflight, and actual training are later decisions informed by the inspected pilot. The owner's current instruction continues to defer all weight updates.
