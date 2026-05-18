// SPDX-License-Identifier: Apache-2.0
// B1 — Hardware Root-of-Trust (DePIN v1.1 stub for TT SKY26b)
// Reuses Lucas POST L2..L7 + phi-anchor 0x47C0 low byte
// Author: Dmitrii Vasilev (sole author, admin@t27.ai)
// R-SI-1 compliant: only XOR, shift, lookup

`default_nettype none

module depin_b1_rot (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  challenge,
    output reg  [7:0]  response
);
    reg [7:0] lucas_rom [0:7];
    initial begin
        lucas_rom[0] = 8'd3;
        lucas_rom[1] = 8'd4;
        lucas_rom[2] = 8'd7;
        lucas_rom[3] = 8'd11;
        lucas_rom[4] = 8'd18;
        lucas_rom[5] = 8'd29;
        lucas_rom[6] = 8'd47;
        lucas_rom[7] = 8'h47;
    end

    wire [2:0] idx = challenge[2:0] ^ challenge[5:3];
    wire [7:0] lucas_val = lucas_rom[idx];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            response <= 8'hC0;
        else
            response <= challenge ^ lucas_val ^ 8'hC0;
    end
endmodule

`default_nettype wire
