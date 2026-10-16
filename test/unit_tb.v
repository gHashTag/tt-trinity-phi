// SPDX-License-Identifier: Apache-2.0
// Vector-file testbench for the isolated GF16 units. Inputs and the EXPECTED results come
// from the independent Fraction oracle (test/gf16_oracle.py) as hex files; this bench only
// compares. Build with -DUNIT_ADD for gf16_v2_add, without it for gf16_v2_mul.
//   vvp unit +A=a.hex +B=b.hex +E=exp.hex +N=<count>
// Result line: UNIT_RESULT <add|mul> N=<count> MISMATCH=<count>   (!== so X never passes)
// SETTLE: wait in ns after the inputs change before the output is compared. The default 1 is the generic
// (zero-delay) run, unchanged. Only test/physical_fa_check.py overrides it (-Punit_tb.SETTLE=...) for the
// technology branch with the unit-delay PDK models; an unsettled output differs and counts as a mismatch.
`timescale 1ns/1ps
module unit_tb;
    parameter MAXN = 262144;
    parameter SETTLE = 1;

    reg [15:0] av [0:MAXN-1];
    reg [15:0] bv [0:MAXN-1];
    reg [15:0] ev [0:MAXN-1];
    reg [15:0] a;
    reg [15:0] b;
    wire [15:0] r;

`ifdef UNIT_ADD
    gf16_v2_add dut (.a(a), .b(b), .result(r));
`else
    gf16_v2_mul dut (.a(a), .b(b), .result(r));
`endif

    integer i, bad, n;
    reg [1023:0] fa, fb, fe;

    initial begin
        if (!$value$plusargs("A=%s", fa) || !$value$plusargs("B=%s", fb) ||
            !$value$plusargs("E=%s", fe) || !$value$plusargs("N=%d", n)) begin
            $display("UNIT_ERROR missing plusarg");
            $finish;
        end
        if (n < 1 || n > MAXN) begin
            $display("UNIT_ERROR N out of range: %0d", n);
            $finish;
        end
        $readmemh(fa, av);
        $readmemh(fb, bv);
        $readmemh(fe, ev);
        bad = 0;
        for (i = 0; i < n; i = i + 1) begin
            a = av[i];
            b = bv[i];
            #(SETTLE);
            if (r !== ev[i]) begin
                bad = bad + 1;
                if (bad <= 10)
                    $display("MISMATCH i=%0d a=%h b=%h got=%h expected=%h", i, a, b, r, ev[i]);
            end
        end
`ifdef UNIT_ADD
        $display("UNIT_RESULT add N=%0d MISMATCH=%0d", n, bad);
`else
        $display("UNIT_RESULT mul N=%0d MISMATCH=%0d", n, bad);
`endif
        $finish;
    end
endmodule
