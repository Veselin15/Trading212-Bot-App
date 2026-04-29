import { type ReactNode } from "react";

import { Container } from "@/components/ui/Container";

export function Section({
  title,
  lead,
  children,
  id,
}: {
  title: ReactNode;
  lead?: ReactNode;
  children: ReactNode;
  id?: string;
}) {
  return (
    <Container>
      <section id={id} className="pb-16 sm:pb-20">
        <div className="grid gap-10 lg:grid-cols-12 lg:items-end">
          <div className="lg:col-span-4">
            <h2 className="text-3xl font-semibold tracking-tight">{title}</h2>
            {lead ? <p className="mt-3 text-sm leading-6 text-slate-300">{lead}</p> : null}
          </div>
          <div className="lg:col-span-8">{children}</div>
        </div>
      </section>
    </Container>
  );
}

