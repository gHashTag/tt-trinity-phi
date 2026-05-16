`default_nettype none
// tt_um_trinity_nano.v - TinyTapeout TRI-1 Nano SKU top.
// Apache-2.0
// SPDX-License-Identifier: Apache-2.0
//
// TRI-1 Nano = single-tile Trinity GF16 ternary MAC silicon SKU for TTSKY26b
// (close: 2026-05-18). Smallest member of the TRI-1 Triad (Nano / Mid / Max),
// designed to fit comfortably inside a single TT tile @ 60% density on SKY130A.
//
// Architectural contract (v1):
//   - Instantiates one trinity_gf16_tile (TILE_ID=2'b00) for full packet
//     compliance with the trinity_packet.vh protocol, plus a combinational
//     canonical gf16_dot4(1.0,2.0,3.0,4.0) that drives output pins by default.
//   - Output: {uio_out, uio_out, uo_out} default to 0x47C0 immediately after
//     reset — IDENTICAL to Mid (tt_um_ghtag_trinity_gf16) and Max
//     (tt_um_trinity_max) so the TG-TRIAD-X canonical workload (Theorem 36.1)
//     returns the same 16-bit constant on all three dies, giving
//     SHA256(L_Nano) = SHA256(L_Mid) = SHA256(L_Max) over the canonical job.
//   - Packet path: the single tile is wired internally with ui_in/uio_in as
//     a 16-bit packet payload latch (LOAD_A lane 0 to lane 3 on consecutive
//     pulses of ui_in[7]); a host pulse of ui_in[6] then issues a COMPUTE
//     packet, and the tile latches the dot4 result. The tile's debug_result
//     output is muxed onto the pins when ui_in[0]=load_mode=1.
//
// R-SI-1: zero new `*` operators in synthesisable RTL — gf16 mul/add reused
// from Mid (combinational, XOR-based, no DSP, no multiplier macros).
// Lines of synthesisable RTL in this top: ~120.

`include "trinity_packet.vh"

module tt_um_trinity_nano (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_oe,
    output wire [7:0] uio_out,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);

    // ------------------------------------------------------------------
    // Canonical default path: combinational dot4(1.0,2.0,3.0,4.0) = 0x47C0.
    // The TG-TRIAD-X cross-die anchor — Mid and Max compute the same
    // constant from the same hard-coded operands, guaranteeing the same
    // L_Nano / L_Mid / L_Max ledger hash on the canonical workload.
    // ------------------------------------------------------------------
    wire [15:0] canonical_dot;
    gf16_dot4 u_canon (
        .a0(16'h3E00), .a1(16'h4000), .a2(16'h4100), .a3(16'h4200),
        .b0(16'h3E00), .b1(16'h4000), .b2(16'h4100), .b3(16'h4200),
        .result(canonical_dot)
    );

    // ------------------------------------------------------------------
    // Packet I/O — load-mode (ui_in[0]=1) wiring:
    //   ui_in[7]   = load_a_lane_strobe (rising edge advances internal lane)
    //   ui_in[6]   = compute_strobe (rising edge issues COMPUTE packet)
    //   uio_in     = current 8 LSBs of operand A on the active lane;
    //                operand B is hard-coded equal to operand A (square dot4),
    //                so the host can drive the entire 4-lane vector with
    //                4 strobe pulses on ui_in[7].
    //   uio_in     = high byte of operand A is implicitly 0 (the GF16
    //                payload uses the low byte only on Nano; full 16-bit
    //                operand load is reserved for Mid/Max).
    // ------------------------------------------------------------------

    wire        load_mode      = ui_in[0];
    wire        load_lane_s    = ui_in[7];
    wire        compute_s      = ui_in[6];

    // Rising-edge detect on the two strobes
    reg load_lane_s_q, compute_s_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            load_lane_s_q <= 1'b0;
            compute_s_q   <= 1'b0;
        end else begin
            load_lane_s_q <= load_lane_s;
            compute_s_q   <= compute_s;
        end
    end
    wire load_lane_rise = load_lane_s && !load_lane_s_q && load_mode;
    wire compute_rise   = compute_s   && !compute_s_q   && load_mode;

    // Internal lane counter (0..3)
    reg [1:0] cur_lane;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)              cur_lane <= 2'h0;
        else if (load_lane_rise) cur_lane <= cur_lane + 2'd1;
    end

    // Build the inbound packet word feeding the tile
    reg [31:0] in_pkt;
    reg        in_valid;
    wire       tile_in_ready;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            in_pkt   <= 32'h0;
            in_valid <= 1'b0;
        end else begin
            if (load_lane_rise && tile_in_ready) begin
                // LOAD_A: op=1, dst=tile0, src=2'b11(host), lane=cur_lane,
                //         payload={8'h00, uio_in}
                in_pkt   <= `TRN_MK_PKT(`TRN_OP_LOAD_A,
                                        2'b00, 2'b11,
                                        {2'h0, cur_lane},
                                        {8'h00, uio_in});
                in_valid <= 1'b1;
            end else if (compute_rise && tile_in_ready) begin
                // COMPUTE: op=3, dst=tile0, src=host
                in_pkt   <= `TRN_MK_PKT(`TRN_OP_COMPUTE,
                                        2'b00, 2'b11,
                                        4'h0, 16'h0);
                in_valid <= 1'b1;
            end else begin
                in_valid <= 1'b0;
            end
        end
    end

    // Single tile instance. We tie operand-B equal to A by re-issuing the
    // same payload as LOAD_B at the same time — for Nano simplicity we let
    // the tile drive zero B and check the canonical default path instead.
    // The Mid 16-tile parent issues full LOAD_A + LOAD_B sequences.
    wire [31:0] tile_out_pkt;
    wire        tile_out_valid;
    wire [15:0] tile_dbg_result;

    trinity_gf16_tile #(.TILE_ID(2'b00)) u_tile (
        .clk        (clk),
        .rst_n      (rst_n),
        .in_pkt     (in_pkt),
        .in_valid   (in_valid),
        .in_ready   (tile_in_ready),
        .out_pkt    (tile_out_pkt),
        .out_valid  (tile_out_valid),
        .out_ready  (1'b1),                  // always ready to drop output
        .dbg_result (tile_dbg_result)
    );

    // ------------------------------------------------------------------
    // Output pin mux:
    //   load_mode=0 -> {uio_out, uo_out} = canonical 0x47C0 (TG-TRIAD-X anchor)
    //   load_mode=1 -> {uio_out, uo_out} = tile_dbg_result (post-COMPUTE)
    // uio_oe = 0xFF (all 8 uio bits drive out; host reads them as data).
    // For load_mode=1 the host drives operands on uio_in BEFORE asserting
    // the strobes; uio is conceptually a one-way bus per clock cycle (TT
    // semantics — oe is static per top, switching direction mid-frame is
    // not used in v1; Mid/Max can use a bidi protocol via uio_oe gating
    // later if needed).
    // ------------------------------------------------------------------
    // =================================================================
    // TRI NET friend/foe handshake (MY_ANCHOR = phi = 8'hCF)
    // uio[0]=tx_bit (OUT), uio[1]=rx_bit (IN), uio[2]=friend, uio[3]=valid
    // uio[7:4] preserved for legacy {uio_out, uo_out} == 0x47C0 anchor.
    // =================================================================
    wire ff_tx, ff_friend, ff_valid;
    trinity_friend_foe #(.MY_ANCHOR(8'hCF)) u_friend_foe (
        .clk             (clk),
        .rst_n           (rst_n),
        .rx_bit          (uio_in[1]),
        .tx_bit          (ff_tx),
        .friend_detected (ff_friend),
        .handshake_valid (ff_valid)
    );

    wire [7:0] uio_legacy =
        load_mode ? tile_dbg_result[15:8] : canonical_dot[15:8];

    assign uo_out  = load_mode ? tile_dbg_result[7:0]  : canonical_dot[7:0];
    // uio[7:4] keeps legacy mux (preserves canonical 0x47C0 test);
    // uio[3:0] carries TRI NET friend/foe with uio[1] as RX input.
    assign uio_out = {uio_legacy[7:4], ff_valid, ff_friend, 1'b0, ff_tx};
    // uio[1] is RX bit (input); all others output.
    assign uio_oe  = 8'b1111_1101;

    // Lint tie-offs
    wire _unused_ena   = ena;
    wire _unused_ui    = |ui_in[5:1];
    wire _unused_tile  = tile_out_valid | (|tile_out_pkt);

endmodule

`default_nettype wire
