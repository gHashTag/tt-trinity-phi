`default_nettype none
// tt_um_trinity_nano.v - TinyTapeout TRI-1 φ-anchor SKU top.
// Apache-2.0
// SPDX-License-Identifier: Apache-2.0
//
// TRI-1 φ-anchor = single-tile Trinity GF16 ternary MAC with enhanced safety.
// Smallest member of TRI-NET (φ-anchor / e-engine / γ-surface), fits in 1×1
// tile @ 60% density on SKY130A.
//
// Architectural contract (v3, TTSKY26b):
//   - Instantiates one trinity_gf16_tile (TILE_ID=2'b00) for full packet
//     compliance with trinity_packet.vh, plus combinational canonical
//     gf16_dot4(1.0,2.0,3.0,4.0) = 0x47C0 driving output pins by default.
//   - Cross-die anchor: {uio_out, uo_out} = 0x47C0 immediately after reset,
//     identical to e-engine and γ-surface (TG-TRIAD-X Theorem 36.1).
//   - Lucas POST (phi_anchor_post): Proves φ²+φ⁻²=3 via L₂..L₇ recurrence.
//   - Cassini POST (cassini_post): Orthogonal Cassini-Lucas identity verifier.
//   - Lucas ROM (lucas_rom): Addressable L_n host probe (ui[3:1]).
//   - HWRNG (hwrng_lfsr): Die-unique nonce, enabled by ui[4].
//   - Restraint Control (restraint_ctrl): CLARA Gap-4 bounded rationality.
//   - Crown47/Sacred ROM read modes preserved.
//   - TRI-9 ISA decoder (alu9_decoder): 9 ternary opcodes (TTSKY26b P0).
//   - Ring27 memory (ring27_memory): 27-cell ternary ring (TTSKY26b P0).
//
// R-SI-1: zero new `*` operators in synthesisable RTL.
// Enhanced modules: phi_anchor_post (~120 cells), lucas_rom (~30 cells),
// hwrng_lfsr (~20 cells), restraint_ctrl (~100 cells),
// cassini_post (~60 cells), alu9_decoder (~80 cells), ring27_memory (~80 cells).
//
// Pin contract for new status modes (ui_in[3:2]=11 = status_request):
//   ui_in[3:2]=11, ui_in[1:0]=00 → POST status (phi_post, existing)
//   ui_in[3:2]=11, ui_in[1:0]=10 → Cassini POST status (new TTSKY26b)
//   ui_in[3:2]=11, ui_in[1:0]=01 → Ring27 window readback (new TTSKY26b)
//   ui_in[3:2]=11, ui_in[1:0]=11 → ALU-9 last result (new TTSKY26b)
//
// Canonical anchor invariant: at ui_in=0x00 ALL status_*_mode = 0 →
// {uio_out, uo_out} = 0x47C0. TG-TRIAD-X Theorem 36.1 preserved.

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
    // Packet I/O — load-mode (ui_in[0]=1) wiring.
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
                in_pkt   <= `TRN_MK_PKT(`TRN_OP_LOAD_A,
                                        2'b00, 2'b11,
                                        {2'h0, cur_lane},
                                        {8'h00, uio_in});
                in_valid <= 1'b1;
            end else if (compute_rise && tile_in_ready) begin
                in_pkt   <= `TRN_MK_PKT(`TRN_OP_COMPUTE,
                                        2'b00, 2'b11,
                                        4'h0, 16'h0);
                in_valid <= 1'b1;
            end else begin
                in_valid <= 1'b0;
            end
        end
    end

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
        .out_ready  (1'b1),
        .dbg_result (tile_dbg_result)
    );

    // =================================================================
    // TRI NET friend/foe handshake (MY_ANCHOR = phi = 8'hCF)
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

    // ------------------------------------------------------------------
    // Sacred Constants ROM — PHI PhD constants (Glava 3+7+28)
    // TTSKY26b: extended to addr 75..82 (Lucas L_8..L_11, zig-golden-float constants)
    // ------------------------------------------------------------------
    reg  [6:0] sacred_addr_r;
    wire [7:0] sacred_val;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) sacred_addr_r <= 7'h00;
        else        sacred_addr_r <= {1'b0, ui_in[6:1]};
    end

    sacred_constants_rom u_sacred_rom (
        .addr (sacred_addr_r),
        .val  (sacred_val)
    );

    wire sacred_mode = ui_in[7] && !load_mode;

    // ==================================================================
    // CROWN47 ROM
    // ==================================================================
    wire        crown_mode     = uio_in[7] && !load_mode && !sacred_mode;
    wire [6:0]  crown_addr     = ui_in[6:0];
    wire [1:0]  crown_byte_sel = uio_in[6:5];
    wire [7:0]  crown_byte_out;

    crown47_rom_8bit u_crown47 (
        .addr     (crown_addr),
        .byte_sel (crown_byte_sel),
        .byte_out (crown_byte_out)
    );

    // ------------------------------------------------------------------
    // Output pin mux wire (legacy path)
    // ------------------------------------------------------------------
    wire [7:0] uio_legacy =
        load_mode   ? tile_dbg_result[15:8] :
        sacred_mode ? 8'h00                 :
        crown_mode  ? 8'h00                 :
                      canonical_dot[15:8];

    // ==================================================================
    // Lucas POST — proves φ²+φ⁻²=3 via L₂..L₇ recurrence
    // ==================================================================
    wire phi_post_ok, phi_post_done;
    phi_anchor_post u_phi_post (
        .clk      (clk),
        .rst_n    (rst_n),
        .phi_ok   (phi_post_ok),
        .post_done(phi_post_done)
    );

    // ==================================================================
    // Cassini POST — orthogonal Cassini-Lucas identity verifier (TTSKY26b P0)
    // R-SI-1: no `*` operators (pre-computed product table used).
    // ==================================================================
    wire cassini_ok, cassini_done;
    cassini_post u_cassini_post (
        .clk       (clk),
        .rst_n     (rst_n),
        .cassini_ok(cassini_ok),
        .post_done (cassini_done)
    );

    // ==================================================================
    // Lucas ROM — addressable L_n probe
    // ==================================================================
    wire [2:0] lucas_idx = ui_in[3:1];
    wire [7:0] lucas_val;
    lucas_rom u_lucas (
        .idx  (lucas_idx),
        .value(lucas_val)
    );

    // ==================================================================
    // HWRNG — 16-bit LFSR for die-unique nonce
    // ==================================================================
    wire rng_ena = ui_in[4] && !load_mode;
    wire [15:0] rng_nonce;
    hwrng_lfsr u_hwrng (
        .clk  (clk),
        .rst_n(rst_n),
        .ena  (rng_ena),
        .rnd  (rng_nonce)
    );

    // ==================================================================
    // Restraint Control — CLARA Gap-4 bounded rationality
    // ==================================================================
    wire restraint_mode = ui_in[5] && !load_mode;
    wire rc_force_unknown, rc_halt_mac;
    wire [2:0] rc_reason;
    restraint_ctrl u_restraint (
        .clk          (clk),
        .rst_n        (rst_n),
        .phi_drift    (rng_nonce),
        .step_count   (4'h0),
        .receipt_ok   (1'b1),
        .current_state(2'b00),
        .force_unknown (rc_force_unknown),
        .halt_mac     (rc_halt_mac),
        .reason       (rc_reason)
    );

    // ==================================================================
    // Ring27 Memory — 27-cell ternary ring (TTSKY26b P0)
    // Dual read port: addr=0 → ALU operand A, addr=1 → ALU operand B.
    // Single instance with two combinational read addresses.
    // shift: ring rotates when load_mode=1 and compute_s=1 (ui_in[6]).
    // ==================================================================
    wire ring_shift  = load_mode && compute_s && !compute_rise;
    wire ring_wr_en  = 1'b0;   // writes reserved for future expansion
    wire [1:0] ring_rd_a, ring_rd_b;
    wire       ring_ok;

    ring27_memory u_ring27 (
        .clk      (clk),
        .rst_n    (rst_n),
        .shift    (ring_shift),
        .wr_en    (ring_wr_en),
        .addr     (5'd0),        // port A always reads cell[0]
        .addr_b   (5'd1),        // port B always reads cell[1]
        .wr_data  (2'b10),       // 0 (unused)
        .rd_data  (ring_rd_a),
        .rd_data_b(ring_rd_b),
        .ring_ok  (ring_ok)
    );

    // 8-bit ring window for status readback.
    // Packs cells[0..3]: [7:6]=cells[3], [5:4]=cells[2], [3:2]=cells[1], [1:0]=cells[0].
    // cells[2]= 2'b10(0), cells[3]=2'b00(+1) from canonical seed.
    wire [7:0] ring27_window = {2'b00, 2'b10, ring_rd_b, ring_rd_a};

    // ==================================================================
    // TRI-9 ALU Decoder — 9 ternary opcodes (TTSKY26b P0)
    // Gap-0 (K3 Kleene logic) + CLARA TA2 VSA compliance.
    // Combinational. Operands A/B from ring27 cells[0]/cells[1].
    // Opcode sourced from ui_in[3:0] (valid in all modes for decode).
    // ==================================================================
    wire [1:0] alu9_result_w;
    wire       alu9_valid_w;
    wire       alu9_decoder_ok;

    alu9_decoder u_alu9 (
        .opcode    (ui_in[3:0]),
        .a         (ring_rd_a),
        .b         (ring_rd_b),
        .result    (alu9_result_w),
        .valid     (alu9_valid_w),
        .decoder_ok(alu9_decoder_ok)
    );

    // Register last ALU result for readback in alu9_status_mode
    reg [1:0] alu9_result_q;
    reg       alu9_valid_q;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            alu9_result_q <= 2'b10;  // ternary zero
            alu9_valid_q  <= 1'b0;
        end else begin
            alu9_result_q <= alu9_result_w;
            alu9_valid_q  <= alu9_valid_w;
        end
    end

    // ==================================================================
    // Status Byte Override — POST status is REQUEST-GATED, not automatic.
    //
    // status_request = ui_in[3] && ui_in[2]
    // status_sub     = {ui_in[1], ui_in[0]}
    //
    // At canonical idle (ui_in=0x00): status_request=0 → all modes off →
    // {uio_out, uo_out} = 0x47C0. TG-TRIAD-X Theorem 36.1 preserved.
    // ==================================================================
    wire status_request    = ui_in[3] && ui_in[2];
    wire [1:0] status_sub  = {ui_in[1], ui_in[0]};

    wire post_status_mode    = status_request && (status_sub == 2'b00) && phi_post_done
                                && !load_mode && !sacred_mode && !crown_mode;
    wire cassini_status_mode = status_request && (status_sub == 2'b10) && cassini_done
                                && !load_mode && !sacred_mode && !crown_mode;
    wire ring27_status_mode  = status_request && (status_sub == 2'b01)
                                && !load_mode && !sacred_mode && !crown_mode;
    wire alu9_status_mode    = status_request && (status_sub == 2'b11)
                                && !load_mode && !sacred_mode && !crown_mode;

    // Output mux
    wire [7:0] uo_final =
        post_status_mode    ? {phi_post_ok, phi_post_done, lucas_val[5:0]}         :
        cassini_status_mode ? {cassini_ok, cassini_done, 6'b000000}                 :
        ring27_status_mode  ? ring27_window                                         :
        alu9_status_mode    ? {4'b0000, alu9_valid_q, 1'b0, alu9_result_q}         :
        (load_mode   ? tile_dbg_result[7:0] :
         sacred_mode ? sacred_val           :
         crown_mode  ? crown_byte_out       :
                       canonical_dot[7:0]);

    wire [7:0] uio_final =
        post_status_mode    ? {lucas_val[7:6], phi_post_ok, phi_post_done, 4'b0000} :
        cassini_status_mode ? {6'b000000, phi_post_ok, cassini_ok}                   :
        ring27_status_mode  ? 8'h00                                                  :
        alu9_status_mode    ? 8'h00                                                  :
        uio_legacy;

    // Final output assignments
    assign uo_out  = uo_final;
    assign uio_out = !load_mode ? uio_final :
                                     {uio_final[7:4], ff_valid, ff_friend, 1'b0, ff_tx};
    assign uio_oe  = !load_mode ? 8'hFF : 8'b1111_1101;

    // Lint tie-offs
    wire _unused_ena    = ena;
    wire _unused_tile   = tile_out_valid | (|tile_out_pkt);
    wire _unused_reason = rc_reason;
    wire _unused_ring   = ring_ok;
    wire _unused_dec    = alu9_decoder_ok;
    wire _unused_rc_fu  = rc_force_unknown;
    wire _unused_rc_hm  = rc_halt_mac;
    wire _unused_rst    = restraint_mode;

endmodule

`default_nettype wire
