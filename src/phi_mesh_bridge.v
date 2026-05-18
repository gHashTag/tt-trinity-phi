`default_nettype none
// =====================================================================
// phi_mesh_bridge.v  —  Friend/Foe auth gate for mesh packets
// TRI-10 / TTSKY26c  target branch: unified/champion-bpb-oracle
// Repository: tt-trinity-phi
//
// Author : Dmitrii Vasilev <admin@t27.ai>
// DOI    : 10.5281/zenodo.19227877
//
// Policy :
//   Packet allowed IFF  ff_friend_detected && ff_handshake_valid
//   Otherwise:          packet dropped, packet_dropped_cnt incremented
//                       (saturating counter, ceiling 0xFF)
//
// Latency: 2 clock cycles (stage-1 latch + stage-2 gate)
//
// R-SI-1 compliant: ZERO standalone `*` operators.
// Verilog-2005 only. No SystemVerilog. One reg per line.
// =====================================================================

module phi_mesh_bridge (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        ff_friend_detected,
    input  wire        ff_handshake_valid,
    input  wire [31:0] packet_in,
    input  wire        packet_in_valid,
    output reg  [31:0] packet_out,
    output reg         packet_out_valid,
    output reg  [7:0]  packet_dropped_cnt
);

// ---------------------------------------------------------------------
// Stage 1 pipeline registers — latch inputs for clean timing
// ---------------------------------------------------------------------
reg [31:0] s1_packet;
reg        s1_valid;
reg        s1_friend;
reg        s1_shake;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        s1_packet <= 32'd0;
        s1_valid  <= 1'b0;
        s1_friend <= 1'b0;
        s1_shake  <= 1'b0;
    end else begin
        s1_packet <= packet_in;
        s1_valid  <= packet_in_valid;
        s1_friend <= ff_friend_detected;
        s1_shake  <= ff_handshake_valid;
    end
end

// ---------------------------------------------------------------------
// Stage 2 — auth gate
// Pass packet only if both friend AND handshake flags are asserted.
// Drop otherwise and increment saturating counter.
// ---------------------------------------------------------------------
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        packet_out         <= 32'd0;
        packet_out_valid   <= 1'b0;
        packet_dropped_cnt <= 8'd0;
    end else begin
        // Default: no output this cycle
        packet_out_valid <= 1'b0;

        if (s1_valid) begin
            if (s1_friend && s1_shake) begin
                // ---- Authorised: forward ----
                packet_out       <= s1_packet;
                packet_out_valid <= 1'b1;
            end else begin
                // ---- Foe or incomplete handshake: drop ----
                // Saturating increment — never wraps past 0xFF
                if (packet_dropped_cnt != 8'hFF) begin
                    packet_dropped_cnt <= packet_dropped_cnt + 8'd1;
                end
            end
        end
    end
end

endmodule
`default_nettype wire
