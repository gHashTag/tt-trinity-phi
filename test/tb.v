`default_nettype none
`timescale 1ns / 1ps

// TRI-1 Nano cocotb-compatible testbench wrapper.
// Apache-2.0
// Mirrors the Mid (tt-trinity-gf16) tb.v shape so the TinyTapeout
// GL test harness can drop in a gate-level netlist via VERILOG_SOURCES.

module tb ();

    // Dump waves
    initial begin
        $dumpfile("tb.vcd");
        $dumpvars(0, tb);
        #1;
    end

    // Top-level signals
    reg  clk;
    reg  rst_n;
    reg  ena;
    reg  [7:0] ui_in;
    reg  [7:0] uio_in;
    wire [7:0] uo_out;
    wire [7:0] uio_out;
    wire [7:0] uio_oe;

`ifdef GL_TEST
    wire VPWR = 1'b1;
    wire VGND = 1'b0;
`endif

    tt_um_trinity_nano dut (
`ifdef GL_TEST
        .VPWR   (VPWR),
        .VGND   (VGND),
`endif
        .ui_in  (ui_in),
        .uo_out (uo_out),
        .uio_in (uio_in),
        .uio_out(uio_out),
        .uio_oe (uio_oe),
        .ena    (ena),
        .clk    (clk),
        .rst_n  (rst_n)
    );

endmodule

`default_nettype wire
