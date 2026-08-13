import assert from "node:assert/strict";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { build, createServer } from "vite";

const result = await build({ logLevel: "silent", build: { write: false } });
const outputs = Array.isArray(result) ? result : [result];
const moduleIds = outputs.flatMap(({ output }) =>
  output.flatMap((chunk) =>
    chunk.type === "chunk" ? Object.keys(chunk.modules) : [],
  ),
);

assert.equal(
  moduleIds.some((id) => id.endsWith("/src/components/PlaybackControls.tsx")),
  false,
  "Dashboard bundle still includes PlaybackControls",
);
assert.equal(
  moduleIds.some((id) => id.endsWith("/src/components/PlayerBar.tsx")),
  true,
  "Dashboard bundle no longer includes PlayerBar",
);

const server = await createServer({
  appType: "custom",
  logLevel: "silent",
  server: { middlewareMode: true },
});

try {
  const { PlayerBarError } = await server.ssrLoadModule(
    "/src/components/PlayerBar.tsx",
  );

  assert.equal(
    typeof PlayerBarError,
    "function",
    "PlayerBar must expose accessible error feedback",
  );

  for (const message of ["Pause failed.", "Resume failed.", "Stop failed."]) {
    const markup = renderToStaticMarkup(
      createElement(PlayerBarError, { message }),
    );
    assert.match(markup, /role="alert"/);
    assert.ok(markup.includes(message), `${message} must be visible`);
  }
} finally {
  await server.close();
}
