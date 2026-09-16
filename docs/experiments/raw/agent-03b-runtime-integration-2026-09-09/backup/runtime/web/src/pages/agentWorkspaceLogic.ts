/** 展示层消息流：保留跨字节中文、CRLF 和结尾帧，不推算任何技术结论。 */
export async function* readAgentEvents(body: ReadableStream<Uint8Array>) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const parse = (frame: string) => {
    let event = "";
    const data: string[] = [];
    for (const line of frame.split(/\r?\n/)) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    }
    return event && data.length ? { event, data: JSON.parse(data.join("\n")) as Record<string, unknown> } : null;
  };
  try {
    for (;;) {
      const { done, value } = await reader.read();
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true });
      let boundary: RegExpExecArray | null;
      while ((boundary = /\r?\n\r?\n/.exec(buffer))) {
        const parsed = parse(buffer.slice(0, boundary.index));
        buffer = buffer.slice(boundary.index + boundary[0].length);
        if (parsed) yield parsed;
      }
      if (done) {
        if (buffer.trim()) { const parsed = parse(buffer); if (parsed) yield parsed; }
        break;
      }
    }
  } finally { reader.releaseLock(); }
}

export function shouldFollowOutput(top: number, height: number, total: number) {
  return total - top - height < 80;
}

/** 仅拆开原文首段，绝不改写或推断结论。 */
export function replyPreview(text: string) {
  const paragraphs = text.trim().split(/\n\s*\n/);
  if (paragraphs.length > 1 && paragraphs[0].length <= 320 && !/^(#|[-*+]\s|\d+[.、]\s|```|\|)/.test(paragraphs[0])) {
    return { lead: paragraphs[0], rest: paragraphs.slice(1).join("\n\n") };
  }
  return { lead: "", rest: text };
}
