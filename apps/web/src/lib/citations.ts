export type ChatCitation = {
  index: number;
  title: string;
  url: string;
  snippet: string;
};

export function citationsFromWebSearchResult(result: any): ChatCitation[] {
  if (!result || !Array.isArray(result)) return [];
  return result.map((item: any, index: number) => ({
    index: index + 1,
    title: item.title || "",
    url: item.url || "",
    snippet: item.snippet || item.description || "",
  }));
}

export function mergeCitations(
  citations1: ChatCitation[],
  citations2: ChatCitation[]
): ChatCitation[] {
  const merged = [...citations1, ...citations2];
  // Re-index
  return merged.map((c, i) => ({ ...c, index: i + 1 }));
}
