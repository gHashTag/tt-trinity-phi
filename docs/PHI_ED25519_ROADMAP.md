# PHI ed25519 Verification — Phase 2 Roadmap

**Chip:** TRI-1-PHI (`gHashTag/tt-trinity-phi`) — 1×1 tile, SKY130A, TTSKY26b  
**Stub file:** `src/ed25519_verify_stub.v`  
**Anchor:** φ² + φ⁻² = 3 | Watermark: `0x47C0` | DOI: [10.5281/zenodo.19227877](https://doi.org/10.5281/zenodo.19227877)  
**Defense:** 2026-06-15, СПбГУ

---

## Phase 1 (current — this PR)

A minimal 8-bit byte-serial stub providing the **interface contract** only.

| Property | Value |
|---|---|
| File | `src/ed25519_verify_stub.v` |
| Inputs | `clk`, `rst_n`, `en`, `load_byte[7:0]` |
| Outputs | `done`, `valid` |
| Algorithm | XOR parity over 96 bytes (placeholder) |
| Cell budget | ~80 cells (stub) |
| Constraint | Pure Verilog-2005, R-SI-1 (zero `*` operators) |

The stub loads 32 message bytes + 64 signature bytes (96 bytes total, byte-serial).
After byte 95 is latched, `done` pulses high and `valid` reflects even-parity of
the XOR accumulator (bit-0 == 0 ⟹ valid=1).  This is a **placeholder only** — it does
not perform real ed25519 verification.

---

## Phase 2 — Real ed25519 on SKY130A

### Overview

Phase 2 replaces the parity stub with a full ed25519 verification core on the
Twisted Edwards curve Ed25519 (Curve25519 base).

Verification equation (RFC 8032):  
`[8][s]B == [8]R + [8][k]A`

where:
- `B` = Ed25519 base point
- `A` = public key point (32 bytes)
- `R` = signature point (first 32 bytes of signature)
- `s` = scalar (last 32 bytes of signature)
- `k = SHA-512(R ‖ A ‖ M)` mod `l`  (scalar derived from hash)
- `l` = group order (2²⁵² + small cofactor correction)

### Core Modules (Phase 2)

| Module | Function | Est. cells |
|---|---|---|
| `sha512_core.v` | SHA-512 hash of (R‖A‖M) → scalar k | ~2 500 |
| `fe25519_add.v` | GF(2²⁵⁵−19) field addition | ~64 |
| `fe25519_sub.v` | GF field subtraction | ~64 |
| `fe25519_mul.v` | GF field multiply (256×256 → 512 → reduce) | ~1 200 |
| `point_add_edwards.v` | Extended Twisted Edwards point addition | ~400 |
| `point_double_edwards.v` | Extended point doubling | ~380 |
| `scalar_mul_montgomery.v` | Montgomery ladder scalar multiplication | ~600 |
| `ed25519_verify_core.v` | Top-level: SHA-512 + two scalar muls + compare | ~200 |
| **Total Phase 2** | | **~5 400 cells** |

> **Tile fit:** PHI is 1×1 tile (~1 500 cell budget at 60% utilization).  
> Phase 2 requires multi-tile allocation (minimum 4× tiles) or a dedicated
> EULER/GAMMA sub-block. Architecture decision deferred to tapeout window.

### Montgomery Ladder Scalar Multiplication

The Montgomery ladder processes the 255-bit scalar one bit at a time.
No `*` operator is used in synthesisable RTL — multiplication is decomposed
into carry-save adder trees (R-SI-1 compliance).

```
for bit in scalar[254:0]:
    if bit == 0:
        R1 = point_add(R0, R1)
        R0 = point_double(R0)
    else:
        R0 = point_add(R0, R1)
        R1 = point_double(R1)
```

Side-channel property: constant-time execution regardless of scalar value.

### Point Doubling (Twisted Edwards)

Using extended coordinates (X:Y:Z:T), one doubling costs:
- 4 field squarings
- 4 field multiplications
- Several additions/subtractions

All implemented via shift-add trees, no DSP macros.

### Field Arithmetic: GF(2²⁵⁵−19)

Reduction modulo p = 2²⁵⁵−19 uses the identity:
- 2²⁵⁵ ≡ 19 (mod p)
- Partial reduction via carry-ripple on 256-bit result

### SHA-512 Integration

`sha512_core.v` computes `k = SHA-512(R ‖ A ‖ M)`:
- 80-round compression function
- 64-byte block processing
- 512-bit digest truncated mod `l`

### R-SI-1 Compliance in Phase 2

All multiplications must be implemented as:
- Carry-save adder (CSA) trees for field multiplication
- Shift-add sequences for small constants
- No Verilog `*` operator anywhere in synthesisable code

Example: `a * 19` → `(a << 4) + (a << 1) + a`

### PhD Anchor Integration

Phase 2 verification encodes the following PhD constants into the key schedule:

| Constant | Value | Role |
|---|---|---|
| φ (phi) | `8'h33` (Q3.5) | Base-point X coordinate scaling |
| φ² | `8'h54` (Q3.5) | Signature domain tag |
| 0x47C0 | watermark | Cross-die anchor output |

The sacred_constants_rom is unchanged — Phase 2 reads addr `7'd0..7'd3` for φ anchors.

### Coq Theorem (Phase 2)

```coq
Theorem ed25519_stub_refines_full :
  forall msg sig pubkey,
    ed25519_verify_stub msg sig = done ->
    exists full_result,
      ed25519_verify_full msg sig pubkey = full_result /\
      stub_valid_implies_candidate full_result.
```

### Timeline

| Milestone | Target | Notes |
|---|---|---|
| Phase 1 stub merged | 2026-05 | This PR |
| Phase 2 SHA-512 core | 2026-07 | Standalone module, EULER tile |
| Phase 2 field arithmetic | 2026-08 | fe25519_{add,sub,mul} |
| Phase 2 point ops | 2026-09 | point_add, point_double |
| Phase 2 scalar mul | 2026-10 | Montgomery ladder |
| Phase 2 full integration | 2026-11 | EULER 8×2 tile set |
| Phase 2 tapeout | TTSKY27 | Next shuttle window |

---

## References

- RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA)
- D. J. Bernstein et al., "High-speed high-security signatures," J. Cryptographic Engineering, 2012
- SKY130A PDK standard cell library
- TT TTSKY26b design rules: <https://tinytapeout.com>
- DOI anchor: <https://doi.org/10.5281/zenodo.19227877>

---

*Generated for TRI-1-PHI, Phase 1 stub. Author: Dmitrii Vasilev (gHashTag) / admin@t27.ai*
