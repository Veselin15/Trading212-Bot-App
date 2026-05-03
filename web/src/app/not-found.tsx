import { Home } from "lucide-react";

import { BrandLogo } from "@/components/BrandLogo";
import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <main>
      <Container className="py-20">
        <div className="mx-auto max-w-2xl text-center">
          <div className="mb-8 flex justify-center">
            <BrandLogo variant="header" />
          </div>
          <h1 className="mb-4 text-6xl">404</h1>
          <h2 className="mb-4 text-3xl">Page not found</h2>
          <p className="mb-8 text-slate-400">The page you&apos;re looking for doesn&apos;t exist or has been moved.</p>

          <ButtonLink href="/" className="gap-2 bg-emerald-600 hover:bg-emerald-400">
            <Home className="h-4 w-4" />
            Go home
          </ButtonLink>
        </div>
      </Container>
    </main>
  );
}

