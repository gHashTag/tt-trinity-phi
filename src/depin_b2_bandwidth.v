// SPDX-License-Identifier: Apache-2.0
// B2 — Proof-of-Bandwidth on-chip counter
// Author: Dmitrii Vasilev (sole author, admin@t27.ai)
// R-SI-1 compliant

`default_nettype none

module depin_b2_bandwidth (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        packet_in,
    output reg  [15:0] bytes_counter,
    output reg  [15:0] timestamp
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            bytes_counter <= 16'd0;
            timestamp     <= 16'd0;
        end else begin
            timestamp <= timestamp + 16'd1;
            if (packet_in)
                bytes_counter <= bytes_counter + 16'd1;
        end
    end
endmodule

`default_nettype wire
