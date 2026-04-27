import type { Config } from "tailwindcss";
import sharedConfig from "@devforge/ui/tailwind.config";
const config: Config = {
  ...sharedConfig,
  content: ["./src/**/*.{ts,tsx}", "../../../packages/ui/components/**/*.{ts,tsx}"],
};
export default config;
