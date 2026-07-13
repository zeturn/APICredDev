export type LedgerItem = {
  id: string;
  entry_type: string;
  amount_credits: number;
  created_at?: string | null;
};

export const normalizeLedger = (data: unknown): LedgerItem[] => {
  if (Array.isArray(data)) {
    return data.slice(0, 10) as LedgerItem[];
  }

  if (data && typeof data === "object") {
    const items = (data as { items?: unknown }).items;
    if (Array.isArray(items)) {
      return items.slice(0, 10) as LedgerItem[];
    }
  }

  return [];
};
