`default_nettype none
// trinity_gf16_tile.v - addressable GF16 dot4 tile wrapping the existing combinational gf16_dot4.
// Apache-2.0
//
// Packet-driven interface:
//   - Accepts LOAD_A / LOAD_B packets to fill 4 operand lanes (lane 0..3).
//   - Accepts LOAD_JOB / LOAD_NONCE packets to set persisted (job_id_q, nonce_q)
//     used for deterministic on-die receipt emission (G4 — DePIN).
//   - On COMPUTE packet, latches result of gf16_dot4 into result register.
//   - On READ_RES packet, drives one outgoing RESULT packet on out_valid; the
//     cycle the host hands the RESULT off (`out_valid && out_ready`) the tile
//     re-asserts out_valid with the paired RECEIPT packet carrying
//       (tile_id, op_code=COMPUTE, checksum=(job_id_q ^ result_q[7:0]) & 0xFF,
//        job_id_lo=job_id_q).
//
// The compute is combinational (existing dot4), but the tile latches inputs and result, so
// the tile behaves as a real synchronous packet-addressable compute element inside the mesh.
//
// R-SI-1 (silicon constraint): no `*` introduced. Checksum is pure XOR-fold.

`include "trinity_packet.vh"

module trinity_gf16_tile #(
    parameter [1:0] TILE_ID = 2'b00
) (
    input  wire                    clk,
    input  wire                    rst_n,

    // Inbound packet (from router)
    input  wire [`TRN_PKT_W-1:0]   in_pkt,
    input  wire                    in_valid,
    output wire                    in_ready,

    // Outbound packet (to router) - RESULT then RECEIPT
    output reg  [`TRN_PKT_W-1:0]   out_pkt,
    output reg                     out_valid,
    input  wire                    out_ready,

    // Debug visibility
    output wire [15:0]             dbg_result
);

    // Operand registers
    reg [15:0] a0, a1, a2, a3;
    reg [15:0] b0, b1, b2, b3;
    reg [15:0] result_q;
    reg        result_valid;

    // DePIN receipt registers
    reg [7:0]  job_id_q;
    reg [7:0]  nonce_q;
    reg [1:0]  rcpt_dst;          // remembered host src so the RECEIPT goes back to the host
    reg        pending_receipt;   // set after RESULT handshake; cleared after RECEIPT handshake

    // Combinational dot4 over current latched operands
    wire [15:0] dot_out;
    gf16_dot4 u_dot (
        .a0(a0), .a1(a1), .a2(a2), .a3(a3),
        .b0(b0), .b1(b1), .b2(b2), .b3(b3),
        .result(dot_out)
    );

    // Accept any packet addressed to us when out FIFO slot is free
    assign in_ready = !out_valid || out_ready;

    wire pkt_for_me = (`TRN_PKT_DST(in_pkt) == TILE_ID);
    wire [3:0] op   = `TRN_PKT_OP(in_pkt);
    wire [3:0] lane = `TRN_PKT_LANE(in_pkt);
    wire [15:0] pl  = `TRN_PKT_PAYLOAD(in_pkt);

    // R-SI-1 honest checksum: 8-bit XOR-fold. Matches Python
    // tools/receipt_verifier/tri_receipt_verifier.compute_checksum() byte-for-byte.
    wire [7:0] rcpt_checksum_w = job_id_q ^ result_q[7:0];

    assign dbg_result = result_q;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            a0 <= 16'h0; a1 <= 16'h0; a2 <= 16'h0; a3 <= 16'h0;
            b0 <= 16'h0; b1 <= 16'h0; b2 <= 16'h0; b3 <= 16'h0;
            result_q <= 16'h0;
            result_valid <= 1'b0;
            job_id_q  <= 8'h00;
            nonce_q   <= 8'h00;
            rcpt_dst  <= 2'h0;
            pending_receipt <= 1'b0;
            out_pkt   <= {`TRN_PKT_W{1'b0}};
            out_valid <= 1'b0;
        end else begin
            // Outbound handshake: clear, then re-arm with RECEIPT if pending.
            if (out_valid && out_ready) begin
                if (pending_receipt) begin
                    // We just handed RESULT to the host; re-fire with the paired RECEIPT.
                    out_pkt   <= `TRN_MK_RCPT(rcpt_dst,
                                              TILE_ID,
                                              `TRN_OP_COMPUTE,
                                              job_id_q,
                                              rcpt_checksum_w);
                    out_valid <= 1'b1;
                    pending_receipt <= 1'b0;
                end else begin
                    // RECEIPT (or any other final packet) handed off.
                    out_valid <= 1'b0;
                end
            end

            // Inbound handling. Note: we still accept LOAD_*/COMPUTE packets while
            // out_valid is high if in_ready latched them; pkt_for_me is the gate.
            if (in_valid && in_ready && pkt_for_me) begin
                case (op)
                    `TRN_OP_LOAD_A: begin
                        case (lane[1:0])
                            2'd0: a0 <= pl;
                            2'd1: a1 <= pl;
                            2'd2: a2 <= pl;
                            2'd3: a3 <= pl;
                        endcase
                    end
                    `TRN_OP_LOAD_B: begin
                        case (lane[1:0])
                            2'd0: b0 <= pl;
                            2'd1: b1 <= pl;
                            2'd2: b2 <= pl;
                            2'd3: b3 <= pl;
                        endcase
                    end
                    `TRN_OP_LOAD_JOB: begin
                        job_id_q <= pl[7:0];
                    end
                    `TRN_OP_LOAD_NONCE: begin
                        nonce_q  <= pl[7:0];
                    end
                    `TRN_OP_COMPUTE: begin
                        result_q     <= dot_out;
                        result_valid <= 1'b1;
                    end
                    `TRN_OP_READ_RES: begin
                        if (!out_valid || out_ready) begin
                            out_pkt   <= `TRN_MK_PKT(`TRN_OP_RESULT,
                                                    `TRN_PKT_SRC(in_pkt),
                                                    TILE_ID,
                                                    4'h0,
                                                    result_q);
                            out_valid <= 1'b1;
                            // Schedule the paired RECEIPT for the cycle after the
                            // RESULT handshake completes. Remember the host id.
                            rcpt_dst        <= `TRN_PKT_SRC(in_pkt);
                            pending_receipt <= 1'b1;
                        end
                    end
                    default: ; // NOP / unknown -> ignore
                endcase
            end
        end
    end

endmodule
