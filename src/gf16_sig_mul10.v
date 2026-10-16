// SPDX-License-Identifier: Apache-2.0
// gf16_sig_mul10.v - 10x10 unsigned multiplier, 20-bit product, sparse carry-save array.
// Used by gf16_v2_mul for the significand product {1,M} x {1,M}.
// R-SI-1: no arithmetic multiply operator.
//
// Interface and function are unchanged for ALL 2^20 operand pairs (not only operands whose
// top bit is 1): p = a * b.
//
// Structure: row i is the partial product R_i = (b[i] ? a : 0) << i. The rows are added in
// carry-save form: a vector S (sums) and a vector C (carries) with the invariant
//   S + C = R_0 + ... + R_i                 (integers, no truncation)
// maintained by one 3:2 compressor per bit position, using the full-adder identity
//   x + y + z = (x ^ y ^ z) + 2 * maj(x, y, z)  for single bits:
//   S' = S ^ C ^ R,   C' = maj(S, C, R) << 1.
// Known-zero bits are folded by hand, so every position keeps only the terms that can be 1:
//   0 terms -> nothing, 1 term -> a wire, 2 terms -> a half adder written as xor/and logic,
//   3 terms -> one full adder (module gf16_fa1). Row 1 has 9 half adders; rows 2..9 have 9 full
//   adders each (positions k..k+8); the final carry-propagate chain is p[9:0] = S[9:0], one
//   half adder at bit 10, full adders at bits 11..18 and p[19] = the last carry. Total: 80 full
//   adders, 10 half adders. Rows 0..9 never lose a carry: every partial sum is at most
//   1023 * 1023 < 2^20. A technology full-adder cell is a black box to the logic optimiser,
//   which is why constants are folded here and not left to it.
//
// gf16_fa1 has two implementations of the SAME function (sum = a ^ b ^ cin, cout = majority):
//   * generic logic: simulation, host Yosys audit, unit sweeps, mutation runs;
//   * the technology cell sky130_fd_sc_hd__fa_1 of the official flow, selected only when the
//     official LibreLane synthesis defines __pnr__ (or when PHI_FA_PHYS is defined explicitly, which
//     the CI physical-model check does together with the real PDK Verilog models).
// No cell is declared here: the PDK model or black-box definition supplies it, nothing is
// shadowed. A simulation with the generic branch is NOT a proof for the cell branch: that branch
// is checked separately against the PDK model (test/physical_fa_check.py, CI after the GDS job) and
// by the gate-level pin test. Test coverage: test/tb_sig_mul10.v compares all 2^20 operand pairs
// with an integer product (test code, a multiply operator is allowed there); this comment
// records no result of it.
`default_nettype none

`ifdef __pnr__
`define PHI_FA_PHYS
`endif

module gf16_fa1 (
    input  wire a,
    input  wire b,
    input  wire cin,
    output wire sum,
    output wire cout
);
`ifdef PHI_FA_PHYS
    sky130_fd_sc_hd__fa_1 u_fa (.A(a), .B(b), .CIN(cin), .COUT(cout), .SUM(sum));
`else
    assign sum  = a ^ b ^ cin;
    assign cout = (a & b) | (a & cin) | (b & cin);
`endif
endmodule

// One carry-save row k = 2..9: adds R_k = (a & bk) << k into (s_in, c_in). Inputs hold exactly
// the bits that can be non-zero after row k-1 (S: bits 0..k+8, C: bits k..k+8).
module gf16_sm10_row #(
    parameter K = 2
) (
    input  wire [9:0]     a,
    input  wire           bk,
    input  wire [K+8:0]   s_in,
    input  wire [K+8:K]   c_in,
    output wire [K+9:0]   s_out,
    output wire [K+9:K+1] c_out
);
    genvar j;
    generate
        for (j = 0; j < K; j = j + 1) begin : g_pass
            assign s_out[j] = s_in[j];
        end
        for (j = K; j <= K + 8; j = j + 1) begin : g_fa
            gf16_fa1 u_fa (.a(s_in[j]), .b(c_in[j]), .cin(a[j-K] & bk),
                           .sum(s_out[j]), .cout(c_out[j+1]));
        end
    endgenerate
    assign s_out[K+9] = a[9] & bk;
endmodule

module gf16_sig_mul10 (
    input  wire [9:0]  a,
    input  wire [9:0]  b,
    output wire [19:0] p
);

    genvar j;

    // row 0: S = R_0, C = 0
    wire [9:0] s0 = a & {10{b[0]}};

    // row 1: two terms per bit (S, R_1) -> half adders; bit 0 and bit 10 have one term
    wire [10:0] s1;
    wire [10:2] c1;
    assign s1[0]  = s0[0];
    assign s1[10] = a[9] & b[1];
    generate
        for (j = 1; j <= 9; j = j + 1) begin : g_ha1
            assign s1[j]   = s0[j] ^ (a[j-1] & b[1]);
            assign c1[j+1] = s0[j] & (a[j-1] & b[1]);
        end
    endgenerate

    // rows 2..9: three terms (S, C, R_k) at bits k..k+8 -> full adders
    wire [11:0] s2;
    wire [11:3] c2;
    wire [12:0] s3;
    wire [12:4] c3;
    wire [13:0] s4;
    wire [13:5] c4;
    wire [14:0] s5;
    wire [14:6] c5;
    wire [15:0] s6;
    wire [15:7] c6;
    wire [16:0] s7;
    wire [16:8] c7;
    wire [17:0] s8;
    wire [17:9] c8;
    wire [18:0] s9;
    wire [18:10] c9;

    gf16_sm10_row #(.K(2)) u_row2 (.a(a), .bk(b[2]), .s_in(s1), .c_in(c1), .s_out(s2), .c_out(c2));
    gf16_sm10_row #(.K(3)) u_row3 (.a(a), .bk(b[3]), .s_in(s2), .c_in(c2), .s_out(s3), .c_out(c3));
    gf16_sm10_row #(.K(4)) u_row4 (.a(a), .bk(b[4]), .s_in(s3), .c_in(c3), .s_out(s4), .c_out(c4));
    gf16_sm10_row #(.K(5)) u_row5 (.a(a), .bk(b[5]), .s_in(s4), .c_in(c4), .s_out(s5), .c_out(c5));
    gf16_sm10_row #(.K(6)) u_row6 (.a(a), .bk(b[6]), .s_in(s5), .c_in(c5), .s_out(s6), .c_out(c6));
    gf16_sm10_row #(.K(7)) u_row7 (.a(a), .bk(b[7]), .s_in(s6), .c_in(c6), .s_out(s7), .c_out(c7));
    gf16_sm10_row #(.K(8)) u_row8 (.a(a), .bk(b[8]), .s_in(s7), .c_in(c7), .s_out(s8), .c_out(c8));
    gf16_sm10_row #(.K(9)) u_row9 (.a(a), .bk(b[9]), .s_in(s8), .c_in(c8), .s_out(s9), .c_out(c9));

    // final carry-propagate chain: bits 0..9 have only S; bit 10 has S and C (half adder);
    // bits 11..18 have S, C and the carry (full adders); bit 19 is the last carry
    wire [19:11] cy;
    assign p[9:0]   = s9[9:0];
    assign p[10]    = s9[10] ^ c9[10];
    assign cy[11]   = s9[10] & c9[10];
    generate
        for (j = 11; j <= 18; j = j + 1) begin : g_cpa
            gf16_fa1 u_fa (.a(s9[j]), .b(c9[j]), .cin(cy[j]), .sum(p[j]), .cout(cy[j+1]));
        end
    endgenerate
    assign p[19] = cy[19];

endmodule
`default_nettype wire
