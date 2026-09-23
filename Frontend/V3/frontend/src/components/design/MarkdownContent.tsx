import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import "katex/dist/katex.min.css";

export function MarkdownContent({ content, muted = false }: { content: string; muted?: boolean }) {
  return <div className={`ai-markdown ${muted ? "ai-markdown-muted" : ""}`}>
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{
        a: ({ href, children }) => href && /^(https?:\/\/|#)/i.test(href)
          ? <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
          : <span>{children}</span>,
        img: () => null,
      }}
    >{content}</ReactMarkdown>
  </div>;
}
