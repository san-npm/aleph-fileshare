"use client";

import { getDefaultConfig } from "@rainbow-me/rainbowkit";
import { mainnet, sepolia } from "wagmi/chains";
import { config as appConfig } from "./config";

export const wagmiConfig = getDefaultConfig({
  appName: appConfig.appName,
  projectId: appConfig.walletConnectProjectId || "demo",
  chains: [mainnet, sepolia],
  ssr: true,
});
