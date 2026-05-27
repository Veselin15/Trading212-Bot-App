# Forward Stripe test webhooks to the local Next.js portal (port 3000).
# Only needed while testing checkout — not required for normal dev.
#
# Usage (from repo root):
#   .\scripts\stripe-webhooks.ps1
#
# From web/:
#   npm run stripe:listen

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envFile = Join-Path $repoRoot "web\.env.local"
$forwardUrl = "localhost:3000/api/stripe/webhook"
$events =
  "checkout.session.completed,customer.subscription.created,customer.subscription.updated,customer.subscription.deleted,invoice.payment_failed,invoice.payment_succeeded,invoice.paid"

function Test-StripeSecretKey {
  if (-not (Test-Path $envFile)) {
    throw "Missing web/.env.local. Copy web/.env.local.example and set STRIPE_SECRET_KEY."
  }
  $hasKey = Select-String -Path $envFile -Pattern '^\s*STRIPE_SECRET_KEY\s*=\s*\S+' -Quiet
  if (-not $hasKey) {
    throw "STRIPE_SECRET_KEY is not set in web/.env.local."
  }
}

function Show-WebhookInstructions {
  Write-Host ""
  Write-Host "Stripe webhook forwarding (local dev only)" -ForegroundColor Cyan
  Write-Host "  1. Keep this window open while testing checkout." -ForegroundColor Gray
  Write-Host "  2. Run the web portal in another terminal: cd web; npm run dev" -ForegroundColor Gray
  Write-Host "  3. Copy the whsec_... secret from the output below into web/.env.local as STRIPE_WEBHOOK_SECRET." -ForegroundColor Gray
  Write-Host "  4. Restart npm run dev after updating the secret." -ForegroundColor Gray
  Write-Host ""
  Write-Host "If you skip this, reload /dashboard after checkout — subscription syncs from Stripe API." -ForegroundColor DarkGray
  Write-Host ""
}

Set-Location $repoRoot
Test-StripeSecretKey
Show-WebhookInstructions

function Get-DockerExe {
  $cmd = Get-Command docker -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  $candidates = @(
    "${env:ProgramFiles}\Docker\Docker\resources\bin\docker.exe",
    "${env:ProgramFiles(x86)}\Docker\Docker\resources\bin\docker.exe"
  )
  foreach ($path in $candidates) {
    if (Test-Path $path) { return $path }
  }
  return $null
}

$dockerExe = Get-DockerExe
if ($dockerExe) {
  Write-Host "Starting Stripe CLI via Docker (profile: stripe)..." -ForegroundColor Green
  & $dockerExe compose --profile stripe up stripe-cli
  exit $LASTEXITCODE
}

$stripe = Get-Command stripe -ErrorAction SilentlyContinue
if ($stripe) {
  Write-Host "Docker not found — using native Stripe CLI..." -ForegroundColor Yellow
  & stripe listen --forward-to $forwardUrl --events $events
  exit $LASTEXITCODE
}

throw @"
Neither Docker nor the Stripe CLI was found.

Install one of:
  - Docker Desktop, then re-run this script
  - Stripe CLI: https://stripe.com/docs/stripe-cli
"@
