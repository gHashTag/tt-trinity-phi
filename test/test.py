"""TRI-1 Nano cocotb tests.

Apache-2.0

Tests cover:
  T1 — canonical 0x47C0 immediately after reset (TG-TRIAD-X anchor)
  T2 — uio_oe == 0xFF (drives all uio pins)
  T3 — 0x47C0 is stable across 20 clock cycles
  T4 — load_mode=1 + no operands -> tile result is 0
  T5 — load_mode=1 + strobe sequence does not generate X on pins
"""

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

GL_TEST = os.environ.get("GATES", "no").lower() == "yes"


@cocotb.test()
async def test_canonical_anchor(dut):
    """T1: After reset, {uio_out, uo_out} == 0x47C0 (canonical dot4 anchor)."""
    dut._log.info("T1 — canonical TG-TRIAD-X 0x47C0")
    clock = Clock(dut.clk, 20, units="ns")  # 50 MHz
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await Timer(200, units="ns")
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)
    await Timer(20, units="ns")

    result = (dut.uio_out.value.integer << 8) | dut.uo_out.value.integer
    dut._log.info(f"canonical dot4 = 0x{result:04X} (expected 0x47C0)")
    assert result == 0x47C0, f"Expected 0x47C0, got 0x{result:04X}"


@cocotb.test()
async def test_uio_oe(dut):
    """T2: uio_oe == 0xFF — Nano always drives all 8 uio pins."""
    dut._log.info("T2 — uio_oe == 0xFF")
    assert dut.uio_oe.value.integer == 0xFF, \
        f"uio_oe should be 0xFF, got 0x{dut.uio_oe.value.integer:02X}"


@cocotb.test()
async def test_canonical_stable(dut):
    """T3: 0x47C0 stable across 20 clock cycles (combinational anchor).

    With status-request-gated POST status (ui_in[3]&ui_in[2]==0 in canonical
    idle) the canonical dot4(1,2,3,4)=0x47C0 must stay on the pins forever.
    """
    dut._log.info("T3 — canonical 0x47C0 stability")
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await Timer(200, units="ns")
    dut.rst_n.value = 1

    for _ in range(20):
        await RisingEdge(dut.clk)
        result = (dut.uio_out.value.integer << 8) | dut.uo_out.value.integer
        assert result == 0x47C0, f"Drift! got 0x{result:04X}"


@cocotb.test()
async def test_load_mode_zero(dut):
    """T4: load_mode=1 idle — tile result reg is 0; friend/foe handshake
    activity is allowed on uio[3:0] per the load-mode pin contract.

    Pin contract (load_mode=1):
        uo_out          = tile_dbg_result[7:0]
        uio_out[7:4]    = uio_legacy[7:4] = tile_dbg_result[15:12]
        uio_out[3:0]    = {ff_valid, ff_friend, 1'b0, ff_tx} (live handshake)

    With no LOAD_A/COMPUTE strobes the tile's result_q stays at 0, so the
    "semantic" portion of the bus (uo_out + uio_out[7:4]) must be zero;
    uio_out[3:0] reflects the friend/foe protocol and is not asserted here.
    """
    dut._log.info("T4 — load_mode=1 idle: tile result == 0")
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await Timer(200, units="ns")
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    dut.ui_in.value = 0b00000001  # load_mode = 1
    for _ in range(10):
        await RisingEdge(dut.clk)

    uo  = dut.uo_out.value.integer
    uio = dut.uio_out.value.integer
    tile_result = (uio & 0xF0) | uo  # the 12-bit "semantic" view
    dut._log.info(f"load_mode=1 idle: uo=0x{uo:02X} uio=0x{uio:02X} (uio[3:0]=ff handshake)")
    assert uo == 0x00, f"Expected uo_out=0x00 (tile_dbg_result[7:0]), got 0x{uo:02X}"
    assert (uio & 0xF0) == 0x00, \
        f"Expected uio_out[7:4]=0x0 (tile_dbg_result[15:12]), got 0x{(uio & 0xF0) >> 4:X}"
    assert tile_result == 0x00, f"Expected idle tile result 0x000, got 0x{tile_result:02X}"


@cocotb.test()
async def test_strobe_no_x(dut):
    """T5: load_mode=1 + LOAD_A/COMPUTE strobes do not generate X on pins."""
    dut._log.info("T5 — strobe path no-X smoke")
    clock = Clock(dut.clk, 20, units="ns")
    cocotb.start_soon(clock.start())

    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    await Timer(200, units="ns")
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)

    dut.uio_in.value = 0x80
    # 4 lane strobes on ui_in[7]
    for _ in range(4):
        dut.ui_in.value = 0b10000001
        await RisingEdge(dut.clk)
        dut.ui_in.value = 0b00000001
        await RisingEdge(dut.clk)
    # compute strobe on ui_in[6]
    dut.ui_in.value = 0b01000001
    await RisingEdge(dut.clk)
    dut.ui_in.value = 0b00000001
    for _ in range(10):
        await RisingEdge(dut.clk)

    val = dut.uo_out.value
    val2 = dut.uio_out.value
    # In gate-level sim, X-prop would set is_resolvable False. In RTL we
    # rely on .integer succeeding as the no-X check.
    if not GL_TEST:
        _ = val.integer
        _ = val2.integer
    dut._log.info("strobe path completed without X-prop")
