/**
 * One-off Supabase setup check. Reads web/.env.local and backend/.env.
 * Does not print secret values.
 */
import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

function parseEnvFile(path) {
  if (!existsSync(path)) return {};
  const out = {};
  for (const line of readFileSync(path, "utf8").split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#")) continue;
    const i = t.indexOf("=");
    if (i < 1) continue;
    out[t.slice(0, i).trim()] = t.slice(i + 1).trim();
  }
  return out;
}

function mask(s) {
  if (!s || s.length < 12) return s ? "(set, short)" : "(missing)";
  return `${s.slice(0, 8)}…${s.slice(-4)} (${s.length} chars)`;
}

const webEnv = parseEnvFile(join(root, "web", ".env.local"));
const backendEnv = parseEnvFile(join(root, "backend", ".env"));

const webUrl = webEnv.NEXT_PUBLIC_SUPABASE_URL || "";
const webAnon = webEnv.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";
const webService = webEnv.SUPABASE_SERVICE_ROLE_KEY || "";
const backendUrl = backendEnv.SUPABASE_URL || "";
const backendService = backendEnv.SUPABASE_SERVICE_ROLE_KEY || "";
const siteUrl = webEnv.NEXT_PUBLIC_SITE_URL || "(not set)";

console.log("\n=== Env files ===\n");
console.log("web/.env.local exists:", existsSync(join(root, "web", ".env.local")));
console.log("backend/.env exists:", existsSync(join(root, "backend", ".env")));
console.log("NEXT_PUBLIC_SUPABASE_URL:", webUrl || "(missing)");
console.log("NEXT_PUBLIC_SUPABASE_ANON_KEY:", mask(webAnon));
console.log("web SUPABASE_SERVICE_ROLE_KEY:", mask(webService));
console.log("backend SUPABASE_URL:", backendUrl || "(missing)");
console.log("backend SUPABASE_SERVICE_ROLE_KEY:", mask(backendService));
console.log("URLs match:", Boolean(webUrl && webUrl === backendUrl));
console.log(
  "Service keys match:",
  Boolean(webService && webService === backendService),
);
console.log("NEXT_PUBLIC_SITE_URL:", siteUrl);

if (!webUrl || !webService) {
  console.error("\nMissing web Supabase env — cannot continue.");
  process.exit(1);
}

const headers = {
  apikey: webService,
  Authorization: `Bearer ${webService}`,
  Accept: "application/json",
};

async function probeTable(name, columns = "id") {
  const url = `${webUrl}/rest/v1/${name}?select=${columns}&limit=1`;
  const res = await fetch(url, { headers });
  const text = await res.text();
  let body;
  try {
    body = JSON.parse(text);
  } catch {
    body = text.slice(0, 200);
  }
  return { name, status: res.status, ok: res.ok, body };
}

async function probeLicensesColumns() {
  const url = `${webUrl}/rest/v1/licenses?select=id,expires_at,last_ip_address,last_seen_at&limit=0`;
  const res = await fetch(url, { headers });
  const text = await res.text();
  const missingCol =
    /column.*does not exist|Could not find the '([^']+)' column/i.test(text);
  return { status: res.status, ok: res.ok, missingCol, snippet: text.slice(0, 180) };
}

console.log("\n=== Tables (service role) ===\n");
for (const table of ["subscriptions", "licenses", "signals"]) {
  const r = await probeTable(table);
  if (r.ok) {
    console.log(`✓ public.${table} — reachable (HTTP ${r.status})`);
  } else if (r.status === 404 || String(r.body).includes("does not exist")) {
    console.log(`✗ public.${table} — MISSING (run migrations)`);
  } else {
    console.log(`? public.${table} — HTTP ${r.status}:`, r.body);
  }
}

console.log("\n=== Migration 3 columns on licenses ===\n");
const licCols = await probeLicensesColumns();
if (licCols.ok) {
  console.log("✓ expires_at, last_ip_address, last_seen_at — present");
} else if (licCols.missingCol) {
  console.log("✗ licenses missing enforcement columns — run 20260428_000003 migration");
  console.log("  ", licCols.snippet);
} else {
  console.log("? licenses column check:", licCols.status, licCols.snippet);
}

// Anon key smoke (read-only probe)
if (webAnon) {
  const anonRes = await fetch(`${webUrl}/rest/v1/subscriptions?select=id&limit=1`, {
    headers: { apikey: webAnon, Authorization: `Bearer ${webAnon}` },
  });
  console.log("\n=== Anon key ===\n");
  console.log(
    anonRes.ok
      ? `✓ anon key accepted (HTTP ${anonRes.status})`
      : `? anon probe HTTP ${anonRes.status}`,
  );
}

console.log("\n=== Auth URL config (manual in dashboard) ===\n");
console.log("Cannot read Site URL / Redirect URLs via API from this script.");
console.log("In Supabase → Authentication → URL configuration, you should have:");
console.log(`  Site URL: ${siteUrl}`);
console.log(`  Redirect: ${siteUrl.replace(/\/$/, "")}/auth/callback`);
console.log("(Update both when you move off localhost.)\n");
