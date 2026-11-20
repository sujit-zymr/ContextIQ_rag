import ReactMarkdown, { type Components } from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

/** Links in AI answers open in a new tab without giving the target page access to ours. */
const components: Components = {
  a: ({ href, title, children }) => (
    <a href={href} title={title} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
};

/**
 * Renders AI answer markdown (plan §2): GFM tables/lists, highlighted code.
 * Raw HTML in the answer is NOT rendered (react-markdown escapes it).
 */
export function MarkdownContent({ content, className }: { content: string; className?: string }) {
  return (
    <div
      className={cn(
        "prose prose-sm max-w-none leading-relaxed prose-invert md:prose-base",
        "prose-headings:font-semibold prose-headings:tracking-tight",
        "prose-a:text-primary prose-strong:text-foreground",
        "prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:font-mono prose-code:before:content-none prose-code:after:content-none",
        "prose-pre:border prose-pre:bg-muted/60 [&_pre_code]:bg-transparent [&_pre_code]:p-0",
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
