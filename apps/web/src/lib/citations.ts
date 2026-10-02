export type ChatCitation = {
  title: string | null;
  url: string;
};

/**
 * Parse a WebSearchTools tool result into citations.
 * The result is typically a JSON string (or array) of
 * `{ title, url/href/link, ... }` objects.
 */
export function citationsFromWebSearchResult(result: unknown): ChatCitation[] {
  let items: unknown = result;
  if (typeof result === "string") {
    try {
      items = JSON.parse(result);
    } catch {
      return [];
    }
  }
  if (!Array.isArray(items)) return [];
  const out: ChatCitation[] = [];
  for (const raw of items) {
    if (!raw || typeof raw !== "object") continue;
    const item = raw as Record<string, unknown>;
    const url = item.url ?? item.href ?? item.link;
    if (typeof url !== "string" || !url) continue;
    const title = item.title ?? item.name ?? null;
    out.push({ title: typeof title === "string" ? title : null, url });
  }
  return out;
}

/** Merge two citation lists, deduping by URL (first occurrence wins). */
export function mergeCitations(
  a: ChatCitation[],
  b: ChatCitation[],
): ChatCitation[] {
  const seen = new Set<string>();
  const out: ChatCitation[] = [];
  for (const c of [...a, ...b]) {
    if (!c.url || seen.has(c.url)) continue;
    seen.add(c.url);
    out.push(c);
  }
  return out;
}
