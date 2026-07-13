import { Check, Loader2, Truck } from "lucide-react";
import { useState } from "react";

import { CollectDialog } from "@/components/requests/CollectDialog";
import { DecisionDialog } from "@/components/requests/DecisionDialog";
import { Button } from "@/components/ui/button";
import { useDecideRequest, useTransitionRequest } from "@/hooks/useRequests";
import { useToast } from "@/context/toast";
import { messageFromError } from "@/lib/errors";
import { nextActionsFor } from "@/lib/requestStatus";
import type { CollectionRequest } from "@/types";

/**
 * Renders exactly the operator actions legal from the request's current status,
 * per `nextActionsFor` — the frontend mirror of the backend state machine, so
 * the UI never offers a move the API would 409.
 */
export function RequestActions({ request }: { request: CollectionRequest }) {
  const [decisionOpen, setDecisionOpen] = useState(false);
  const [collectOpen, setCollectOpen] = useState(false);

  const toast = useToast();
  const decideMut = useDecideRequest();
  const transitionMut = useTransitionRequest();

  const actions = nextActionsFor(request.status);
  if (actions.length === 0) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }

  async function advance(target: "on_the_way" | "completed") {
    try {
      await transitionMut.mutateAsync({ id: request.id, payload: { target } });
      toast.success(
        target === "on_the_way" ? "Marked on the way." : "Request completed.",
      );
    } catch (error) {
      toast.error(messageFromError(error, "Could not update the request."));
    }
  }

  const busy = transitionMut.isPending;

  return (
    <div className="flex justify-end gap-1">
      {actions.includes("decide") && (
        <Button size="sm" onClick={() => setDecisionOpen(true)}>
          Review
        </Button>
      )}

      {actions.includes("on_the_way") && (
        <Button size="sm" variant="outline" disabled={busy} onClick={() => advance("on_the_way")}>
          {busy ? <Loader2 className="animate-spin" /> : <Truck />}
          On the way
        </Button>
      )}

      {actions.includes("collected") && (
        <Button size="sm" variant="outline" onClick={() => setCollectOpen(true)}>
          <Check />
          Collected
        </Button>
      )}

      {actions.includes("completed") && (
        <Button size="sm" disabled={busy} onClick={() => advance("completed")}>
          {busy ? <Loader2 className="animate-spin" /> : <Check />}
          Complete
        </Button>
      )}

      {decisionOpen && (
        <DecisionDialog
          open={decisionOpen}
          request={request}
          onClose={() => setDecisionOpen(false)}
          onSubmit={async (payload) => {
            await decideMut.mutateAsync({ id: request.id, payload });
            toast.success(payload.accept ? "Request accepted." : "Request rejected.");
          }}
        />
      )}

      {collectOpen && (
        <CollectDialog
          open={collectOpen}
          request={request}
          onClose={() => setCollectOpen(false)}
          onSubmit={async (payload) => {
            await transitionMut.mutateAsync({ id: request.id, payload });
            toast.success("Collection confirmed.");
          }}
        />
      )}
    </div>
  );
}
