`default_nettype none
// ring27_memory.v — 27-cell circular ternary memory (3³ sacred constant)
// Apache-2.0
// Ported from gHashTag/tt-trinity-gf16 (TTSKY26a ancestor)
// TTSKY26b: extended with second read port (addr_b / rd_data_b) for
//           dual-operand ALU feed without extra flip-flop cost.
// R-SI-1 port: synchronous reset pattern aligned with tt_um_trinity_nano style.
// Reset unrolled (no for-loop) for better Yosys compatibility.
//
// PhD anchor: CANON_DE_ZIGFICATION / t27 RING spec. 27 = 3³.
// Each cell holds 2-bit ternary value (00=+1, 01=-1, 10/11=0).
// Dual read port (combinational) + single write port.
// On every clock with shift=1, the ring rotates by one position —
// a low-cost associative-memory primitive for VSA cleanup operations.
//
// Canonical seed on reset: alternating +1, -1, 0 (first 27 trits of
// the Trinity canonical frame).
//
// R-SI-1: zero `*` operators.
// TG-TRIAD-X: no interaction with canonical_anchor_reg — purely internal.

module ring27_memory (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        shift,      // rotate ring left by one position
    input  wire        wr_en,
    input  wire [4:0]  addr,       // read/write addr port A (0..26)
    input  wire [4:0]  addr_b,     // read addr port B (0..26, combinational)
    input  wire [1:0]  wr_data,
    output wire [1:0]  rd_data,    // read data port A (combinational)
    output wire [1:0]  rd_data_b,  // read data port B (combinational)
    output wire        ring_ok
);

    // 27 × 2-bit ternary cells
    reg [1:0] cells [0:26];

    // Read ports: combinational, return 2'b10 (=0) for out-of-range addr
    assign rd_data   = (addr   <= 5'd26) ? cells[addr]   : 2'b10;
    assign rd_data_b = (addr_b <= 5'd26) ? cells[addr_b] : 2'b10;

    // Write + rotate (synchronous reset)
    always @(posedge clk) begin
        if (!rst_n) begin
            // Canonical seed: i%3==0 → +1 (00), i%3==1 → -1 (01), i%3==2 → 0 (10)
            // Unrolled for Yosys compatibility (no for-loop in always block)
            cells[0]  <= 2'b00; cells[1]  <= 2'b01; cells[2]  <= 2'b10;
            cells[3]  <= 2'b00; cells[4]  <= 2'b01; cells[5]  <= 2'b10;
            cells[6]  <= 2'b00; cells[7]  <= 2'b01; cells[8]  <= 2'b10;
            cells[9]  <= 2'b00; cells[10] <= 2'b01; cells[11] <= 2'b10;
            cells[12] <= 2'b00; cells[13] <= 2'b01; cells[14] <= 2'b10;
            cells[15] <= 2'b00; cells[16] <= 2'b01; cells[17] <= 2'b10;
            cells[18] <= 2'b00; cells[19] <= 2'b01; cells[20] <= 2'b10;
            cells[21] <= 2'b00; cells[22] <= 2'b01; cells[23] <= 2'b10;
            cells[24] <= 2'b00; cells[25] <= 2'b01; cells[26] <= 2'b10;
        end else begin
            if (wr_en && addr <= 5'd26)
                cells[addr] <= wr_data;
            if (shift) begin
                // Rotate left by one: cells[0]←cells[26], cells[i]←cells[i-1]
                cells[0]  <= cells[26];
                cells[1]  <= cells[0];
                cells[2]  <= cells[1];
                cells[3]  <= cells[2];
                cells[4]  <= cells[3];
                cells[5]  <= cells[4];
                cells[6]  <= cells[5];
                cells[7]  <= cells[6];
                cells[8]  <= cells[7];
                cells[9]  <= cells[8];
                cells[10] <= cells[9];
                cells[11] <= cells[10];
                cells[12] <= cells[11];
                cells[13] <= cells[12];
                cells[14] <= cells[13];
                cells[15] <= cells[14];
                cells[16] <= cells[15];
                cells[17] <= cells[16];
                cells[18] <= cells[17];
                cells[19] <= cells[18];
                cells[20] <= cells[19];
                cells[21] <= cells[20];
                cells[22] <= cells[21];
                cells[23] <= cells[22];
                cells[24] <= cells[23];
                cells[25] <= cells[24];
                cells[26] <= cells[25];
            end
        end
    end

    assign ring_ok = 1'b1;

endmodule

`default_nettype wire
