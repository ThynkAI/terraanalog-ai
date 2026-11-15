"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function Markdown({ text }: { text: string }) {
  return (
    <div className="prose-terra space-y-3 text-sm leading-relaxed text-lunar-200 [&_a]:text-mars-300 [&_a]:underline [&_blockquote]:rounded [&_blockquote]:border-l-4 [&_blockquote]:border-pink-400/60 [&_blockquote]:bg-pink-500/10 [&_blockquote]:px-3 [&_blockquote]:py-2 [&_blockquote]:text-pink-100 [&_code]:rounded [&_code]:bg-white/10 [&_code]:px-1 [&_code]:font-mono [&_code]:text-[12px] [&_h1]:text-xl [&_h1]:font-semibold [&_h1]:text-white [&_h2]:mt-5 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:text-white [&_li]:ml-5 [&_ol]:list-decimal [&_table]:w-full [&_td]:border-b [&_td]:border-white/5 [&_td]:px-2 [&_td]:py-1 [&_th]:border-b [&_th]:border-white/10 [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_ul]:list-disc">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Document headings are demoted so each page keeps exactly one <h1>.
          h1: ({ children }) => <h2 className="text-xl font-semibold text-white">{children}</h2>,
          h2: ({ children }) => <h3 className="mt-5 text-base font-semibold text-white">{children}</h3>,
          h3: ({ children }) => <h4 className="mt-4 text-sm font-semibold text-white">{children}</h4>,
          // Wide research tables scroll inside their own focusable region instead of overflowing the page on mobile.
          table: ({ children }) => (
            <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Scrollable table">
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
