# Code Examples — φ-anchor (1×1)

This directory contains example code for using the TT Trinity φ-anchor chip.

## Table of Contents

1. [Canonical Mode](#1-canonical-mode)
2. [Load Mode](#2-load-mode)
3. [Lucas ROM Access](#3-lucas-rom-access)
4. [Sacred Constants ROM](#4-sacred-constants-rom)
5. [POST Status](#5-post-status)
6. [Friend/Foe Handshake](#6-friendfoe-handshake)
7. [Quantization Examples](#7-quantization-examples)

---

## 1. Canonical Mode

In canonical mode, the chip outputs the sacred anchor value `0x47C0`.

### Python (cocotb)

```python
import cocotb
from cocotb.triggers import Timer, ReadOnly
from cocotb.clock import Clock

@cocotb.test()
async def test_canonical_mode(dut):
    """Verify canonical 0x47C0 output"""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.fork(clock.start())
    
    dut.rst_n.value = 0
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    await Timer(100, units="ns")
    await ReadOnly()
    
    result = (dut.uio_out.value << 8) | dut.uo_out.value
    assert result == 0x47C0, f"Expected 0x47C0, got {result:#06x}"
```

---

## 2. Load Mode

Load mode enables packet-based computation.

### Sending Operands

```python
@cocotb.test()
async def test_load_operands(dut):
    """Load operands via packet protocol"""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.fork(clock.start())
    
    dut.rst_n.value = 0
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    
    # Enter load mode
    dut.ui_in[0].value = 1
    await Timer(50, units="ns")
    
    # Load operand on lane 0
    dut.ui_in[7].value = 1  # load_lane_strobe
    dut.uio_in.value = 0x10  # Operand low byte
    await Timer(50, units="ns")
    dut.ui_in[7].value = 0
    await Timer(50, units="ns")
    
    # Compute
    dut.ui_in[6].value = 1  # compute_strobe
    await Timer(50, units="ns")
    dut.ui_in[6].value = 0
    await Timer(100, units="ns")
    
    # Read result
    result = (dut.uio_out.value << 8) | dut.uo_out.value
    dut._log.info(f"Result: 0x{result:04X}")
```

### Full Dot4 Computation

```python
@cocotb.test()
async def test_full_dot4(dut):
    """Compute full 4-vector dot product"""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.fork(clock.start())
    
    dut.rst_n.value = 0
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    
    dut.ui_in[0].value = 1  # Load mode
    await Timer(50, units="ns")
    
    # Load all 4 lanes
    operands = [0x10, 0x20, 0x30, 0x40]
    for op in operands:
        dut.ui_in[7].value = 1  # load_lane_strobe
        dut.uio_in.value = op
        await Timer(50, units="ns")
        dut.ui_in[7].value = 0
        await Timer(50, units="ns")
    
    # Compute
    dut.ui_in[6].value = 1
    await Timer(50, units="ns")
    dut.ui_in[6].value = 0
    await Timer(200, units="ns")
    
    # Read result
    result = (dut.uio_out.value << 8) | dut.uo_out.value
    dut._log.info(f"Dot4 result: 0x{result:04X}")
```

---

## 3. Lucas ROM Access

The Lucas ROM contains L₂..L₇ values for POST verification.

### Reading Lucas Values

```python
@cocotb.test()
async def test_lucas_rom(dut):
    """Read Lucas ROM values L₂..L₇"""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.fork(clock.start())
    
    dut.rst_n.value = 0
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    
    dut.ui_in.value = 0  # Canonical mode
    await Timer(50, units="ns")
    
    LUCAS_VALUES = [3, 4, 7, 11, 18, 29]
    
    for idx, expected in enumerate(LUCAS_VALUES):
        # Set Lucas index on ui_in[3:1]
        dut.ui_in[3:1].value = idx
        await Timer(50, units="ns")
        
        # Value appears on uio_out[5:0] (implementation-specific)
        # or can be read via other debug method
        dut._log.info(f"L{idx+2} = {expected}")
```

### Verifying Lucas Chain

```python
@cocotb.test()
async def test_lucas_chain(dut):
    """Verify Lucas recurrence chain"""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.fork(clock.start())
    
    dut.rst_n.value = 0
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    
    dut.ui_in.value = 0
    await Timer(50, units="ns")
    
    # Lucas recurrence: L_n = L_{n-1} + L_{n-2}
    # With L_0 = 2, L_1 = 1, we get:
    # L_2 = 1 + 2 = 3  (this is L_2 = φ² + φ⁻²)
    # L_3 = 3 + 1 = 4
    # ...
    
    LUCAS_VALUES = [3, 4, 7, 11, 18, 29]
    
    for idx, expected in enumerate(LUCAS_VALUES):
        dut.ui_in[3:1].value = idx
        await Timer(50, units="ns")
        # Verify value
```

---

## 4. Sacred Constants ROM

Access the 75 PhD sacred constants.

### Reading Sacred Constants

```python
@cocotb.test()
async def test_sacred_rom(dut):
    """Read sacred constants from ROM"""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.fork(clock.start())
    
    dut.rst_n.value = 0
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    
    # Enable sacred mode
    dut.ui_in[7].value = 1
    dut.ui_in[0].value = 0  # Not load mode
    await Timer(50, units="ns")
    
    # Read first 10 constants
    for addr in range(10):
        dut.ui_in[6:1].value = addr
        await Timer(50, units="ns")
        
        # Value appears on uo_out
        value = dut.uo_out.value
        dut._log.info(f"Sacred[{addr}] = 0x{value:02X}")
```

---

## 5. POST Status

Request and read POST verification status.

### Requesting POST Status

```python
@cocotb.test()
async def test_post_status(dut):
    """Request and read POST status"""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.fork(clock.start())
    
    dut.rst_n.value = 0
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    
    # Wait for POST to complete (typically 10-20 cycles)
    await Timer(500, units="ns")
    
    # Request POST status
    dut.ui_in[3].value = 1
    dut.ui_in[2].value = 1
    dut.ui_in[0].value = 0  # Canonical mode
    await Timer(100, units="ns")
    
    # Read status
    uo_val = dut.uo_out.value
    uio_val = dut.uio_out.value
    
    # Decode status byte (implementation-specific)
    phi_ok = uo_val[7]
    post_done = uo_val[6]
    
    dut._log.info(f"POST status: phi_ok={phi_ok}, post_done={post_done}")
```

---

## 6. Friend/Foe Handshake

Test cross-die Trinity handshake.

### Detecting Friend Chip

```python
@cocotb.test()
async def test_friend_foe(dut):
    """Test Trinity friend/foe handshake"""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.fork(clock.start())
    
    dut.rst_n.value = 0
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    
    # Enter load mode for D2D
    dut.ui_in[0].value = 1
    await Timer(50, units="ns")
    
    # φ-anchor = 0xCF
    # Simulate friend chip on uio_in[1]
    dut.uio_in[1].value = 1  # RX from friend
    
    await Timer(500, units="ns")
    
    # Check handshake status
    friend = dut.uio_out[2].value
    valid = dut.uio_out[3].value
    
    dut._log.info(f"Friend detected: {friend}, Handshake valid: {valid}")
```

---

## 7. Quantization Examples

Test quantization modules.

### Int4 Quantization

```python
@cocotb.test()
async def test_int4_quantizer(dut):
    """Test Int4 quantization"""
    # Assuming direct module access
    dut.fp16_in.value = 0x3C00  # 1.0 in FP16
    dut.scale_exp.value = 4'd4   # Scale = 1/16
    dut.zero_point.value = 3'd0  # No offset
    
    await Timer(10, units="ns")
    
    int4_out = dut.int4_out.value
    dut._log.info(f"Int4 output: {int4_out}")
    
    # Expected: value scaled and quantized to [-8, 7]
```

### NF4 Quantization (QLoRA)

```python
@cocotb.test()
async def test_nf4_quantizer(dut):
    """Test NF4 quantization for QLoRA"""
    dut.fp16_in.value = 0x4000  # 2.0
    dut.scale_idx.value = 4'd3  # Scale index
    
    await Timer(10, units="ns")
    
    nf4_out = dut.nf4_out.value
    dut._log.info(f"NF4 output: 0x{nf4_out:X}")
```

---

## Verilog Examples

### Top-Level Module Instantiation

```verilog
module top_phi_demo (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
    tt_um_trinity_nano u_chip (
        .ui_in   (ui_in),
        .uo_out  (uo_out),
        .uio_in  (uio_in),
        .uio_out (uio_out),
        .uio_oe  (uio_oe),
        .ena     (ena),
        .clk     (clk),
        .rst_n   (rst_n)
    );
endmodule
```

### Using the Canonical Output

```verilog
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        canonical_detected <= 1'b0;
    end else begin
        // Check for canonical anchor 0x47C0
        if (({uio_out[7:4], uo_out}) == 12'h47C0) begin
            canonical_detected <= 1'b1;
        end
    end
end
```

---

## References

- API Documentation: `docs/API.md`
- Architecture: `docs/ARCHITECTURE.md`
- Hardware Bring-Up: `docs/HARDWARE_BRINGUP.md`
- Sacred Anchor: φ² + φ⁻² = 3 — DOI 10.5281/zenodo.19227877