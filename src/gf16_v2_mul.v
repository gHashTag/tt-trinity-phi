// SPDX-License-Identifier: Apache-2.0
// gf16_v2_mul.v - GoldenFloat16 multiplier [S(1) | E(6) | M(9)], bias 31.
// value = (-1)^S (1 + M/2^9) 2^(E-31); E = 0 with M != 0 is a NORMAL number, E = 0
// with M = 0 is zero, E = 63 is Inf (M = 0) or NaN (M != 0).
//
// SKY26d contract (specs/numeric/gf16_dot4_sky26d.t27, issue #100):
//   - the exact product is normalised into an unbounded 1.9 binade, rounded to nearest
//     with a tie going TOWARD ZERO (round up only if the discarded part is > 1/2),
//     with carry into the next binade; only THEN the range rules apply:
//     biased exponent >= 63 -> signed Inf; < 0, or 0 with M = 0 -> +0.
//   - every zero result is +0 (the sign of a zero product is dropped).
//   - any NaN operand, and Inf * 0, give NaN 0xFE01. Inf * nonzero -> Inf, sign S_a ^ S_b.
// History: the file name is kept from the archived baseline (617c0fc). The rounding
// mode and the zero/underflow/overflow policy are unchanged from that baseline; the
// only change is that the significand product is built by gf16_sig_mul10 (shift-and-add)
// instead of an arithmetic multiply operator (R-SI-1).
`default_nettype none
module gf16_v2_mul (
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

    wire rs = sa ^ sb;

    // significand product, 20 bits: 2^18 <= prod < 2^20
    wire [19:0] prod;
    gf16_sig_mul10 u_sig (.a({1'b1, ma}), .b({1'b1, mb}), .p(prod));

    // Normalisation, rounding and exponent are computed for BOTH binades in parallel and the
    // binade (prod[19]) only selects at the end. Behaviour is identical to "select the binade
    // first, then round, then add the exponent carries".
    //
    // The operands are {1, M}, so 512 <= A, B <= 1023 and P = A*B satisfies
    //   2^18 <= P <= 1023*1023 = 1046529 < 2^20.
    //   top = prod[19]  <=>  P >= 2^19.
    //   lower binade [1,2)  (top = 0): keep prod[18:9], discard prod[8:0]; half is 256; round up
    //     iff the discarded part is > 256, i.e. prod[8] and any of prod[7:0] (a tie stays down).
    //     prod[18] is always 1 (the hidden one), the fraction is prod[17:9]. Adding the round-up to
    //     it wraps to 0 exactly when the 10-bit significand 1023 rounds up to 1024: that is the
    //     rounding carry cy_lo (mantissa 0, exponent + 1). It IS reachable (724 * 724 = 524176).
    //   upper binade [2,4)  (top = 1): keep prod[19:10], discard prod[9:0]; half is 512; round up
    //     iff the discarded part is > 512, i.e. prod[9] and any of prod[8:0]. The hidden one is
    //     prod[19], the fraction is prod[18:10]. A rounding carry would need significand
    //     prod[19:10] = 1023, i.e. P >= 1023 * 1024 = 1047552 (> 1046529), and a round-up with a
    //     tie staying down also needs a remainder above 512, so P >= 1023 * 1024 + 513 = 1048065.
    //     Either bound exceeds the maximum, so the upper-binade carry is unreachable: P <= 1022 * 1024 + 1, the
    //     significand is at most 1022 and +1 never overflows. This argument is for THIS wrapper
    //     only (hidden-one inputs), not for an arbitrary 20-bit input; gf16_sig_mul10 itself
    //     still covers all 1024 x 1024 pairs. test/mul_pack_bound.py checks the bound and the
    //     equivalence on all 512 x 512 integer pairs.
    wire        top     = prod[19];

    wire        up_lo   = prod[8] & (|prod[7:0]);
    wire [8:0]  mant_lo = prod[17:9] + {8'd0, up_lo};
    wire        cy_lo   = (&prod[17:9]) & up_lo;

    wire        up_hi   = prod[9] & (|prod[8:0]);
    wire [8:0]  mant_hi = prod[18:10] + {8'd0, up_hi};

    wire [8:0]  mant    = top ? mant_hi : mant_lo;

    // Biased exponent of the result, 8-bit two's complement, range -31 .. 96. Both candidates
    // and their range flags are formed from esum alone, in parallel with the product:
    //   e31 = esum - 31  (lower binade, no carry)
    //   e30 = esum - 30  (upper binade, or lower binade with the rounding carry)
    wire [7:0] esum = {2'b00, ea} + {2'b00, eb};
    wire [7:0] e31  = esum - 8'd31;
    wire [7:0] e30  = esum - 8'd30;
    wire       neg31 = e31[7];
    wire       neg30 = e30[7];
    wire       zer31 = (e31 == 8'd0);
    wire       zer30 = (e30 == 8'd0);
    wire       ovf31 = (e31[6:0] >= 7'd63);
    wire       ovf30 = (e30[6:0] >= 7'd63);

    wire       sel30 = top | cy_lo;
    wire       eneg  = sel30 ? neg30 : neg31;
    wire       ezero = sel30 ? zer30 : zer31;
    wire       eovf  = sel30 ? ovf30 : ovf31;
    wire [5:0] efld  = sel30 ? e30[5:0] : e31[5:0];

    always @* begin
        if (nan_a || nan_b || (inf_a && zero_b) || (inf_b && zero_a))
            result = 16'hFE01;
        else if (inf_a || inf_b)
            result = {rs, 6'd63, 9'd0};
        else if (zero_a || zero_b)
            result = 16'h0000;
        else if (eneg || (ezero && (mant == 9'd0)))
            result = 16'h0000;                     // underflow and the 2^-31 gap flush to +0
        else if (eovf)
            result = {rs, 6'd63, 9'd0};            // overflow
        else
            result = {rs, efld, mant};
    end

endmodule
`default_nettype wire
