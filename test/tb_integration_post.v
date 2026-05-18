// SPDX-License-Identifier: Apache-2.0
// tb_integration_post.v — Integration test for POST chain
// Tests Lucas POST, ROM, and status byte aggregation

`default_nettype none
`timescale 1ns / 1ps

module tb_integration_post;

    reg clk;
    reg rst_n;

    // POST modules
    wire phi_ok, post_done;

    // Lucas ROM
    reg [2:0] lucas_idx;
    wire [7:0] lucas_val;

    // Status register
    wire [7:0] status_byte;

    // HWRNG
    wire rng_ena = 1'b1;
    wire [15:0] hwrng_word;
    wire hwrng_nonzero = |hwrng_word;

    phi_anchor_post u_post (
        .clk(clk), .rst_n(rst_n),
        .phi_ok(phi_ok),
        .post_done(post_done)
    );

    lucas_rom u_lucas (
        .idx(lucas_idx),
        .value(lucas_val)
    );

    wb_status_reg u_status (
        .clk(clk), .rst_n(rst_n),
        .phi_ok(phi_ok),
        .lucas_ok(1'b1),
        .matmul_ok(1'b0),
        .post_done(post_done),
        .rcpt_valid(1'b0),
        .hwrng_nonzero(hwrng_nonzero),
        .status_byte(status_byte)
    );

    hwrng_lfsr u_rng (
        .clk(clk), .rst_n(rst_n),
        .ena(rng_ena),
        .rnd(hwrng_word)
    );

    // Clock
    initial begin
        clk = 0;
        forever #10 clk = ~clk;
    end

    integer pass_count = 0;
    integer fail_count = 0;

    task check_lucas;
        input [7:0] expected;
        input [2:0] idx;
        begin
            lucas_idx = idx;
            #10;
            if (lucas_val !== expected) begin
                $display("FAIL: Lucas L%d = %d (expected %d)", idx+2, lucas_val, expected);
                fail_count++;
            end else begin
                $display("PASS: Lucas L%d = %d", idx+2, lucas_val);
                pass_count++;
            end
        end
    endtask

    initial begin
        $dumpfile("tb_integration_post.vcd");
        $dumpvars(0, tb_integration_post);
        $display("=== INTEGRATION TEST: POST CHAIN ===");

        rst_n = 0;
        lucas_idx = 3'h0;
        #100;
        rst_n = 1;
        #100;

        // Test 1: Lucas ROM values
        $display("\nTest 1: Lucas ROM verification");
        check_lucas(8'd3, 3'd0);   // L₂ = 3
        check_lucas(8'd4, 3'd1);   // L₃ = 4
        check_lucas(8'd7, 3'd2);   // L₄ = 7
        check_lucas(8'd11, 3'd3);  // L₅ = 11
        check_lucas(8'd18, 3'd4);  // L₆ = 18
        check_lucas(8'd29, 3'd5);  // L₇ = 29

        // Test 2: POST completion
        $display("\nTest 2: POST completion");
        #200;  // Wait for POST
        if (post_done && phi_ok) begin
            $display("PASS: POST passed (φ²+φ⁻²=3 verified)");
            pass_count++;
        end else begin
            $display("FAIL: POST not passed");
            fail_count++;
        end

        // Test 3: Status byte
        $display("\nTest 3: Status byte");
        $display("Status byte = 0x%02h", status_byte);
        if (status_byte !== 8'h00) begin
            $display("PASS: Status byte non-zero");
            pass_count++;
        end

        // Test 4: HWRNG non-zero
        $display("\nTest 4: HWRNG entropy");
        #50;
        if (hwrng_nonzero) begin
            $display("PASS: HWRNG generating entropy");
            pass_count++;
        end else begin
            $display("FAIL: HWRNG stuck at zero");
            fail_count++;
        end

        // Summary
        $display("\n=== TEST SUMMARY ===");
        $display("PASS: %d", pass_count);
        $display("FAIL: %d", fail_count);
        $finish;
    end

endmodule