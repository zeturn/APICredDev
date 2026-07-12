import assert from "node:assert";
import { describe, test } from "node:test";
import { normalizeLedger } from "./dashboardData.ts";

describe("normalizeLedger", () => {
  test("limits array responses to the latest ten entries", () => {
    const entries = Array.from({ length: 12 }, (_, index) => ({
      id: String(index),
      entry_type: "credit",
      amount_credits: index,
    }));

    assert.deepStrictEqual(normalizeLedger(entries), entries.slice(0, 10));
  });

  test("supports an items response envelope", () => {
    const entries = [{ id: "1", entry_type: "credit", amount_credits: 1 }];
    assert.deepStrictEqual(normalizeLedger({ items: entries }), entries);
  });

  test("returns an empty list for malformed responses", () => {
    assert.deepStrictEqual(normalizeLedger("unexpected response"), []);
    assert.deepStrictEqual(normalizeLedger({ error: "unauthorized" }), []);
    assert.deepStrictEqual(normalizeLedger(null), []);
  });
});
