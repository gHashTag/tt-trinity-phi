# SPDX-License-Identifier: Apache-2.0
"""Pin-level cocotb tests for the SKY26d GF16 DOT4 (specs/numeric/gf16_dot4_sky26d.t27).

ONE test set for RTL and for the gate-level netlist: it drives and reads only the real pins
(ui_in, uio_in, uo_out, uio_out, uio_oe, ena, clk, rst_n) and never touches DUT internals.
Every cycle the pins are compared with an independent cycle-accurate model of the contract
(pin_model.py, arithmetic from the exact rational oracle gf16_oracle.py), and the key
contract points are ALSO asserted with hand-derived constants so that a shared
misunderstanding of model and RTL cannot hide. A failing check raises PinTestFailure, whose
message starts with PINFAIL; the mutation runner relies on that prefix.

Environment: PHI_RANDOM_N (random vectors, default 300).
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cocotb
from cocotb.triggers import Timer

import gf16_oracle as orc
from pin_model import PinModel

HERE = os.path.dirname(os.path.abspath(__file__))
VECTORS = os.path.join(HERE, "conformance", "gf16_dot4_sky26d_vectors.json")

ONE, TWO, THREE, FOUR = 0x3E00, 0x4000, 0x4100, 0x4200
SELFTEST = [ONE, TWO, THREE, FOUR]
ST_DONE = 0x02
ST_BUSY = 0x01
ST_ERR = 0x04


class PinTestFailure(AssertionError):
    """Raised by every check in this file; the message starts with PINFAIL."""


def need(cond, msg):
    if not cond:
        raise PinTestFailure("PINFAIL " + msg)


class Chip:
    """Drives the pins of the DUT and compares them with the pin model every cycle."""

    def __init__(self, dut):
        self.dut = dut
        self.m = PinModel()
        self.ui = 0
        self.uio = 0
        self.ena = 1
        self.cycles = 0
        self.uo_post = 0

    # ---- pin access -----------------------------------------------------------
    def _get(self, handle, name):
        v = handle.value
        try:
            return int(v)
        except ValueError:
            raise PinTestFailure("PINFAIL X or Z on %s: %s (cycle %d)" % (name, v, self.cycles))

    def check(self, tag):
        uo = self._get(self.dut.uo_out, "uo_out")
        uout = self._get(self.dut.uio_out, "uio_out")
        oe = self._get(self.dut.uio_oe, "uio_oe")
        need(oe == 0, "[%s] uio_oe = 0x%02x, must be 0x00 (cycle %d)" % (tag, oe, self.cycles))
        need(uout == 0, "[%s] uio_out = 0x%02x, must be 0x00 (cycle %d)" % (tag, uout, self.cycles))
        exp = self.m.read(self.ui, self.uio)
        need(uo == exp,
             "[%s] uo_out = 0x%02x, model expects 0x%02x (cycle %d, ui=0x%02x uio=0x%02x, "
             "model status=0x%02x)" % (tag, uo, exp, self.cycles, self.ui, self.uio,
                                       self.m.status()))
        return uo

    # ---- clocking -------------------------------------------------------------
    async def power_up(self):
        d = self.dut
        d.clk.value = 0
        d.rst_n.value = 0
        d.ena.value = 1
        d.ui_in.value = 0
        d.uio_in.value = 0
        await Timer(1, unit="us")
        for _ in range(2):
            d.clk.value = 1
            await Timer(1, unit="us")
            d.clk.value = 0
            await Timer(1, unit="us")
        d.rst_n.value = 1
        await Timer(1, unit="us")
        self.m.reset()
        self.ui, self.uio, self.ena = 0, 0, 1
        self.check("after power-up reset")

    async def async_reset(self, ui=None, uio=None):
        """Assert rst_n in the middle of a cycle, with no clock edge, then release it."""
        d = self.dut
        if ui is not None:
            d.ui_in.value = ui
            self.ui = ui
        if uio is not None:
            d.uio_in.value = uio
            self.uio = uio
        d.rst_n.value = 0
        await Timer(1, unit="us")
        self.m.reset()
        self.check("async reset asserted")
        d.rst_n.value = 1
        await Timer(1, unit="us")
        self.check("async reset released")

    async def cycle(self, ui, uio, ena=1):
        d = self.dut
        d.ui_in.value = ui
        d.uio_in.value = uio
        d.ena.value = ena
        self.ui, self.uio, self.ena = ui, uio, ena
        await Timer(1, unit="us")
        self.check("pre-edge")
        d.clk.value = 1
        await Timer(1, unit="us")
        self.m.clock(ui, uio, ena)
        self.uo_post = self.check("post-edge")
        d.clk.value = 0
        await Timer(1, unit="us")
        self.cycles += 1
        return self.uo_post

    # ---- host operations ------------------------------------------------------
    async def read_sel(self, rsel, ui=0, uio_hi=0):
        """One idle cycle that selects rsel; returns uo_out."""
        return await self.cycle(ui, (rsel << 2) | (uio_hi << 5))

    async def status(self):
        return await self.read_sel(0)

    async def write_byte(self, b):
        await self.cycle(b & 0xFF, 0x01)
        await self.cycle(0x00, 0x00)

    async def load_bytes(self, bytes16):
        for b in bytes16:
            await self.write_byte(b)

    @staticmethod
    def to_bytes(A, B):
        out = []
        for w in list(A) + list(B):
            out += [w & 0xFF, (w >> 8) & 0xFF]
        return out

    async def load(self, A, B):
        await self.load_bytes(self.to_bytes(A, B))

    async def go_edge(self):
        """The GO rising-edge cycle (E0); returns uo_out after it."""
        return await self.cycle(0x00, 0x02)

    async def run_compute(self):
        """After E0: 8 enabled clocks, returns the 9 post-edge status bytes E0..E8."""
        seen = [self.uo_post]
        for _ in range(8):
            seen.append(await self.cycle(0x00, 0x00))
        return seen

    async def read_result(self):
        lo = await self.read_sel(1)
        hi = await self.read_sel(2)
        return lo | (hi << 8)

    async def dot4(self, A, B):
        """Load, GO, exactly 8 clocks, read. Returns the 16-bit result read from the pins."""
        await self.load(A, B)
        await self.go_edge()
        seen = await self.run_compute()
        need(seen == [ST_BUSY] * 8 + [ST_DONE],
             "DOT4 status sequence E0..E8 = %s, expected 8 x 0x01 then 0x02"
             % [hex(x) for x in seen])
        return await self.read_result()


def vec_str(A, B):
    return "A=[%s] B=[%s]" % (",".join("0x%04x" % x for x in A), ",".join("0x%04x" % x for x in B))


async def start(dut):
    chip = Chip(dut)
    await chip.power_up()
    return chip


# ===========================================================================
# tests
# ===========================================================================
@cocotb.test()
async def test_01_reset_state(dut):
    chip = await start(dut)
    need(await chip.read_sel(0) == 0x00, "status after reset must be 0x00")
    need(await chip.read_sel(1) == 0x00, "RES_LO after reset must be 0x00")
    need(await chip.read_sel(2) == 0x00, "RES_HI after reset must be 0x00")
    need(await chip.read_sel(3) == 0xC0, "SIG_LO must be 0xC0")
    need(await chip.read_sel(4) == 0x47, "SIG_HI must be 0x47")
    need(await chip.read_sel(6) == 0x00, "select 6 must read 0x00")
    need(await chip.read_sel(7) == 0x00, "select 7 must read 0x00")
    for a in range(16):
        need(await chip.read_sel(5, ui=0xF0 | a) == 0x00, "cell %d must be 0 after reset" % a)
    # the old reset anchor 0x47C0 is a signature only: nothing but select 3/4 shows it
    need(await chip.cycle(0, 0) == 0x00, "all-zero pins after reset read the status 0x00")


@cocotb.test()
async def test_02_selftest_47c0_8_clocks(dut):
    chip = await start(dut)
    r = await chip.dot4(SELFTEST, SELFTEST)
    need(r == 0x47C0, "DOT4((1,2,3,4),(1,2,3,4)) = 0x%04x, expected 0x47C0 (30.0)" % r)
    need(await chip.status() == ST_DONE, "status after DONE must be 0x02")


def load_vectors():
    with open(VECTORS) as f:
        data = json.load(f)
    need(isinstance(data.get("vectors"), list) and len(data["vectors"]) > 0,
         "conformance vector file is empty or malformed")
    out = []
    for v in data["vectors"]:
        out.append((v["name"], [int(x, 16) for x in v["A"]], [int(x, 16) for x in v["B"]],
                    int(v["expected"], 16)))
    return out


@cocotb.test()
async def test_03_independent_ab_conformance(dut):
    chip = await start(dut)
    for name, A, B, exp in load_vectors():
        need(orc.dot4(A, B) == exp, "conformance file disagrees with the oracle on %s" % name)
        await chip.async_reset()
        r = await chip.dot4(A, B)
        need(r == exp, "vector %s: %s -> 0x%04x, expected 0x%04x" % (name, vec_str(A, B), r, exp))


@cocotb.test()
async def test_04_readback_all_cells(dut):
    chip = await start(dut)
    pat = [(i * 17 + 0x3C) & 0xFF for i in range(16)]
    need(len(set(pat)) == 16, "test pattern must have 16 distinct bytes")
    await chip.load_bytes(pat)
    rng = random.Random(4)
    for a in range(16):
        junk = rng.getrandbits(4) << 4
        got = await chip.read_sel(5, ui=junk | a)
        need(got == pat[a], "readback cell %d = 0x%02x, expected 0x%02x" % (a, got, pat[a]))
    # independent words: low byte and high byte of A and B are different cells
    need(await chip.read_sel(5, ui=0) == pat[0] and await chip.read_sel(5, ui=1) == pat[1]
         and await chip.read_sel(5, ui=8) == pat[8] and await chip.read_sel(5, ui=15) == pat[15],
         "A low/high and B low/high cells must be independent")


@cocotb.test()
async def test_05_pointer_wrap_and_go_resets_ptr(dut):
    chip = await start(dut)
    for i in range(5):
        await chip.write_byte(0x10 + i)
    need(await chip.status() == 0x50, "status after 5 writes must be 0x50 (PTR 5)")
    for i in range(5, 16):
        await chip.write_byte(0x10 + i)
    need(await chip.status() == 0x00, "PTR wraps 15 -> 0 after 16 writes: status 0x00")
    await chip.write_byte(0xEE)
    need(await chip.status() == 0x10, "17th write: PTR 1, status 0x10")
    need(await chip.read_sel(5, ui=0) == 0xEE, "17th write overwrites cell 0")
    need(await chip.read_sel(5, ui=1) == 0x11, "cell 1 keeps its first value")
    # GO resets PTR to 0
    await chip.write_byte(0x77)
    await chip.write_byte(0x78)
    need(await chip.status() == 0x30, "PTR 3 before GO")
    need(await chip.go_edge() == ST_BUSY, "after the GO edge: BUSY, PTR 0 -> status 0x01")
    await chip.run_compute()
    need(await chip.status() == ST_DONE, "after DONE PTR is still 0")
    await chip.write_byte(0x5A)
    need(await chip.read_sel(5, ui=0) == 0x5A, "first write after GO lands in cell 0")


@cocotb.test()
async def test_06_partial_load_uses_stored_cells(dut):
    chip = await start(dut)
    await chip.load_bytes(chip.to_bytes(SELFTEST, [])[:8])       # A0..A3 only
    await chip.go_edge()
    await chip.run_compute()
    need(await chip.read_result() == 0x0000, "A loaded, B never written: result must be 0x0000")
    await chip.async_reset()
    await chip.load_bytes(chip.to_bytes(SELFTEST, [])[:8])       # A again, then B0 only
    await chip.write_byte(ONE & 0xFF)
    await chip.write_byte(ONE >> 8)
    await chip.go_edge()
    await chip.run_compute()
    need(await chip.read_result() == ONE,
         "only B0 = 1.0 written: result must be A0 * B0 = 1.0 (0x3E00)")


@cocotb.test()
async def test_07_reset_mid_load_and_mid_busy(dut):
    chip = await start(dut)
    for i in range(5):
        await chip.write_byte(0xA0 + i)
    await chip.async_reset(ui=0xFF, uio=0x00)
    need(await chip.status() == 0x00, "reset mid-load: status must be 0x00")
    for a in range(16):
        need(await chip.read_sel(5, ui=a) == 0x00, "reset mid-load must clear cell %d" % a)
    # reset in the middle of a compute
    await chip.load(SELFTEST, SELFTEST)
    await chip.go_edge()
    for _ in range(3):
        await chip.cycle(0, 0)
    await chip.async_reset()
    need(await chip.status() == 0x00, "reset mid-busy: status must be 0x00")
    need(await chip.read_result() == 0x0000, "reset mid-busy: result must be 0x0000")
    need(await chip.dot4(SELFTEST, SELFTEST) == 0x47C0, "chip must work again after the resets")
    # a strobe held high through reset release is an edge on the first enabled clock
    await chip.async_reset(ui=0x33, uio=0x01)
    await chip.cycle(0x33, 0x01)
    need(await chip.status() == 0x10, "WR held high through reset release is a rising edge")


@cocotb.test()
async def test_08_ena_pause_and_strobe_history(dut):
    chip = await start(dut)
    # (a) pause in the middle of a compute: exactly 8 ENABLED clocks, state frozen
    await chip.load(SELFTEST, SELFTEST)
    await chip.go_edge()
    seen = [chip.uo_post]
    for i in range(8):
        if i == 3:
            for _ in range(5):
                held = await chip.cycle(0x00, 0x00, ena=0)
                need(held == ST_BUSY, "state must stay BUSY while ena = 0")
        seen.append(await chip.cycle(0x00, 0x00))
    need(seen == [ST_BUSY] * 8 + [ST_DONE], "ena pause must not change the 8-clock count")
    need(await chip.read_result() == 0x47C0, "result after an ena pause must still be 0x47C0")
    # (b) strobe high while ena = 0 is an edge when ena returns (last enabled sample was low)
    await chip.async_reset()
    for _ in range(3):
        need(await chip.cycle(0x21, 0x01, ena=0) == 0x00, "no write while ena = 0")
    need(await chip.cycle(0x21, 0x01, ena=1) == 0x10, "WR high when ena returns writes once")
    await chip.cycle(0x00, 0x00)                                  # WR low, history low
    await chip.cycle(0x22, 0x01)                                  # write 2, history high
    for _ in range(2):
        await chip.cycle(0x00, 0x00, ena=0)                       # frozen: history stays high
    need(await chip.cycle(0x23, 0x01, ena=1) == 0x20,
         "WR still high after a pause is NOT a new edge (history is frozen): PTR stays 2")
    need(await chip.read_sel(5, ui=0) == 0x21 and await chip.read_sel(5, ui=1) == 0x22,
         "cells written before the pause keep their values")


@cocotb.test()
async def test_09_wr_go_same_clock_idle(dut):
    chip = await start(dut)
    st = await chip.cycle(0x55, 0x03)
    need(st == 0x10, "WR+GO in the same idle clock: WR accepted (PTR 1), GO ignored, no ERR")
    need(await chip.cycle(0x00, 0x00) == 0x10, "after WR+GO the chip is still idle")
    need(await chip.read_sel(5, ui=0) == 0x55, "the byte of the WR+GO clock is stored")
    need(await chip.go_edge() == ST_BUSY, "a later GO edge starts the compute")


@cocotb.test()
async def test_10_busy_ignores_and_sets_err(dut):
    chip = await start(dut)
    for kind, uio_hit in (("WR", 0x01), ("GO", 0x02)):
        # GO is high in the E0 cycle, so a second GO can be a rising edge only from E2 on
        for k in (range(1, 9) if kind == "WR" else range(2, 9)):
            await chip.async_reset()
            await chip.load(SELFTEST, SELFTEST)
            await chip.go_edge()
            seen = [chip.uo_post]
            for i in range(1, 9):
                seen.append(await chip.cycle(0xFF, uio_hit if i == k else 0x00))
            need(seen[-1] == (ST_DONE | ST_ERR),
                 "%s edge at compute clock E%d must set ERR: final status 0x%02x, expected 0x06"
                 % (kind, k, seen[-1]))
            need(await chip.read_result() == 0x47C0,
                 "%s edge during BUSY must not disturb the result" % kind)
            need(await chip.read_sel(5, ui=0) == 0x00 and await chip.read_sel(5, ui=1) == 0x3E,
                 "%s edge during BUSY must not write memory" % kind)
    # a WR edge in the first idle clock after E8 is accepted and sets no ERR
    await chip.async_reset()
    await chip.load(SELFTEST, SELFTEST)
    await chip.go_edge()
    for _ in range(8):
        await chip.cycle(0x00, 0x00)
    need(await chip.cycle(0x99, 0x01) == 0x10, "WR right after E8 is accepted, no ERR")
    # ERR is sticky through writes and is cleared by an accepted GO
    await chip.async_reset()
    await chip.load(SELFTEST, SELFTEST)
    await chip.go_edge()
    await chip.cycle(0x00, 0x01)
    for _ in range(7):
        await chip.cycle(0x00, 0x00)
    need(await chip.status() == (ST_DONE | ST_ERR), "ERR set, DONE set")
    await chip.write_byte(0x12)
    need(await chip.status() == (0x10 | ST_ERR), "ERR stays set after an accepted WR, DONE cleared")
    need(await chip.go_edge() == ST_BUSY, "an accepted GO clears ERR")


@cocotb.test()
async def test_11_result_visibility(dut):
    chip = await start(dut)
    await chip.load(SELFTEST, SELFTEST)
    await chip.go_edge()
    for i in range(1, 9):
        got = await chip.cycle(0x00, (1 if i % 2 == 0 else 2) << 2)
        if i < 8:
            need(got == 0x00, "RES_LO/RES_HI must read 0x00 while BUSY (clock E%d)" % i)
        else:
            need(got == 0xC0, "after E8 RES_LO shows 0xC0")
    need(await chip.read_result() == 0x47C0, "result after DONE")
    await chip.write_byte(0x01)
    need(await chip.status() == 0x10, "one new WR clears DONE (PTR 1)")
    need(await chip.read_result() == 0x47C0, "the OLD result stays visible, stale, after a new WR")


@cocotb.test()
async def test_12_read_select_and_reserved(dut):
    chip = await start(dut)
    await chip.dot4(SELFTEST, SELFTEST)
    rng = random.Random(12)
    for _ in range(200):
        rsel = rng.randint(0, 7)
        hi = rng.getrandbits(3)
        ui = rng.getrandbits(8)
        got = await chip.read_sel(rsel, ui=ui, uio_hi=hi)
        if rsel == 3:
            need(got == 0xC0, "select 3 must read 0xC0 for any reserved bits")
        elif rsel == 4:
            need(got == 0x47, "select 4 must read 0x47 for any reserved bits")
        elif rsel in (6, 7):
            need(got == 0x00, "selects 6 and 7 must read 0x00")
        elif rsel == 1:
            need(got == 0xC0, "RES_LO must read 0xC0")
        elif rsel == 2:
            need(got == 0x47, "RES_HI must read 0x47")
        elif rsel == 0:
            need(got == ST_DONE, "status must read 0x02")


@cocotb.test()
async def test_13_order_of_rounding_counterexample(dut):
    chip = await start(dut)
    A, B, left, tree = orc.find_reorder_counterexample()
    need(left != tree, "oracle search returned a vector on which the order does not matter")
    r = await chip.dot4(A, B)
    need(r == left, "order vector %s: DUT 0x%04x, left fold %04x, tree %04x"
         % (vec_str(A, B), r, left, tree))
    need(r != tree, "DUT used the tree order on %s" % vec_str(A, B))


@cocotb.test()
async def test_14_random_vectors(dut):
    chip = await start(dut)
    n = int(os.environ.get("PHI_RANDOM_N", "300"))
    rng = random.Random(20261015)
    for i in range(n):
        A = [orc.rand_code(rng) for _ in range(4)]
        B = [orc.rand_code(rng) for _ in range(4)]
        exp = orc.dot4(A, B)
        r = await chip.dot4(A, B)
        need(r == exp, "random vector %d %s: DUT 0x%04x, oracle 0x%04x" % (i, vec_str(A, B), r, exp))
