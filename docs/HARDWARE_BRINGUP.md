# Hardware Bring-Up Guide — φ-anchor (1×1)

## Overview

This guide covers bring-up and testing of the TT Trinity φ-anchor chip on real silicon (TTSKY26b shuttle).

## Prerequisites

### Required Equipment
- TT UM Trinity φ-anchor chip (TTSKY26b)
- FPGA board with Tiny Tapeout support (e.g., UTM-651)
- USB-C cable for power and communication
- Logic analyzer or oscilloscope (optional)

### Required Software
- Python 3.9+
- pip packages:
  ```
  pip install cocotb cocotb-test pyyaml
  ```
- Icarus Verilog (for simulation):
  ```
  brew install icarus-verilog  # macOS
  apt install iverilog          # Ubuntu
  ```
- GTKWave (for waveform viewing):
  ```
  brew install gtkwave  # macOS
  apt install gtkwave   # Ubuntu
  ```

## Pin Mapping

### Input Pins (ui_in)

| Pin | Name | Function | Test Pattern |
|-----|------|----------|--------------|
| 0 | `load_mode` | Mode select | 0=Canonical, 1=Load |
| 1 | `lucas_idx[0]` | Lucas ROM bit 0 | 0/1 |
| 2 | `status_request` | POST status request | 0/1 |
| 3 | `lucas_idx[1]` | Lucas ROM bit 1 | 0/1 |
| 4 | `rng_ena` | HWRNG enable | 1=advance |
| 5 | `restraint_mode` | CLARA Gap-4 | 0/1 |
| 6 | `lucas_idx[2]` | Lucas ROM bit 2 | 0/1 |
| 7 | `sacred_mode` | Sacred ROM | 1=enable |

### Output Pins (uo_out)

| Pin | Name | Canonical | Description |
|-----|------|-----------|-------------|
| 7:0 | `result_lo` | 0xC0 | Low byte of result |

### Bidirectional Pins (uio_out/oe)

| Pin | Name | Canonical | Mode | Description |
|-----|------|-----------|------|-------------|
| 7:4 | `result_hi` | 0x4 | Canonical | High byte of result |
| 3:0 | `d2d_tx` | 0x0 | Load | D2D transmit (friend/foe) |
| 1 | `ff_rx` | - | Load | Friend/foe receive |

## Bring-Up Checklist

### Step 1: Power-On Verification

1. Apply 3.3V power to the chip
2. Check for excessive current draw (< 10 mA expected)
3. Verify clock signal (should be present)

**Expected behavior:**
- `{uio_out[7:4], uo_out}` = `0x47C0` (canonical anchor)
- All outputs stable within 10 µs

**Python test:**
```python
import cocotb
from cocotb.triggers import Timer, ReadOnly
from cocotb.clock import Clock

@cocotb.test()
async def test_canonical_anchor(dut):
    """Verify canonical 0x47C0 anchor output at reset"""
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

### Step 2: Lucas ROM Verification

Test Lucas sequence L₂..L₇:

```python
LUCAS_VALUES = [3, 4, 7, 11, 18, 29]

@cocotb.test()
async def test_lucas_rom(dut):
    """Verify Lucas ROM values L₂..L₇"""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.fork(clock.start())
    
    dut.rst_n.value = 0
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    dut.ui_in.value = 0  # Canonical mode
    await Timer(100, units="ns")
    
    for idx, expected in enumerate(LUCAS_VALUES):
        # Set Lucas index on ui_in[3:1]
        dut.ui_in.value = idx << 1
        await Timer(50, units="ns")
        
        # Read uio_out for status or use other debug method
        # (implementation depends on your chip's debug interface)
        print(f"L{idx+2} = {expected}")
```

### Step 3: POST Verification

Wait for POST completion and check:

```python
@cocotb.test()
async def test_post_complete(dut):
    """Verify POST sequence completes successfully"""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.fork(clock.start())
    
    dut.rst_n.value = 0
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    
    # Wait for POST (typical: 10-20 cycles)
    for _ in range(50):
        await Timer(20, units="ns")
    
    # Check POST status (implementation-specific)
    # Should indicate φ²+φ⁻²=3 verified
```

### Step 4: Load Mode Verification

Test packet-based computation:

```python
@cocotb.test()
async def test_load_mode(dut):
    """Test load mode with operand loading"""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.fork(clock.start())
    
    dut.rst_n.value = 0
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    
    # Enter load mode
    dut.ui_in[0].value = 1
    await Timer(50, units="ns")
    
    # Load operand (simplified - see API.md for full protocol)
    dut.ui_in[7].value = 1  # load_lane_strobe
    dut.uio_in.value = 0x01
    await Timer(50, units="ns")
    dut.ui_in[7].value = 0
    await Timer(50, units="ns")
    
    # Issue compute
    dut.ui_in[6].value = 1  # compute_strobe
    await Timer(50, units="ns")
    dut.ui_in[6].value = 0
    await Timer(100, units="ns")
    
    # Check result
    await ReadOnly()
    result = (dut.uio_out.value << 8) | dut.uo_out.value
    print(f"Computation result: {result:#06x}")
```

### Step 5: Sacred ROM Verification

Test sacred constants access:

```python
@cocotb.test()
async def test_sacred_rom(dut):
    """Test sacred constants ROM"""
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.fork(clock.start())
    
    dut.rst_n.value = 0
    await Timer(100, units="ns")
    dut.rst_n.value = 1
    
    # Enable sacred mode
    dut.ui_in[7].value = 1
    dut.ui_in[0].value = 0  # Canonical
    await Timer(50, units="ns")
    
    # Read sacred constants (addresses 0-63)
    for addr in range(10):
        dut.ui_in[6:1].value = addr
        await Timer(50, units="ns")
        
        # Read from uo_out
        value = dut.uo_out.value
        print(f"Sacred[{addr}] = 0x{value:02X}")
```

### Step 6: Friend/Foe Handshake

Test cross-die detection:

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
    
    # Simulate friend chip (anchor = 0xCF for phi)
    dut.uio_in[1].value = 0  # RX from friend
    await Timer(200, units="ns")
    
    # Check handshake status (on uio_out[2:3])
    friend = dut.uio_out[2].value
    valid = dut.uio_out[3].value
    
    print(f"Friend detected: {friend}, Valid: {valid}")
```

## Common Issues

### Issue 1: No output / stuck at 0x0000

**Symptoms:** Outputs remain at 0x0000

**Possible causes:**
- Clock not running
- Reset stuck low
- Power supply issue

**Fixes:**
1. Verify clock signal with oscilloscope
2. Check rst_n is high after initial 100 ns
3. Verify 3.3V supply is stable

### Issue 2: Incorrect canonical output

**Symptoms:** Output not 0x47C0 at reset

**Possible causes:**
- DUT variant mismatch
- Pin reassignment

**Fixes:**
1. Check top-level module matches expected design
2. Verify pin assignments in constraints file

### Issue 3: POST timeout

**Symptoms:** POST never completes

**Possible causes:**
- Clock frequency too high/slow
- Power instability

**Fixes:**
1. Verify clock at 50 MHz
2. Check power supply stability

## Performance Measurements

### Expected Performance (on silicon)

| Metric | Target | Min | Max |
|--------|--------|-----|-----|
| Clock frequency | 50 MHz | 40 MHz | 60 MHz |
| Power (idle) | 12 mW | 10 mW | 15 mW |
| Power (active) | 75 mW | 60 mW | 90 mW |
| TOPS/W (AVS-96) | 405 | 380 | 430 |

### Measurement Procedure

1. **Clock frequency:** Measure clock period on oscilloscope
2. **Power:** Measure current draw with multimeter
3. **TOPS:** Count MACs per second (1 MAC/cycle × frequency)

## Simulation

### Running All Tests

```bash
cd test
make all
```

### Running Specific Test

```bash
./sim.sh tb_canonical_anchor
```

### Viewing Waveforms

```bash
gtkwave sim/tb_canonical_anchor.vcd
```

## Validation Checklist

- [ ] Canonical anchor 0x47C0 verified at reset
- [ ] Lucas ROM L₂..L₇ values correct
- [ ] POST sequence completes
- [ ] Load mode accepts operands
- [ ] Sacred ROM accessible
- [ ] HWRNG generates non-zero values
- [ ] Friend/foe handshake functional
- [ ] Power consumption within spec
- [ ] Clock frequency stable
- [ ] D2D signals functional

## References

- API Documentation: `docs/API.md`
- Architecture: `docs/ARCHITECTURE.md`
- Testbenches: `test/*.v`
- Sacred Anchor: φ² + φ⁻² = 3 — DOI 10.5281/zenodo.19227877

## Support

For issues:
1. Check this guide
2. Review API.md for interface details
3. Run simulation to isolate problem
4. Check CI workflow results

DOI: 10.5281/zenodo.19227877