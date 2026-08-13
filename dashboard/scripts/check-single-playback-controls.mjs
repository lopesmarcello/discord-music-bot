import assert from "node:assert/strict";
import { build } from "vite";

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
