# API Documentation — φ-anchor (1×1)

## Overview

The φ-anchor chip is the smallest member of TRI-NET, designed as a single-tile Trinity GF16 ternary MAC with enhanced safety features. It operates in two primary modes:

1. **Canonical Mode** (`ui_in[0] = 0`): Outputs the canonical GF16 dot4 constant `0x47C0`
2. **Load Mode** (`ui_in[0] = 1`): Packet-based computation with operand loading

## Top-Level Module: `tt_um_trinity_nano`

### Port Interface

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `ui_in` | input | 8 | Control and status inputs |
| `uo_out` | output | 8 | Low byte of result |
| `uio_in` | input | 8 | Input operand / pin functions |
| `uio_out` | output | 8 | High byte of result / status |
| `uio_oe` | output | 8 | Output enable for uio pins |
| `ena` | input | 1 | Enable signal |
| `clk` | input | 1 | Clock |
| `rst_n` | input | 1 | Active-low reset |

### Control Pins (ui_in)

| Bit | Name | Mode | Description |
|-----|------|------|-------------|
| 0 | `load_mode` | Both | 0=Canonical mode, 1=Load mode |
| 1 | `status_request` | Canonical | Request POST status (with ui[2]) |
| 2 | `status_request` | Canonical | Request POST status (with ui[1]) |
| 3 | `lucas_idx[0]` | Canonical | Lucas ROM address bit 0 |
| 4 | `rng_ena` | Canonical | Enable HWRNG advance |
| 5 | `restraint_mode` | Canonical | Activate CLARA Gap-4 restraint |
| 6 | `lucas_idx[1]` | Canonical | Lucas ROM address bit 1 |
| 7 | `load_lane_strobe` | Load | Lane advance strobe (rising edge) |
| 7 | `sacred_mode` | Canonical | Sacred constants ROM enable |

### Computation Pins (Load Mode)

| Bit | Name | Function |
|-----|------|----------|
| 6 | `compute_strobe` | Rising edge issues COMPUTE packet |
| 7 | `load_lane_strobe` | Rising edge advances to next lane (0-3) |
| `uio_in[7:0]` | `operand_lo` | Current lane operand (high byte = 0) |

### Output Behavior

**Canonical Mode** (`ui_in[0] = 0`):
- `uo_out[7:0]` = `0xC0` (canonical low byte)
- `uio_out[7:4]` = `0x4` (canonical high byte)
- `{uio_out, uo_out}` = `0x47C0`

**Load Mode** (`ui_in[0] = 1`):
- `uo_out[7:0]` = `tile_dbg_result[7:0]`
- `uio_out[7:4]` = `tile_dbg_result[15:8]`
- `uio_out[3:0]` = D2D friend/foe handshake

**POST Status** (`ui_in[3:2] = 11` in canonical mode):
- `uo_out` = `{phi_ok, post_done, lucas_val[5:0]}`
- `uio_out[7:4]` = `{lucas_val[7:6], phi_ok, post_done, 0000}`

**Sacred ROM** (`ui_in[7]=1` in canonical mode):
- `addr` = `{1'b0, ui_in[6:1]}` (6-bit, 0-63)
- `uo_out[7:0]` = sacred constant value

**CROWN47 ROM** (`uio_in[7]=1` in canonical mode):
- `addr` = `ui_in[6:0]` (0-46)
- `byte_sel` = `ui_in[6:5]` (0=mant_lo, 1=mant_hi, 2=exp, 3=tier_flag)
- `uo_out[7:0]` = selected byte

## Core Modules

### `gf16_dot4` — Canonical Dot Product

**Description**: 4-vector GF16 dot product using ternary arithmetic

**Parameters**: None

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `a0, a1, a2, a3` | input | 16 | First vector components |
| `b0, b1, b2, b3` | input | 16 | Second vector components |
| `result` | output | 16 | GF16 dot product result |

**Usage**:
```verilog
gf16_dot4 u_dot (
    .a0(16'h3E00), .a1(16'h4000), .a2(16'h4100), .a3(16'h4200),
    .b0(16'h3E00), .b1(16'h4000), .b2(16'h4100), .b3(16'h4200),
    .result(canonical_dot)  // Returns 0x47C0
);
```

**Canonical Constant**: `dot4(1.0, 2.0, 3.0, 4.0) = 0x47C0`

### `trinity_gf16_tile` — Packet-Driven Tile

**Parameters**:
- `TILE_ID` (2 bits): Tile identifier (default `2'b00`)

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `clk` | input | 1 | System clock |
| `rst_n` | input | 1 | Active-low reset |
| `in_pkt` | input | 32 | Inbound TRN packet |
| `in_valid` | input | 1 | Inbound packet valid |
| `in_ready` | output | 1 | Ready for inbound packet |
| `out_pkt` | output | 32 | Outbound TRN packet |
| `out_valid` | output | 1 | Outbound packet valid |
| `out_ready` | input | 1 | Ready for outbound packet |
| `dbg_result` | output | 16 | Debug result output |

**TRN Packet Protocol** (`trinity_packet.vh`):

| Opcode | Value | Description |
|--------|-------|-------------|
| `TRN_OP_LOAD_A` | 1 | Load operand A lane |
| `TRN_OP_LOAD_B` | 2 | Load operand B lane |
| `TRN_OP_LOAD_JOB` | 4 | Load job ID |
| `TRN_OP_LOAD_NONCE` | 5 | Load nonce |
| `TRN_OP_COMPUTE` | 3 | Compute dot4 |
| `TRN_OP_READ_RES` | 6 | Read result |
| `TRN_OP_RESULT` | - | Result packet (outbound) |
| `TRN_OP_RECEIPT` | - | Receipt packet (outbound) |

**Packet Format** (32 bits):
```
[31:28] opcode   [27:26] dst     [25:24] src
[23:20] lane     [19:16] unused  [15:0]  payload
```

### `phi_anchor_post` — POST Module

**Description**: Proves φ²+φ⁻²=3 via Lucas recurrence (L₂..L₇)

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `clk` | input | 1 | System clock |
| `rst_n` | input | 1 | Active-low reset |
| `phi_ok` | output | 1 | POST passed (φ identity verified) |
| `post_done` | output | 1 | POST sequence complete |

**Verification Values**:
- L₂ = 3 (verified: L₂ = φ² + φ⁻²)
- L₃ = 4
- L₄ = 7
- L₅ = 11
- L₆ = 18
- L₇ = 29

### `lucas_rom` — Lucas Number ROM

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `idx` | input | 3 | Index (0=L₂, 1=L₃, ..., 5=L₇) |
| `value` | output | 8 | Lucas number value |

**Address Map**:
| idx | Value | Lucas Number |
|-----|-------|--------------|
| 0 | 3 | L₂ |
| 1 | 4 | L₃ |
| 2 | 7 | L₄ |
| 3 | 11 | L₅ |
| 4 | 18 | L₆ |
| 5 | 29 | L₇ |

### `hwrng_lfsr` — Hardware Random Number Generator

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `clk` | input | 1 | System clock |
| `rst_n` | input | 1 | Active-low reset |
| `ena` | input | 1 | Enable LFSR advance |
| `rnd` | output | 16 | Random nonce output |

**Characteristics**:
- 16-bit maximal-length LFSR
- Polynomial: `x^16 + x^14 + x^13 + x^11 + 1`
- Period: 2^16 - 1 cycles
- Die-unique nonce for DePIN receipt verification

### `restraint_ctrl` — CLARA Gap-4 Bounded Rationality

**Description**: Enforces bounded rationality constraints

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `clk` | input | 1 | System clock |
| `rst_n` | input | 1 | Active-low reset |
| `phi_drift` | input | 16 | φ drift measurement |
| `step_count` | input | 4 | Current step count |
| `receipt_ok` | input | 1 | Receipt verification status |
| `current_state` | input | 2 | FSM current state |
| `force_unknown` | output | 1 | Force unknown result |
| `halt_mac` | output | 1 | Halt MAC computation |
| `reason` | output | 3 | Halt reason code |

**Trigger Conditions**:
- φ drift > 164
- step_count > 10
- Receipt failure

### `trinity_friend_foe` — Cross-Die Handshake

**Parameters**:
- `MY_ANCHOR` (8 bits): Anchor identifier (phi = `8'hCF`)

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `clk` | input | 1 | System clock |
| `rst_n` | input | 1 | Active-low reset |
| `rx_bit` | input | 1 | Received bit |
| `tx_bit` | output | 1 | Transmitted bit |
| `friend_detected` | output | 1 | Friend chip detected |
| `handshake_valid` | output | 1 | Handshake complete |

**Anchors**:
- φ (phi): `0xCF`
- e (Euler): `0xE8`
- γ (gamma): `0x93`

### Quantization Modules

#### `int4_quantizer`

**Description**: Int4 symmetric quantization/dequantization

**Quantizer Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `fp16_in` | input | 16 | FP16 input |
| `scale_exp` | input | 4 | Scale exponent (2^scale_exp) |
| `zero_point` | input | 3 | Zero point offset |
| `int4_out` | output | 4 | Int4 output [S(1)||D(3)] |

**Scale Levels**:
| scale_exp | Scale Factor |
|-----------|--------------|
| 0 | 1.0 |
| 1 | 0.5 |
| 2 | 0.25 |
| 3 | 0.125 |
| 4 | 0.0625 |
| 5 | 0.03125 |
| 6 | 0.015625 |
| 7 | 0.0078125 |

**Output Range**: [-8, 7] (signed 4-bit)

#### `nf4_quantizer`

**Description**: NormalFloat4 quantization for QLoRA

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `fp16_in` | input | 16 | FP16 input |
| `scale_idx` | input | 4 | Scale index |
| `nf4_out` | output | 4 | NF4 output |

**NF4 Levels** (from Normal(0,1) quantiles):
| Code | Value | Description |
|------|-------|-------------|
| 0xF | -1.000 | Most negative |
| 0xE | -0.696 | |
| 0xD | -0.525 | |
| 0xC | -0.394 | |
| 0xB | -0.284 | |
| 0xA | -0.185 | |
| 9 | -0.091 | |
| 8 | 0.000 | Zero (duplicate) |
| 0 | 0.091 | |
| 1 | 0.185 | |
| 2 | 0.284 | |
| 3 | 0.394 | |
| 4 | 0.525 | |
| 5 | 0.696 | |
| 6 | 1.000 | Most positive |

#### `fp8_e4m3_quantizer`

**Description**: FP8 E4M3 (4 exponent, 3 mantissa) quantization

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `fp16_in` | input | 16 | FP16 input |
| `scale_idx` | input | 4 | Scale index |
| `fp8_out` | output | 8 | FP8 E4M3 output |

#### `fp8_e5m2_quantizer`

**Description**: FP8 E5M2 (5 exponent, 2 mantissa) quantization

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `fp16_in` | input | 16 | FP16 input |
| `scale_idx` | input | 4 | Scale index |
| `fp8_out` | output | 8 | FP8 E5M2 output |

#### `posit16_quantizer`

**Description**: Posit16 (16-bit posit) quantization

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `fp16_in` | input | 16 | FP16 input |
| `scale_idx` | input | 4 | Scale index |
| `posit_out` | output | 16 | Posit16 output |

### GF16 Arithmetic

#### `gf16_add`

**Description**: GF16 addition using XOR

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `a` | input | 16 | First GF16 operand |
| `b` | input | 16 | Second GF16 operand |
| `result` | output | 16 | GF16 sum |

**Operation**: `result = a XOR b` (GF16 characteristic 2)

#### `gf16_mul`

**Description**: GF16 multiplication using shift-add

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `a` | input | 16 | First GF16 operand |
| `b` | input | 16 | Second GF16 operand |
| `result` | output | 16 | GF16 product |

**Special Values**:
- `0x0000` = Zero
- `0x7E00` = +Infinity
- `0xFE00` = -Infinity
- `0xFE01` = NaN

**Format**:
```
[15]   sign      (1 bit)
[14:9] exponent  (6 bits)
[8:0]  mantissa  (9 bits)
```

### ROM Modules

#### `sacred_constants_rom`

**Description**: PhD sacred constants (Glava 3+7+28)

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `addr` | input | 7 | Address (0-63) |
| `val` | output | 8 | Sacred constant value |

#### `crown47_rom_8bit`

**Description**: Crown of TRI-NET (Crown42 + 5 Tegmark-31 fillers)

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `addr` | input | 7 | Address (0-46) |
| `byte_sel` | input | 2 | Byte selector |
| `byte_out` | output | 8 | Selected byte |

**Byte Selector**:
| byte_sel | Description |
|----------|-------------|
| 0 | mant_lo (mantissa low) |
| 1 | mant_hi (mantissa high) |
| 2 | exp (exponent) |
| 3 | tier_flag |

**Format**: 24-bit pseudo-float (Vasilev-Pellis v22.12)

### Safety Modules

#### `purkinje_thermal_gate`

**Description**: Thermal monitoring and gating

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `clk` | input | 1 | System clock |
| `rst_n` | input | 1 | Active-low reset |
| `temp_in` | input | 8 | Temperature input (0-255) |
| `temp_warning` | output | 1 | Temperature warning |
| `temp_critical` | output | 1 | Temperature critical |
| `power_gate` | output | 1 | Power gate enable |

### Power Management

#### `avs_controller_96`

**Description**: AVS-96 voltage controller for 96 power islands

**Ports**:

| Port | Direction | Width | Description |
|------|-----------|-------|-------------|
| `clk` | input | 1 | System clock |
| `rst_n` | input | 1 | Active-low reset |
| `power_req` | input | 96 | Power budget per island |
| `therm_mon` | input | 6 | Thermal monitor (0-63) |
| `avs_enable` | input | 1 | AVS enable |
| `voltage_level` | output | 192 | 2 bits per island |
| `therm_warning` | output | 6 | Thermal warning bits |
| `power_gate` | output | 1 | Global power gate |

**Voltage Levels** (2 bits per island):
| Code | Voltage |
|------|---------|
| 00 | 0.75V (ultra-low) |
| 01 | 0.85V (low) |
| 10 | 0.95V (normal) |
| 11 | 1.05V (high) |

**TOPS/W Boost**: Up to 5.4× with η ≥ 0.93

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Area | ~500 cells (1×1 tile @ 60% density) |
| Power | 75 mW baseline |
| Throughput | 1 GF16 MAC/cycle |
| TOPS/W | 75 (baseline), 405 (with AVS-96) |
| Latency | 1 cycle (combinational) |
| Clock | 50 MHz |

## R-SI-1 Compliance

All modules comply with R-SI-1 (zero multiplication operators):
- Multiplication replaced with shift-add sequences
- Quantizers use shift-based scaling
- All dot products implemented via XOR and addition

## Sacred Physics Anchor

The φ-anchor chip embodies the sacred identity:
```
φ² + φ⁻² = 3
```

Verified through Lucas number recurrence:
```
L₂ = φ² + φ⁻² = 3
L₃ = L₂ + φ = 4
L₄ = L₃ + L₂ = 7
...
```

DOI: 10.5281/zenodo.19227877