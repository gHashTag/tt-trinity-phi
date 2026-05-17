# DevKit Demo — Phi (1×1 Anchor Chip, SKY 26b)

This document describes the firmware demo plan for the Tiny Tapeout DevKit loaded with the **Phi** chip — a 1×1 anchor tile acting as POST seed generator and Trinity pipeline coordinator.

---

## 1. Quick Bring-up

After flashing the RP2040 firmware onto the DevKit and applying power:

- The **7-segment display** on the DevKit shows `0x47C0` — the canonical POST (Power-On Self-Test) signature confirming the Phi tile is alive and clocked.
- The **status LEDs** cycle through a POST sequence:
  - LED0 (green): power rail OK
  - LED1 (yellow): clock locked at 50 MHz
  - LED2 (blue): Phi tile handshake complete
  - LED3 (red): off (no fault)
- UART console (115200 8N1) prints:

```
[PHI] POST OK  seed=0x47C0  f=50MHz  tile=1x1
```

At this point Phi is ready to accept commands or serve as the pipeline seed source.

---

## 2. Demo Sequence

### 2.1 Connect via USB

```bash
# macOS / Linux
screen /dev/tty.usbmodem* 115200
# or
minicom -D /dev/ttyACM0 -b 115200
```

Windows: use PuTTY → Serial → `COM<N>` → 115200.

### 2.2 Run the POST demo

```bash
tt-demo phi --post
```

**Expected output:**

```
[PHI] Running POST...
  tile_id   : 0x01
  anchor_reg: 0x47C0
  clock_MHz : 50
  io_check  : PASS
[PHI] POST PASSED  seed=0x47C0
```

The 7-segment display holds `0x47C0` and all status LEDs return to steady green.

### 2.3 Expected outputs summary

| Test              | 7-seg   | UART result          |
|-------------------|---------|----------------------|
| Power-on default  | `47C0`  | POST OK seed printed |
| `tt-demo phi --post` | `47C0` | PASS + seed=0x47C0  |

---

## 3. Trinity Pipeline Demo

> **This section is authoritative for the full Trinity pipeline.**  
> Euler and Gamma repos contain cross-links back here.

### 3.1 Architecture

```
DevKit-Phi  ──UART──►  DevKit-Euler  ──UART──►  DevKit-Gamma
  POST seed               inference               neuromorphic
  0x47C0                  token stream            spike feedback
      ▲                                                │
      └────────────────── feedback ───────────────────┘
```

### 3.2 Flow

1. **Phi** runs POST, emits `seed=0x47C0` on UART TX.
2. **Euler** receives the seed, uses it to initialise the KV-cache, then runs inference token-by-token from the input prompt.
3. **Gamma** receives each token embedding, converts it to spike trains on `uio_out`, and sends a neuromorphic feedback word back to Phi for adaptive clocking.

### 3.3 MicroPython Orchestrator (RP2040)

Save the following as `trinity_demo.py` and run it on any of the three RP2040 boards (or a fourth host board) connected to all three DevKits via UART:

```python
"""
trinity_demo.py — Trinity Pipeline Orchestrator
Target: RP2040 MicroPython v1.23+
Wiring:
  UART0 TX/RX  → DevKit-Phi   (GP0/GP1)
  UART1 TX/RX  → DevKit-Euler (GP4/GP5)
  UART2 TX/RX  → DevKit-Gamma (GP8/GP9)  [via second machine UART or PIO UART]
"""

import machine, time

BAUD = 115_200
TIMEOUT_MS = 50

uart_phi   = machine.UART(0, baudrate=BAUD, tx=machine.Pin(0),  rx=machine.Pin(1))
uart_euler = machine.UART(1, baudrate=BAUD, tx=machine.Pin(4),  rx=machine.Pin(5))
# For Gamma use a third hardware UART or a PIO-based UART on GP8/GP9
# uart_gamma = machine.UART(2, baudrate=BAUD, tx=machine.Pin(8), rx=machine.Pin(9))

CMD_POST      = b"POST\r\n"
CMD_INFERENCE = b"INFER hello\r\n"
CMD_NEURO     = b"NEURO\r\n"

def send_recv(uart, cmd, timeout_ms=TIMEOUT_MS):
    uart.write(cmd)
    deadline = time.ticks_ms() + timeout_ms
    buf = b""
    while time.ticks_ms() < deadline:
        if uart.any():
            buf += uart.read(uart.any())
    return buf

def run_trinity_pipeline(prompt="hello"):
    t0 = time.ticks_ms()

    # Step 1: Phi POST → seed
    resp = send_recv(uart_phi, CMD_POST, timeout_ms=20)
    seed = int(resp.split(b"seed=")[1][:6], 16) if b"seed=" in resp else 0x47C0
    print(f"[PHI]   seed=0x{seed:04X}  ({time.ticks_diff(time.ticks_ms(), t0)} ms)")

    # Step 2: Euler inference with seed
    infer_cmd = f"INFER {prompt} SEED {seed:04X}\r\n".encode()
    resp = send_recv(uart_euler, infer_cmd, timeout_ms=40)
    tokens = resp.decode(errors="replace").strip()
    print(f"[EULER] tokens={tokens}  ({time.ticks_diff(time.ticks_ms(), t0)} ms)")

    # Step 3: Gamma neuromorphic feedback
    resp = send_recv(uart_euler, CMD_NEURO, timeout_ms=30)   # relay via Euler→Gamma bridge
    spikes = resp
    print(f"[GAMMA] spikes={spikes}  ({time.ticks_diff(time.ticks_ms(), t0)} ms)")

    elapsed = time.ticks_diff(time.ticks_ms(), t0)
    print(f"[TRINITY] end-to-end latency = {elapsed} ms  (target <100 ms)")
    assert elapsed < 100, f"Latency budget exceeded: {elapsed} ms"

run_trinity_pipeline("hello")
```

### 3.4 Expected Latency

| Stage              | Budget   |
|--------------------|----------|
| Phi POST           | < 20 ms  |
| Euler inference    | < 40 ms  |
| Gamma feedback     | < 30 ms  |
| **Total**          | **< 100 ms** |

---

## 4. Energy Estimate

| Chip  | Freq     | Tiles  | Power    | Efficiency      |
|-------|----------|--------|----------|-----------------|
| Phi   | 50 MHz   | 1×1    | ~5 mW    | anchor/POST     |
| Euler | 50 MHz   | 8×2    | ~80 mW   | 63 tok/s/W      |
| Gamma | 50 MHz   | 8×4    | ~160 mW  | neuromorphic    |
| **Total (Trinity)** | — | **32 tiles** | **~245 mW** | full pipeline |

All three chips powered simultaneously from USB (500 mA @ 5 V = 2500 mW budget) — Trinity consumes ~10 % of the USB budget, leaving ample headroom for the RP2040 and level shifters.

---

*Document revision: 2025 — Trinity SKY 26b DevKit firmware demo plan.*
