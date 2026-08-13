import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

const server = await createServer({
  root: fileURLToPath(new URL('.', import.meta.url)),
  server: { middlewareMode: true },
  appType: 'custom',
  logLevel: 'silent',
});

try {
  const { GuildCard } = await server.ssrLoadModule(
    '/src/pages/GuildPickerPage.tsx',
  );
  const renderCard = (icon) => renderToStaticMarkup(
    createElement(GuildCard, {
      guild: { id: '123', name: 'Test Guild', icon },
      onClick() {},
    }),
  );
  const iconMarkup = renderCard('icon');
  const initialMarkup = renderCard(null);

  for (const markup of [iconMarkup, initialMarkup]) {
    assert.match(markup, /<button /);
    assert.match(markup, /type="button"/);
    assert.match(markup, /aria-label="Test Guild"/);
  }
  assert.match(iconMarkup, /alt=""/);
  assert.match(initialMarkup, /aria-hidden="true"/);
} finally {
  await server.close();
}
