"use client";

import dynamic from "next/dynamic";

const FileUpload = dynamic(() => import("@/components/FileUpload").then((m) => m.FileUpload), {
  ssr: false,
});

export default function HomePage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl sm:text-5xl font-bold text-white mb-4">
          Share Files,{" "}
          <span className="text-aleph-blue">Decentralized</span>
        </h1>
        <p className="text-gray-400 text-lg max-w-2xl mx-auto">
          Upload files to IPFS via Aleph Cloud. No sign-up, no limits, no
          central server. Just connect your wallet and share.
        </p>
      </div>

      <FileUpload />

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-20 max-w-4xl mx-auto">
        <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl text-center">
          <div className="text-3xl mb-3">🌐</div>
          <h3 className="text-white font-semibold mb-2">IPFS Storage</h3>
          <p className="text-gray-400 text-sm">
            Files are stored on the InterPlanetary File System, accessible
            globally.
          </p>
        </div>
        <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl text-center">
          <div className="text-3xl mb-3">🔐</div>
          <h3 className="text-white font-semibold mb-2">Wallet Auth</h3>
          <p className="text-gray-400 text-sm">
            No passwords, no accounts. Sign in with your Ethereum wallet.
          </p>
        </div>
        <div className="p-6 bg-gray-900/50 border border-gray-800 rounded-xl text-center">
          <div className="text-3xl mb-3">🤖</div>
          <h3 className="text-white font-semibold mb-2">AI Powered</h3>
          <p className="text-gray-400 text-sm">
            Autonomous agents scan, tag, and index your files automatically.
          </p>
        </div>
      </div>
    </div>
  );
}
