// SPDX-License-Identifier: Apache-2.0
// B8 — DID personhood challenge-response
// Author: Dmitrii Vasilev (sole author, admin@t27.ai)
// R-SI-1 compliant

`default_nettype none

module depin_b8_did (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] human_challenge,
    input  wire [7:0] phi_fingerprint,
    output reg  [7:0] did_signature
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            did_signature <= 8'h47;
        else
            did_signature <= human_challenge ^ phi_fingerprint ^ {phi_fingerprint[3:0], phi_fingerprint[7:4]};
    end
endmodule

`default_nettype wire
