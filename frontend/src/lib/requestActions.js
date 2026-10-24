import { useCallback, useState } from "react";
import { acceptRequest, setRequestStatus } from "../api";
import { SOS_STEPS } from "../constants";
import { useToast } from "../state/contexts";

const DONE = {
  ACKNOWLEDGED: "Accepted. The citizen now sees your organisation as the responder.",
  DISPATCHED: "The citizen now sees that help is on the way.",
  RESOLVED: "The request is closed.",
};

// Accept a request or move it on (provider), with a toast either way; `refresh` reloads the board.
export function useRequestActions(refresh) {
  const toast = useToast();
  const [busyId, setBusyId] = useState(null);
  const act = useCallback(
    async (sos, action) => {
      setBusyId(sos.id);
      try {
        const updated = action === "accept" ? await acceptRequest(sos.id) : await setRequestStatus(sos.id, action);
        toast.success(`Request #${sos.id}: ${SOS_STEPS[updated.status].label}`, DONE[updated.status]);
      } catch (err) {
        toast.error(`Request #${sos.id} not updated`, err.message);
      } finally {
        setBusyId(null);
        refresh();
      }
    },
    [toast, refresh],
  );
  return { busyId, act };
}
