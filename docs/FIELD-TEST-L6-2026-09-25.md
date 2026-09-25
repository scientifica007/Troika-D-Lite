# L6 Field Test — 2026-09-25

## Tested build

Repository: `scientifica007/Troika-D-Lite`

Branch: `milestone/l6-packaging-dependency-audit`

Packaging/runtime commit tested:

```
4bedf353a32d203c67fea06c783436b0b9cfb2d1
```

Target environment: Ubuntu 24.04 / Wayland.

## Human package acceptance result

**L6 HUMAN FIELD GATE: PASS**

The generated Debian package was installed, launched, exercised, and removed successfully on the field machine.

Validated:

1. local `.deb` installed with APT without manual file copying;
2. package status reported `install ok installed`;
3. package version reported `0.1.0~alpha0-1`;
4. `/usr/bin/troika-d-lite` was available while the package was installed;
5. Troika D Lite appeared in the GNOME application launcher with its application icon;
6. launcher opened the accepted L5 interface;
7. microphone and system-audio controls were present;
8. one 30 FPS recording with system audio completed successfully;
9. output behavior remained the accepted `~/Videos` product behavior;
10. APT removal completed successfully;
11. desktop entry and application icon were removed;
12. the installed command file was confirmed absent after removal.

## Installation evidence

APT installed the local package as:

```text
troika-d-lite 0.1.0~alpha0-1
```

Post-install checks:

```text
/usr/bin/troika-d-lite
Status: install ok installed
Version: 0.1.0~alpha0-1
```

The GNOME application launcher displayed **Troika D Lite** with its packaged icon.

APT emitted the informational notice that the local package file could not be read by the `_apt` sandbox user and was therefore read as root. The package still installed successfully. This notice concerns the permissions/location of the local `.deb` file used for the field test, not the application package contents.

## Recording evidence from installed package

The installed command completed a normal recording with system audio:

```text
EOS request: source-pads=[screen_src:1,system_audio_src:1] pipeline-fallback=0 accepted=1
Video timing stats [eos] fps=30 mic=0 system=1 in=53 out=91 drop=3 duplicate=41
```

No recording error, pipeline fallback, or finalization timeout was reported.

## Removal evidence

APT removal completed successfully.

The desktop entry and icon were confirmed absent.

Immediately after removal, the same interactive Bash shell initially returned:

```text
/usr/bin/troika-d-lite
```

for `command -v troika-d-lite`.

A direct filesystem check established that the command file had actually been removed:

```text
ls: cannot access '/usr/bin/troika-d-lite': No such file or directory
FILE REMOVED
bash: type: troika-d-lite: not found
command removed
```

After `hash -r`, `command -v` no longer returned the path.

This confirms that the earlier result was shell command-hash state, not leftover package content.

**Package removal cleanliness: PASS.**

## L6 decision

**L6 HUMAN FIELD GATE: PASS**

L6 is accepted as the native Debian/Ubuntu packaging and dependency-contract baseline.

The next milestone is the controlled performance benchmark and final field acceptance. L6 does not itself assign beta/stable release status.
