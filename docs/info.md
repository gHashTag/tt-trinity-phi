<!---
This file is used to generate your project datasheet. Please fill in the information below
and delete any unused sections. You can also include images in this folder and reference
them here.
--->

## How it works

A pin-loadable dot product of two 4-element vectors in the 16-bit **GF16** float format:

`r = A0*B0 + A1*B1 + A2*B2 + A3*B3`

GF16 is `[S(1) E(6) M(9)]`, exponent bias 31. A finite number is `(-1)^S * (1 + M/512) * 2^(E-31)`.
There are no subnormals: `E=0, M>0` is an ordinary number with the leading one, and the smallest
positive code is `0x0001`. `E=0, M=0` is zero (either sign is accepted as an input), `E=63, M=0`
is infinity and `E=63, M>0` is NaN. The NaN result is always `0xFE01`. The value `2^-31` has no
code. This is a custom format, not IEEE 754.

The host writes the eight 16-bit operands as 16 bytes, starts the computation, waits for DONE and
reads the 16-bit result a byte at a time. One shared multiplier and one shared adder do the work
in exactly 8 enabled clock cycles, in this fixed order, with every operation rounded to GF16:

`p_k = MUL(A_k, B_k)`, then `acc = p_0`, `acc = ADD(acc, p_1)`, `acc = ADD(acc, p_2)`, `r = ADD(acc, p_3)`.

There is no fused multiply-add and no tree order.

**Arithmetic.** The exact product or sum is rounded into a 10-bit significand (9 stored bits) in an
unbounded exponent range, with carry into the next binade, and only then the range rules apply:
biased exponent 63 or more gives signed infinity; below 0, or exactly `E=0, M=0`, gives `+0`.
Multiply rounds to nearest and a tie goes **toward zero**. Add rounds to nearest and a tie goes to
the **even** mantissa (exact round-to-nearest-even). Every arithmetic result that is zero is `+0`.
Infinity times zero, infinity plus minus infinity and any NaN operand give `0xFE01`.

The contract is written in the project's own language in `specs/numeric/gf16_dot4_sky26d.t27`
and is the source of truth for everything below.

## Pins

`uio` is **input only** (`uio_oe = 0x00`, `uio_out = 0x00` in every state).

| Pin | Direction | Meaning |
|---|---|---|
| `ui[7:0]` | in | data byte for a write; in read select 5, `ui[3:0]` is the cell address |
| `uio[0]` WR | in | rising edge writes `ui[7:0]` into the cell at PTR, then PTR = PTR + 1 (mod 16) |
| `uio[1]` GO | in | rising edge starts the dot product and resets PTR to 0 |
| `uio[4:2]` RSEL | in | read select, see below |
| `uio[7:5]` | in | reserved, ignored (drive 0) |
| `uo[7:0]` | out | byte chosen by RSEL (combinational, no clock needed) |
| `rst_n` | in | asynchronous, active low; clears everything |
| `ena` | in | 0 freezes all state, including the memory of the previous WR and GO levels |

A strobe acts on its **rising edge**: high now and low at the previous enabled clock. After reset the
previous level is low.

**Memory.** 16 byte cells, little endian words, cleared by reset. PTR 0..7 is A0.lo, A0.hi, A1.lo,
A1.hi, A2.lo, A2.hi, A3.lo, A3.hi; PTR 8..15 is B0.lo ... B3.hi. PTR wraps from 15 to 0. There is
no "loaded" flag: a partial load computes over the stored cells (zero for cells never written since reset).

**Read select (`uio[4:2]`).**

| RSEL | `uo[7:0]` |
|---|---|
| 0 | STATUS `{PTR[3:0], 0, ERR, DONE, BUSY}` |
| 1 | result low byte (`0x00` while BUSY) |
| 2 | result high byte (`0x00` while BUSY) |
| 3 | `0xC0` - signature low byte |
| 4 | `0x47` - signature high byte |
| 5 | raw byte of cell `ui[3:0]` (readback; `ui[7:4]` ignored) |
| 6, 7 | `0x00` |

The signature `0x47C0` is a constant of this interface. It is **not** a computed result and it is
not shown on the pins after reset. (Earlier revisions drove `0x47C0` on the output pins after reset;
that behaviour is gone because `uio` is now input only.)

**Rules.** WR and GO rising in the same idle clock: the write is accepted and GO is ignored, without
an error. While BUSY, WR and GO edges are ignored and set the sticky ERR flag (cleared by an accepted
GO and by reset). An accepted WR clears DONE but leaves the result register, so after one new byte the
result bytes still show the OLD result: use them only when DONE = 1. The result register is `0x0000`
after reset. DONE is set after exactly 8 enabled clocks following the clock that accepted GO.

## How to test

Reset (`rst_n` low, then high), then:

Strobes are sampled on the clock edge, so each strobe must be held high across one enabled clock edge
and low across at least one enabled clock edge before the next rising edge. Changing a strobe only
between clock edges (a half-cycle pulse) is not a reliable way to drive WR or GO: hold it, and
keep it low for at least one ENABLED clock between two rising edges. Clocks with `ena = 0` do not count,
because they do not update the remembered previous level.

1. For each of the 16 bytes: put the byte on `ui`, hold `uio[0]` high for one enabled clock, then hold it
   low for at least one enabled clock before the next byte.
   Order: A0.lo, A0.hi, A1.lo, ... A3.hi, B0.lo, ... B3.hi.
2. Hold `uio[1]` (GO) high for one enabled clock, then low for at least one enabled clock (and keep it low
   while BUSY, or the extra edge sets ERR). STATUS reads `0x01` (BUSY) for 8 clocks.
3. Poll `RSEL = 0` until STATUS is `0x02` (DONE).
4. Read `RSEL = 1` (low byte) and `RSEL = 2` (high byte).

Self-test: A = B = (1.0, 2.0, 3.0, 4.0) = `0x3E00, 0x4000, 0x4100, 0x4200` gives 30.0 = `0x47C0`.
With B = (1.0, 1.0, 1.0, 1.0) the result is 10.0 = `0x4480`.

The same pin-level cocotb test set (`test/test.py`) is run on the RTL and on the gate-level netlist,
against an independent exact rational reference model. The source list, the Yosys audit, the
isolated multiplier and adder sweeps and the negative controls are described in `docs/DOT4-REPRODUCE.md`.

## External hardware

None.

## Status and limits

- Fit in one 1x1 tile and the 50 MHz clock are **unknown** until the GDS run of the final commit.
- No performance, energy or area claim is made.
- Archived blocks of earlier revisions (formats, quantizers, ROMs, mesh, power modules) remain in
  `src/` and `docs/` as history only. They are not part of this design.

Original project by Dmitrii Vasilev; DOT4 rewrite by Dmitrii Fedorov. Apache-2.0.
