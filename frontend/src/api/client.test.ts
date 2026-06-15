import assert from 'node:assert';
import { describe, test } from 'node:test';
import api, { apiBaseUrl } from './client.ts';

describe('user API client', () => {
  test('uses the default API base URL outside Vite', () => {
    assert.strictEqual(apiBaseUrl, 'http://localhost:8103/v1');
    assert.strictEqual(api.defaults.baseURL, apiBaseUrl);
    assert.strictEqual(api.defaults.withCredentials, true);
  });

  test('registers loading and error interceptors', () => {
    assert.ok(api.interceptors.request);
    assert.ok(api.interceptors.response);
  });
});
