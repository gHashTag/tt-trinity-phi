#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cycle-accurate reference model of the SKY26d DOT4 pin contract.

Written from specs/numeric/gf16_dot4_sky26d.t27 (sections 3-5). All arithmetic is done by
the independent exact oracle (gf16_oracle); there is no copy of the RTL datapath here.
The model sees only pins: ui_in, uio_in, ena and reset, exactly like a real host.
"""
import gf16_oracle as orc

SIG_LO = 0xC0
SIG_HI = 0x47


class PinModel:
    def __init__(self):
        self.reset()

    def reset(self):
        self.mem = [0] * 16
        self.ptr = 0
        self.step_idx = 0
        self.busy = 0
        self.done = 0
        self.err = 0
        self.wr_q = 0
        self.go_q = 0
        self.prod = 0
        self.acc = 0

    # ---- one enabled/disabled rising clock edge --------------------------------
    def clock(self, ui, uio, ena=1):
        if not ena:
            return
        wr = uio & 1
        go = (uio >> 1) & 1
        wr_rise = wr and not self.wr_q
        go_rise = go and not self.go_q
        self.wr_q = wr
        self.go_q = go
        if self.busy:
            if wr_rise or go_rise:
                self.err = 1
            s = self.step_idx
            lane = s >> 1
            if s in (0, 2, 4, 6):
                self.prod = orc.mul(self.word(2 * lane), self.word(8 + 2 * lane))
            elif s == 1:
                self.acc = self.prod
            else:
                self.acc = orc.add(self.acc, self.prod)
            if s == 7:
                self.busy = 0
                self.done = 1
            self.step_idx = (s + 1) & 7
        elif wr_rise:
            self.mem[self.ptr] = ui & 0xFF
            self.ptr = (self.ptr + 1) & 15
            self.done = 0
        elif go_rise:
            self.ptr = 0
            self.done = 0
            self.err = 0
            self.busy = 1
            self.step_idx = 0

    def word(self, base):
        """16-bit little-endian word at byte address base (A_k at 2k, B_k at 8 + 2k)."""
        return self.mem[base] | (self.mem[base + 1] << 8)

    # ---- combinational read (uo_out) ---------------------------------------------
    def status(self):
        return (self.ptr << 4) | (self.err << 2) | (self.done << 1) | self.busy

    def read(self, ui, uio):
        rsel = (uio >> 2) & 7
        if rsel == 0:
            return self.status()
        if rsel == 1:
            return 0 if self.busy else self.acc & 0xFF
        if rsel == 2:
            return 0 if self.busy else (self.acc >> 8) & 0xFF
        if rsel == 3:
            return SIG_LO
        if rsel == 4:
            return SIG_HI
        if rsel == 5:
            return self.mem[ui & 0x0F]
        return 0
