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
        <h2 className="text-3xl font-semibold tracking-tight">{title}</h2>
        {lead ? <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">{lead}</p> : null}
        <div className="mt-8 w-full min-w-0">{children}</div>
      </section>
    </Container>
  );
}
