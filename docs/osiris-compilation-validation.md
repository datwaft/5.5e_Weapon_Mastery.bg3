# Osiris compilation inputs and validation

## Current result

BG3 compiles and runs `WM55_Nick.txt` when the repository contains the campaign dependencies and the Toolkit-generated metadata.

The campaign dependencies alone did not make the goal active. The next experiment must isolate the Toolkit-generated inputs.

## Toolkit-generated inputs

The Toolkit added these inputs:

| Input | Previous value | Current value |
| --- | --- | --- |
| `GUI/metadata.lsf` | File absent | 1,141-byte LSF resource |
| `ModuleInfo/FileSize` | Attribute absent | `0` |
| `ModuleInfo/MD5` | Empty string | `c0a8f3412870277331306e0719fc6f77` |
| `ModuleInfo/Version64` | `36028797018963968` | `36028797018963969` |
| `ModuleInfo/PublishVersion` | Node absent | Version `36028797018963968` |
| `ModuleInfo/Scripts` | Node absent | Two script entries |

LSLib converts `GUI/metadata.lsf` to this logical structure:

```xml
<region id="config">
  <node id="config">
    <children>
      <node id="entries" />
    </children>
  </node>
</region>
```

The resource contains no project-specific entry. Its presence or resource format can still act as a marker, so the empty content does not prove that the file is unnecessary.

The current package does not contain `story.div`, `story.div.osi`, or `goals.raw`. `PublishHandle` is still `0`.

## Run the minimum-input experiment

The manual `Build Osiris metadata experiments` workflow creates eleven packages from the same revision. It changes one candidate at a time and includes positive and negative controls.

1. Open the repository's **Actions** page.
2. Select **Build Osiris metadata experiments**.
3. Run the workflow from the revision that contains the working Osiris implementation.
4. Download the `osiris-metadata-experiments` artifact.
5. Install only one experiment package at a time.
6. Load the same save and use the same Nick combat setup for each package.
7. Record whether `WM55_Nick` runs.

Use this interpretation:

- `control-working` must work.
- `control-pre-toolkit` must fail to load the goal.
- A failing `no-*` package identifies a required input.
- A working `no-*` package shows that the removed input is not independently required.
- `gui-metadata-only` tests whether `GUI/metadata.lsf` is sufficient with the old manifest shape.

If all one-change packages work, two or more inputs can be alternatives. Add a second matrix that removes combinations before declaring any input unnecessary.

## Offline database-type check

Run the checked-in validator from the repository root:

```shell
python3 tools/check_osiris_database_types.py
```

The default command uses a small signature snapshot and runs on Windows, macOS, and Linux. CI runs the same check.

Use the installed game header for a broader local check:

```shell
python3 tools/check_osiris_database_types.py \
  --story-header "/path/to/Baldurs Gate 3/Data/Mods/GustavDev/Story/RawFiles/story_header.div"
```

The validator checks function signatures and inferred database column types. It detects the previous Nick error where one rule defined a database actor as `CHARACTER` and another rule supplied `GUIDSTRING`.

This is a focused static check. It does not compile a story or prove that BG3 will merge a goal into the campaign story.

## LSLib StoryCompiler result

[LSLib v1.20.4](https://github.com/Norbyte/lslib/releases/tag/v1.20.4) includes `StoryCompiler.exe`. The tool supports BG3, JSON diagnostics, and a `--check-only` mode.

The current BG3 `story_header.div` does not parse without modification. The header contains `enum_type` declarations and aliases that refer to other aliases. The current [LSLib header loader and type registry](https://github.com/Norbyte/lslib/tree/master/LSLib/LS/Story) do not accept those forms.

A temporary compatibility transform lets LSLib check the current Nick goal. However, LSLib also accepts the exact `GUIDSTRING`/`CHARACTER` regression that BG3 rejects. Therefore, LSLib is useful for some syntax and reference checks, but it is not a complete replacement for BG3's compiler.

## Remaining work

- Run the generated packages in BG3 and record the result for each variant.
- Build combination variants if the first matrix does not identify a unique required input.
- Repeat the confirmed minimum with the `./link` setup.
- Decide whether to keep the focused validator, extend it, or replace it if a compatible compiler becomes available.
