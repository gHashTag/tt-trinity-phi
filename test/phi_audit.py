#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Phi (nano die) instantiated-block conformance audit.
#
# Extends the gamma/euler instantiated-subsystem audits to the third taped-out die.
# Checks the Phi-specific instantiated blocks against their contracts:
#
#   phi_anchor_post      -- Lucas-chain POST: passes clean AND detects a corrupted
#                           expected value (live checker, like cassini_post)
#   sacred_constants_rom -- Q3.5 fixed-point constant ROM: 59 residual constants
#                           within +-1 LSB of value*32, 14 clamp addrs -> 0x7F (all
#                           true values >= 3.969), zero region clean, watermarks ok
#   phi_mesh_bridge      -- friend/foe auth gate: forward on friend&shake, else
#                           drop + saturating(0xFF) counter
#   phi_d2d_lite         -- die-to-die serial link. FINDING: RX requires a 2-cycle
#                           START but TX emits 1 cycle -> TX->RX loopback delivers
#                           NOTHING (receive path non-functional). Latent on the
#                           single-die shuttle. phi_d2d_lite_v2 fixes RX framing
#                           (RX_IDLE -> RX_DATA) -> loopback round-trips.
#                           (lucas_rom / hwrng_lfsr are identical to gamma and are
#                            covered by gamma/euler's receipt_path_audit.)
#
# 2026-06 result: POST / sacred ROM / mesh bridge CORRECT; phi_d2d_lite RX framing
# bug confirmed, phi_d2d_lite_v2 verified.
import os, subprocess, tempfile, math, sys
HERE=os.path.dirname(os.path.abspath(__file__)); SRC=os.path.join(HERE,"..","src")

def sim(srcs, tb, tag):
    d=tempfile.mkdtemp(); open(d+"/tb.v","w").write(tb)
    files=[os.path.join(SRC,s) for s in srcs]+[d+"/tb.v"]
    c=subprocess.run(["iverilog","-g2012","-o",d+"/x",*files],capture_output=True,text=True)
    if c.returncode: print(f"{tag}: COMPILE FAIL\n{c.stderr[:300]}"); sys.exit(2)
    return subprocess.run(["vvp",d+"/x"],capture_output=True,text=True).stdout
def L(out,p): return [l[len(p):].strip() for l in out.splitlines() if l.startswith(p)]

def audit_post():
    def run(text):
        d=tempfile.mkdtemp(); sp=d+"/m.v"; open(sp,"w").write(text)
        tb="""`timescale 1ns/1ps
module tb; reg clk=0,rst_n=0; wire ok,dn;
 phi_anchor_post u(.clk(clk),.rst_n(rst_n),.phi_ok(ok),.post_done(dn));
 always #5 clk=~clk; integer k;
 initial begin @(negedge clk) rst_n=0; @(negedge clk) rst_n=1;
  for(k=0;k<12 && !dn;k=k+1) @(negedge clk); #1 $display("R %b %b", ok, dn); $finish; end endmodule"""
        open(d+"/tb.v","w").write(tb)
        subprocess.run(["iverilog","-g2012","-o",d+"/x",sp,d+"/tb.v"],capture_output=True,text=True,check=True)
        return subprocess.run(["vvp",d+"/x"],capture_output=True,text=True).stdout
    orig=open(os.path.join(SRC,"phi_anchor_post.v")).read()
    clean=L(run(orig),"R ")[0]
    fault=L(run(orig.replace("4'd4: lucas_expect = 8'd7;","4'd4: lucas_expect = 8'd8;")),"R ")[0]
    ok=(clean=="1 1") and fault.startswith("0")
    print(f"phi_anchor_post      : clean={clean} fault={fault} (live checker)  -> {'OK' if ok else 'FAIL'}")
    return ok

def audit_sacred():
    PHI=(1+5**0.5)/2; PI=math.pi; E=math.e; G=0.5772156649; S5=5**0.5
    ref={0:PHI,1:1/PHI,2:PHI**2,3:PHI**-2,4:PI,6:E,7:G,8:math.log(2),9:math.log(3),10:3.0,
     21:PHI**-3,22:PHI**-4,25:1/PI,26:1/E,27:math.sin(PI/3),28:math.cos(PI/3),29:2**.5,30:3**.5,
     31:S5,32:0.763932,33:math.log(PHI),34:math.log(PI),35:1.0,36:math.log(2)/math.log(PHI),
     37:math.log(3)/math.log(PHI),38:PHI/E,39:PHI/PI,40:E/PI,41:PI/E,42:G*PHI,43:G*PI,44:G*E,
     45:1/2**.5,46:1/3**.5,47:1/S5,48:2**.5*PHI,49:3**.5*PHI,50:.5,51:math.sin(PI/4),
     52:math.cos(PI/4),53:math.cos(PI/6),54:1.0,55:math.tan(PI/3),56:1.0,57:S5,58:S5,59:3.0,
     61:E-PHI,62:PI-E,63:PI-PHI,64:PHI**-2,65:math.log10(E),66:math.log10(PHI),67:math.log10(PI),
     68:math.log(PHI+1),69:1/PI**2,70:PI/4,71:E/4,72:PHI/2}
    clamp={5:PI**2,11:9,12:27,13:81,14:243,15:PHI*PI,18:PHI**3,19:PHI**4,20:PHI**5,
           23:PI**3,24:E**2,60:E*PHI,73:2*PI,74:E+PHI}
    tb="""`timescale 1ns/1ps
module tb; reg [6:0] a; wire [7:0] v; sacred_constants_rom u(.addr(a),.val(v));
 integer i; initial begin for(i=0;i<128;i=i+1) begin a=i[6:0]; #1 $display("V %0d %0d", i, v); end $finish; end endmodule"""
    rom={int(l.split()[0]):int(l.split()[1]) for l in L(sim(["sacred_constants_rom.v"],tb,"sacred"),"V ")}
    verr=[a for a,v in ref.items() if abs(rom[a]-round(v*32))>1]
    cerr=[a for a,v in clamp.items() if rom[a]!=0x7F or v<3.96875]
    zerr=[a for a in range(75,128) if rom[a]!=0]
    ok=not verr and not cerr and not zerr and rom[16]==0x47
    print(f"sacred_constants_rom : {len(ref)} consts +-1LSB ({'clean' if not verr else verr}); "
          f"clamp {len(clamp)}->0x7F {'ok' if not cerr else cerr}; zero {'ok' if not zerr else 'bad'}"
          f"  -> {'OK' if ok else 'FAIL'}")
    return ok

def audit_bridge():
    tb=r"""`timescale 1ns/1ps
module tb; reg clk=0,rst_n=0,fr=0,sh=0,piv=0; reg [31:0] pin; wire [31:0] pout; wire pov; wire [7:0] drop;
 phi_mesh_bridge u(.clk(clk),.rst_n(rst_n),.ff_friend_detected(fr),.ff_handshake_valid(sh),
   .packet_in(pin),.packet_in_valid(piv),.packet_out(pout),.packet_out_valid(pov),.packet_dropped_cnt(drop));
 always #5 clk=~clk; integer k;
 task send(input f,input s,input [31:0]p); begin
   @(negedge clk) begin fr=f;sh=s;pin=p;piv=1; end @(negedge clk) piv=0; @(negedge clk); end endtask
 initial begin @(negedge clk) rst_n=0; repeat(2)@(negedge clk); rst_n=1;
  send(1,1,32'hAA11AA11); #1 $display("P %08h %b", pout, pov);
  send(1,0,32'h0); #1 $display("D %b %0d", pov, drop);
  for(k=0;k<300;k=k+1) send(0,0,32'h0); #1 $display("S %0d", drop); $finish; end endmodule"""
    out=sim(["phi_mesh_bridge.v"],tb,"bridge")
    fwd=L(out,"P ")[0]; drop1=L(out,"D ")[0]; sat=L(out,"S ")[0]
    ok=(fwd=="aa11aa11 1") and drop1=="0 1" and sat=="255"
    print(f"phi_mesh_bridge      : fwd={fwd}; foe drop={drop1}; saturate={sat}/255  -> {'OK' if ok else 'FAIL'}")
    return ok

def audit_d2d():
    def loop(mod,src,pkt):
        tb=f"""`timescale 1ns/1ps
module tb; reg clk=0,rst_n=0,ena=1,mesh=1,piv=0; reg [31:0] pin; wire etx,wtx; wire [31:0] pout; wire pov;
 {mod} u(.clk(clk),.rst_n(rst_n),.ena(ena),.packet_in(pin),.packet_in_valid(piv),
   .e_rx(etx),.w_rx(1'b1),.mesh_mode(mesh),.e_tx(etx),.w_tx(wtx),.packet_out(pout),.packet_out_valid(pov));
 always #5 clk=~clk; integer k;
 initial begin pin=32'h{pkt:08x}; @(negedge clk) rst_n=0; repeat(3)@(negedge clk); rst_n=1;
  @(negedge clk) piv=1; @(negedge clk) piv=0;
  for(k=0;k<80;k=k+1) begin @(negedge clk); if(pov) $display("D %08h", pout); end $finish; end endmodule"""
        return L(sim([src],tb,mod),"D ")
    pkts=[0xDEADBEEF,0xCAFEBABE,0,0xFFFFFFFF,0x12345678]
    shipped_none=all(loop("phi_d2d_lite","phi_d2d_lite.v",p)==[] for p in pkts)
    v2_ok=all(loop("phi_d2d_lite_v2","phi_d2d_lite_v2.v",p)==[f"{p:08x}"] for p in pkts)
    ok=shipped_none and v2_ok
    print(f"phi_d2d_lite         : shipped TX->RX loopback delivers nothing (RX 2-cycle-start bug) "
          f"{shipped_none}; v2 round-trips all {v2_ok}  -> {'BUG CONFIRMED + FIXED' if ok else 'UNEXPECTED'}")
    return ok

def main():
    print("== Phi (nano die) instantiated-block conformance audit ==")
    r=[audit_post(), audit_sacred(), audit_bridge(), audit_d2d()]
    allok=all(r)
    print("RESULT:", "POST/sacred/bridge CORRECT; phi_d2d_lite RX framing bug characterized + v2 fix verified"
          if allok else "UNEXPECTED")
    return 0 if allok else 1

if __name__=="__main__":
    sys.exit(main())
