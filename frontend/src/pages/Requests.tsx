import { HotelRequestsView } from "@/components/requests/HotelRequestsView";
import { OperatorQueueView } from "@/components/requests/OperatorQueueView";
import { useAuth } from "@/context/auth";

/**
 * Single `/requests` route with a role-aware face:
 *  - hotel_manager → their own requests + a create action
 *  - operator      → the priority-sorted collection queue with actions
 *  - admin         → the same queue, read-only (supervision)
 */
export function Requests() {
  const { user } = useAuth();

  if (user?.role === "hotel_manager") {
    return <HotelRequestsView />;
  }
  return <OperatorQueueView readOnly={user?.role === "admin"} />;
}
