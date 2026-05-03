import { test, describe } from 'node:test';
import assert from 'node:assert';
import { formatPricingSummary } from './pricing.ts';

describe('formatPricingSummary', () => {
  test('returns ["未配置"] for null or non-object pricing', () => {
    assert.deepStrictEqual(formatPricingSummary(null), ["未配置"]);
    assert.deepStrictEqual(formatPricingSummary(undefined), ["未配置"]);
    assert.deepStrictEqual(formatPricingSummary("free"), ["未配置"]);
    assert.deepStrictEqual(formatPricingSummary(123), ["未配置"]);
  });

  test('returns ["免费"] when mode is "free"', () => {
    assert.deepStrictEqual(formatPricingSummary({ mode: "free" }), ["免费"]);
  });

  test('handles "token_segments" mode with various fields', () => {
    const pricing = {
      mode: "token_segments",
      input_per_million: 0.1,
      cached_input_per_million: 0.05,
      output_per_million: 0.2,
      audio_input_per_million: 0.3,
      audio_output_per_million: 0.4,
      image_output_per_million: 0.5,
      cache_write_5m_per_million: 0.01,
      cache_write_1h_per_million: 0.02,
      priority_input_per_million: 0.15,
      priority_output_per_million: 0.25,
      priority_image_output_per_million: 0.55
    };
    const expected = [
      "输入 $0.1/1M",
      "缓存输入 $0.05/1M",
      "输出 $0.2/1M",
      "音频输入 $0.3/1M",
      "音频输出 $0.4/1M",
      "图片输出 $0.5/1M",
      "5m 缓存写入 $0.01/1M",
      "1h 缓存写入 $0.02/1M",
      "Priority 输入 $0.15/1M",
      "Priority 输出 $0.25/1M",
      "Priority 图片输出 $0.55/1M"
    ];
    assert.deepStrictEqual(formatPricingSummary(pricing), expected);
  });

  test('handles "token_segments" mode with image_prices and tiers', () => {
    const pricing = {
      mode: "token_segments",
      image_prices: {
        "1024x1024": 0.04,
        "512x512": 0.02
      },
      tiers: [
        { up_to: 100, price: 0.1 },
        { up_to: 1000, price: 0.08 }
      ]
    };
    const expected = [
      "1024x1024 图 $0.04/张",
      "512x512 图 $0.02/张",
      "分段计费 2 档"
    ];
    assert.deepStrictEqual(formatPricingSummary(pricing), expected);
  });

  test('returns ["结构化 token 计费"] for "token_segments" mode with no fields', () => {
    assert.deepStrictEqual(formatPricingSummary({ mode: "token_segments" }), ["结构化 token 计费"]);
  });

  test('handles unit-based pricing', () => {
    const pricing = {
      unit: "次",
      price: 0.5
    };
    assert.deepStrictEqual(formatPricingSummary(pricing), ["$0.5/次"]);
  });

  test('falls back to JSON stringification for unknown formats', () => {
    const pricing = { mode: "unknown", foo: "bar" };
    assert.deepStrictEqual(formatPricingSummary(pricing), [JSON.stringify(pricing)]);
  });
});
