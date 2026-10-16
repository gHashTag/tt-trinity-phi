// SPDX-License-Identifier: Apache-2.0
// gf16_v2_add.v - GoldenFloat16 adder [S(1) | E(6) | M(9)], bias 31, EXACT round-to-
// nearest-even of the exact sum.
//
// SKY26d contract (specs/numeric/gf16_dot4_sky26d.t27, issue #100). For finite nonzero
// operands the exact sum is normalised into an unbounded 1.9 binade, rounded to nearest
// with a tie going to the EVEN mantissa, with carry into the next binade; only then the
// range rules apply: biased exponent >= 63 -> signed Inf; < 0, or 0 with M = 0 -> +0.
// Every zero result is +0 (exact cancellation, zero + zero, underflow). zero + x -> x
// unchanged. Any NaN operand and Inf + (-Inf) give NaN 0xFE01; Inf + Inf of equal sign
// and Inf + finite give that Inf.
//
// History: the file name is kept from the archived baseline (617c0fc). The baseline adder
// rounded faithfully (<= 1 ULP) with a truncating alignment; for SKY26d the adder is
// replaced by this exact one. The baseline is frozen and is NOT claimed unchanged.
//
// Method (13-bit significands with 3 extra low bits, 14-bit sum):
//   * the operand with the larger magnitude {E,M} is the high one, the other the low one;
//   * the low significand is shifted right by d = E_hi - E_lo in stages of 1, 2, 4 and 8
//     positions (d <= 12); every bit shifted out of a stage is OR-ed into one sticky bit,
//     which is then OR-ed into bit 0 of the result (jam). For d >= 13 the whole low
//     significand leaves the 13-bit window and the aligned operand is exactly 1 (jam of a
//     nonzero value; 0 for a zero low operand). For d <= 3 nothing nonzero is lost. For d >= 4 an effective
//     subtraction moves the leading bit by at most one place, so the jammed bit only ever
//     sits below the rounding position and the decision on guard and "rest is nonzero" is
//     exactly that of the true difference;
//   * ONE 14-bit adder does both operations: for an effective subtraction the aligned
//     operand is inverted and a carry-in of 1 is added (two's complement); the carry-in is the
//     seed of one ripple chain (gf16_fa1 of gf16_sig_mul10.v on the 10 bits with three variable
//     inputs), so this file needs gf16_sig_mul10.v in every compile list;
//   * after the add the sum is normalised by a fixed 8/4/2/1 left-normalisation tree (module
//     gf16_add_norm14 below, same count and word as a leading-zero encoder plus shift) and rounded.
//   * zero operands go through the same arithmetic (no separate output path): a finite zero enters
//     with significand 0 (every nonzero code, also E = 0 with M > 0, with its hidden 1), and the far
//     jam bit of a zero low operand is 0. Policy and proof boundaries:
//     specs/physical/gf16_dot4_addnorm_probe.t27 section 5. Zero + x: x is the high operand (larger
//     {E,M}), the aligned low part is 0 for every d, tsum = {0, 1, M, 000} for add and subtract (the
//     two's complement of 0 wraps to 0), the normaliser shifts by 1, guard/sticky are 0, so eres = E,
//     mant = M and the result is x bit for bit. Zero + zero: tsum = 0, so +0. Checked by
//     test/add_zero_sweep.py (both zero signs x all 65536 codes, both orders) and the full sweeps.
//
// Algebra (checked by test/unit_sweeps.py against the exact rational oracle, not asserted here):
//   staged shift: the stages move by 1, 2, 4, 8 exactly when bits 0..3 of d are set, so the total
//   shift is d (d <= 12) and the OR of the bits dropped stage by stage is the OR of the d
//   lowest bits of the original significand, the same set as the single-shift form;
//   add/sub: for X in [0, 2^13), Y in [0, 2^13): X - Y (X >= Y) = X + (~Y) + 1 modulo 2^14 with
//   ~Y taken over 14 bits, and the 14-bit result equals the true difference because X >= Y;
//   X + Y < 2^14 needs no wrap. With c = eff_sub and Y' = Y xor eff_sub the sum is (X + Y' + c) mod 2^14.
//   The former form {X,1} + {Y',c} (15 bits, result in bits [14:1]) is the same function: bit 0 contributes
//   1 + c, whose carry is c. It is now written as a 14-bit ripple chain with carry seed c (gf16_fa1 where
//   all three inputs vary, half adders / xor where a bit of X is the constant 0).
`default_nettype none

// Left-normaliser of the 14-bit sum: lz is the number of leading zeros (14 for x = 0) and norm is x shifted
// left by lz (so the leading one sits at bit 13; norm is 0 for x = 0). The same function as the earlier
// priority encoder followed by a variable shift (lz = 13 - position of the leading one, 14 for zero), but
// built as four fixed stages of 8, 4, 2 and 1 positions: each stage tests whether the top group of the
// word that is left is empty and, if so, shifts the word by exactly that group size; the tests ARE the bits
// of lz. Why it works: after the 8-stage a nonzero word has its leading one in bits 13..6 (the stage moves
// a one from bits 5..0 up by 8), after the 4-stage in 13..10, after the 2-stage in 13..12, and the
// 1-stage moves a one at bit 12 to 13. For x = 0 every group test is true except the last one, which is
// qualified by n2[12]: a zero word leaves lz = 8 + 4 + 2 = 14, matching the old encoder's "default" case.
// test/tb_add_norm14.v compares this module with the old definition on all 16384 inputs.
module gf16_add_norm14 (
    input  wire [13:0] x,
    output wire [13:0] norm,
    output wire [3:0]  lz
);
    wire        s8 = ~(|x[13:6]);
    wire [13:0] n8 = s8 ? {x[5:0], 8'd0} : x;
    wire        s4 = ~(|n8[13:10]);
    wire [13:0] n4 = s4 ? {n8[9:0], 4'd0} : n8;
    wire        s2 = ~(|n4[13:12]);
    wire [13:0] n2 = s2 ? {n4[11:0], 2'd0} : n4;
    wire        s1 = ~n2[13] & n2[12];
    assign norm = s1 ? {n2[12:0], 1'b0} : n2;
    assign lz   = {s8, s4, s2, s1};
endmodule

module gf16_v2_add (
    input  wire [15:0] a,
    input  wire [15:0] b,
    output reg  [15:0] result
);

    wire        sa = a[15];
    wire [5:0]  ea = a[14:9];
    wire [8:0]  ma = a[8:0];
    wire        sb = b[15];
    wire [5:0]  eb = b[14:9];
    wire [8:0]  mb = b[8:0];

    wire zero_a = (ea == 6'd0)  && (ma == 9'd0);
    wire zero_b = (eb == 6'd0)  && (mb == 9'd0);
    wire inf_a  = (ea == 6'd63) && (ma == 9'd0);
    wire inf_b  = (eb == 6'd63) && (mb == 9'd0);
    wire nan_a  = (ea == 6'd63) && (ma != 9'd0);
    wire nan_b  = (eb == 6'd63) && (mb != 9'd0);

    // magnitude order of the {E,M} fields (meaningful for finite operands)
    wire        a_big   = (a[14:0] >= b[14:0]);
    wire [14:0] mg_hi   = a_big ? a[14:0] : b[14:0];
    wire [14:0] mg_lo   = a_big ? b[14:0] : a[14:0];
    wire        sgn_big = a_big ? sa : sb;       // sign of the larger-magnitude operand
    wire        eff_sub = sa ^ sb;               // effective subtraction (order independent)

    // a finite zero enters the arithmetic with significand 0, every finite nonzero code (also E = 0, M > 0)
    // with its hidden 1; the zero flags are sorted by the same compare as the fields
    wire        zero_hi = a_big ? zero_a : zero_b;
    wire        zero_lo = a_big ? zero_b : zero_a;
    wire [5:0]  e_big   = mg_hi[14:9];
    wire [5:0]  e_sml   = mg_lo[14:9];
    wire [9:0]  sig_big = {~zero_hi, mg_hi[8:0]};
    wire [9:0]  sig_sml = {~zero_lo, mg_lo[8:0]};

    wire [5:0]  dif  = e_big - e_sml;
    wire [12:0] bext = {sig_big, 3'b000};
    wire [12:0] sext = {sig_sml, 3'b000};

    // alignment: d >= 13 -> the aligned operand is exactly 1 (everything jammed) for a nonzero low operand,
    // exactly 0 for a zero low operand
    wire        far  = (|dif[5:4]) | (dif[3] & dif[2] & (dif[1] | dif[0]));

    // right shift by d (d <= 12) in stages 1, 2, 4, 8 with a sticky bit
    wire [12:0] v1 = dif[0] ? {1'b0,  sext[12:1]} : sext;
    wire        k1 = dif[0] & sext[0];
    wire [12:0] v2 = dif[1] ? {2'b00, v1[12:2]}   : v1;
    wire        k2 = k1 | (dif[1] & (|v1[1:0]));
    wire [12:0] v3 = dif[2] ? {4'b0,  v2[12:4]}   : v2;
    wire        k3 = k2 | (dif[2] & (|v2[3:0]));
    wire [12:0] v4 = dif[3] ? {8'b0,  v3[12:8]}   : v3;
    wire        k4 = k3 | (dif[3] & (|v3[7:0]));
    wire [12:0] smj_near = {v4[12:1], v4[0] | k4};
    wire [12:0] smj      = far ? {12'd0, ~zero_lo} : smj_near;

    // ONE adder for add and subtract: tsum = ({1'b0, bext} + (smj xor eff_sub) + eff_sub) mod 2^14, written as a
    // ripple chain with the carry seed eff_sub. {1'b0, bext} has the constant bits [2:0] = 0 and [13] = 0, so
    // bits 0..2 are half adders and bit 13 is an xor (its carry out is dropped, mod 2^14); bits 3..12 have three
    // variable inputs and use the full-adder wrapper gf16_fa1 of gf16_sig_mul10.v. Policy and the equivalence
    // with the former 15-bit form: specs/physical/gf16_dot4_addnorm_probe.t27 section 6.
    wire [13:0] smj_x  = {1'b0, smj} ^ {14{eff_sub}};
    wire        c_seed = eff_sub;                // carry into bit 0 (the +1 of the two's complement)
    wire [13:0] tsum;
    wire [13:1] cy;                              // cy[i]: carry into bit i
    assign tsum[0] = smj_x[0] ^ c_seed;
    assign cy[1]   = smj_x[0] & c_seed;
    assign tsum[1] = smj_x[1] ^ cy[1];
    assign cy[2]   = smj_x[1] & cy[1];
    assign tsum[2] = smj_x[2] ^ cy[2];
    assign cy[3]   = smj_x[2] & cy[2];
    genvar j;
    generate
        for (j = 3; j <= 12; j = j + 1) begin : g_sum_fa
            gf16_fa1 u_fa (.a(bext[j]), .b(smj_x[j]), .cin(cy[j]), .sum(tsum[j]), .cout(cy[j+1]));
        end
    endgenerate
    assign tsum[13] = smj_x[13] ^ cy[13];
    wire _unused_bext = &{1'b0, bext[2:0]};     // the three constant guard zeros of bext take no adder cell

    // normalisation: leading-zero count and the left-aligned word from one fixed 8/4/2/1 tree
    wire [3:0]  lz;
    wire [13:0] norm;                            // leading one at bit 13 (tsum != 0)
    gf16_add_norm14 u_norm (.x(tsum), .norm(norm), .lz(lz));
    wire [9:0]  sigk = norm[13:4];
    wire        g    = norm[3];
    wire        rest = |norm[2:0];
    wire        lsb  = sigk[0];
    wire        up   = g & (rest | lsb);          // tie goes to the even mantissa
    wire [10:0] sig_r = {1'b0, sigk} + {10'd0, up};
    wire        carry = sig_r[10];
    wire [8:0]  mant  = carry ? 9'd0 : sig_r[8:0];

    // biased exponent: e_big + 1 - lz + carry, 8-bit two's complement, range -12 .. 64
    wire [7:0] eres = {2'b00, e_big} + 8'd1 + {7'd0, carry} - {4'd0, lz};
    wire       eneg = eres[7];

    always @* begin
        if (nan_a || nan_b)
            result = 16'hFE01;
        else if (inf_a && inf_b)
            result = (sa == sb) ? a : 16'hFE01;
        else if (inf_a)
            result = a;
        else if (inf_b)
            result = b;
        else if (tsum == 14'd0)
            result = 16'h0000;                     // exact cancellation, and zero + zero
        else if (eneg || ((eres == 8'd0) && (mant == 9'd0)))
            result = 16'h0000;                     // underflow and the 2^-31 gap flush to +0
        else if (eres[6:0] >= 7'd63)
            result = {sgn_big, 6'd63, 9'd0};       // overflow
        else
            result = {sgn_big, eres[5:0], mant};
    end

endmodule
`default_nettype wire
