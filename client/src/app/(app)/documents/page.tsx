import type { Metadata } from "next";

import { PhasePlaceholder } from "@/components/layout/PhasePlaceholder";

export const metadata: Metadata = { title: "Knowledge Base" };

/** TEMPORARY: replaced by the document management page in Phase 9. */
export default function DocumentsPage() {
  return <PhasePlaceholder title="Knowledge Base" phase={9} />;
}
