# SPDX-License-Identifier: Apache-2.0
# DePIN v1 cocotb test stub — B1 RoT + B2 Bandwidth + B8 DID
# Author: Dmitrii Vasilev (sole author, admin@t27.ai)
#
# Tests:
#   test_b1_rot_deterministic  — B1 challenge/response is deterministic
#   test_b2_bandwidth_counter  — B2 bytes_counter increments on packet_in
#   test_b8_did_signature      — B8 DID signature is deterministic
#
# Wiring convention (tt_um_trinity_nano top-level):
#   ui_in[7:5] = 3'b001 -> B1 response on uo_out
#   ui_in[7:5] = 3'b010 -> B2 bytes_counter[7:0] on uo_out
#   ui_in[7:5] = 3'b011 -> B8 did_signature on uo_out
#   uio_in     = challenge / packet data
#   ui_in[0]   = 0 (canonical mode, not load mode)

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles


async def reset_dut(dut):
    """Apply reset for 5 cycles then release."""
    dut.rst_n.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.ena.value = 1
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)


@cocotb.test()
async def test_b1_rot_deterministic(dut):
    """B1 HW Root-of-Trust: same challenge always produces same response."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # Select B1 mode: ui_in[7:5] = 3'b001, ui_in[0]=0
    # ui_in = 0b00100000 = 0x20
    CHALLENGE = 0xA5
    dut.ui_in.value = 0x20
    dut.uio_in.value = CHALLENGE

    await ClockCycles(dut.clk, 2)
    response_first = int(dut.uo_out.value)

    # Apply same challenge again
    await ClockCycles(dut.clk, 3)
    response_second = int(dut.uo_out.value)

    assert response_first == response_second, (
        f"B1 RoT non-deterministic: {response_first:#04x} != {response_second:#04x}"
    )
    assert response_first != 0x00, "B1 response should not be zero for non-zero challenge"

    dut._log.info(f"B1 RoT: challenge=0x{CHALLENGE:02X} response=0x{response_first:02X} PASS")


@cocotb.test()
async def test_b2_bandwidth_counter(dut):
    """B2 Proof-of-Bandwidth: bytes_counter increments on each packet pulse."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # Select B2 mode: ui_in[7:5] = 3'b010, ui_in[0]=0
    # ui_in = 0b01000000 = 0x40
    # B2 packet_in is driven by load_lane_rise (ui_in[7] edge in load_mode=1)
    # For simplicity, drive in load_mode to trigger load_lane_rise pulses,
    # then switch to B2 read mode to observe bytes_counter.

    # Trigger 3 load_lane_rise pulses (load_mode=1, ui_in[7] rising edges)
    # load_mode = ui_in[0]=1, load_lane_strobe = ui_in[7]
    dut.uio_in.value = 0x00
    for _ in range(3):
        dut.ui_in.value = 0x01          # load_mode=1, strobe=0
        await ClockCycles(dut.clk, 1)
        dut.ui_in.value = 0x81          # load_mode=1, strobe=1 (rising edge)
        await ClockCycles(dut.clk, 1)
        dut.ui_in.value = 0x01          # strobe=0
        await ClockCycles(dut.clk, 1)

    # Now switch to B2 read mode: ui_in = 0x40 (ui_in[7:5]=3'b010, load_mode=0)
    dut.ui_in.value = 0x40
    await ClockCycles(dut.clk, 2)

    counter_val = int(dut.uo_out.value)
    # counter should be > 0 (we sent 3 packets)
    assert counter_val > 0, (
        f"B2 bandwidth counter should be >0 after 3 packets, got {counter_val:#04x}"
    )

    dut._log.info(f"B2 bandwidth: bytes_counter[7:0]=0x{counter_val:02X} PASS")


@cocotb.test()
async def test_b8_did_signature(dut):
    """B8 DID personhood: same challenge + phi_fingerprint always produces same signature."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    await reset_dut(dut)

    # Select B8 mode: ui_in[7:5] = 3'b011, ui_in[0]=0
    # ui_in = 0b01100000 = 0x60
    HUMAN_CHALLENGE = 0x3C
    dut.ui_in.value = 0x60
    dut.uio_in.value = HUMAN_CHALLENGE

    await ClockCycles(dut.clk, 2)
    sig_first = int(dut.uo_out.value)

    await ClockCycles(dut.clk, 3)
    sig_second = int(dut.uo_out.value)

    assert sig_first == sig_second, (
        f"B8 DID signature non-deterministic: {sig_first:#04x} != {sig_second:#04x}"
    )
    # After reset phi_fingerprint = canonical_dot[7:0] = 0xC0
    # Expected: HUMAN_CHALLENGE ^ 0xC0 ^ {0xC0[3:0], 0xC0[7:4]}
    #         = 0x3C ^ 0xC0 ^ {4'b0000, 4'b1100} = 0x3C ^ 0xC0 ^ 0x0C
    #         = 0xFC ^ 0x0C = 0xF0
    expected = HUMAN_CHALLENGE ^ 0xC0 ^ ((0xC0 & 0x0F) << 4 | (0xC0 >> 4))
    expected &= 0xFF
    assert sig_first == expected, (
        f"B8 DID: expected 0x{expected:02X}, got 0x{sig_first:02X}"
    )

    dut._log.info(f"B8 DID: challenge=0x{HUMAN_CHALLENGE:02X} sig=0x{sig_first:02X} PASS")
