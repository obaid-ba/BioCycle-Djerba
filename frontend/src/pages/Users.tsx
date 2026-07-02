import { Users as UsersIcon } from "lucide-react";

import { PagePlaceholder } from "@/components/common/PagePlaceholder";

export function Users() {
  return (
    <PagePlaceholder
      title="Users"
      description="Manage platform accounts and roles (administrators only)."
      icon={UsersIcon}
    />
  );
}
