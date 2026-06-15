import assert from 'node:assert';
import { afterEach, describe, test } from 'node:test';
import axios from 'axios';
import adminApi, { apiBaseUrl, clearAdminAccessToken, decodeJwtExp, ensureAdminToken } from './adminClient.ts';

const originalGet = axios.get;
const originalDateNow = Date.now;

const makeJwt = (payload: Record<string, unknown>): string => {
  const encode = (value: Record<string, unknown>) =>
    Buffer.from(JSON.stringify(value)).toString('base64url');
  return `${encode({ alg: 'none' })}.${encode(payload)}.signature`;
};

afterEach(() => {
  axios.get = originalGet;
  Date.now = originalDateNow;
  clearAdminAccessToken();
});

describe('admin API client', () => {
  test('uses the default API base URL outside Vite', () => {
    assert.strictEqual(apiBaseUrl, 'http://localhost:8103/v1');
    assert.strictEqual(adminApi.defaults.baseURL, apiBaseUrl);
    assert.strictEqual(adminApi.defaults.withCredentials, true);
  });

  test('decodes valid, malformed, and exp-less JWT values', () => {
    assert.strictEqual(decodeJwtExp(makeJwt({ exp: 123 })), 123);
    assert.strictEqual(decodeJwtExp(makeJwt({})), 0);
    assert.strictEqual(decodeJwtExp('not-a-token'), 0);
  });

  test('fetches and caches an admin access token until near expiry', async () => {
    Date.now = () => 1_000_000;
    const token = makeJwt({ exp: 2_000 });
    let calls = 0;
    axios.get = async (url: string, config: unknown) => {
      calls += 1;
      assert.strictEqual(url, `${apiBaseUrl}/auth/admin-token`);
      assert.deepStrictEqual(config, { withCredentials: true });
      return { data: { admin_access_token: token } };
    };

    assert.strictEqual(await ensureAdminToken(), token);
    assert.strictEqual(await ensureAdminToken(), token);
    assert.strictEqual(calls, 1);
  });

  test('clears cached token after a failed refresh', async () => {
    axios.get = async () => {
      throw new Error('denied');
    };

    assert.strictEqual(await ensureAdminToken(), null);
    assert.strictEqual(await ensureAdminToken(), null);
  });
});
