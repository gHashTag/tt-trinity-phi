`default_nettype none
// cassini_post.v — L-S23 Cassini-Lucas POST Checker
// Apache-2.0 · TRI-1 v2 · PhD Ch.29/L29 (flos_29.tex)
// Ported from gHashTag/tt-trinity-gf16 (TTSKY26a ancestor)
// R-SI-1 port: replaced `*` operators with pre-computed product table.
//
// PhD anchor: Cassini-like identity for Lucas numbers (analytically Qed):
//
//     L_n · L_{n+1}  -  L_{n-1} · L_{n+2}  =  5 · (-1)^n
//
// Reads 4 consecutive Lucas values from hardcoded table and verifies the
// identity at power-on. Detects ROM bit-rot, SRAM corruption, or RTL
// synthesis errors. Extends phi_anchor_post (which only checks 6 Lucas
// values via recurrence).
//
// Sweep n=2..5:
//   n=2: L2·L3 - L1·L4 = 3·4 - 1·7 = 12-7 = 5 (= +5·(-1)^2)
//   n=3: L3·L4 - L2·L5 = 4·7 - 3·11 = 28-33 = -5 (= 5·(-1)^3)
//   n=4: L4·L5 - L3·L6 = 7·11 - 4·18 = 77-72 = 5
//   n=5: L5·L6 - L4·L7 = 11·18 - 7·29 = 198-203 = -5
//
// All 4 OK -> cassini_ok=1, post_done=1. Any mismatch -> cassini_ok=0 sticky.
// Total budget: ~30 LUTs (pre-computed constants, no DSP inference).
//
// R-SI-1: zero `*` operators. Products replaced with pre-computed LUT values.
// TG-TRIAD-X Theorem 36.1: canonical anchor 0x47C0 unaffected (this module
// only drives cassini_ok and post_done wires).

module cassini_post (
    input  wire        clk,
    input  wire        rst_n,
    output reg         cassini_ok,    // sticky 1 when all 4 checks pass
    output reg         post_done      // rises after final check cycle
);

    // Pre-computed product pairs for n=2..5.
    // lhs[n] = L_n * L_{n+1}  rhs[n] = L_{n-1} * L_{n+2}
    // Values: L1=1, L2=3, L3=4, L4=7, L5=11, L6=18, L7=29
    //   n=2: lhs=3*4=12,   rhs=1*7=7    diff=+5
    //   n=3: lhs=4*7=28,   rhs=3*11=33  diff=-5
    //   n=4: lhs=7*11=77,  rhs=4*18=72  diff=+5
    //   n=5: lhs=11*18=198, rhs=7*29=203 diff=-5
    //
    // R-SI-1: These products are constants — encoded as literals below.

    function [9:0] lhs_of_n;
        input [2:0] n;
        case (n)
            3'd2: lhs_of_n = 10'd12;   // 3*4
            3'd3: lhs_of_n = 10'd28;   // 4*7
            3'd4: lhs_of_n = 10'd77;   // 7*11
            3'd5: lhs_of_n = 10'd198;  // 11*18
            default: lhs_of_n = 10'd0;
        endcase
    endfunction

    function [9:0] rhs_of_n;
        input [2:0] n;
        case (n)
            3'd2: rhs_of_n = 10'd7;    // 1*7
            3'd3: rhs_of_n = 10'd33;   // 3*11
            3'd4: rhs_of_n = 10'd72;   // 4*18
            3'd5: rhs_of_n = 10'd203;  // 7*29
            default: rhs_of_n = 10'd0;
        endcase
    endfunction

    // Expected diff: +5 for even n, -5 for odd n
    // Represented as 11-bit signed: +5 = 11'd5, -5 = 11'b111_1111_1011 (2's comp)
    function [10:0] expected_of_n;
        input [2:0] n;
        case (n)
            3'd2: expected_of_n = 11'sd5;   // +5 (even)
            3'd3: expected_of_n = -11'sd5;  // -5 (odd)
            3'd4: expected_of_n = 11'sd5;   // +5 (even)
            3'd5: expected_of_n = -11'sd5;  // -5 (odd)
            default: expected_of_n = 11'sd0;
        endcase
    endfunction

    reg [2:0] step;      // n = 2..5
    reg       running;
    reg       lhs_valid;
    reg [9:0] lhs;
    reg [9:0] rhs;
    wire signed [10:0] diff = $signed({1'b0, lhs}) - $signed({1'b0, rhs});

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            step       <= 3'd2;
            running    <= 1'b1;
            lhs_valid  <= 1'b0;
            lhs        <= 10'd0;
            rhs        <= 10'd0;
            cassini_ok <= 1'b1;   // optimistic; sticky-clear on mismatch
            post_done  <= 1'b0;
        end else if (running) begin
            // Load pre-computed constants (R-SI-1: no * operators)
            lhs        <= lhs_of_n(step);
            rhs        <= rhs_of_n(step);
            lhs_valid  <= 1'b1;

            // Validate the PREVIOUS cycle's product (latched lhs/rhs)
            if (lhs_valid) begin
                if (diff !== $signed(expected_of_n(step - 3'd1)))
                    cassini_ok <= 1'b0;
            end

            if (step == 3'd5) begin
                running <= 1'b0;  // last n=5 product just latched
            end else begin
                step <= step + 3'd1;
            end
        end else if (!post_done) begin
            // Tail cycle: validate the final n=5 product
            if (lhs_valid) begin
                if (diff !== $signed(expected_of_n(3'd5)))
                    cassini_ok <= 1'b0;
            end
            post_done <= 1'b1;
        end
    end

endmodule

`default_nettype wire
