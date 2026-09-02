'use client';

import React from 'react';

/**
 * The small slice of Markdown a chat reply actually uses.
 *
 * Built from React elements rather than `dangerouslySetInnerHTML`: the input is
 * model output, and a rendering path that accepts raw HTML is one prompt away
 * from injecting it. Anything unrecognised falls through as literal text, so a
 * stray asterisk reads as an asterisk instead of eating the rest of the line.
 *
 * Supported: **bold**, *italic*, `code`, - bullets, 1. numbered, and blank-line
 * paragraphs. Everything else is text.
 */

const INLINE = /(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`\n]+`)/g;

/** Split one line into bold / italic / code / plain runs. */
const renderInline = (text: string, keyPrefix: string): React.ReactNode[] =>
  text.split(INLINE).filter(Boolean).map((part, i) => {
    const key = `${keyPrefix}-${i}`;
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return (
        <strong key={key} className="font-semibold text-ink-black">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
      return <em key={key}>{part.slice(1, -1)}</em>;
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return (
        <code
          key={key}
          className="px-1 py-0.5 rounded bg-stone-canvas border border-stone-border text-[0.85em] font-mono"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return <React.Fragment key={key}>{part}</React.Fragment>;
  });

type Block =
  | { type: 'p'; lines: string[] }
  | { type: 'ul'; items: string[] }
  | { type: 'ol'; items: string[] };

const BULLET = /^\s*[-*]\s+(.*)$/;
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/;

/** Group lines into paragraphs and lists. A blank line closes the current block. */
const toBlocks = (source: string): Block[] => {
  const blocks: Block[] = [];

  for (const line of source.split('\n')) {
    const bullet = line.match(BULLET);
    const numbered = !bullet && line.match(NUMBERED);
    const last = blocks[blocks.length - 1];

    if (bullet) {
      if (last?.type === 'ul') last.items.push(bullet[1]);
      else blocks.push({ type: 'ul', items: [bullet[1]] });
    } else if (numbered) {
      if (last?.type === 'ol') last.items.push(numbered[1]);
      else blocks.push({ type: 'ol', items: [numbered[1]] });
    } else if (line.trim() === '') {
      // A blank line ends whatever was open; it never starts an empty paragraph.
      if (last?.type === 'p' && last.lines.length) blocks.push({ type: 'p', lines: [] });
    } else if (last?.type === 'p') {
      last.lines.push(line);
    } else {
      blocks.push({ type: 'p', lines: [line] });
    }
  }

  return blocks.filter((b) => (b.type === 'p' ? b.lines.length > 0 : b.items.length > 0));
};

export const MarkdownText: React.FC<{ content: string; className?: string }> = ({
  content,
  className = '',
}) => {
  if (!content?.trim()) return null;
  const blocks = toBlocks(content);

  return (
    <div className={`text-sm text-ink-black leading-relaxed space-y-2 break-words ${className}`}>
      {blocks.map((block, bi) => {
        if (block.type === 'ul' || block.type === 'ol') {
          const List = block.type === 'ul' ? 'ul' : 'ol';
          return (
            <List
              key={bi}
              className={`pl-5 space-y-1 ${block.type === 'ul' ? 'list-disc' : 'list-decimal'} marker:text-ash-gray`}
            >
              {block.items.map((item, ii) => (
                <li key={ii}>{renderInline(item, `${bi}-${ii}`)}</li>
              ))}
            </List>
          );
        }
        // Single newlines inside a paragraph stay visible — the model uses them.
        return (
          <p key={bi} className="whitespace-pre-wrap">
            {block.lines.map((line, li) => (
              <React.Fragment key={li}>
                {li > 0 && '\n'}
                {renderInline(line, `${bi}-${li}`)}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
};
