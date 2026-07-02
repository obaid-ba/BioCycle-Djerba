import { Bell } from "lucide-react";

import { PagePlaceholder } from "@/components/common/PagePlaceholder";

export function Alerts() {
  return (
    <PagePlaceholder
      title="Alerts"
      description="Operational alerts for full bins, low batteries, and system events."
      icon={Bell}
    />
  );
}
