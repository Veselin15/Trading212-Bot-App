import { redirect } from "next/navigation";

// Backwards-compatible route: the protected portal is now under `/dashboard`.
export default async function AccountPage() {
  redirect("/dashboard");
}

