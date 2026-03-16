import type { Metadata } from "next";
import { Inter } from "next/font/google";
import dynamic from "next/dynamic";
import "./globals.css";

const Providers = dynamic(() => import("./providers").then((m) => m.Providers), {
  ssr: false,
});
const Navbar = dynamic(() => import("@/components/Navbar").then((m) => m.Navbar), {
  ssr: false,
});

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AlephFileShare — Decentralized File Sharing",
  description:
    "Upload and share files on IPFS via Aleph Cloud. No accounts, no limits, fully decentralized.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <Navbar />
          <main className="min-h-[calc(100vh-4rem)]">{children}</main>
          <footer className="border-t border-gray-800 py-8 text-center text-gray-500 text-sm">
            <p>
              Powered by{" "}
              <a
                href="https://aleph.cloud"
                target="_blank"
                rel="noopener noreferrer"
                className="text-aleph-blue hover:underline"
              >
                Aleph Cloud
              </a>{" "}
              — Fully decentralized infrastructure
            </p>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
