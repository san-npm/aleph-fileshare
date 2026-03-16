"use client";

import dynamic from "next/dynamic";

const FileUpload = dynamic(
  () => import("@/components/FileUpload").then((m) => m.FileUpload),
  { ssr: false, loading: () => <UploadSkeleton /> }
);

function UploadSkeleton() {
  return (
    <div className="max-w-2xl mx-auto">
      <div className="border-2 border-dashed border-gray-700 rounded-xl p-12 bg-gray-900/50 animate-pulse">
        <div className="h-12 w-12 bg-gray-800 rounded-lg mx-auto mb-4" />
        <div className="h-4 w-48 bg-gray-800 rounded mx-auto mb-2" />
        <div className="h-3 w-64 bg-gray-800 rounded mx-auto" />
      </div>
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Hero */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-aleph-blue/10 border border-aleph-blue/20 rounded-full text-aleph-blue text-sm mb-6">
          <span className="w-2 h-2 bg-aleph-blue rounded-full animate-pulse" />
          Built on Aleph Cloud
        </div>
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white mb-4 tracking-tight">
          Share Files,{" "}
          <span className="bg-gradient-to-r from-aleph-blue to-aleph-purple bg-clip-text text-transparent">
            Decentralized
          </span>
        </h1>
        <p className="text-gray-400 text-lg max-w-2xl mx-auto leading-relaxed">
          Upload files to IPFS via Aleph Cloud. No sign-up, no limits, no
          central server. Just connect your wallet and share.
        </p>
      </div>

      <FileUpload />

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-20 max-w-4xl mx-auto">
        <div className="group p-6 bg-gray-900/50 border border-gray-800 rounded-xl text-center hover:border-aleph-blue/30 transition-all duration-300">
          <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center mx-auto mb-4 group-hover:bg-blue-500/20 transition-colors">
            <span className="text-2xl">🌐</span>
          </div>
          <h3 className="text-white font-semibold mb-2">IPFS Storage</h3>
          <p className="text-gray-400 text-sm leading-relaxed">
            Files are stored on the InterPlanetary File System, accessible
            globally and censorship-resistant.
          </p>
        </div>
        <div className="group p-6 bg-gray-900/50 border border-gray-800 rounded-xl text-center hover:border-aleph-blue/30 transition-all duration-300">
          <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center mx-auto mb-4 group-hover:bg-purple-500/20 transition-colors">
            <span className="text-2xl">🔐</span>
          </div>
          <h3 className="text-white font-semibold mb-2">Wallet Auth</h3>
          <p className="text-gray-400 text-sm leading-relaxed">
            No passwords, no accounts. Authenticate with your Ethereum wallet
            — you own your data.
          </p>
        </div>
        <div className="group p-6 bg-gray-900/50 border border-gray-800 rounded-xl text-center hover:border-aleph-blue/30 transition-all duration-300">
          <div className="w-12 h-12 bg-green-500/10 rounded-xl flex items-center justify-center mx-auto mb-4 group-hover:bg-green-500/20 transition-colors">
            <span className="text-2xl">🤖</span>
          </div>
          <h3 className="text-white font-semibold mb-2">AI Powered</h3>
          <p className="text-gray-400 text-sm leading-relaxed">
            Autonomous agents scan, tag, and index your files automatically
            using decentralized AI.
          </p>
        </div>
      </div>

      {/* How it works */}
      <div className="mt-24 max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold text-white text-center mb-10">
          How It Works
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-8">
          {[
            {
              step: "01",
              title: "Connect Wallet",
              desc: "Link your Ethereum wallet — MetaMask, WalletConnect, or any EVM wallet.",
            },
            {
              step: "02",
              title: "Upload File",
              desc: "Drag & drop or browse. Your file is stored on IPFS via Aleph Cloud.",
            },
            {
              step: "03",
              title: "Share Link",
              desc: "Get a permanent share link. Anyone with the link can download.",
            },
          ].map((item) => (
            <div key={item.step} className="text-center">
              <div className="text-aleph-blue font-mono text-sm font-bold mb-2">
                {item.step}
              </div>
              <h3 className="text-white font-semibold mb-1">{item.title}</h3>
              <p className="text-gray-400 text-sm">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
