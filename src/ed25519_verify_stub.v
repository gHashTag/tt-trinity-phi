`default_nettype none
// ed25519_verify_stub.v — TRI-1-PHI ed25519 signature verification stub
// Phase 2 silicon placeholder — interface only.
// Real ed25519 (point doubling, Montgomery ladder) deferred to Phase 2.
//
// Anchor: phi^2 + phi^-2 = 3 | 0x47C0 watermark | DOI 10.5281/zenodo.19227877
// SPDX-License-Identifier: Apache-2.0
// R-SI-1: zero `*` operators in synthesisable RTL.
// Pure Verilog-2005.
//
// Interface (8-bit byte-serial):
//   load_byte [7:0]  — one byte loaded per clock when en=1
//   en               — byte-load enable (active high)
//   rst_n            — synchronous active-low reset
//   clk              — clock
//   done             — high for one cycle when verification complete
//   valid            — result: 1 = parity check passes (Phase 2: real ed25519)
//
// Protocol:
//   1. Drive rst_n=0 for at least 1 cycle to clear state.
//   2. Load 32 message bytes (byte 0..31) with en=1 sequentially.
//   3. Load 64 signature bytes (byte 32..95) with en=1 sequentially.
//   4. Exactly 1 cycle after byte 95 is clocked in, done pulses high.
//      valid reflects the parity result at the same time as done.
//   5. De-assert en before re-use; pulse rst_n to restart.
//
// Cell budget: ~80 cells (stub). Phase 2 real ed25519 ~6000 cells.
// 96 bytes total = 32 (message) + 64 (signature).
//
// Placeholder algorithm: XOR parity over all 96 loaded bytes.
//   valid = 1 when parity[0] == 0 (even parity — bit-0 of XOR accumulator).
// This is a PLACEHOLDER for Phase 2 real signature verification.
//
// Two-phase design (clean timing, no combinational sampling race):
//   Phase LOAD:  en=1, byte_cnt 0..95, parity_acc accumulates XOR.
//   Phase DONE:  one cycle after byte 95: done=1, valid=~parity_acc_reg[0].
//                parity_acc_reg captures the running XOR at byte_cnt==LAST_BYTE.

`timescale 1ns/1ps

module ed25519_verify_stub (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    input  wire [7:0] load_byte,
    output reg        done,
    output reg        valid
);

    // -------------------------------------------------------------------
    // Phase 2 anchor comment: watermark 0x47C0
    // Real ed25519 deferred: point doubling on Curve25519, Montgomery ladder,
    // modular inversion (Fermat), SHA-512 hash of R‖A‖M. See PHI_ED25519_ROADMAP.md
    // -------------------------------------------------------------------

    // Byte counter: counts 0..95 (96 bytes total)
    reg [6:0] byte_cnt;   // 7 bits: 0..127 sufficient for 96

    // Running XOR parity accumulator over all loaded bytes
    reg [7:0] parity_acc;

    // Registered capture of parity after all bytes loaded
    reg [7:0] parity_final;

    // State flag: set for one cycle to fire done/valid output
    reg        fire;

    // Total bytes to load: 96 (32 msg + 64 sig)
    // LAST_BYTE = 95 (zero-indexed, triggers after 96th byte)
    localparam [6:0] LAST_BYTE = 7'd95;

    // Phase 1: accumulate bytes and detect last byte
    always @(posedge clk) begin
        if (!rst_n) begin
            byte_cnt    <= 7'd0;
            parity_acc  <= 8'h00;
            parity_final<= 8'h00;
            fire        <= 1'b0;
        end else begin
            fire <= 1'b0;  // default

            if (en && !fire) begin
                if (byte_cnt == LAST_BYTE) begin
                    // All 96 bytes received: capture final parity and trigger done
                    parity_final <= parity_acc ^ load_byte;
                    fire         <= 1'b1;
                    byte_cnt     <= 7'd0;
                    parity_acc   <= 8'h00;
                end else begin
                    parity_acc   <= parity_acc ^ load_byte;
                    byte_cnt     <= byte_cnt + 7'd1;
                end
            end
        end
    end

    // Phase 2: output done/valid one cycle after fire
    always @(posedge clk) begin
        if (!rst_n) begin
            done  <= 1'b0;
            valid <= 1'b0;
        end else begin
            done  <= fire;
            // valid = 1 when even parity (bit-0 of final XOR == 0)
            // R-SI-1: no * operator; single bit negation only
            if (fire) begin
                valid <= ~parity_final[0];
            end else if (done) begin
                valid <= valid;  // hold until reset or next done
            end
        end
    end

endmodule
