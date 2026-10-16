// SPDX-License-Identifier: Apache-2.0
// Exhaustive check of the real RTL module gf16_add_norm14 (src/gf16_v2_add.v): all 2^14 = 16384 inputs,
// including 0, every position of the leading one and bit 13. The reference is the OLD definition (a
// priority encoder with a default of 14 for zero, then a left shift by that count, 14 bits wide), written
// here as test code. Prints ADDNORM14_RESULT N=16384 MISMATCH=0 on success; run by test/unit_sweeps.py.
`timescale 1ns/1ps
module tb_add_norm14;
    reg  [13:0] x;
    wire [13:0] norm;
    wire [3:0]  lz;
    reg  [3:0]  ref_lz;
    reg  [13:0] ref_norm;
    integer i, k, bad, n;
    reg found;

    gf16_add_norm14 dut (.x(x), .norm(norm), .lz(lz));

    initial begin
        bad = 0;
        n = 0;
        for (i = 0; i < 16384; i = i + 1) begin
            x = i;
            #1;
            ref_lz = 4'd14;
            found = 1'b0;
            for (k = 13; k >= 0; k = k - 1) begin
                if (!found && x[k]) begin
                    ref_lz = 13 - k;
                    found = 1'b1;
                end
            end
            ref_norm = x << ref_lz;
            n = n + 1;
            if (lz !== ref_lz || norm !== ref_norm) begin
                bad = bad + 1;
                if (bad <= 10) $display("MISMATCH x=%b lz=%0d/%0d norm=%b/%b", x, lz, ref_lz, norm, ref_norm);
            end
        end
        $display("ADDNORM14_RESULT N=%0d MISMATCH=%0d", n, bad);
        $finish;
    end
endmodule
