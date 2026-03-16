"use client";

import Link from "next/link";
import { useAccount } from "wagmi";
import { WalletButton } from "./WalletButton";

export function Navbar() {
  const { isConnected } = useAccount();

  return (
    <nav className="border-b border-gray-800 bg-aleph-dark/95 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <Link
              href="/"
              className="text-xl font-bold text-white flex items-center gap-2"
            >
              <span className="text-aleph-blue">⬡</span>
              AlephFileShare
            </Link>

            {isConnected && (
              <div className="hidden sm:flex items-center gap-6">
                <Link
                  href="/"
                  className="text-gray-400 hover:text-white transition-colors text-sm"
                >
                  Upload
                </Link>
                <Link
                  href="/files"
                  className="text-gray-400 hover:text-white transition-colors text-sm"
                >
                  My Files
                </Link>
              </div>
            )}
          </div>

          <WalletButton />
        </div>
      </div>
    </nav>
  );
}
