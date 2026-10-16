// SPDX-License-Identifier: Apache-2.0
// The 8 truth cases of the technology full adder, run ONLY by test/physical_fa_check.py against the
// real PDK Verilog models (primitives.v + sky130_fd_sc_hd.v of the pinned PDK) and src/gf16_sig_mul10.v
// compiled with -DPHI_FA_PHYS. It checks the PDK model cell sky130_fd_sc_hd__fa_1 directly and the
// project wrapper gf16_fa1 (which instantiates that cell in this mode) against sum = a ^ b ^ cin
// and cout = majority(a, b, cin). A simulation of the PDK model is not a layout or LVS proof.
`timescale 1ns/1ps
module tb_fa1_truth;
    reg  a, b, cin;
    wire s_cell, c_cell, s_wrap, c_wrap;
    reg  exp_s, exp_c;
    integer i, bad, n;

    sky130_fd_sc_hd__fa_1 u_cell (.A(a), .B(b), .CIN(cin), .COUT(c_cell), .SUM(s_cell));
    gf16_fa1 u_wrap (.a(a), .b(b), .cin(cin), .sum(s_wrap), .cout(c_wrap));

    initial begin
        bad = 0;
        n = 0;
        for (i = 0; i < 8; i = i + 1) begin
            {a, b, cin} = i[2:0];
            #20;
            exp_s = a ^ b ^ cin;
            exp_c = (a & b) | (a & cin) | (b & cin);
            n = n + 1;
            if (s_cell !== exp_s || c_cell !== exp_c || s_wrap !== exp_s || c_wrap !== exp_c) begin
                bad = bad + 1;
                $display("TRUTH MISMATCH abc=%b cell sum/cout=%b/%b wrapper=%b/%b expected=%b/%b",
                         {a, b, cin}, s_cell, c_cell, s_wrap, c_wrap, exp_s, exp_c);
            end
        end
        $display("FA1_TRUTH_RESULT N=%0d MISMATCH=%0d", n, bad);
        $finish;
    end
endmodule
