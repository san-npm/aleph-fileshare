"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useAccount } from "wagmi";
import { useFileUpload } from "@/hooks/useFileUpload";
import { config } from "@/lib/config";

export function FileUpload() {
  const { isConnected } = useAccount();
  const { upload, isUploading, progress, error, result, reset } =
    useFileUpload();
  const [copied, setCopied] = useState(false);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;
      reset();
      await upload(acceptedFiles[0]);
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
      <div className="text-center py-20">
        <div className="text-6xl mb-6">⬡</div>
        <h2 className="text-2xl font-bold text-white mb-3">
          Decentralized File Sharing
        </h2>
        <p className="text-gray-400 mb-6 max-w-md mx-auto">
          Upload files to IPFS via Aleph Cloud. Connect your wallet to get
          started.
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* Drop zone */}
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
          transition-all duration-200
          ${
            isDragActive
              ? "border-aleph-blue bg-aleph-blue/10"
              : "border-gray-700 hover:border-gray-500 bg-gray-900/50"
          }
          ${isUploading ? "pointer-events-none opacity-60" : ""}
        `}
      >
        <input {...getInputProps()} />

        {isUploading ? (
          <div>
            <div className="text-4xl mb-4 animate-pulse">📤</div>
            <p className="text-white mb-4">Uploading...</p>
            <div className="w-full bg-gray-800 rounded-full h-3 max-w-md mx-auto">
              <div
                className="bg-aleph-blue h-3 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-gray-400 text-sm mt-2">{progress}%</p>
          </div>
        ) : (
          <div>
            <div className="text-4xl mb-4">
              {isDragActive ? "📂" : "📁"}
            </div>
            <p className="text-white mb-2">
              {isDragActive
                ? "Drop your file here"
                : "Drag & drop a file, or click to browse"}
            </p>
            <p className="text-gray-500 text-sm">
              Files are stored on IPFS via Aleph Cloud
            </p>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 p-4 bg-red-900/30 border border-red-800 rounded-lg text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Success */}
      {result && (
        <div className="mt-6 p-6 bg-gray-900 border border-gray-800 rounded-xl">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-green-400 text-lg">✓</span>
            <h3 className="text-white font-semibold">Upload Complete</h3>
          </div>

          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-400">File</span>
              <span className="text-white">{result.filename}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Type</span>
              <span className="text-white">{result.mime_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Hash</span>
              <span className="text-white font-mono text-xs">
                {result.hash.slice(0, 16)}...
              </span>
            </div>
          </div>

          <button
            onClick={copyShareUrl}
            className="mt-4 w-full py-2.5 px-4 bg-aleph-blue hover:bg-aleph-blue/80 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {copied ? "✓ Copied!" : "📋 Copy Share Link"}
          </button>
        </div>
      )}
    </div>
  );
}
