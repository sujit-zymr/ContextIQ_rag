import type { Metadata } from "next";

import { DocumentsView } from "@/components/documents/DocumentsView";

export const metadata: Metadata = { title: "Knowledge Base" };

/** Shared document management (plan §7.7). */
export default function DocumentsPage() {
  return <DocumentsView />;
}
