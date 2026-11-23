import type { Citation } from "@/types/api";

/** Inline marker the backend keeps in answers, e.g. [S1] (server/app/generation/answerer.py). */
const CITATION_MARKER = /\[(S\d+)\]/g;

/** Elements whose text must stay literal (code samples may contain "[S1]"). */
const SKIP_TAGS = new Set(["code", "pre"]);

/** Minimal hast node shape; enough for this plugin without depending on @types/hast. */
interface HastNode {
  type: string;
  tagName?: string;
  value?: string;
  properties?: Record<string, unknown>;
  children?: HastNode[];
}

function splitMarkers(text: string, sourceIds: ReadonlySet<string>): HastNode[] | null {
  const parts: HastNode[] = [];
  let last = 0;
  for (const match of text.matchAll(CITATION_MARKER)) {
    if (!sourceIds.has(match[1])) continue;
    if (match.index > last) parts.push({ type: "text", value: text.slice(last, match.index) });
    parts.push({
      type: "element",
      tagName: "cite",
      properties: { dataSourceId: match[1] },
      children: [{ type: "text", value: match[0] }],
    });
    last = match.index + match[0].length;
  }
  if (parts.length === 0) return null;
  if (last < text.length) parts.push({ type: "text", value: text.slice(last) });
  return parts;
}

function transform(node: HastNode, sourceIds: ReadonlySet<string>) {
  if (!node.children) return;
  if (node.type === "element" && SKIP_TAGS.has(node.tagName ?? "")) return;
  node.children = node.children.flatMap((child) => {
    if (child.type === "text") return splitMarkers(child.value ?? "", sourceIds) ?? [child];
    transform(child, sourceIds);
    return [child];
  });
}

/**
 * rehype plugin: turns [S1] markers that match one of the message's citations
 * into `<cite data-source-id="S1">` elements, which MarkdownContent renders as
 * CitationChips. Unknown markers and markers inside code stay plain text.
 */
export function rehypeCitationMarkers(options: { sourceIds: ReadonlySet<string> }) {
  return (tree: HastNode) => transform(tree, options.sourceIds);
}

/** Version labels of other revisions (backend sends strings; ignore anything else). */
export function getCompetingVersions(citation: Citation): string[] {
  if (!citation.has_competing_versions) return [];
  return citation.competing_versions.filter((v): v is string => typeof v === "string");
}
