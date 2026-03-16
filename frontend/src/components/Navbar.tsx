"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAccount } from "wagmi";
import { WalletButton } from "./WalletButton";

export function Navbar() {
  const { isConnected } = useAccount();
  const pathname = usePathname();

  const navLink = (href: string, label: string) => {
    const isActive = pathname === href;
    return (
      <Link
        href={href}
        className={`text-sm transition-colors ${
          isActive
            ? "text-white font-medium"
            : "text-gray-400 hover:text-white"
        }`}
      >
        {label}
      </Link>
    );
  };

  return (
    <nav className="border-b border-gray-800 bg-aleph-dark/95 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center gap-8">
            <Link
              href="/"
              className="text-xl font-bold text-white flex items-center gap-2 group"
            >
              <span className="text-aleph-blue group-hover:scale-110 transition-transform inline-block">
                ⬡
              </span>
              <span className="hidden sm:inline">AlephFileShare</span>
              <span className="sm:hidden">AFS</span>
            </Link>

            {isConnected && (
              <div className="flex items-center gap-6">
                {navLink("/", "Upload")}
                {navLink("/files", "My Files")}
              </div>
            )}
          </div>

          <WalletButton />
        </div>
      </div>
    </nav>
  );
}
