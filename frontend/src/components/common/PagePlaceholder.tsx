import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

interface PagePlaceholderProps {
  title: string;
  description: string;
  icon: LucideIcon;
}

/** Temporary content for routes whose real screens land in later phases. */
export function PagePlaceholder({
  title,
  description,
  icon: Icon,
}: PagePlaceholderProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        <p className="text-muted-foreground">{description}</p>
      </div>
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <div className="flex size-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Icon className="size-6" />
          </div>
          <p className="text-sm text-muted-foreground">
            This screen is coming in a later phase.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
