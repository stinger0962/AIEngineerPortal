type Block =
  | { type: "heading"; level: 2 | 3; text: string }
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] }
  | { type: "code"; code: string }
  | { type: "quote"; text: string };

function inlineFormat(text: string): React.ReactNode[] {
  return text.split(/(`[^`]+`)/g).filter(Boolean).map((part, index) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={`${part}-${index}`} className="rounded bg-ink/5 px-1.5 py-0.5 font-mono text-[0.9em] text-ink">
          {part.slice(1, -1)}
        </code>
      );
    }
    return <span key={`${part}-${index}`}>{part}</span>;
  });
}

function parseMarkdown(markdown: string): Block[] {
  const lines = markdown.split("\n");
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let listItems: string[] = [];
  let codeLines: string[] = [];
  let inCodeBlock = false;

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: "paragraph", text: paragraph.join(" ") });
      paragraph = [];
    }
  };

  const flushList = () => {
    if (listItems.length) {
      blocks.push({ type: "list", items: listItems });
      listItems = [];
    }
  };

  const flushCode = () => {
    if (codeLines.length) {
      blocks.push({ type: "code", code: codeLines.join("\n") });
      codeLines = [];
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    if (line.startsWith("```")) {
      flushParagraph();
      flushList();
      if (inCodeBlock) {
        flushCode();
      }
      inCodeBlock = !inCodeBlock;
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(rawLine);
      continue;
    }

    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }

    if (line.startsWith("## ")) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading", level: 2, text: line.slice(3).trim() });
      continue;
    }

    if (line.startsWith("### ")) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading", level: 3, text: line.slice(4).trim() });
      continue;
    }

    if (line.startsWith("- ")) {
      flushParagraph();
      listItems.push(line.slice(2).trim());
      continue;
    }

    if (line.startsWith("> ")) {
      flushParagraph();
      flushList();
      blocks.push({ type: "quote", text: line.slice(2).trim() });
      continue;
    }

    paragraph.push(line.trim());
  }

  flushParagraph();
  flushList();
  flushCode();

  return blocks;
}

export function LessonMarkdown({ content }: { content: string }) {
  const blocks = parseMarkdown(content);

  return (
    <div className="space-y-5 text-base leading-8 text-ink/85">
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          if (block.level === 2) {
            return (
              <h2 key={index} className="pt-3 text-2xl font-semibold text-ink">
                {block.text}
              </h2>
            );
          }
          return (
            <h3 key={index} className="pt-2 text-lg font-semibold text-ink">
              {block.text}
            </h3>
          );
        }

        if (block.type === "list") {
          return (
            <ul key={index} className="space-y-2 pl-5 text-ink/80">
              {block.items.map((item) => (
                <li key={item} className="list-disc">
                  {inlineFormat(item)}
                </li>
              ))}
            </ul>
          );
        }

        if (block.type === "code") {
          return (
            <pre key={index} className="overflow-x-auto rounded-2xl bg-[#0f172a] p-4 text-sm leading-6 text-slate-100">
              <code>{block.code}</code>
            </pre>
          );
        }

        if (block.type === "quote") {
          return (
            <blockquote key={index} className="rounded-2xl border border-gold/40 bg-gold/10 px-4 py-3 text-ink">
              {inlineFormat(block.text)}
            </blockquote>
          );
        }

        return (
          <p key={index} className="text-ink/80">
            {inlineFormat(block.text)}
          </p>
        );
      })}
    </div>
  );
}
