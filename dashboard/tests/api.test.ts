// @ts-expect-error Node types are not installed; assert is built into Node.
import assert from 'node:assert/strict';

import { fetchQueue } from '../src/api.js';

Object.defineProperty(globalThis, 'window', {
  value: { location: { href: '/dashboard' } },
});
Object.defineProperty(globalThis, 'fetch', {
  value: async () => new Response(null, { status: 401 }),
});

await fetchQueue('123').catch(() => {});

assert.equal(window.location.href, '/', '401 redirects to login');
