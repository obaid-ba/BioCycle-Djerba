import { Trash2 } from "lucide-react";

import { PagePlaceholder } from "@/components/common/PagePlaceholder";

export function Bins() {
  return (
    <PagePlaceholder
      title="Smart Bins"
      description="Sensor-equipped bins reporting fill level, weight, and battery."
      icon={Trash2}
    />
  );
}
