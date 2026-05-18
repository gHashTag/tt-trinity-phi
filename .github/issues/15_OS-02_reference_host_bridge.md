# [OS-02] Reference host bridge in `examples/`

**Local plan ID:** `#15` (placeholder).
**Track:** OS-02.
**SIP section:** §6.
**Labels:** `track:OS`, `area:integration`, `r5:target`, `type:example`.

## Goal (target)

Add a reference host bridge under [`examples/`](../../examples/) that
implements the verification flow described in
[`TRI_NET_API.md`](../../TRI_NET_API.md) §2 — verify the canonical
anchor `0x47C0`, exercise Lucas POST, read the HWRNG nonce.

## Scope

- Either MCU C (e.g. RP2040 stub) or Python on a USB / FT2232 bridge.
- Read-only: no on-die signing performed here.
- Documented as `target` — only useful once silicon is in hand.

## Done when

- [ ] Reference bridge lands under `examples/`.
- [ ] [`TRI_NET_API.md`](../../TRI_NET_API.md) §2 cross-links it.

## Anti-claims

- No claim that silicon has been characterised against this bridge.
- The example is illustrative, not a vendor-supported SDK.
