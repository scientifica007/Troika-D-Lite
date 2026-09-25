# L8 — Beta Release Preparation and Decision

## Purpose

L8 prepares the first public Troika D Lite beta without silently publishing it.

The candidate is:

```text
v0.1.0-beta.1
```

No Git tag or GitHub Release is created until the final release decision is explicitly approved.

## Release identity mapping

| Surface | Version |
| --- | --- |
| Git tag / GitHub Release | `v0.1.0-beta.1` |
| Python / PEP 440 | `0.1.0b1` |
| Debian | `0.1.0~beta1-1` |
| AppStream | `0.1.0-beta.1` |

`scripts/verify-release-metadata.py` and CI enforce this alignment.

## Release baseline

L8 starts from the accepted L7 main baseline:

```text
d4aedd3224da90d100afa9ffaa83fa37f3a628a7
```

At that baseline:

- L1–L7 are accepted;
- main Post-merge CI is PASS;
- no Git tags exist in the Lite repository;
- no GitHub Releases exist in the Lite repository.

## Product scope

The beta keeps the v0.1 product boundary unchanged:

- Full Screen only;
- 15/30 FPS;
- optional microphone;
- optional system audio;
- microphone + system audio mixing;
- MP4/H.264;
- Start/Stop;
- Ubuntu 24.04 / Wayland first.

No new recording feature is introduced in L8.

## Release-candidate corrections

L8 aligns release metadata after field acceptance:

- Python version moves to `0.1.0b1`;
- Debian default version becomes `0.1.0~beta1-1`;
- AppStream records `0.1.0-beta.1`;
- CI expects beta-named Python and Debian artifacts;
- README reflects completed L7 acceptance;
- the v0.1 UI specification is corrected to the accepted static recording view;
- release notes document validated behavior and known limitations.

## Required automated gate

Before the release decision, CI must pass and verify:

- release metadata alignment;
- project metadata parsing;
- GTK/GStreamer imports;
- required GStreamer elements;
- runtime dependency ownership;
- desktop/AppStream metadata;
- unit tests;
- wheel + sdist build for `0.1.0b1`;
- Debian package build for `0.1.0~beta1-1`;
- Debian package structural verification;
- Lintian error gate;
- APT install/remove;
- benchmark-tooling smoke;
- compileall.

## Artifact expected for publication

Primary Debian build filename:

```text
troika-d-lite_0.1.0~beta1-1_all.deb
```

Published GitHub release asset filename:

```text
troika-d-lite_0.1.0.beta1-1_all.deb
```

GitHub normalizes `~` to `.` in uploaded asset filenames. This does not
change the Debian package version stored in the package metadata, which
remains `0.1.0~beta1-1`.

Source remains available through the Git tag and GitHub source archives.

Python wheel/sdist are CI-validated but do not need to be published to PyPI for this beta.

## Release notes

User-facing notes:

- `docs/RELEASE-NOTES-v0.1.0-beta.1.md`

## Known non-blocking observations

- Ubuntu 24.04 / Wayland is the validated target; X11 is not claimed;
- system-side Share Screen Portal text rendering may be imperfect on some graphics configurations;
- host-wide stutter under the tested extreme local-video/workspace-switch workload reproduced without a recorder and is not classified as a Lite defect;
- bounded finalization can take several seconds in some low-motion cases while still completing through normal EOS.

## Release decision gate

A public beta may be created only after:

1. the L8 candidate PR is green;
2. beta release metadata is internally consistent;
3. the beta Debian package builds and installs in CI;
4. no new field-blocking defect is introduced by release-only metadata changes;
5. the user explicitly approves publishing the tag and GitHub Release.

## Publication plan after approval

After explicit approval:

1. merge the L8 candidate PR to `main`;
2. verify Post-merge CI on the exact merge commit;
3. build the final `.deb` from that exact `main` commit;
4. verify the package;
5. create tag `v0.1.0-beta.1` on that exact commit;
6. create a GitHub prerelease named **Troika D Lite v0.1.0-beta.1**;
7. attach the GitHub-safe asset `troika-d-lite_0.1.0.beta1-1_all.deb` (Debian package version remains `0.1.0~beta1-1`);
8. use `docs/RELEASE-NOTES-v0.1.0-beta.1.md` as the release-note basis;
9. verify the published tag, asset, and release metadata.

L8 preparation does not itself authorize step 5 or later.


## Publication authorization and execution

Publication of `v0.1.0-beta.1` was explicitly authorized on 2026-09-25.

Because the connected GitHub action surface does not expose a direct create-release mutation, publication is implemented as an auditable repository workflow:

- `.github/workflows/publish-v0.1.0-beta.1.yml`

The workflow publishes only after the normal `CI` workflow succeeds on the dedicated release-trigger branch:

```text
milestone/release-v0.1.0-beta.1
```

Before publication it verifies that the CI-tested SHA equals the current `main` SHA. It then:

1. checks out that exact SHA;
2. verifies release metadata;
3. builds and verifies `troika-d-lite_0.1.0~beta1-1_all.deb`;
4. creates or verifies tag `v0.1.0-beta.1` on the exact SHA;
5. creates a GitHub prerelease using the committed release notes;
6. uploads the Debian asset;
7. re-reads the tag, release state, prerelease flag, and asset list.

This workflow is idempotent for the same release SHA: an existing correct tag/release is verified, and the Debian asset may be refreshed from the same exact source commit.
