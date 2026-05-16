`default_nettype none
// tb_ed25519_verify_stub.v — Testbench for ed25519_verify_stub
// Pure Verilog-2005. R-SI-1: zero `*` operators.
// 3 scenarios:
//   S1: valid parity   — 96 bytes with even XOR parity (valid=1 expected)
//   S2: invalid parity — 96 bytes with odd  XOR parity (valid=0 expected)
//   S3: reset mid-stream — reset after 48 bytes, then full 96 bytes S1 again
//
// SPDX-License-Identifier: Apache-2.0

`timescale 1ns/1ps

module tb_ed25519_verify_stub;

    // DUT ports
    reg        clk;
    reg        rst_n;
    reg        en;
    reg  [7:0] load_byte;
    wire       done;
    wire       valid;

    // Instantiate DUT
    ed25519_verify_stub dut (
        .clk       (clk),
        .rst_n     (rst_n),
        .en        (en),
        .load_byte (load_byte),
        .done      (done),
        .valid     (valid)
    );

    // Clock: 10 ns period
    initial clk = 0;
    always #5 clk = ~clk;

    // Test tracking
    integer pass_count;
    integer fail_count;
    integer i;
    integer timeout_cnt;

    // Byte storage: 96 bytes (Verilog-2005 compatible arrays)
    reg [7:0] test_bytes [0:95];

    // Captured result
    reg cap_done;
    reg cap_valid;

    // Task: apply reset (synchronous active-low)
    task do_reset;
        begin
            rst_n     = 1'b0;
            en        = 1'b0;
            load_byte = 8'h00;
            @(posedge clk); #1;
            @(posedge clk); #1;
            rst_n = 1'b1;
            @(posedge clk); #1;
        end
    endtask

    // Task: load all 96 bytes, then wait up to 4 cycles for done pulse
    // Captures done/valid into cap_done/cap_valid
    task load_all_wait_done;
        begin
            // Load all 96 bytes
            for (i = 0; i < 96; i = i + 1) begin
                en        = 1'b1;
                load_byte = test_bytes[i];
                @(posedge clk); #1;
            end
            en        = 1'b0;
            load_byte = 8'h00;

            // Wait for done pulse: up to 4 extra cycles
            cap_done  = 1'b0;
            cap_valid = 1'b0;
            timeout_cnt = 0;
            while (!cap_done && timeout_cnt < 4) begin
                // Sample current state
                cap_done  = done;
                cap_valid = valid;
                if (!cap_done) begin
                    @(posedge clk); #1;
                    timeout_cnt = timeout_cnt + 1;
                end
            end
        end
    endtask

    // Build even-parity byte set: 96 bytes where final XOR parity bit-0 = 0
    // 95 bytes of 0xAA (0xAA bit-0=0), last byte 0x00 => parity[0]=0 => valid=1
    task build_even_parity_bytes;
        integer j;
        begin
            for (j = 0; j < 95; j = j + 1)
                test_bytes[j] = 8'hAA;
            test_bytes[95] = 8'h00;
        end
    endtask

    // Build odd-parity byte set: last byte 0x01 flips bit-0 => parity[0]=1 => valid=0
    task build_odd_parity_bytes;
        integer j;
        begin
            for (j = 0; j < 95; j = j + 1)
                test_bytes[j] = 8'hAA;
            test_bytes[95] = 8'h01;
        end
    endtask

    initial begin
        pass_count  = 0;
        fail_count  = 0;
        en          = 0;
        load_byte   = 8'h00;
        rst_n       = 1'b0;
        cap_done    = 1'b0;
        cap_valid   = 1'b0;
        timeout_cnt = 0;

        // Allow simulation boot time
        repeat(3) @(posedge clk); #1;

        // -------------------------------------------------------
        // SCENARIO 1: Valid parity (even) — expect done=1, valid=1
        // -------------------------------------------------------
        $display("=== S1: Valid parity (even XOR) — expect done=1, valid=1 ===");
        do_reset;
        build_even_parity_bytes;
        load_all_wait_done;
        if (cap_done === 1'b1 && cap_valid === 1'b1) begin
            $display("S1 PASS: done=%0b valid=%0b", cap_done, cap_valid);
            pass_count = pass_count + 1;
        end else begin
            $display("S1 FAIL: done=%0b valid=%0b (expected 1 1)", cap_done, cap_valid);
            fail_count = fail_count + 1;
        end
        @(posedge clk); #1;

        // -------------------------------------------------------
        // SCENARIO 2: Invalid parity (odd) — expect done=1, valid=0
        // -------------------------------------------------------
        $display("=== S2: Invalid parity (odd XOR) — expect done=1, valid=0 ===");
        do_reset;
        build_odd_parity_bytes;
        load_all_wait_done;
        if (cap_done === 1'b1 && cap_valid === 1'b0) begin
            $display("S2 PASS: done=%0b valid=%0b", cap_done, cap_valid);
            pass_count = pass_count + 1;
        end else begin
            $display("S2 FAIL: done=%0b valid=%0b (expected 1 0)", cap_done, cap_valid);
            fail_count = fail_count + 1;
        end
        @(posedge clk); #1;

        // -------------------------------------------------------
        // SCENARIO 3: Reset mid-stream, then complete valid run
        // -------------------------------------------------------
        $display("=== S3: Reset mid-stream (after 48 bytes), then full even-parity run ===");
        do_reset;
        build_even_parity_bytes;
        // Load only first 48 bytes
        for (i = 0; i < 48; i = i + 1) begin
            en        = 1'b1;
            load_byte = test_bytes[i];
            @(posedge clk); #1;
        end
        en        = 1'b0;
        load_byte = 8'h00;
        $display("S3: mid-stream reset at byte 48");
        // Mid-stream reset
        do_reset;
        // Fresh even-parity run
        load_all_wait_done;
        if (cap_done === 1'b1 && cap_valid === 1'b1) begin
            $display("S3 PASS: done=%0b valid=%0b (reset + full run correct)", cap_done, cap_valid);
            pass_count = pass_count + 1;
        end else begin
            $display("S3 FAIL: done=%0b valid=%0b (expected 1 1)", cap_done, cap_valid);
            fail_count = fail_count + 1;
        end

        // -------------------------------------------------------
        // Summary
        // -------------------------------------------------------
        $display("");
        $display("=== RESULTS: %0d PASS, %0d FAIL ===", pass_count, fail_count);
        if (fail_count == 0)
            $display("ALL TESTS PASSED");
        else
            $display("SOME TESTS FAILED");

        $finish;
    end

endmodule
