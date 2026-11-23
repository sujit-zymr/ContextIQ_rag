import type { Metadata } from "next";

import { DocumentsView } from "@/components/documents/DocumentsView";

export const metadata: Metadata = { title: "Knowledge Base" };

/** Signed-in only: RequireAuth renders a loader on the server, so instant validation can't render this page. */
export const instant = false;

/** Shared document management (plan §7.7). */
export default function DocumentsPage() {
  return <DocumentsView />;
}
