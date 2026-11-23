import { useMemo } from "react";
import ReactMarkdown, { type Components, type Options } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import { CitationChip } from "@/components/sources/CitationChip";
import { rehypeCitationMarkers } from "@/lib/citations";
import { cn } from "@/lib/utils";
import type { Citation } from "@/types/api";

/** Links in AI answers open in a new tab without giving the target page access to ours. */
const link: Components["a"] = ({ href, title, children }) => (
  <a href={href} title={title} target="_blank" rel="noopener noreferrer">
    {children}
  </a>
);

const remarkPlugins: Options["remarkPlugins"] = [remarkGfm];

interface MarkdownContentProps {
  content: string;
  className?: string;
  /** When given, [S1] markers matching these citations render as clickable chips. */
  citations?: { messageId: string; items: Citation[] };
}

/**
 * Renders AI answer markdown (plan §2): GFM tables/lists, highlighted code,
 * inline citation chips. Raw HTML in the answer is NOT rendered
 * (react-markdown escapes it).
 */
export function MarkdownContent({ content, className, citations }: Readonly<MarkdownContentProps>) {
  const { rehypePlugins, components } = useMemo(() => {
    const items = citations?.items ?? [];
    if (!citations || items.length === 0) {
      return { rehypePlugins: [rehypeHighlight], components: { a: link } satisfies Components };
    }
    const bySourceId = new Map(items.map((c) => [c.source_id, c]));
    const cite: Components["cite"] = ({ node, children }) => {
      const sourceId = node?.properties?.dataSourceId;
      const citation = typeof sourceId === "string" ? bySourceId.get(sourceId) : undefined;
      return citation ? (
        <CitationChip messageId={citations.messageId} citation={citation} />
      ) : (
        <>{children}</>
      );
    };
    return {
      rehypePlugins: [
        rehypeHighlight,
        [rehypeCitationMarkers, { sourceIds: new Set(bySourceId.keys()) }],
      ] satisfies Options["rehypePlugins"],
      components: { a: link, cite } satisfies Components,
    };
  }, [citations]);

  return (
    <div
      className={cn(
        "prose prose-sm max-w-none leading-relaxed dark:prose-invert md:prose-base",
        "prose-headings:font-semibold prose-headings:tracking-tight",
        "prose-a:text-primary prose-strong:text-foreground",
        "prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:font-mono prose-code:before:content-none prose-code:after:content-none",
        "prose-pre:border prose-pre:bg-muted/60 prose-pre:text-foreground [&_pre_code]:bg-transparent [&_pre_code]:p-0",
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={remarkPlugins} rehypePlugins={rehypePlugins} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
