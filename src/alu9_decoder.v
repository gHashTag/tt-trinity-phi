`default_nettype none
// alu9_decoder.v — Trinity ternary 9-instruction ALU decoder
// Apache-2.0
// Ported from gHashTag/tt-trinity-gf16 (TTSKY26a ancestor)
// R-SI-1 port: TRI_MUL replaced with ternary sign-product LUT (no `*`).
//
// PhD anchor: t27 ISA — ternary (base-3) computer architecture.
// 9 instructions = 3² (sacred constant). Each instruction is 4 bits but only
// 9 codes are valid; the rest map to NOP. The decoder produces strobes for
// downstream execution units.
//
// ISA:
//   0: TRI_NOP         no-op
//   1: TRI_ADD         a + b   (mod 3 lift, clamp to {-1,0,+1})
//   2: TRI_SUB         a - b   (clamp to {-1,0,+1})
//   3: TRI_MUL         a * b   (ternary: sign-product LUT — no `*` operator)
//   4: TRI_AND         a AND b (Kleene min)
//   5: TRI_OR          a OR b  (Kleene max)
//   6: TRI_NOT         -a
//   7: TRI_BIND        VSA bind (XOR on sign)
//   8: TRI_BUNDLE      VSA bundle (majority: sign(a+b))
//
// Gap-0 (K3 Kleene logic) coverage: TRI_AND + TRI_OR + TRI_NOT
// CLARA TA2 VSA compliance: TRI_BIND + TRI_BUNDLE
// R-SI-1: zero `*` operators in synthesisable RTL.
// Combinational module — 0 flip-flops in critical path.
// Verilog-2005 compatible.

module alu9_decoder (
    input  wire [3:0] opcode,
    input  wire [1:0] a,          // ternary operand A: 00=+1 01=-1 1x=0
    input  wire [1:0] b,          // ternary operand B: 00=+1 01=-1 1x=0
    output reg  [1:0] result,     // ternary result:   00=+1 01=-1 1x=0
    output reg        valid,
    output wire       decoder_ok
);

    // ----------------------------------------------------------------
    // TRI_MUL / TRI_BIND product table — R-SI-1 replacement.
    // ternary_mul(a, b): {-1,0,+1} × {-1,0,+1} → {-1,0,+1}
    // Truth table: (+1)x(+1)=+1, (+1)x(-1)=-1, (+1)x0=0,
    //              (-1)x(+1)=-1, (-1)x(-1)=+1, (-1)x0=0, 0xany=0
    // Encoded as 4-bit LUT over {a[1],a[0],b[1],b[0]}.
    // a[1]=1 or b[1]=1 → zero; else result sign = a[0]^b[0]
    // ----------------------------------------------------------------
    function [1:0] ternary_mul;
        input [1:0] ta;
        input [1:0] tb;
        begin
            if (ta[1] | tb[1])
                ternary_mul = 2'b10;         // 0 if either operand is 0
            else if (ta[0] ^ tb[0])
                ternary_mul = 2'b01;         // -1 if opposite signs
            else
                ternary_mul = 2'b00;         // +1 if same signs
        end
    endfunction

    // ----------------------------------------------------------------
    // Ternary signed comparison helpers.
    // Encoding: 2'b00=+1, 2'b01=-1, 2'b10/11=0
    // Order: -1 < 0 < +1  → in encoding: 01 < 10 < 00
    // Map to numeric: 00→2, 01→0, 10→1, 11→1 (for comparison purposes)
    // ----------------------------------------------------------------
    function [1:0] tri_min;   // Kleene AND = min
        input [1:0] ta;
        input [1:0] tb;
        // numeric rank: -1=0, 0=1, +1=2
        // ta rank:  ta[1]=1→1(zero); else ta[0]=0→2(+1),ta[0]=1→0(-1)
        // Return the one with lower rank
        reg [1:0] ra, rb;
        begin
            ra = ta[1] ? 2'd1 : (ta[0] ? 2'd0 : 2'd2);
            rb = tb[1] ? 2'd1 : (tb[0] ? 2'd0 : 2'd2);
            tri_min = (ra <= rb) ? ta : tb;
        end
    endfunction

    function [1:0] tri_max;   // Kleene OR = max
        input [1:0] ta;
        input [1:0] tb;
        reg [1:0] ra, rb;
        begin
            ra = ta[1] ? 2'd1 : (ta[0] ? 2'd0 : 2'd2);
            rb = tb[1] ? 2'd1 : (tb[0] ? 2'd0 : 2'd2);
            tri_max = (ra >= rb) ? ta : tb;
        end
    endfunction

    // ----------------------------------------------------------------
    // ADD/SUB helpers: operate on signed {-1,0,+1} values, clamp result
    // We use integer-valued signed 3-bit intermediates.
    // Decode: 00→+1, 01→-1, 1x→0. Encode back after arithmetic.
    // ----------------------------------------------------------------
    function [1:0] encode_sum;  // encode a clamped integer sum to ternary
        input signed [2:0] s;
        begin
            if      (s > 0) encode_sum = 2'b00;  // +1
            else if (s < 0) encode_sum = 2'b01;  // -1
            else            encode_sum = 2'b10;  // 0
        end
    endfunction

    // Decode ternary to signed 2-bit integer value
    function signed [2:0] tri_decode;
        input [1:0] t;
        begin
            case (t[1])
                1'b0:    tri_decode = t[0] ? -3'sd1 : 3'sd1;
                default: tri_decode = 3'sd0;
            endcase
        end
    endfunction

    // BUNDLE: sign(a+b) = majority
    function [1:0] ternary_bundle;
        input [1:0] ta;
        input [1:0] tb;
        reg signed [2:0] s;
        begin
            s = tri_decode(ta) + tri_decode(tb);
            ternary_bundle = encode_sum(s);
        end
    endfunction

    // ----------------------------------------------------------------
    // Main decode logic (combinational always @(*))
    // ----------------------------------------------------------------
    reg signed [2:0] sa, sb, sr;

    always @(*) begin
        sa    = tri_decode(a);
        sb    = tri_decode(b);
        sr    = 3'sd0;
        valid = 1'b1;
        result = 2'b10;  // default: ternary 0

        case (opcode)
            4'd0: begin // NOP
                result = 2'b10;
                sr     = 3'sd0;
            end
            4'd1: begin // ADD: clamp sum to {-1,0,+1}
                sr     = sa + sb;
                result = encode_sum(sr);
            end
            4'd2: begin // SUB: clamp difference
                sr     = sa - sb;
                result = encode_sum(sr);
            end
            4'd3: begin // MUL: ternary sign-product LUT (R-SI-1: no `*`)
                result = ternary_mul(a, b);
                sr     = 3'sd0;
            end
            4'd4: begin // AND: Kleene min
                result = tri_min(a, b);
                sr     = 3'sd0;
            end
            4'd5: begin // OR: Kleene max
                result = tri_max(a, b);
                sr     = 3'sd0;
            end
            4'd6: begin // NOT: negate
                case (a)
                    2'b00:   result = 2'b01;   // +1 → -1
                    2'b01:   result = 2'b00;   // -1 → +1
                    default: result = 2'b10;   // 0  →  0
                endcase
                sr = 3'sd0;
            end
            4'd7: begin // BIND: VSA bind = ternary product (same as MUL)
                result = ternary_mul(a, b);
                sr     = 3'sd0;
            end
            4'd8: begin // BUNDLE: sign(a+b)
                result = ternary_bundle(a, b);
                sr     = 3'sd0;
            end
            default: begin
                valid  = 1'b0;
                result = 2'b10;
                sr     = 3'sd0;
            end
        endcase
    end

    assign decoder_ok = 1'b1;

    // Suppress unused warning on sr (used for ADD/SUB path only)
    wire _unused_sr = sr[2];

endmodule

`default_nettype wire
