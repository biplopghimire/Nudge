const path = require("path");
const { getDefaultConfig } = require("expo/metro-config");
const { withUniwindConfig } = require("uniwind/metro");

const config = getDefaultConfig(__dirname);

// The API types live with the backend (../nudge-api/nudge-types.ts) so the app
// and the server can't drift apart. Let Metro see that folder.
config.watchFolders = [...(config.watchFolders ?? []), path.resolve(__dirname, "../nudge-api")];

module.exports = withUniwindConfig(config, {
  cssEntryFile: "./src/global.css",
});
