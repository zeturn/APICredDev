import assert from 'node:assert';
import { test, describe } from 'node:test';
import { formatPricingSummary } from './pricing.ts';

describe('formatPricingSummary', () => {
  test('returns ["未配置"] for null or undefined', () => {
    assert.deepStrictEqual(formatPricingSummary(null), ["未配置"]);
    assert.deepStrictEqual(formatPricingSummary(undefined), ["未配置"]);
  });

  test('returns ["未配置"] for non-object types', () => {
    assert.deepStrictEqual(formatPricingSummary('string'), ["未配置"]);
    assert.deepStrictEqual(formatPricingSummary(123), ["未配置"]);
  });

  describe('per_token and per_request types (from issue)', () => {
    test('formats per_token pricing', () => {
      const pricing = {
        type: 'per_token',
        prompt_token_price: 0.001,
        completion_token_price: 0.002
      };
      assert.deepStrictEqual(formatPricingSummary(pricing), [
        'Prompt: $0.001/1k',
        'Completion: $0.002/1k'
      ]);
    });

    test('formats per_token pricing with missing fields', () => {
      assert.deepStrictEqual(formatPricingSummary({ type: 'per_token', prompt_token_price: 0.001 }), ['Prompt: $0.001/1k']);
      assert.deepStrictEqual(formatPricingSummary({ type: 'per_token', completion_token_price: 0.002 }), ['Completion: $0.002/1k']);
      assert.deepStrictEqual(formatPricingSummary({ type: 'per_token' }), []);
    });

    test('formats per_request pricing', () => {
      const pricing = {
        type: 'per_request',
        request_price: 0.5
      };
      assert.deepStrictEqual(formatPricingSummary(pricing), ['$0.5/req']);
    });
  });

  test('returns ["免费"] when mode is free', () => {
    assert.deepStrictEqual(formatPricingSummary({ mode: 'free' }), ["免费"]);
  });

  describe('token_segments mode', () => {
    test('returns fallback for empty token segments', () => {
      assert.deepStrictEqual(formatPricingSummary({ mode: 'token_segments' }), ["结构化 token 计费"]);
    });

    test('formats various million-based prices', () => {
      const pricing = {
        mode: 'token_segments',
        input_per_million: 1,
        cached_input_per_million: 0.5,
        output_per_million: 2,
        audio_input_per_million: 10,
        audio_output_per_million: 20,
        image_output_per_million: 5,
        cache_write_5m_per_million: 0.1,
        cache_write_1h_per_million: 0.2,
        priority_input_per_million: 1.5,
        priority_output_per_million: 3,
        priority_image_output_per_million: 7,
      };
      const result = formatPricingSummary(pricing);
      assert.ok(result.includes('输入 $1/1M'));
      assert.ok(result.includes('缓存输入 $0.5/1M'));
      assert.ok(result.includes('输出 $2/1M'));
      assert.ok(result.includes('音频输入 $10/1M'));
      assert.ok(result.includes('音频输出 $20/1M'));
      assert.ok(result.includes('图片输出 $5/1M'));
      assert.ok(result.includes('5m 缓存写入 $0.1/1M'));
      assert.ok(result.includes('1h 缓存写入 $0.2/1M'));
      assert.ok(result.includes('Priority 输入 $1.5/1M'));
      assert.ok(result.includes('Priority 输出 $3/1M'));
      assert.ok(result.includes('Priority 图片输出 $7/1M'));
    });

    test('formats image prices', () => {
      const pricing = {
        mode: 'token_segments',
        image_prices: {
          '1024x1024': 0.04,
          '512x512': 0.02
        }
      };
      const result = formatPricingSummary(pricing);
      assert.ok(result.includes('1024x1024 图 $0.04/张'));
      assert.ok(result.includes('512x512 图 $0.02/张'));
    });

    test('formats tiers', () => {
      const pricing = {
        mode: 'token_segments',
        tiers: [{}, {}, {}]
      };
      const result = formatPricingSummary(pricing);
      assert.ok(result.includes('分段计费 3 档'));
    });
  });

  test('formats unit and price', () => {
    const pricing = {
      unit: '1k tokens',
      price: 0.002
    };
    assert.deepStrictEqual(formatPricingSummary(pricing), ["$0.002/1k tokens"]);
  });

  test('fallbacks to JSON stringify', () => {
    const pricing = { unknown: 'field' };
    assert.deepStrictEqual(formatPricingSummary(pricing), [JSON.stringify(pricing)]);
  });
});
