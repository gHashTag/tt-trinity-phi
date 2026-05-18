`default_nettype none
// tri_token_accumulator.v — $TRI Hardware Token Accumulator
// Apache-2.0
// SPDX-License-Identifier: Apache-2.0
//
// DePIN proof-of-compute on-chip token reward counter.
// Each valid attestable work cycle (attest_pulse) increments token_balance
// by reward_amount. Saturates at all-ones (overflow_flag). Reset-safe.
//
// R-SI-1: zero standalone `*` operators in synthesisable RTL.
// Verilog-2005 compliant.
// DOI: 10.5281/zenodo.19227877

module tri_token_accumulator #(
    parameter WIDTH       = 16,  // 64K tokens max per session
    parameter REWARD_BITS = 2    // 1-4 tokens per attest pulse (config)
)(
    input  wire                   clk,
    input  wire                   rst_n,
    input  wire                   attest_pulse,    // 1-cycle pulse: valid job done
    input  wire [REWARD_BITS-1:0] reward_amount,   // tokens per attest (cfg)
    output reg  [WIDTH-1:0]       token_balance,
    output wire                   overflow_flag    // saturates at MAX
);

    // overflow when all bits are 1 (saturated at 2^WIDTH - 1)
    assign overflow_flag = &token_balance;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            token_balance <= {WIDTH{1'b0}};
        end else if (attest_pulse && !overflow_flag) begin
            token_balance <= token_balance + {{(WIDTH-REWARD_BITS){1'b0}}, reward_amount};
        end
    end

endmodule

`default_nettype wire
