# Antivirus false positives (Avast / Defender SmartScreen)

When users run `SwiftTrade.exe`, Avast may **pop up, close the app, scan it, then
reopen it**. This is Avast **CyberCapture / DeepScreen**, not a permissions/UAC
prompt the user can grant once. It happens to almost every unsigned PyInstaller
app and has four causes:

1. **The EXE is unsigned** — no Authenticode publisher, so the OS and AV have no
   identity to trust.
2. **Low prevalence** — Avast has never seen this exact file before. Every rebuild
   is a brand-new, "rare" file, which CyberCapture treats as suspicious by default.
3. **PyInstaller bootloader heuristics** — a lot of commodity malware is also
   built with PyInstaller, so the unpack-and-run pattern scores badly.
4. **Missing metadata** — an EXE with no company/product/version resource looks
   anonymous.

There is **no single switch** that removes this. You reduce it with metadata
(already done) and you *eliminate* it with **code signing + reputation** (the real
fix). Below is the full picture.

---

## 1. What is already built in (free, no certificate)

These ship in the repo and are applied automatically by `SwiftTrade.spec`:

| Mitigation | File | Effect |
|---|---|---|
| Version metadata (CompanyName, ProductName, version, copyright) | `desktop/version_info.txt` | EXE no longer looks anonymous |
| Application icon (multi-resolution) | `desktop/assets/SwiftTrade.ico` | Real icon instead of the generic blank one |
| `asInvoker` manifest (no admin request) | `desktop/SwiftTrade.manifest` | Avoids UAC + the "wants elevation" suspicion |
| One-folder build, no UPX packing | `SwiftTrade.spec` | UPX-packed / one-file EXEs score worse with AV |
| Ship a ZIP, not a bare EXE | build script | Slightly better download reputation |

These **lower** the false-positive rate but will **not** fully stop Avast
CyberCapture on a brand-new unsigned build.

---

## 2. The real fix — code signing (do this for production)

A valid **Authenticode signature** gives the EXE a verifiable publisher. Avast and
SmartScreen trust signed binaries and, just as importantly, **reputation
accumulates against your certificate** — so every future build inherits the trust
you have already earned instead of starting from zero.

### Certificate options

| Type | Cost (approx.) | SmartScreen | Notes |
|---|---|---|---|
| **OV** (Organization Validation) | ~$200–400 / yr | Builds reputation over days/weeks | Cheapest; reputation ramps up as users run it |
| **EV** (Extended Validation) | ~$300–600 / yr | **Instant** SmartScreen trust | Ships on a hardware token / HSM; best for a paid product |

Buy from a CA that chains to a Microsoft-trusted root: **DigiCert, Sectigo,
SSL.com, GlobalSign, Certera**. For a product you sell, **EV** is worth it — no
"Windows protected your PC" wall on day one.

### Signing a build

The build script already supports it. Once you have a cert:

```powershell
# Option A — PFX file
.\desktop\scripts\build-windows.ps1 `
    -DefaultExecutorWsUrl "wss://signals.swifttrade.app/ws/exec" `
    -SignCertFile "C:\path\to\swifttrade.pfx" -SignCertPassword "••••••"

# Option B — certificate already installed in your Windows cert store (e.g. EV token)
.\desktop\scripts\build-windows.ps1 `
    -DefaultExecutorWsUrl "wss://signals.swifttrade.app/ws/exec" `
    -SignSubject "SwiftTrade Ltd"
```

The script finds `signtool.exe` (Windows SDK), signs with SHA-256, **timestamps**
the signature (so it stays valid after the cert expires), and verifies the chain.
Signing is skipped automatically when no cert argument is passed (dev builds).

> Install signtool via the **Windows 10/11 SDK** ("Windows App Certification" /
> "Signing Tools for Desktop Apps" component) if it is not already present.

---

## 3. Submit a false-positive report to Avast

Even signed, a brand-new build can be flagged once before reputation kicks in.
Whitelist it directly with the vendors:

- **Avast / AVG:** https://www.avast.com/false-positive-file-form.php
  (upload `SwiftTrade.exe`, category "I believe this file is safe").
- **Microsoft Defender:** https://www.microsoft.com/wdsi/filesubmission
- Optionally submit to https://www.virustotal.com to monitor which engines flag it.

Turnaround is usually 24–72h. Re-submit after a version bump if a specific engine
keeps flagging it. With an EV cert this step is rarely needed.

---

## 4. End-user workaround (last resort)

For the occasional user whose Avast still nags before reputation is established,
they can allow the app once:

1. Open **Avast → Menu → Settings → General → Exceptions → Add Exception**.
2. Add the folder where `SwiftTrade.exe` lives (e.g. the extracted ZIP folder).
3. Optionally **Avast → Protection → Virus Chest** → restore the file if it was
   quarantined, and mark it safe.

Keep this as a documented fallback in your install guide — it should not be the
primary experience. Signing is what removes the need for it.

---

## TL;DR priority order

1. ✅ Metadata + icon + manifest — **done, in the repo.**
2. ⭐ Buy an **EV (or OV) code-signing certificate** and build with `-SignCertFile`
   / `-SignSubject`. This is the only durable fix.
3. Submit the build to Avast's false-positive form for the first release.
4. Document the Avast exception steps in the customer install guide as a fallback.
