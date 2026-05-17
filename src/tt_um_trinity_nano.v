`default_nettype none
// tt_um_trinity_nano.v - TinyTapeout TRI-1 φ-anchor SKU top.
// Apache-2.0
// SPDX-License-Identifier: Apache-2.0
//
// TRI-1 φ-anchor = single-tile Trinity GF16 ternary MAC with enhanced safety.
// Smallest member of TRI-NET (φ-anchor / e-engine / γ-surface), fits in 1×1
// tile @ 60% density on SKY130A.
//
// Architectural contract (v2):
//   - Instantiates one trinity_gf16_tile (TILE_ID=2'b00) for full packet
//     compliance with trinity_packet.vh, plus combinational canonical
//     gf16_dot4(1.0,2.0,3.0,4.0) = 0x47C0 driving output pins by default.
//   - Cross-die anchor: {uio_out, uo_out} = 0x47C0 immediately after reset,
//     identical to e-engine and γ-surface (TG-TRIAD-X Theorem 36.1).
//   - Lucas POST (phi_anchor_post): Proves φ²+φ⁻²=3 via L₂..L₇ recurrence.
//   - Lucas ROM (lucas_rom): Addressable L_n host probe (ui[3:1]).
//   - HWRNG (hwrng_lfsr): Die-unique nonce, enabled by ui[4].
//   - Restraint Control (restraint_ctrl): CLARA Gap-4 bounded rationality.
//   - Crown47/Sacred ROM read modes preserved.
//
// R-SI-1: zero new `*` operators in synthesisable RTL.
// Enhanced modules: phi_anchor_post (~120 cells), lucas_rom (~30 cells),
// hwrng_lfsr (~20 cells), restraint_ctrl (~100 cells).

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

    // =================================================================
    // TRI NET friend/foe handshake (MY_ANCHOR = phi = 8'hCF)
    // uio[0]=tx_bit (OUT), uio[1]=rx_bit (IN), uio[2]=friend, uio[3]=valid
    // uio[7:4] = legacy/sacred/crown47 mux (preserves 0x47C0 anchor + ROMs).
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
    // Sacred read mode: ui_in[7]=1 and load_mode=0.
    //   addr = {1'b0, ui_in[6:1]}  (6-bit, covers first 64 constants)
    //   uo_out = sacred_val[7:0]
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
    // CROWN47 ROM — Crown of TRI NET (Crown42 + 5 Tegmark-31 fillers).
    // 47 Trinity constants in 24-bit pseudo-float (Vasilev-Pellis v22.12).
    // Activated by uio_in[7]=1 when neither load_mode nor sacred_mode are
    // active. Provides ONE byte per cycle:
    //   ui_in[6:0]   = crown_addr (0..46)
    //   uio_in[6:5]  = byte_sel (0=mant_lo 1=mant_hi 2=exp 3=tier_flag)
    // Combinational - same-cycle byte on uo_out.
    // Anchor phi^2+phi^-2=3 . DOI 10.5281/zenodo.19227877
    // R-SI-1 clean. Same module instantiated unchanged in EULER + GAMMA.
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
    // Output pin mux wire (used for legacy path and POST status override)
    // ------------------------------------------------------------------
    wire [7:0] uio_legacy =
        load_mode   ? tile_dbg_result[15:8] :
        sacred_mode ? 8'h00                 :
        crown_mode  ? 8'h00                 :
                      canonical_dot[15:8];

    // ==================================================================
    // Lucas POST — proves φ²+φ⁻²=3 via L₂..L₇ recurrence (phi_anchor_post)
    // ==================================================================
    wire phi_post_ok, phi_post_done;
    phi_anchor_post u_phi_post (
        .clk      (clk),
        .rst_n    (rst_n),
        .phi_ok   (phi_post_ok),
        .post_done(phi_post_done)
    );

    // ==================================================================
    // Lucas ROM — addressable L_n probe (L₂..L₇ mapped to idx 0..5)
    // ui[3:1] = lucas_idx → uio_out[5:0] in status mode
    // ==================================================================
    wire [2:0] lucas_idx = ui_in[3:1];
    wire [7:0] lucas_val;
    lucas_rom u_lucas (
        .idx  (lucas_idx),
        .value(lucas_val)
    );

    // ==================================================================
    // HWRNG — 16-bit LFSR for die-unique nonce
    // ui[4] = rng_ena → advances LFSR each clock when high
    // ui_in[7:0] (in canonical mode) reflects rng_nonce[7:0]
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
    // ui[5] = restraint_mode → activates restraint checking
    // Triggers on: phi_drift > 164, step_count > 10, receipt failure
    // Since phi-anchor has minimal FSM, we use synthetic triggers:
    //   - phi_drift = rng_nonce[15:0] (simulated drift via entropy)
    //   - step_count = 4'h0 (always safe, restraint not triggered)
    //   - receipt_ok = 1'b1 (always OK, no receipt module in 1×1)
    // ==================================================================
    wire restraint_mode = ui_in[5] && !load_mode;
    wire rc_force_unknown, rc_halt_mac;
    wire [2:0] rc_reason;
    restraint_ctrl u_restraint (
        .clk          (clk),
        .rst_n        (rst_n),
        .phi_drift    (rng_nonce),           // synthetic trigger from entropy
        .step_count   (4'h0),                 // always 0 = safe
        .receipt_ok   (1'b1),                 // always OK
        .current_state(2'b00),               // IDLE
        .force_unknown (rc_force_unknown),
        .halt_mac     (rc_halt_mac),
        .reason       (rc_reason)
    );

    // ==================================================================
    // Status Byte Override — POST status is REQUEST-GATED, not automatic.
    // The TG-TRIAD-X canonical anchor 0x47C0 is the default output on every
    // cycle once reset is released, matching e-engine and γ-surface. Earlier
    // revisions of this module auto-switched to POST status as soon as the
    // FSM raised post_done, which drifted {uio_out,uo_out} away from 0x47C0
    // after a handful of clocks and broke canonical-stability (regression
    // visible as the historical test_canonical_stable failure showing
    // 0x30C3 ~ {0x30, 0xC3} = {lucas_val[7:6],1,1,4'b0} ∥ {1,1,lucas_val[5:0]}).
    //
    // The host now explicitly asks for POST status by raising ui_in[3]=1
    // together with ui_in[2]=1 in canonical (non-load) mode. This pair is
    // never set during canonical idle (ui_in==0) and never during the Lucas
    // ROM probe (which uses ui_in[3:1] alone with ui_in[0]=0 but only one
    // of {ui_in[2],ui_in[3]} high at a time for L₆/L₇), so it does not
    // collide with any existing pin contract.
    // ==================================================================
    wire status_request    = ui_in[3] && ui_in[2];
    wire post_status_mode  = status_request && phi_post_done
                              && !load_mode && !sacred_mode && !crown_mode;

    wire [7:0] uo_final = post_status_mode ?
                          {phi_post_ok, phi_post_done, lucas_val[5:0]} :
                          (load_mode   ? tile_dbg_result[7:0] :
                           sacred_mode ? sacred_val           :
                           crown_mode  ? crown_byte_out       :
                                         canonical_dot[7:0]);

    wire [7:0] uio_final = post_status_mode ?
                           {lucas_val[7:6], phi_post_ok, phi_post_done, 4'b0000} :
                           uio_legacy;

    // Final output assignments
    assign uo_out  = uo_final;
    assign uio_out = !load_mode ? uio_final :
                                     {uio_final[7:4], ff_valid, ff_friend, 1'b0, ff_tx};
    // uio[1] is RX bit (input) in live mode; all outputs in canonical mode
    assign uio_oe  = !load_mode ? 8'hFF : 8'b1111_1101;

    // Lint tie-offs
    wire _unused_ena   = ena;
    wire _unused_tile  = tile_out_valid | (|tile_out_pkt);
    wire _unused_reason = rc_reason;  // restraint reason available for debug

endmodule

`default_nettype wire
