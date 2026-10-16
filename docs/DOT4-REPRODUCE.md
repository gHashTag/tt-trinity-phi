# Reproducing every check of the SKY26d GF16 DOT4

Contract: `specs/numeric/gf16_dot4_sky26d.t27` (issue #100). Run all commands from the repository
root. Nothing here proves fit in one tile or the 50 MHz clock: only the GDS run of the final commit does.

Tools: `iverilog` + `vvp`, `yosys`, `verilator` (only for the archived width gate), Python 3, and a
virtualenv with `cocotb==2.0.1` (`pip install -r test/requirements.txt`). The Python helpers use only
the standard library.

## 0. Run one heavy job at a time (local) - CI is the place for the heavy runs
The unit sweeps and the gate-level run are heavy. LOCALLY run at most one heavy job at a time, check the
machine load first (memory pressure, swap), use `--jobs 1`, and do not start a heavy job while the machine
is under pressure; the full sweeps and the gate-level run belong to the remote CI (a fork push), where
`--jobs 4` uses the 4 cores of the GitHub runner. The commands below use `--jobs 1` locally; the CI file
uses `--jobs 4`. The coverage of the full profile is not reduced for either.

## 1. Static: spec, oracle, source list (seconds)
```
T27C=/Users/ssdm4/Documents/t27/target/release/t27c      # path of the local t27c build
$T27C parse     specs/numeric/gf16_dot4_sky26d.t27       # syntax
$T27C typecheck specs/numeric/gf16_dot4_sky26d.t27       # types ("0 errors, 0 warnings")
python3 test/t27_exec.py             # executes all 23 tests + 5 invariants (fail closed)
python3 test/oracle_selfcheck.py     # oracle vs code-space derivation, conformance JSON, spec vs model
python3 test/check_project.py        # info.yaml == Makefile == instantiated files; pins; action pin; no '*'
```
`t27c parse` and `typecheck` do not evaluate `assert`. `test/t27_exec.py` does, for this one spec, by
transpiling the small .t27 subset it uses; it is an honest equivalent, not the t27 seal.
Seal: use the repository's `t27c seal` procedure only after parse and typecheck pass, and only with the
`t27c` subcommand and flags shown by `$T27C --help`; do not hand-write seal files.

## 2. Synthesis audit (about a minute)
```
python3 test/synth_audit.py          # yosys: no $mul/$div/$mod/$pow; synth -flatten succeeds
```

## 3. Isolated units against the exact oracle
```
python3 test/unit_sweeps.py --profile quick --jobs 1     # local: sampled, NOT exhaustive
python3 test/unit_sweeps.py --profile full  --jobs 1     # exhaustive; very long locally, prefer CI
python3 test/unit_sweeps.py --profile full  --jobs 4     # what the GitHub job runs (4 cores, 240 min limit)
```
`--jobs N` is the number of worker processes (each runs the Python oracle and one `vvp`); it changes the
time, never the coverage. The CI job `unit-full` has a 240-minute limit.
Also runs `test/tb_sig_mul10.v`: all 2^20 products of the shift-and-add multiplier against the integer
product. `full` = ADD: all 63 exponent differences x both sign relations x all 512x512 mantissa pairs
(33,030,144 vectors); MUL: all 512x512 mantissa pairs for the 33 exponent sums around the threshold
values, stride 7 for the other sums; both: boundary sweeps and a zero/Inf/NaN class sweep. The count of
vectors is printed; a `quick` run says so. Required: 0 mismatches.

## 4. Pin-level tests on the RTL
```
source /Users/ssdm4/trinity-results/toolchains/phi-sky26d-venv/bin/activate
cd test && PHI_RANDOM_N=300 make && cd ..                 # 14 cocotb tests
python3 test/check_results.py test/results.xml test/test.py
```
`PHI_RANDOM_N` is the number of random vectors (CI uses 2000). Waves only with `make PLUSARGS=+vcd`.

## 5. Negative controls (mutated RTL must FAIL)
```
python3 test/mutation_runner.py       # inside the cocotb venv; copies src/ and test/ to a temp dir
```
It first requires the unmodified RTL to pass all tests, then applies 18 mutations (the original ones, where the single MUL tie mutation became three for the lower-binade tie, the upper-binade tie and the lower-binade rounding carry, plus four for the explicit write enables, the readback group select, the staged alignment sticky and a too-low far-alignment threshold, plus one that drops a carry term of the generic full adder in the multiplier; a mutation that cannot change the GF16 result, such as turning the far jam 1 into 0, is deliberately NOT included because an equivalent mutant cannot be killed) to the temporary
copy (B forced to 0, wrong `uio_oe`, signature shown as a result, result visible while busy, ERR never
set, WR/GO priority swapped, `ena` ignored, GO not resetting PTR, wrong MUL tie, wrong ADD tie, no sticky
bit) and requires every one to be KILLED by a PINFAIL; a surviving mutation or an infrastructure error
fails the run.

## 6. Gate level
The same `test/test.py` runs on the gate-level netlist in CI (`gl_test` of the official action, which
installs `cocotb==2.0.1` from `test/requirements.txt` and runs `make -B GATES=yes`). Locally, after a
GDS build produced `test/gate_level_netlist.v`:
`cd test && make -B GATES=yes` (needs `PDK_ROOT`), then `check_results.py` as above.

## 7. Same commit, official actions
`gds.yaml` (GDS, precheck, gl_test, viewer) and `docs.yaml` use the official `@ttsky26d` actions pinned
to commit `395eedb3eeec3c2f4961c3b04ff2cf87f5525636`. The physical checks `gds`, `precheck` and `gl_test`
(and the Docs build, and every job of `test.yaml`) are REQUIRED and must be green on the SAME final commit;
download the artifacts and record their SHA256.

The `viewer` job only publishes the layout view to GitHub Pages. It is optional and is not a physical
check: it runs only on the default branch (`main`) of whichever repository runs the workflow and is SKIPPED on
every other branch (no `continue-on-error`, nothing masked). On the `main` of a fork it does run, and
whether Pages is configured there is not verified. A skipped viewer is not a physical pass and not a
failure; a green `gds` + `precheck` + `gl_test` is what counts.

## 8. Native t27 toolchain gate (CI only; local build not required)
Job `t27-native` in `test.yaml` runs the REAL `t27c`, not the Python adapter. It checks out the pinned t27
commit `32c25e8798e33e03d5f6e7aee876df8629008a49` into `t27-src/` (a separate folder), builds
`cargo build --release -p t27c --locked`, fetches Zig 0.16.0 with `python3 test/fetch_zig.py --version 0.16.0
--dest "$RUNNER_TEMP/zig" --path-file "$GITHUB_PATH"` (verifies size and SHA-256 against
`https://ziglang.org/download/index.json`, prints the verified version and digest, changes PATH for that job
only), then runs `python3 test/t27_native_gate.py --t27c t27-src/target/release/t27c --spec
specs/numeric/gf16_dot4_sky26d.t27 --out native-t27`, which executes, from this repository's root:
`t27c parse SPEC`, `t27c typecheck SPEC`, `t27c test-report SPEC --specs-dir specs --verbose`,
`t27c seal SPEC --save`, `t27c seal SPEC --verify`. `--force` is never used and
`T27C_TEST_REPORT_EXIT_ZERO` must be unset. A BLOCKED run, zero tests, any failing test, a refused seal, a
forced test record, or a `gen_hash` of `none` fails the job. The seal's `tests.vacuous` is an INTEGER (the
number of passing tests that executed zero RUNTIME asserts; compile-time assertions are checked by the Zig
compiler instead), so it is validated as a non-negative integer and reported as `vacuous of total`, not treated
as a flag. What must hold instead is a negative control of the native toolchain: two copies of the spec, each
with ONE existing assertion made false, must still parse and typecheck, and `test-report` on each must either
FAIL (exit 1, FAIL >= 1) or be rejected by the compiler with the specific message of a false assertion
(BLOCKED, `does not compile` AND `assertion failed`, the text of the generated `@compileError`); any other
compile failure (missing import, type, linker), a pass, a crash or a missing Zig fails the gate. The native counts (23 `test` blocks) and the runtime-assert counters are different
from the 112 assertions executed by `test/t27_exec.py`; they are reported separately and are not added up. The native outputs and the seal JSON are
uploaded as the artifact `t27-native-gate`; the seal is NOT committed automatically; a person reviews the
artifact first. `python3 test/t27_exec.py` (28 blocks) remains a separate cross-check, not the seal.

### Seal origin metadata (test runner witness)
`t27c seal` records `toolchain.test_runner` as the sha256 of the file `bootstrap/src/test_report.rs` read
RELATIVE TO THE WORKING DIRECTORY (t27 `main.rs`, `seal_toolchain`), and `missing` when that file is absent;
it also refuses a spec that is outside the working directory (`seal_spec_path`), so the seal must run from this
repository's root. `t27_native_gate.py --t27-src t27-src --t27-commit 32c25e87...` therefore checks that the
t27 checkout is at the pinned commit and that its `bootstrap/src/test_report.rs` is byte-identical to the git
blob at that commit (the `t27c` that runs was built from the same commit), makes that real file visible at the
relative path for the seal run, requires `seal.toolchain.test_runner` to equal `sha256:<that digest>`, and
removes the temporary copy afterwards. The seal JSON is never edited by hand and `--force` is never used.

## 9a. Hierarchical area diagnosis (CI, after Build GDS)
`gds.yaml` runs `python3 test/area_profile.py --out area-profile --pdk sky130A` (the variant of `pdk: sky130A` in
the Build GDS step; the PDK store on the runner holds both sky130A and sky130B copies of the same liberty name, and
only `.../sky130A/libs.ref/sky130_fd_sc_hd/lib/` is accepted, sky130B is excluded) after the official Build GDS step with
`if: always()` and uploads the artifact `AREA_PROFILE`. It installs the host `yosys` (a different version from the
one inside the GDS flow; recorded), finds exactly one non-empty `sky130_fd_sc_hd__tt_025C_1v80.lib` on the runner,
fetches archived commit `949a634` with `git fetch --depth=1 origin 949a634...` (no checkout, the branch is
untouched) and synthesises, with the SAME recipe (`synth -flatten`, `dffunmap`, `dfflibmap`, `abc -liberty`,
`stat -liberty`) and the same liberty: the carry-save multiplier alone; the multiplier with the hidden-1 bits
constant; the adder of 949a634 and of the current commit; the full top of 949a634 and of the current commit;
and the top with MUL and ADD as non-constant BLACKBOXES (storage, multiplexers and control only; the blackbox
area is excluded and labelled so). Outputs: `AREA_PROFILE.md`, `area-profile.json`, `STATUS.txt`, per-profile
logs, final `stat` reports (`*.stat.txt`) and `.ys` scripts, `commands.txt`, the liberty path and sha256. Only
the final `stat` report is parsed. In the full and arithmetic profiles ANY cell of unknown area or unmapped cell
makes that profile FAIL with no number; in the storage profile the only allowed unknown-area cells are exactly the
blackboxes `gf16_v2_add` and `gf16_v2_mul` (explicitly excluded); anything else is FAIL. Any incomplete
diagnosis makes the step exit non-zero (the artifact upload runs with `if: always()`); the step can never turn a
red Build GDS green. It is a diagnosis (host yosys, not the GDS flow's version), not a fit proof; whether the
liberty and tools exist on the runner is only confirmed by the CI run itself.

## 9b. Official synthesis strategies (CI, after Build GDS)
The host profile of 9a does not reproduce the official synthesis: the official flow maps against a library that
drops the cells listed in the PDK `no_synth.cells` and `drc_exclude.cells`, with its own ABC script. `gds.yaml`
therefore also runs `python3 test/synth_explore.py` (`if: always()`, artifact `SYNTH_EXPLORE`): the official
LibreLane 3.0.14 built-in `SynthesisExploration` flow (`python -m librelane --docker-no-tty --dockerized --flow
SynthesisExploration`; `--docker-no-tty` must come BEFORE `--dockerized`, because the container entry reads it
before the eager `--dockerized` option and forwards only the arguments after it; strategies AREA 0..3 and
DELAY 0..4) on the same `src/config_merged.json`, PDK and cell exclusions, in its own empty `runs/synth-explore` (`--force-run-dir` needs an existing directory, which the
script creates only after every check passed; an existing non-empty directory blocks the run, nothing is removed,
and `--no-run` creates nothing)
(`runs/wokwi` is never touched). The built-in flow can exit 0 with a failed strategy hidden inside, so the nine
rows (cells, area, worst r2r setup slack, worst setup slack, TNS) are rebuilt from the real step states: the
strategy comes strictly from the normalised name of the custom STA directory (`<n>-sta-<strategy>`; the STA
config has no `SYNTH_STRATEGY`), which must be an `OpenROAD.STAPrePNR` step, paired with the matching
`<n>-synthesis-<strategy>` directory (`Yosys.Synthesis`, same `SYNTH_STRATEGY`) for cells and area; a missing,
duplicated or mismatching source fails the row, a missing value is an explicit `null`, never 0. The step exits non-zero on any failed strategy, incomplete table
or flow error, and when the row of the strategy used by the official Build GDS does not reproduce that run's own
area and cell count. That baseline is read (never written) from exactly one
`runs/wokwi/*-yosys-synthesis/{config.json,state_out.json}` of the same SHA (`SYNTH_STRATEGY`,
`design__instance__count`, `design__instance__area`; positive, finite, integer count). Nothing is hard-coded per
RTL change, and if the official strategy changes later, that strategy is the one calibrated. It is a
measurement, not a fit proof: a smaller area does not mean one-tile fit; only the main GDS job on the last SHA
decides that. No config, PDK, clock, tile or exclusion is changed. `--no-run --run-dir <dir> --baseline-run <dir>`
validates existing directories (for example a copied official run) without running the flow.

## 9c. Carry-save multiplier on the technology full adder (one structural change)
`src/gf16_sig_mul10.v` keeps its interface and its function for all 2^20 operand pairs, but the carry-save array
is written sparse: bits that are known zero are folded by hand, so 0 terms vanish, 1 term is a wire, 2 terms are a
half adder in plain xor/and logic and only 3-term positions use the full adder `gf16_fa1` (80 full adders, 10 half
adders). `gf16_fa1` has a generic logic branch (simulation, host audit, unit sweeps, mutations) and, when the
official LibreLane synthesis defines `__pnr__` (or `PHI_FA_PHYS` is set), one `sky130_fd_sc_hd__fa_1` cell, which the
PDK black-box or Verilog model supplies (nothing is declared in `src/`; `fa_1` is allowed by the PDK exclusion
lists, `ha_*`, `maj3_*`, `fa_4` and the `_0`/`_1` logic cells are not used). `test/check_project.py` allows exactly
that one cell, once, inside `gf16_fa1`. The generic simulation is NOT a proof for the cell branch: after Build GDS,
`test/physical_fa_check.py` (artifact `PHYSICAL_FA_CHECK`) compiles the project with `PHI_FA_PHYS` and the real
`primitives.v` + `sky130_fd_sc_hd.v` of the pinned PDK `8afc8346...` (exactly one directory, sha256 recorded; no
fallback model) and requires: the 8 truth cases of the cell and wrapper, all 1048576 products equal to the integer
product with mismatch 0 and exit 0 (an unknown or missing result is a failure; the wait per vector is a
conservative simulation setting, not timing), and a negative control (cell outputs swapped) that must be caught.
It is a PDK-model simulation, not a layout/LVS proof; the gate-level pin test remains required. The host profile of
9a is generic and does not predict the cell branch. No area, timing or fit is claimed before the official GDS: read
the `fa_1` count in `06-yosys-synthesis/reports/stat.json` and the new area/cells there.

## 9d. Official block area profile (CI, after Build GDS)
The host profile of 9a is not the official recipe, so `gds.yaml` also runs `python3 test/official_block_profile.py`
(`if: always()`, artifact `BLOCK_PROFILE`): five synthesis-only runs of the official LibreLane 3.0.14
(`--docker-no-tty` before `--dockerized`, `--flow Classic --to Yosys.Synthesis`, so nothing reaches SDC/STA), same
image, PDK and exclusion union. The provenance of the official run and of every probe is read from that run's single
synthesis step: `extra.json` `libs_synth` (the filtered libraries the mapper really read; each must exist on the host,
be non-empty and unique, with its sha256 and exact (cell name, area) table, every area finite and positive; the tables
must be identical to the official run, and so must the raw sha256 of the filtered library: its timing functions steer
the mapper too; a mismatch is a failure) and `blackbox_models`, the configured SYNTH/PNR exclusion files (sha256, line
count), `EXTRA_EXCLUDED_CELLS`, PDK `sky130A` with the pinned PDK version, `STD_CELL_LIBRARY`, the librelane version,
the real Yosys version from `stat.json` and the docker image id. Missing or unavailable provenance is a failure, never
"equal because both are missing"; on artifacts downloaded to another host the recorded paths do not exist, so
`--no-run` fails explicitly unless the paths are mapped with `--path-map OLD=NEW`. Every library cell type of a probe
must be in its own table with a finite positive area (no name accepted by prefix), counts must be positive integers
and the weighted sum must equal the stat and state area (0.01 um2). `full` is the unchanged `src/config_merged.json` and must reproduce the strategy,
cell count, area and per-type cell counts of the current `runs/wokwi` (read only, never hard-coded); `mul`
(`gf16_v2_mul` + `gf16_sig_mul10`), `add` (`gf16_v2_add`) and `add_norm14` (`DESIGN_NAME` `gf16_add_norm14`, the
normaliser module that already exists inside the unchanged `gf16_v2_add.v`; ports checked before the run; policy in
`specs/physical/gf16_dot4_addnorm_probe.t27`) change only `DESIGN_NAME` and `VERILOG_FILES`;
`storage` is the real top with temporary black boxes for the two arithmetic modules (real port lists parsed from the
sources, the arithmetic files left out). Temporary configs and the black-box file are written next to
`src/config_merged.json` so the `dir::` paths resolve as in the official run, are copied into the artifact and only
the files created by the run are removed; no exclusion list, strategy, density or define is overridden. The area of
the two black boxes is reported as EXCLUDED (not zero, not unknown); exactly those two are allowed, any other cell of
unknown area fails the probe. The probes optimise across different boundaries: their areas are not additive and are
not a physical partition. In particular `add_norm14` is the normaliser synthesised alone: it must not be subtracted
from `add` or summed towards `full`, and its area says nothing about fit. Any missing, non-finite or non-positive value, calibration mismatch, exclusion/library
mismatch with the official run or tool error makes the step exit non-zero; the artifact is always uploaded and a red
Build GDS is never masked. `--no-run --runs-root <dir> --baseline-run <dir>` validates copies. A diagnosis, not a fit proof.

## 9e. MUL normalise/round/exponent in two parallel binades
`src/gf16_v2_mul.v` computes the rounding and the exponent for both binades of the significand product in parallel
and lets `prod[19]` (or the lower-binade rounding carry) select at the end; the order stays round first, then the range
rules, with the same priorities (NaN, Inf, zero, underflow and the 2^-31 gap to +0, overflow, pack). Basis: the operands
are `{1, M}`, so the integer product is `2^18 <= P <= 1023*1023 = 1046529`. Lower binade: round up iff `P[8:0] > 256`
(`P[8]` and any of `P[7:0]`, a tie stays down); the fraction is `P[17:9]`; the round-up carries out exactly when `P[17:9]`
is all ones, which is reachable (`724*724 = 524176`). Upper binade: round up iff `P[9:0] > 512`; the fraction is
`P[18:10]`; a carry would need the significand `P[19:10] = 1023`, i.e. `P >= 1047552` (and, with a tie staying down, a remainder above 512, so `P >= 1023*1024 + 513 = 1048065`), above the
maximum, so it is unreachable for this wrapper (not for an arbitrary 20-bit input: `gf16_sig_mul10` is unchanged and still
covers all 1024 x 1024 pairs). The exponent candidates `esum - 31` and `esum - 30` and their range flags are formed in
parallel and selected by `top | cy_lo`. `test/mul_pack_bound.py`, run inside `test/unit_sweeps.py`, checks in plain integers
over all 512 x 512 = 262144 pairs that the mantissa and exponent increment of the new formulas equal the old
select-then-round scheme, that the upper carry count is 0, that the maximum product is 1046529 and that the lower carry
occurs; it is not an exhaustive check of all GF16 operand pairs, and the RTL itself is checked by the exact-oracle unit
sweeps (all 512 x 512 mantissa pairs at the threshold exponent sums), the pin tests (new exact-tie and carry vectors
`mul_tie_toward_zero_upper_binade` 0x407D and `mul_rounding_carry_into_next_binade` 0x4000) and the mutations. No area or
timing is claimed before the official GDS.

## 9f. ADD normalisation as a fixed 8/4/2/1 tree
After the single 14-bit add, `src/gf16_v2_add.v` normalises the sum with the module `gf16_add_norm14` (same file, purely
combinational, instantiated only by the adder, so the four-file source list is unchanged): four fixed stages of 8, 4, 2
and 1 positions; each stage tests whether the top group of the word that is left is empty and, if so, shifts the word by
that group size, and the four tests are the bits of the leading-zero count. It replaces the earlier priority encoder
followed by a variable shift and is the SAME function: `lz = 13 - position of the leading one`, 14 for a zero sum (the
last stage is qualified by bit 12, so a zero word leaves 8 + 4 + 2 = 14), and `norm = x << lz` in 14 bits (0 for zero).
Alignment, add/subtract, rounding, range and special handling are untouched. Checks: `test/add_norm_check.py` (integer
model of the formulas, all 16384 sums, run by `test/unit_sweeps.py`) and `test/tb_add_norm14.v` (the REAL RTL module
against the old definition on the same 16384 inputs: count and word, including zero, every leading-one position and
bit 13; `ADDNORM14_RESULT N=16384 MISMATCH=0`, also run by `test/unit_sweeps.py`, exit code and the exact N are
required); the adder itself stays covered by the exact-oracle unit sweeps, the pin tests and the existing mutations.
No area or timing is claimed before the official GDS.

## 9g. Operand and readback selection as two-level 2:1 trees
In `src/tt_um_trinity_nano.v` the operand selection (lane = `step[2:1]`) and the 16:1 readback (`ui_in[1:0]` inside
each group of four cells, then `ui_in[3:2]` over the groups) are written as explicit balanced binary trees of 2:1
multiplexers (nested conditional expressions on constant slices) instead of 4:1 `case` statements; the byte of cell c
is `mem_flat[8c+7:8c]`, the indices are one to one the same as before, every selection returns a stored byte at any time
(also while BUSY, after reset, with `ena = 0`), nothing is don't-care or X. The memory registers, write-enable decode,
pointer, FSM, lane formula, `prod`/`acc`, RSEL output mux and the external interface are unchanged. The mutation
`readback_group_select_swapped` now swaps the group-1 and group-2 select in the group tree. The function is the same;
whether the area changes is decided only by the official measurement (no generic netlist count is a physical result).

## 9h. Official ABC area knobs (CI, after SYNTH9)
`gds.yaml` runs `python3 test/synth_area_tune.py` (`if: always()`, artifact `AREA_TUNE`) before the long physical-model
simulation: by default six sequential synthesis-only runs of the official LibreLane 3.0.14 (`--docker-no-tty` before
`--dockerized`, `--flow Classic --to Yosys.Synthesis`) on the same `src/config_merged.json`, sources, PDK, exclusion union
and 20 ns clock, changing only `SYNTH_STRATEGY` (AREA 0 / AREA 1 / AREA 2; AREA 1 is the best strategy of the last full
official SYNTH9 table) and `SYNTH_ABC_AREA_USE_NF` (area mapper `&nf -R 1000` instead of `amap`) with
`SYNTH_ABC_USE_MFS3` False; no linter flag, exclusion, clock or design change. The optional switch `--include-mfs3` adds the
six `SYNTH_ABC_USE_MFS3` True rows (`mfs3 -aemvz -I 4 -O 2`, twelve in total). It is NOT run in CI: at the official 22c run (GDS
workflow 38845905126) the twelve-row matrix was a FAIL, not a PASS, because every MFS3=True row aborted in the upstream
ABC (`yosys-abc ... utilTruth.h: Abc_TtExpand: Assertion pCut[i] == pCut0[k] failed`, yosys-abc exit 134, LibreLane exit 2;
the six MFS3=False rows were valid). That is a recorded property of this tool on this netlist and configuration, not a
general "unsupported flag"; the abort is not masked or bypassed and the tool is not replaced, and the option exists to
reproduce it (still FAIL). If the official run itself used MFS3=True the default mode refuses honestly and asks for
`--include-mfs3`; it never changes the boolean by itself.
The strategy and both knob values of the CURRENT official run (`runs/wokwi`) must be one of these three strategies and real
booleans; the matching row must reproduce the official cell count, area and per-type counts, and every row is checked
against the official provenance (exclusion files, raw filtered library, PDK, versions, Yosys creator) and against its own
step configuration and generated ABC script, so a knob that did not take effect fails the row. Rows are checked like the
block profile (known library cells, finite positive areas, weighted area equal to stat and state). A tool error, an
unsupported option or a missing metric is an explicit failed row with null numbers; any incomplete table, calibration or
provenance mismatch fails the step. The tool exit code is part of every row: after each run the script writes its own small
record `PHI_TOOL_EXIT.json` (rc, command, `GITHUB_SHA` when set) into that run's directory, after the tool finished, and a
row is valid only if that record exists with rc 0; a failed row keeps any partly written numbers only under
`raw_measurements`, its public area/cell fields are null, and it can never be the minimum row. The summary lists the selected
rows and the minimum VALID row, a candidate for the full GDS, not a winner; this is an area-only diagnosis, not timing and
not a fit proof. `--no-run --runs-root <dir> --baseline-run <dir> [--path-map OLD=NEW]` validates copies and also requires
the exit record (a missing record is a failure, never a pass); a non-empty run directory still blocks a run.

## 9i. ADD zero operands through the common arithmetic (one structural candidate)
Policy and proof boundaries: `specs/physical/gf16_dot4_addnorm_probe.t27` section 5; the numeric contract, the oracle,
the top, the 8-clock schedule and `gf16_add_norm14` are unchanged. In `src/gf16_v2_add.v` a finite zero now enters the
arithmetic with significand 0 (the zero flags are sorted by the same compare as the operands; every nonzero code, also
E = 0 with M > 0, keeps its hidden 1), the far jam bit is 0 for a zero low operand, and the three separate zero output
branches are removed; NaN, Inf and Inf - Inf keep their priority. Zero + x gives x bit for bit through the common path
(sum = the significand of x, normaliser shift 1, no rounding, exponent E); zero + zero gives a zero sum and so +0.
Check: `python3 test/add_zero_sweep.py --out add-zero-sweep` (CI job `unit-full`, before the unchanged full sweeps,
artifact `add-zero-sweep`): +0 and -0 against all 65536 codes in both orders, 262144 vectors with the unit bench and
the exact oracle, 0 mismatches required; plus a negative control in a temporary copy (the zero low operand gets the
hidden 1 back) that must show real mismatches including 0x0000 + 0x0001 (a missing mutation text, a compile error or a
missing result line is an error, not a kill). Limits: neither area nor timing is measured here; the effect is decided
only by the official full mapping and the physical flow of the same commit.

## 9j. ADD significand sum on the full-adder wrapper (one structural candidate)
Policy and the equivalence argument: `specs/physical/gf16_dot4_addnorm_probe.t27` section 6. The former 15-bit form
`{1'b0, bext, 1'b1} + {smj_x, eff_sub}`, bits [14:1], is the 14-bit sum `({1'b0, bext} + smj_x + eff_sub) mod 2^14`;
`src/gf16_v2_add.v` now writes that sum as one ripple chain with carry seed `eff_sub`: half adders on bits 0..2 and an
xor on bit 13 (the corresponding bits of `{1'b0, bext}` are the constant 0), `gf16_fa1` (the unchanged wrapper of
`src/gf16_sig_mul10.v`, generic logic in simulation, `fa_1` under `__pnr__`) on bits 3..12. Everything around the sum
is unchanged. Every standalone compile or synthesis of the adder now also lists `gf16_sig_mul10.v`
(`test/unit_sweeps.py`, `test/add_zero_sweep.py` incl. its temporary mutant, `test/official_block_profile.py` `add` and
`add_norm14`, `test/area_profile.py`, `test/width_gate.py`); the four active files, `info.yaml` and the Makefile are
unchanged. Checks: `python3 test/add_carry_check.py --out add-carry-check` (CI job `unit-full`, after the zero sweep,
before the full sweeps): the deterministic set of `test/add_vectors.py` (cancellation, borrow, different signs, carry,
ties, far jam, edge exponents, NaN/Inf, zeros, the ADD steps of the DOT4 conformance vectors) against the oracle with 0
mismatches, and a temporary copy with carry seed 0 that must show a real mismatch on two finite nonzero operands of
different sign (missing text, compile error or missing result is an error, not a kill). `test/physical_fa_check.py`
(after Build GDS) additionally runs the active adder with `-DPHI_FA_PHYS` on the real pinned PDK models
(`-Punit_tb.SETTLE`, the generic default of `unit_tb.v` stays 1) on the zero set and the carry set, and the same
wrong-seed copy there. The old checks (full sweeps, 14 pin tests, 18 mutation controls, 2^20 products) are unchanged.
Limits: no area or timing is measured by these checks; a ripple chain can be slower than the former mapping; only the
official full mapping and physical flow of the same commit decide.

## 9. Datasheet preview (CI)
After the official docs action, job `docs-preview` in `docs.yaml` downloads the artifact `PDF`, requires a
non-empty `datasheet.pdf`, runs `pdfinfo` and `pdftoppm -r 110 -png` for every page, requires one non-empty
PNG per page and uploads the artifact `DocsPreview` (page images and `pdfinfo.txt`) for a visual check. It does
not replace or weaken the official docs job; a local render is not needed.

## Archived comparison jobs
`test/gf16_v2_verify.py`, `test/width_gate.py`, `test/gf_add_sweep.py`, `test/phi_audit.py` test archived
files and stay in CI as they were; their result is not a statement about the current DOT4. The old
`gf16_v2_verify.py` only checks that the v2 units are faithful (<= 1 ULP add, <= 0.5 ULP mul).
