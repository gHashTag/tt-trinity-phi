`default_nettype none
// Testbench: tb_sacred_constants_rom
// Verifies sacred_constants_rom_sparse output matches original ROM
// for ALL 128 addresses (7-bit addr space, 0-127).
// Pure Verilog-2005. R-SI-1 clean.
//
// Pass criterion: ZERO mismatches across addresses 0..127
// Crown47 / 0x47C0 anchor explicitly checked.

`timescale 1ns/1ps

module tb_sacred_constants_rom;

    // ----------------------------------------------------------------
    // DUT: sparse ROM
    // ----------------------------------------------------------------
    reg  [6:0] addr;
    wire [7:0] val_sparse;

    sacred_constants_rom dut (
        .addr(addr),
        .val (val_sparse)
    );

    // ----------------------------------------------------------------
    // Reference: original dense ROM values as a 128x8 memory
    // Initialized via explicit assignments (no $readmemh — pure V-2005)
    // ----------------------------------------------------------------
    reg [7:0] ref_rom [0:127];

    integer i;
    integer mismatches;
    integer addr_int;

    initial begin
        // Zero-fill reserved region first
        for (i = 0; i < 128; i = i + 1)
            ref_rom[i] = 8'h00;

        // --- Addr 0-9: Core transcendental constants ---
        ref_rom[0]  = 8'h33; // phi
        ref_rom[1]  = 8'h14; // phi^-1
        ref_rom[2]  = 8'h54; // phi^2
        ref_rom[3]  = 8'h0C; // phi^-2
        ref_rom[4]  = 8'h65; // pi
        ref_rom[5]  = 8'h7F; // pi^2 CLAMP
        ref_rom[6]  = 8'h57; // e
        ref_rom[7]  = 8'h12; // gamma_EM
        ref_rom[8]  = 8'h16; // ln2
        ref_rom[9]  = 8'h23; // ln3
        // --- Addr 10-14: Powers of 3 ---
        ref_rom[10] = 8'h60; // 3^1
        ref_rom[11] = 8'h7F; // 3^2 CLAMP
        ref_rom[12] = 8'h7F; // 3^3 CLAMP
        ref_rom[13] = 8'h7F; // 3^4 CLAMP
        ref_rom[14] = 8'h7F; // 3^5 CLAMP
        // --- Addr 15-17: Cross-product anchors ---
        ref_rom[15] = 8'h7F; // phi*pi CLAMP
        ref_rom[16] = 8'h47; // Crown47 MSB  (0x47C0 watermark)
        ref_rom[17] = 8'h7F; // Crown47 LSB  CLAMP (0xC0 overflow → 0x7F)
        // --- Addr 18-22: phi powers ---
        ref_rom[18] = 8'h7F; // phi^3 CLAMP
        ref_rom[19] = 8'h7F; // phi^4 CLAMP
        ref_rom[20] = 8'h7F; // phi^5 CLAMP
        ref_rom[21] = 8'h08; // phi^-3
        ref_rom[22] = 8'h05; // phi^-4
        // --- Addr 23-28: More transcendentals ---
        ref_rom[23] = 8'h7F; // pi^3 CLAMP
        ref_rom[24] = 8'h7F; // e^2 CLAMP
        ref_rom[25] = 8'h0A; // 1/pi
        ref_rom[26] = 8'h0C; // 1/e
        ref_rom[27] = 8'h1C; // sin(pi/3)
        ref_rom[28] = 8'h10; // cos(pi/3)
        // --- Addr 29-37: Sqrt and logarithms ---
        ref_rom[29] = 8'h2D; // sqrt2
        ref_rom[30] = 8'h37; // sqrt3
        ref_rom[31] = 8'h48; // sqrt5
        ref_rom[32] = 8'h18; // golden_angle/180
        ref_rom[33] = 8'h0F; // ln(phi)
        ref_rom[34] = 8'h25; // ln(pi)
        ref_rom[35] = 8'h20; // ln(e)
        ref_rom[36] = 8'h2E; // log_phi(2)
        ref_rom[37] = 8'h49; // log_phi(3)
        // --- Addr 38-44: Ratios and gamma products ---
        ref_rom[38] = 8'h13; // phi/e
        ref_rom[39] = 8'h10; // phi/pi
        ref_rom[40] = 8'h1C; // e/pi
        ref_rom[41] = 8'h25; // pi/e
        ref_rom[42] = 8'h1E; // gamma*phi
        ref_rom[43] = 8'h3A; // gamma*pi
        ref_rom[44] = 8'h32; // gamma*e
        // --- Addr 45-49: Inverse sqrt and sqrt-phi products ---
        ref_rom[45] = 8'h17; // 1/sqrt2
        ref_rom[46] = 8'h12; // 1/sqrt3
        ref_rom[47] = 8'h0E; // 1/sqrt5
        ref_rom[48] = 8'h49; // sqrt2*phi
        ref_rom[49] = 8'h5A; // sqrt3*phi
        // --- Addr 50-59: Trig values and Fibonacci identities ---
        ref_rom[50] = 8'h10; // sin(pi/6)
        ref_rom[51] = 8'h17; // sin(pi/4)
        ref_rom[52] = 8'h17; // cos(pi/4)
        ref_rom[53] = 8'h1C; // cos(pi/6)
        ref_rom[54] = 8'h20; // tan(pi/4)
        ref_rom[55] = 8'h37; // tan(pi/3)
        ref_rom[56] = 8'h20; // phi^2 - phi
        ref_rom[57] = 8'h48; // phi + phi^-1 = sqrt5
        ref_rom[58] = 8'h48; // 2*phi - 1 = sqrt5
        ref_rom[59] = 8'h60; // phi^2 + phi^-2 = 3 (sacred anchor)
        // --- Addr 60-64: Differences ---
        ref_rom[60] = 8'h7F; // e*phi CLAMP
        ref_rom[61] = 8'h23; // e - phi
        ref_rom[62] = 8'h0E; // pi - e
        ref_rom[63] = 8'h31; // pi - phi
        ref_rom[64] = 8'h0C; // phi^-2 alias
        // --- Addr 65-74: Log10s, fractions ---
        ref_rom[65] = 8'h0E; // log10(e)
        ref_rom[66] = 8'h07; // log10(phi)
        ref_rom[67] = 8'h10; // log10(pi)
        ref_rom[68] = 8'h1F; // ln(phi+1)
        ref_rom[69] = 8'h03; // 1/pi^2
        ref_rom[70] = 8'h19; // pi/4
        ref_rom[71] = 8'h16; // e/4
        ref_rom[72] = 8'h1A; // phi/2
        ref_rom[73] = 8'h7F; // 2*pi CLAMP
        ref_rom[74] = 8'h7F; // e+phi CLAMP
        // addr 75..127 remain 8'h00 (reserved, set above)
    end

    // ----------------------------------------------------------------
    // Scan all 128 addresses and compare
    // ----------------------------------------------------------------
    initial begin
        mismatches = 0;
        $display("=== tb_sacred_constants_rom: 128-address scan ===");
        $display("    Verifying sparse ROM == reference ROM byte-by-byte");

        #10;

        for (addr_int = 0; addr_int < 128; addr_int = addr_int + 1) begin
            addr = addr_int[6:0];
            #5; // combinational settle
            if (val_sparse !== ref_rom[addr_int]) begin
                $display("MISMATCH addr=%0d  sparse=8'h%02h  ref=8'h%02h",
                         addr_int, val_sparse, ref_rom[addr_int]);
                mismatches = mismatches + 1;
            end
        end

        // ----------------------------------------------------------------
        // Crown47 / 0x47C0 anchor explicit check
        // ----------------------------------------------------------------
        addr = 7'd16; #5;
        if (val_sparse !== 8'h47) begin
            $display("ANCHOR FAIL: addr=16 (Crown47 MSB) expected 8'h47 got 8'h%02h", val_sparse);
            mismatches = mismatches + 1;
        end else begin
            $display("ANCHOR OK : addr=16 Crown47 MSB = 8'h47 checkmark");
        end

        addr = 7'd17; #5;
        if (val_sparse !== 8'h7F) begin
            $display("ANCHOR FAIL: addr=17 (Crown47 LSB clamp) expected 8'h7F got 8'h%02h", val_sparse);
            mismatches = mismatches + 1;
        end else begin
            $display("ANCHOR OK : addr=17 Crown47 LSB (0xC0 clamped) = 8'h7F checkmark");
        end

        // Sacred anchor: phi^2 + phi^-2 = 3 encoded at addr 59
        addr = 7'd59; #5;
        if (val_sparse !== 8'h60) begin
            $display("ANCHOR FAIL: addr=59 (phi^2+phi^-2 sacred anchor) expected 8'h60 got 8'h%02h", val_sparse);
            mismatches = mismatches + 1;
        end else begin
            $display("ANCHOR OK : addr=59 phi^2+phi^-2 = 8'h60 (3.0 Q3.5) checkmark");
        end

        // ----------------------------------------------------------------
        // Final verdict
        // ----------------------------------------------------------------
        if (mismatches == 0) begin
            $display("PASS: all 128 addresses match. Sparse ROM byte-equivalent to original.");
        end else begin
            $display("FAIL: %0d mismatch(es) detected.", mismatches);
            $finish(1);
        end

        $finish(0);
    end

    // Timeout guard
    initial begin
        #50000;
        $display("TIMEOUT");
        $finish(1);
    end

endmodule
`default_nettype wire
