/**
 * frontend/src/components/chatbot/MarkdownRenderer.jsx
 *
 * Rich Markdown, Code, and Table rendering for chatbot responses.
 * Renders:
 * - Markdown tables with responsive container, borders, and column alignment
 * - Fenced code blocks with language badge and copy-to-clipboard button
 * - Headers, lists, blockquotes, inline code chips, and bold/italic formatting
 */

import React, { useState } from 'react';

function CodeBlock({ code, language }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative my-3 rounded-lg overflow-hidden border border-white/10 bg-slate-950 font-mono text-xs shadow-md">
      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900 border-b border-white/10 text-[10px] text-gray-400">
        <span className="uppercase tracking-wider font-semibold text-cyan-400">
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          className="hover:text-white transition-colors flex items-center gap-1"
        >
          {copied ? (
            <span className="text-emerald-400">✓ Copied</span>
          ) : (
            <span>Copy</span>
          )}
        </button>
      </div>
      <pre className="p-3 overflow-x-auto text-gray-200 leading-relaxed font-mono">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function parseMarkdownTable(tableLines) {
  if (tableLines.length < 2) return null;

  const headerLine = tableLines[0];
  const separatorLine = tableLines[1];
  const dataLines = tableLines.slice(2);

  if (!separatorLine.includes('-')) return null;

  const parseRow = (line) =>
    line
      .split('|')
      .map((c) => c.trim())
      .filter((c, idx, arr) => !(idx === 0 && c === '') && !(idx === arr.length - 1 && c === ''));

  const headers = parseRow(headerLine);
  const rows = dataLines.map(parseRow);

  return { headers, rows };
}

export default function MarkdownRenderer({ content = '' }) {
  if (!content) return null;

  const lines = content.split('\n');
  const elements = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Fenced code block detection: ```lang
    if (line.trim().startsWith('```')) {
      const language = line.trim().replace(/^```/, '').trim();
      const codeLines = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      elements.push(
        <CodeBlock
          key={`code-${i}`}
          code={codeLines.join('\n')}
          language={language}
        />
      );
      i++;
      continue;
    }

    // Markdown Table detection: starts with | and next line has |---
    if (line.trim().startsWith('|') && i + 1 < lines.length && lines[i + 1].trim().startsWith('|')) {
      const tableLines = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i]);
        i++;
      }
      const tableData = parseMarkdownTable(tableLines);
      if (tableData) {
        elements.push(
          <div key={`table-${i}`} className="overflow-x-auto my-3 rounded-lg border border-white/10">
            <table className="min-w-full text-xs text-left border-collapse">
              <thead className="bg-slate-800/80 text-cyan-300 font-semibold border-b border-white/10">
                <tr>
                  {tableData.headers.map((h, idx) => (
                    <th key={idx} className="px-3 py-2 border-r border-white/10 last:border-r-0">
                      {renderInlineText(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 bg-slate-900/40">
                {tableData.rows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-white/5 transition-colors">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="px-3 py-1.5 border-r border-white/5 last:border-r-0 text-gray-300">
                        {renderInlineText(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
    }

    // Headers
    if (line.startsWith('### ')) {
      elements.push(
        <h3 key={`h3-${i}`} className="text-sm font-bold text-white mt-3 mb-1.5 flex items-center gap-1.5">
          {renderInlineText(line.replace('### ', ''))}
        </h3>
      );
      i++;
      continue;
    }
    if (line.startsWith('## ')) {
      elements.push(
        <h2 key={`h2-${i}`} className="text-base font-bold text-white mt-4 mb-2">
          {renderInlineText(line.replace('## ', ''))}
        </h2>
      );
      i++;
      continue;
    }
    if (line.startsWith('# ')) {
      elements.push(
        <h1 key={`h1-${i}`} className="text-lg font-extrabold text-white mt-4 mb-2">
          {renderInlineText(line.replace('# ', ''))}
        </h1>
      );
      i++;
      continue;
    }

    // Blockquote
    if (line.startsWith('> ')) {
      elements.push(
        <blockquote key={`quote-${i}`} className="border-l-2 border-cyan-400 bg-white/5 pl-3 py-1 my-2 text-xs italic text-gray-300 rounded-r">
          {renderInlineText(line.replace('> ', ''))}
        </blockquote>
      );
      i++;
      continue;
    }

    // Bullet lists
    if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
      const indent = line.search(/\S/);
      const content = line.trim().substring(2);
      elements.push(
        <div key={`li-${i}`} className="flex items-start gap-2 text-xs text-gray-200 my-0.5" style={{ paddingLeft: `${indent * 8}px` }}>
          <span className="text-cyan-400 mt-1 text-[8px]">•</span>
          <span className="leading-relaxed">{renderInlineText(content)}</span>
        </div>
      );
      i++;
      continue;
    }

    // Numbered lists
    const numMatch = line.trim().match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      elements.push(
        <div key={`numli-${i}`} className="flex items-start gap-2 text-xs text-gray-200 my-0.5 pl-1">
          <span className="font-mono text-cyan-400 text-xs font-semibold">{numMatch[1]}.</span>
          <span className="leading-relaxed">{renderInlineText(numMatch[2])}</span>
        </div>
      );
      i++;
      continue;
    }

    // Empty lines
    if (!line.trim()) {
      elements.push(<div key={`sp-${i}`} className="h-1.5" />);
      i++;
      continue;
    }

    // Standard paragraph
    elements.push(
      <p key={`p-${i}`} className="text-xs text-gray-200 leading-relaxed my-0.5">
        {renderInlineText(line)}
      </p>
    );
    i++;
  }

  return <div className="space-y-0.5">{elements}</div>;
}

/**
 * Format inline markers: `code`, **bold**, *italic*, _italic_
 */
function renderInlineText(text) {
  if (!text) return null;

  // Split by inline code: `code`
  const codeParts = text.split(/(`[^`]+`)/g);

  return codeParts.map((part, idx) => {
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      const code = part.slice(1, -1);
      return (
        <code
          key={idx}
          className="font-mono text-[11px] px-1.5 py-0.5 rounded bg-white/10 text-cyan-300 border border-white/10"
        >
          {code}
        </code>
      );
    }

    // Format bold: **bold**
    const boldParts = part.split(/(\*\*[^*]+\*\*)/g);
    return (
      <span key={idx}>
        {boldParts.map((bPart, bIdx) => {
          if (bPart.startsWith('**') && bPart.endsWith('**') && bPart.length >= 4) {
            return (
              <strong key={bIdx} className="font-semibold text-white">
                {bPart.slice(2, -2)}
              </strong>
            );
          }

          // Format italic: *italic* or _italic_
          const italicParts = bPart.split(/(\*[^*]+\*|_[^_]+_)/g);
          return (
            <span key={bIdx}>
              {italicParts.map((iPart, iIdx) => {
                if (
                  (iPart.startsWith('*') && iPart.endsWith('*') && iPart.length >= 2) ||
                  (iPart.startsWith('_') && iPart.endsWith('_') && iPart.length >= 2)
                ) {
                  return (
                    <em key={iIdx} className="italic text-gray-300">
                      {iPart.slice(1, -1)}
                    </em>
                  );
                }
                return iPart;
              })}
            </span>
          );
        })}
      </span>
    );
  });
}
