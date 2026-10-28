export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Passage = { id: string; document: string; section: string; text: string };

export type ChatResult = {
  answer: string;
  citations: string[];
  invalid_citations: string[];
  tools_called: string[];
  retrieved_ids: string[];
  passages: Passage[];
};

export const LOGIN_URL = `${API_URL}/auth/login`;
export const LOGOUT_URL = `${API_URL}/auth/logout`;

// Who the backend says is signed in (GET /me).
export type Me = { customer_id: number; name: string };

// Demo data: which orders each seeded customer owns, looked up by the customer_id that /me returns.
export const CUSTOMERS = [
  { id: 1, name: "Ada Reader", orders: "1234–1237" },
  { id: 2, name: "Basil Bookworm", orders: "1238" },
] as const;

// Each policy document is bound in its own cloth; the colour is the legend.
export const CLOTHS: Record<string, { name: string; className: string }> = {
  "returns.md": { name: "Returns & refunds", className: "cloth-returns" },
  "shipping.md": { name: "Shipping", className: "cloth-shipping" },
  "promotions.md": { name: "Promotions", className: "cloth-promotions" },
  "catalog.md": { name: "Catalog", className: "cloth-catalog" },
};

export const TOOL_LABELS: Record<string, string> = {
  get_order: "Looked up an order",
  get_latest_order: "Looked up your latest order",
  search_policies: "Searched the policies again",
};

export function clothFor(chunkId: string) {
  return CLOTHS[chunkId.split("#")[0]] ?? { name: "Policy", className: "cloth-unknown" };
}

export function sectionSlug(chunkId: string) {
  return chunkId.split("#")[1]?.replaceAll("-", " ") ?? chunkId;
}

// Splits an answer into text and [file.md#section] citation tokens.
export function splitCitations(answer: string): Array<{ text: string } | { cite: string }> {
  const parts: Array<{ text: string } | { cite: string }> = [];
  const re = /\[([a-z0-9-]+\.md#[a-z0-9-]+)\]/g;
  let last = 0;
  // The model is told not to cite order data, but sometimes writes "[order data]" anyway.
  answer = answer.replace(/\s*\[order(?: data)?\]/gi, "");
  for (const match of answer.matchAll(re)) {
    if (match.index > last) parts.push({ text: answer.slice(last, match.index) });
    parts.push({ cite: match[1] });
    last = match.index + match[0].length;
  }
  if (last < answer.length) parts.push({ text: answer.slice(last) });
  return parts;
}
