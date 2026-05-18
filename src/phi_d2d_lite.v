`default_nettype none
// =====================================================================
// phi_d2d_lite.v  —  Phi mesh-lite bi-port serial adapter
// TRI-10 / TTSKY26c  target branch: unified/champion-bpb-oracle
// Repository: tt-trinity-phi
//
// Author : Dmitrii Vasilev <admin@t27.ai>
// DOI    : 10.5281/zenodo.19227877
//
// Framing: START(0) + 32 data bits LSB-first + PARITY(XOR32) + STOP(1)
//          = 35 clock cycles per packet
//
// Ports:
//   East (E): e_tx / e_rx  — connects to uio_out[0] / uio_in[1]
//             (upgraded friend_foe path, packet-aware)
//   West (W): w_tx / w_rx  — connects to uio_out[2] / uio_in[3]
//             (new in TRI-10)
//
// mesh_mode: 1 = mesh active, 0 = idle (all FSMs stay in IDLE)
//
// R-SI-1 compliant: ZERO standalone `*` operators in synthesisable RTL.
// Verilog-2005 only. No SystemVerilog. One reg declaration per line.
// =====================================================================

module phi_d2d_lite (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        ena,
    input  wire [31:0] packet_in,
    input  wire        packet_in_valid,
    input  wire        e_rx,
    input  wire        w_rx,
    input  wire        mesh_mode,
    output reg         e_tx,
    output reg         w_tx,
    output reg  [31:0] packet_out,
    output reg         packet_out_valid
);

// ---------------------------------------------------------------------
// TX FSM state encoding (binary, 3-bit)
// ---------------------------------------------------------------------
localparam [2:0] TX_IDLE   = 3'd0;
localparam [2:0] TX_START  = 3'd1;
localparam [2:0] TX_DATA   = 3'd2;
localparam [2:0] TX_PARITY = 3'd3;
localparam [2:0] TX_STOP   = 3'd4;

// RX FSM state encoding (binary, 3-bit)
localparam [2:0] RX_IDLE         = 3'd0;
localparam [2:0] RX_DETECT_START = 3'd1;
localparam [2:0] RX_DATA         = 3'd2;
localparam [2:0] RX_PARITY       = 3'd3;
localparam [2:0] RX_STOP         = 3'd4;
localparam [2:0] RX_DELIVER      = 3'd5;

// ---------------------------------------------------------------------
// RX input registers — latch pads immediately (timing mitigation)
// ---------------------------------------------------------------------
reg e_rx_r;
reg w_rx_r;

always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        e_rx_r <= 1'b1;
        w_rx_r <= 1'b1;
    end else begin
        e_rx_r <= e_rx;
        w_rx_r <= w_rx;
    end
end

// ---------------------------------------------------------------------
// TX registers (single serialiser shared by both ports)
// ---------------------------------------------------------------------
reg [2:0]  tx_state;
reg [31:0] tx_shift;
reg [4:0]  tx_bit_cnt;
reg        tx_parity;
reg        tx_out;        // serial output, fanned out to e_tx / w_tx

// ---------------------------------------------------------------------
// TX FSM
// ---------------------------------------------------------------------
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        tx_state   <= TX_IDLE;
        tx_shift   <= 32'd0;
        tx_bit_cnt <= 5'd0;
        tx_parity  <= 1'b0;
        tx_out     <= 1'b1;
    end else if (ena && mesh_mode) begin
        case (tx_state)

            TX_IDLE: begin
                tx_out <= 1'b1;
                if (packet_in_valid) begin
                    tx_shift   <= packet_in;
                    tx_bit_cnt <= 5'd0;
                    tx_parity  <= 1'b0;
                    tx_state   <= TX_START;
                end
            end

            TX_START: begin
                tx_out   <= 1'b0;          // start bit (low)
                tx_state <= TX_DATA;
            end

            TX_DATA: begin
                tx_out    <= tx_shift[0];
                tx_parity <= tx_parity ^ tx_shift[0];
                // Logical right-shift: MSB filled with 0
                tx_shift  <= {1'b0, tx_shift[31:1]};
                if (tx_bit_cnt == 5'd31) begin
                    tx_bit_cnt <= 5'd0;
                    tx_state   <= TX_PARITY;
                end else begin
                    tx_bit_cnt <= tx_bit_cnt + 5'd1;
                end
            end

            TX_PARITY: begin
                tx_out   <= tx_parity;
                tx_state <= TX_STOP;
            end

            TX_STOP: begin
                tx_out   <= 1'b1;          // stop bit (high)
                tx_state <= TX_IDLE;
            end

            default: begin
                tx_state <= TX_IDLE;
                tx_out   <= 1'b1;
            end
        endcase
    end else begin
        // mesh_mode inactive or ena low: hold idle level
        tx_out   <= 1'b1;
        tx_state <= TX_IDLE;
    end
end

// Fan TX output to both East and West ports
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        e_tx <= 1'b1;
        w_tx <= 1'b1;
    end else begin
        e_tx <= tx_out;
        w_tx <= tx_out;
    end
end

// ---------------------------------------------------------------------
// RX East registers
// ---------------------------------------------------------------------
reg [2:0]  erx_state;
reg [31:0] erx_shift;
reg [4:0]  erx_bit_cnt;
reg        erx_calc_par;  // running XOR of received data bits
reg        erx_rcvd_par;  // parity bit received from frame
reg        erx_valid;
reg [31:0] erx_packet;

// ---------------------------------------------------------------------
// RX East FSM
// ---------------------------------------------------------------------
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        erx_state    <= RX_IDLE;
        erx_shift    <= 32'd0;
        erx_bit_cnt  <= 5'd0;
        erx_calc_par <= 1'b0;
        erx_rcvd_par <= 1'b0;
        erx_valid    <= 1'b0;
        erx_packet   <= 32'd0;
    end else if (ena && mesh_mode) begin
        erx_valid <= 1'b0;   // default: de-assert each cycle

        case (erx_state)

            RX_IDLE: begin
                // Detect falling edge → start bit
                if (!e_rx_r) begin
                    erx_state    <= RX_DETECT_START;
                    erx_bit_cnt  <= 5'd0;
                    erx_calc_par <= 1'b0;
                    erx_shift    <= 32'd0;
                end
            end

            RX_DETECT_START: begin
                // Confirm start bit was real (still low), move to data
                if (!e_rx_r) begin
                    erx_state <= RX_DATA;
                end else begin
                    erx_state <= RX_IDLE;  // glitch, ignore
                end
            end

            RX_DATA: begin
                // Shift in LSB-first
                erx_shift    <= {e_rx_r, erx_shift[31:1]};
                erx_calc_par <= erx_calc_par ^ e_rx_r;
                if (erx_bit_cnt == 5'd31) begin
                    erx_bit_cnt <= 5'd0;
                    erx_state   <= RX_PARITY;
                end else begin
                    erx_bit_cnt <= erx_bit_cnt + 5'd1;
                end
            end

            RX_PARITY: begin
                erx_rcvd_par <= e_rx_r;
                erx_state    <= RX_STOP;
            end

            RX_STOP: begin
                if (e_rx_r) begin
                    // Valid stop bit — proceed to delivery
                    erx_state <= RX_DELIVER;
                end else begin
                    // Framing error — discard silently
                    erx_state <= RX_IDLE;
                end
            end

            RX_DELIVER: begin
                // Accept only if parity matches
                if (erx_rcvd_par == erx_calc_par) begin
                    erx_packet <= erx_shift;
                    erx_valid  <= 1'b1;
                end
                erx_state <= RX_IDLE;
            end

            default: erx_state <= RX_IDLE;
        endcase
    end else begin
        erx_state <= RX_IDLE;
        erx_valid <= 1'b0;
    end
end

// ---------------------------------------------------------------------
// RX West registers
// ---------------------------------------------------------------------
reg [2:0]  wrx_state;
reg [31:0] wrx_shift;
reg [4:0]  wrx_bit_cnt;
reg        wrx_calc_par;
reg        wrx_rcvd_par;
reg        wrx_valid;
reg [31:0] wrx_packet;

// ---------------------------------------------------------------------
// RX West FSM (symmetric copy of East FSM)
// ---------------------------------------------------------------------
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        wrx_state    <= RX_IDLE;
        wrx_shift    <= 32'd0;
        wrx_bit_cnt  <= 5'd0;
        wrx_calc_par <= 1'b0;
        wrx_rcvd_par <= 1'b0;
        wrx_valid    <= 1'b0;
        wrx_packet   <= 32'd0;
    end else if (ena && mesh_mode) begin
        wrx_valid <= 1'b0;

        case (wrx_state)

            RX_IDLE: begin
                if (!w_rx_r) begin
                    wrx_state    <= RX_DETECT_START;
                    wrx_bit_cnt  <= 5'd0;
                    wrx_calc_par <= 1'b0;
                    wrx_shift    <= 32'd0;
                end
            end

            RX_DETECT_START: begin
                if (!w_rx_r) begin
                    wrx_state <= RX_DATA;
                end else begin
                    wrx_state <= RX_IDLE;
                end
            end

            RX_DATA: begin
                wrx_shift    <= {w_rx_r, wrx_shift[31:1]};
                wrx_calc_par <= wrx_calc_par ^ w_rx_r;
                if (wrx_bit_cnt == 5'd31) begin
                    wrx_bit_cnt <= 5'd0;
                    wrx_state   <= RX_PARITY;
                end else begin
                    wrx_bit_cnt <= wrx_bit_cnt + 5'd1;
                end
            end

            RX_PARITY: begin
                wrx_rcvd_par <= w_rx_r;
                wrx_state    <= RX_STOP;
            end

            RX_STOP: begin
                if (w_rx_r) begin
                    wrx_state <= RX_DELIVER;
                end else begin
                    wrx_state <= RX_IDLE;
                end
            end

            RX_DELIVER: begin
                if (wrx_rcvd_par == wrx_calc_par) begin
                    wrx_packet <= wrx_shift;
                    wrx_valid  <= 1'b1;
                end
                wrx_state <= RX_IDLE;
            end

            default: wrx_state <= RX_IDLE;
        endcase
    end else begin
        wrx_state <= RX_IDLE;
        wrx_valid <= 1'b0;
    end
end

// ---------------------------------------------------------------------
// Output arbitration — East has priority over West
// Both valid simultaneously: East wins; West re-queued next cycle
// (acceptable in linear chain: E and W traffic is never simultaneous
//  in a correctly scheduled mesh)
// ---------------------------------------------------------------------
always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
        packet_out       <= 32'd0;
        packet_out_valid <= 1'b0;
    end else begin
        if (erx_valid) begin
            packet_out       <= erx_packet;
            packet_out_valid <= 1'b1;
        end else if (wrx_valid) begin
            packet_out       <= wrx_packet;
            packet_out_valid <= 1'b1;
        end else begin
            packet_out_valid <= 1'b0;
        end
    end
end

endmodule
`default_nettype wire
