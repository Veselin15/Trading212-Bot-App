import type { MetadataRoute } from "next";

const BASE = process.env.NEXT_PUBLIC_SITE_URL || "https://swifttrade.app";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  return [
    { url: BASE,                  lastModified: now, changeFrequency: "weekly",  priority: 1.0 },
    { url: `${BASE}/product`,     lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: `${BASE}/pricing`,     lastModified: now, changeFrequency: "weekly",  priority: 0.9 },
    { url: `${BASE}/faq`,         lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: `${BASE}/download`,    lastModified: now, changeFrequency: "monthly", priority: 0.8 },
  ];
}
