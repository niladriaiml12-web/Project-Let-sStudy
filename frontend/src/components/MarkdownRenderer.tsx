import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import rehypeKatex from 'rehype-katex'
import remarkMath from 'remark-math'
import { Copy, Check } from 'lucide-react'
import { useState } from 'react'

interface CodeBlockProps {
  children?: React.ReactNode
  className?: string
  inline?: boolean
}

function CodeBlock({ children, className, inline }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)
  const code = String(children).replace(/\n$/, '')

  if (inline) {
    return (
      <code className="font-mono text-sm bg-[#1a1a2e] text-purple-300 px-1.5 py-0.5 rounded">
        {children}
      </code>
    )
  }

  const copy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative group my-3">
      <button
        onClick={copy}
        className="absolute top-2 right-2 p-1.5 rounded bg-[#262626] text-[#a0a0a0] hover:text-white opacity-0 group-hover:opacity-100 transition-opacity z-10"
        aria-label="Copy code"
      >
        {copied ? <Check size={13} /> : <Copy size={13} />}
      </button>
      <pre className="overflow-x-auto rounded-lg bg-[#0f0f1a] border border-[#2a2a2a] p-4 text-sm font-mono">
        <code className={className}>{children}</code>
      </pre>
    </div>
  )
}

interface MarkdownRendererProps {
  content: string
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="prose prose-sm max-w-none text-[#f0f0f0]">
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeHighlight, rehypeKatex]}
        components={{
          code: ({ className, children, ...props }) => (
            <CodeBlock className={className} {...props}>
              {children}
            </CodeBlock>
          ),
          // Tables
          table: ({ children }) => (
            <div className="overflow-x-auto my-3">
              <table className="w-full text-sm border-collapse border border-[#2a2a2a]">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 bg-[#1f1f1f] text-left text-[#f0f0f0] border border-[#2a2a2a] font-semibold text-xs uppercase tracking-wider">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 border border-[#2a2a2a] text-[#c0c0c0]">{children}</td>
          ),
          // Blockquotes
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-[#3D46E8] pl-4 my-3 text-[#a0a0a0] italic">
              {children}
            </blockquote>
          ),
          // Links
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noopener noreferrer"
               className="text-[#B18CFF] hover:text-[#FFD6E7] underline transition-colors">
              {children}
            </a>
          ),
          // Headings
          h1: ({ children }) => (
            <h1 className="text-xl font-bold text-white mt-4 mb-2">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-semibold text-white mt-3 mb-2">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-semibold text-[#B18CFF] mt-2 mb-1">{children}</h3>
          ),
          // Strong
          strong: ({ children }) => (
            <strong className="font-semibold text-[#B18CFF]">{children}</strong>
          ),
          // Horizontal rule
          hr: () => <hr className="border-[#2a2a2a] my-4" />,
          // Lists
          ul: ({ children }) => (
            <ul className="list-disc list-inside space-y-1 my-2 text-[#d0d0d0]">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside space-y-1 my-2 text-[#d0d0d0]">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="leading-relaxed">{children}</li>
          ),
          p: ({ children }) => (
            <p className="leading-relaxed my-2 text-[#d8d8d8]">{children}</p>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
