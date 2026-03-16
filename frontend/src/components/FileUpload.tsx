"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useAccount } from "wagmi";
import { useFileUpload } from "@/hooks/useFileUpload";
import { formatBytes } from "@/lib/api";

export function FileUpload() {
  const { isConnected } = useAccount();
  const { upload, isUploading, progress, error, result, reset } =
    useFileUpload();
  const [copied, setCopied] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;
      reset();
      setSelectedFile(acceptedFiles[0]);
      await upload(acceptedFiles[0]);
      setSelectedFile(null);
    },
    [upload, reset]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    disabled: !isConnected || isUploading,
  });

  const copyShareUrl = () => {
    if (!result) return;
    const shareUrl = `${window.location.origin}/d/${result.hash}`;
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!isConnected) {
    return (
      <div className="text-center py-16">
        <div className="w-20 h-20 bg-gray-800/50 border border-gray-700 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <span className="text-4xl">⬡</span>
        </div>
        <h2 className="text-2xl font-bold text-white mb-3">
          Connect Your Wallet
        </h2>
        <p className="text-gray-400 mb-6 max-w-md mx-auto">
          Connect your Ethereum wallet to start uploading and sharing files on
          the decentralized web.
        </p>
        <div className="inline-flex items-center gap-2 text-sm text-gray-500">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Supports MetaMask, WalletConnect, and more
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
          transition-all duration-200 overflow-hidden
          ${
            isDragActive
              ? "border-aleph-blue bg-aleph-blue/10 scale-[1.02]"
              : "border-gray-700 hover:border-gray-500 bg-gray-900/50"
          }
          ${isUploading ? "pointer-events-none" : ""}
        `}
      >
        <input {...getInputProps()} />

        {isUploading ? (
          <div className="relative z-10">
            <div className="w-16 h-16 border-4 border-gray-700 border-t-aleph-blue rounded-full animate-spin mx-auto mb-4" />
            <p className="text-white font-medium mb-1">Uploading...</p>
            {selectedFile && (
              <p className="text-gray-500 text-sm mb-4">
                {selectedFile.name} ({formatBytes(selectedFile.size)})
              </p>
            )}
            <div className="w-full bg-gray-800 rounded-full h-2 max-w-sm mx-auto overflow-hidden">
              <div
                className="bg-gradient-to-r from-aleph-blue to-aleph-purple h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-gray-400 text-sm mt-2">{progress}%</p>
          </div>
        ) : (
          <div>
            <div className="w-16 h-16 bg-gray-800/50 border border-gray-700 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">
                {isDragActive ? "📂" : "📁"}
              </span>
            </div>
            <p className="text-white font-medium mb-1">
              {isDragActive
                ? "Drop your file here"
                : "Drag & drop a file, or click to browse"}
            </p>
            <p className="text-gray-500 text-sm">
              Files are stored on IPFS via Aleph Cloud · Max 2 GB
            </p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 p-4 bg-red-900/20 border border-red-800/50 rounded-lg flex items-start gap-3">
          <svg className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="text-red-300 text-sm font-medium">Upload failed</p>
            <p className="text-red-400/80 text-sm mt-0.5">{error}</p>
          </div>
          <button
            onClick={reset}
            className="ml-auto text-red-400 hover:text-red-300 text-sm"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Success */}
      {result && (
        <div className="mt-6 p-6 bg-gray-900 border border-gray-800 rounded-xl">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-8 h-8 bg-green-500/10 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <h3 className="text-white font-semibold">Upload Complete</h3>
              <p className="text-gray-500 text-xs">File stored on IPFS</p>
            </div>
          </div>

          <div className="space-y-2.5 text-sm">
            <div className="flex justify-between items-center">
              <span className="text-gray-400">File</span>
              <span className="text-white truncate ml-4 max-w-[60%] text-right">
                {result.filename}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Size</span>
              <span className="text-white">
                {formatBytes(result.size_bytes)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Type</span>
              <span className="text-white">{result.mime_type}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Hash</span>
              <span className="text-white font-mono text-xs bg-gray-800 px-2 py-0.5 rounded">
                {result.hash.slice(0, 12)}...{result.hash.slice(-6)}
              </span>
            </div>
          </div>

          <div className="flex gap-3 mt-5">
            <button
              onClick={copyShareUrl}
              className="flex-1 py-2.5 px-4 bg-aleph-blue hover:bg-aleph-blue/80 text-white rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
            >
              {copied ? (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Copied!
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copy Share Link
                </>
              )}
            </button>
            <button
              onClick={reset}
              className="py-2.5 px-4 bg-gray-800 hover:bg-gray-700 text-white rounded-lg text-sm transition-colors"
            >
              Upload Another
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
