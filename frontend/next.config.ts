import type { NextConfig } from "next";

import { released, version } from "./package.json";

const nextConfig: NextConfig = {
  // Static export: the model runs in the visitor's browser, so Amplify serves plain files and
  // there is no server to pay for.
  output: "export",
  // Static export has no image optimization server; the images are already small PNGs.
  images: { unoptimized: true },
  // The footer's release line, from package.json: a release sets `version` and `released` (its
  // date, YYYY-MM-DD) together.
  env: { VERSION: version, RELEASED: released },
};

export default nextConfig;
