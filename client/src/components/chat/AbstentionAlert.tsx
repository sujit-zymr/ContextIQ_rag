import { TriangleAlert } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

/**
 * Shown instead of an answer when the backend abstained because the knowledge
 * base did not contain enough evidence (plan §7.4, §9). The backend's internal
 * `answer_reason` is deliberately not shown.
 */
export function AbstentionAlert() {
  return (
    <Alert className="border-warning/30 bg-warning/10 text-warning *:data-[slot=alert-description]:text-warning/90">
      <TriangleAlert aria-hidden />
      <AlertTitle>Not enough information</AlertTitle>
      <AlertDescription>
        The knowledge base did not contain enough information to answer this question.
      </AlertDescription>
    </Alert>
  );
}
