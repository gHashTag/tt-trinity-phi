// SPDX-License-Identifier: Apache-2.0
// tt_um_trinity_nano.v - Tiny Tapeout SKY26d, 1x1 tile: pin-loadable GF16 DOT4.
// Contract: specs/numeric/gf16_dot4_sky26d.t27 (issue #100). Names are kept from the
// original project (author: Dmitrii Vasilev); this top is rewritten by Dmitrii Fedorov.
//
// r = DOT4(A0..A3, B0..B3), GF16 = S1 E6 M9, bias 31:
//   p_k = MUL(A_k, B_k); acc = p_0; acc = ADD(acc, p_1); acc = ADD(acc, p_2);
//   r = ADD(acc, p_3). Each operation is rounded to GF16 at once. One shared MUL and
//   one shared ADD, sequenced by a counter, exactly 8 enabled clocks from GO to DONE.
//
// Pins (uio is INPUT ONLY, uio_oe = 0x00, uio_out = 0x00 in every state):
//   ui_in[7:0]    data byte for a write; in read select 5 only ui_in[3:0] is used
//   uio_in[0]     WR    rising edge writes ui_in into cell[PTR], PTR = PTR + 1 (mod 16)
//   uio_in[1]     GO    rising edge starts DOT4 (PTR is reset to 0)
//   uio_in[4:2]   RSEL  0 STATUS {PTR[3:0], 0, ERR, DONE, BUSY}
//                       1 RES_LO, 2 RES_HI (0x00 while BUSY)
//                       3 SIG_LO 0xC0, 4 SIG_HI 0x47 (constant signature, not a result)
//                       5 READBACK cell[ui_in[3:0]], 6 and 7 read 0x00
//   uio_in[7:5]   reserved, ignored
//   ena = 0 freezes all state including the edge history; rst_n is asynchronous, active low.
// Memory: 16 byte cells, little endian words, A0..A3 at 0..7, B0..B3 at 8..15, reset to 0.
// WR and GO rising in the same idle clock: WR is accepted, GO is ignored, no flag.
// While BUSY, WR and GO rising edges are ignored and set the sticky ERR (cleared by an
// accepted GO and by reset). An accepted WR clears DONE and leaves the result register.
//
// Structure of the memory (same observable behaviour as before, explicit logic):
//   * 16 separate byte registers, each with its OWN write enable from a two-level decode of
//     PTR (4 + 4 one-hot lines, then one AND per byte). Every cell loads ui_in directly; there
//     is no 128-bit indexed write.
//   * operands: two explicit 4:1 selections (lane k selects A_k and B_k) written as two levels of
//     2:1 multiplexers on constant slices;
//   * readback: a hierarchical 16:1 byte multiplexer (4:1 inside each group of four cells, then
//     4:1 over the groups), each 4:1 written as two levels of 2:1 multiplexers, on constant
//     slices. Readback returns the stored raw byte at any
//     time, also while BUSY. No latch, no clock gating, no undriven or X value.
`default_nettype none
module tt_um_trinity_nano (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

    reg [3:0]   ptr;
    reg [2:0]   step;
    reg         busy;
    reg         done;
    reg         err;
    reg         wr_q;
    reg         go_q;
    reg [15:0]  prod;
    reg [15:0]  acc;

    wire wr_rise = uio_in[0] & ~wr_q;
    wire go_rise = uio_in[1] & ~go_q;

    // ---------------------------------------------------------------- memory cells
    wire        wr_accept = ena & ~busy & wr_rise;      // an accepted write (WR wins over GO)
    wire [3:0]  dec_lo = {ptr[1:0] == 2'd3, ptr[1:0] == 2'd2, ptr[1:0] == 2'd1, ptr[1:0] == 2'd0};
    wire [3:0]  dec_hi = {ptr[3:2] == 2'd3, ptr[3:2] == 2'd2, ptr[3:2] == 2'd1, ptr[3:2] == 2'd0};
    wire [127:0] mem_flat;                              // cell g occupies bits [8g+7:8g]

    genvar g;
    generate
        for (g = 0; g < 16; g = g + 1) begin : g_cell
            localparam integer HI = g >> 2;
            localparam integer LO = g & 3;
            wire       we = wr_accept & dec_hi[HI] & dec_lo[LO];
            reg  [7:0] byte_q;
            always @(posedge clk or negedge rst_n) begin
                if (!rst_n)  byte_q <= 8'h00;
                else if (we) byte_q <= ui_in;
            end
            assign mem_flat[(g << 3) +: 8] = byte_q;
        end
    endgenerate

    // ---------------------------------------------------------------- operand select
    wire [1:0]  lane = step[2:1];
    // two levels of 2:1 multiplexers (lane[0] first, then lane[1]) on constant slices; the same
    // function as a 4:1 case on lane, written as an explicit balanced binary tree
    wire [15:0] opa_mux = lane[1] ? (lane[0] ? mem_flat[63:48]   : mem_flat[47:32])
                                  : (lane[0] ? mem_flat[31:16]   : mem_flat[15:0]);
    wire [15:0] opb_mux = lane[1] ? (lane[0] ? mem_flat[127:112] : mem_flat[111:96])
                                  : (lane[0] ? mem_flat[95:80]   : mem_flat[79:64]);
    wire [15:0] opa = opa_mux;
    wire [15:0] opb = opb_mux;

    wire [15:0] mul_y;
    wire [15:0] add_y;
    gf16_v2_mul u_mul (.a(opa), .b(opb), .result(mul_y));
    gf16_v2_add u_add (.a(acc), .b(prod), .result(add_y));

    // ---------------------------------------------------------------- control
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ptr  <= 4'd0;
            step <= 3'd0;
            busy <= 1'b0;
            done <= 1'b0;
            err  <= 1'b0;
            wr_q <= 1'b0;
            go_q <= 1'b0;
            prod <= 16'd0;
            acc  <= 16'd0;
        end else if (ena) begin
            wr_q <= uio_in[0];
            go_q <= uio_in[1];
            if (busy) begin
                if (wr_rise | go_rise) err <= 1'b1;
                step <= step + 3'd1;
                case (step)
                    3'd0, 3'd2, 3'd4, 3'd6: prod <= mul_y;
                    3'd1:                   acc  <= prod;
                    default:                acc  <= add_y;
                endcase
                if (step == 3'd7) begin
                    busy <= 1'b0;
                    done <= 1'b1;
                end
            end else if (wr_rise) begin
                ptr  <= ptr + 4'd1;
                done <= 1'b0;
            end else if (go_rise) begin
                ptr  <= 4'd0;
                done <= 1'b0;
                err  <= 1'b0;
                busy <= 1'b1;
                step <= 3'd0;
            end
        end
    end

    // ---------------------------------------------------------------- read mux (uo_out)
    wire [7:0] status = {ptr, 1'b0, err, done, busy};

    // hierarchical 16:1 readback as two-level 2:1 trees: inside each group of four cells ui_in[1:0]
    // selects (ui_in[0] first, then ui_in[1]), then ui_in[3:2] selects the group the same way. Group g
    // holds cells 4g..4g+3; the byte of cell c is mem_flat[8c+7:8c]. Always a defined stored byte.
    wire [7:0] rb0 = ui_in[1] ? (ui_in[0] ? mem_flat[31:24]   : mem_flat[23:16])
                              : (ui_in[0] ? mem_flat[15:8]    : mem_flat[7:0]);
    wire [7:0] rb1 = ui_in[1] ? (ui_in[0] ? mem_flat[63:56]   : mem_flat[55:48])
                              : (ui_in[0] ? mem_flat[47:40]   : mem_flat[39:32]);
    wire [7:0] rb2 = ui_in[1] ? (ui_in[0] ? mem_flat[95:88]   : mem_flat[87:80])
                              : (ui_in[0] ? mem_flat[79:72]   : mem_flat[71:64]);
    wire [7:0] rb3 = ui_in[1] ? (ui_in[0] ? mem_flat[127:120] : mem_flat[119:112])
                              : (ui_in[0] ? mem_flat[111:104] : mem_flat[103:96]);
    wire [7:0] rb  = ui_in[3] ? (ui_in[2] ? rb3 : rb2) : (ui_in[2] ? rb1 : rb0);

    reg  [7:0] rd;
    always @* begin
        case (uio_in[4:2])
            3'd0:    rd = status;
            3'd1:    rd = busy ? 8'h00 : acc[7:0];
            3'd2:    rd = busy ? 8'h00 : acc[15:8];
            3'd3:    rd = 8'hC0;
            3'd4:    rd = 8'h47;
            3'd5:    rd = rb;
            default: rd = 8'h00;
        endcase
    end

    assign uo_out  = rd;
    assign uio_out = 8'h00;
    assign uio_oe  = 8'h00;

    wire _unused = &{1'b0, uio_in[7:5]};

endmodule
`default_nettype wire
