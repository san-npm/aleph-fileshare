"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getFileMetadata,
  formatBytes,
  FileMetadata,
} from "@/lib/api";
import { config } from "@/lib/config";

const FILE_ICONS: Record<string, string> = {
  "image/": "🖼️",
  "video/": "🎬",
  "audio/": "🎵",
  "application/pdf": "📕",
  "application/zip": "📦",
  "text/": "📝",
  "application/json": "📋",
};

function getFileIcon(mimeType: string): string {
  for (const [prefix, icon] of Object.entries(FILE_ICONS)) {
    if (mimeType.startsWith(prefix)) return icon;
  }
  return "📄";
}

export default function DownloadPage() {
  const params = useParams();
  const hash = params.hash as string;
  const [metadata, setMetadata] = useState<FileMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await getFileMetadata(hash);
        setMetadata(data);
      } catch {
        setError("File not found or unavailable.");
      } finally {
        setIsLoading(false);
      }
    }
    if (hash) load();
  }, [hash]);

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-gray-700 border-t-aleph-blue rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading file info...</p>
        </div>
      </div>
    );
  }

  if (error || !metadata) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center max-w-sm">
          <div className="w-16 h-16 bg-red-900/20 border border-red-800/30 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">😕</span>
          </div>
          <h2 className="text-xl font-bold text-white mb-2">File Not Found</h2>
          <p className="text-gray-400 mb-6 text-sm">
            {error || "This file may have been deleted or the link is invalid."}
          </p>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-aleph-blue hover:underline text-sm"
          >
            ← Back to home
          </Link>
        </div>
      </div>
    );
  }

  const downloadUrl = `${config.apiUrl}/files/${hash}/download`;
  const date = new Date(metadata.uploaded_at).toLocaleString();
  const icon = getFileIcon(metadata.mime_type);

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-br from-aleph-blue/10 to-aleph-purple/5 px-8 py-10 text-center border-b border-gray-800">
          <div className="w-20 h-20 bg-gray-800/50 border border-gray-700 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <span className="text-4xl">{icon}</span>
          </div>
          <h1 className="text-2xl font-bold text-white mb-1 break-words">
            {metadata.filename}
          </h1>
          <p className="text-gray-400 text-sm">
            Shared via AlephFileShare
          </p>
        </div>

        {/* Details */}
        <div className="px-8 py-6">
          <div className="space-y-3 text-sm mb-8">
            <div className="flex justify-between py-2 border-b border-gray-800/50">
              <span className="text-gray-400">Type</span>
              <span className="text-white">{metadata.mime_type}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-800/50">
              <span className="text-gray-400">Size</span>
              <span className="text-white">
                {formatBytes(metadata.size_bytes)}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-800/50">
              <span className="text-gray-400">Uploaded</span>
              <span className="text-white">{date}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-800/50">
              <span className="text-gray-400">Hash</span>
              <span className="text-white font-mono text-xs bg-gray-800 px-2 py-0.5 rounded break-all">
                {metadata.hash}
              </span>
            </div>
            <div className="flex justify-between py-2 border-b border-gray-800/50">
              <span className="text-gray-400">Uploader</span>
              <span className="text-white font-mono text-xs bg-gray-800 px-2 py-0.5 rounded">
                {metadata.uploader.slice(0, 6)}...{metadata.uploader.slice(-4)}
              </span>
            </div>
            {metadata.scan_status !== "pending" && (
              <div className="flex justify-between py-2 border-b border-gray-800/50">
                <span className="text-gray-400">Scan Status</span>
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    metadata.scan_status === "clean"
                      ? "bg-green-900 text-green-300"
                      : metadata.scan_status === "flagged"
                      ? "bg-red-900 text-red-300"
                      : "bg-yellow-900 text-yellow-300"
                  }`}
                >
                  {metadata.scan_status}
                </span>
              </div>
            )}
            {metadata.tags.length > 0 && (
              <div className="flex justify-between py-2 border-b border-gray-800/50">
                <span className="text-gray-400">Tags</span>
                <div className="flex gap-1 flex-wrap justify-end">
                  {metadata.tags.map((tag) => (
                    <span
                      key={tag}
                      className="text-xs px-2 py-0.5 bg-gray-800 rounded-full text-gray-300"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {metadata.description && (
              <div className="py-2">
                <span className="text-gray-400 block mb-1">Description</span>
                <span className="text-white text-sm">
                  {metadata.description}
                </span>
              </div>
            )}
          </div>

          <a
            href={downloadUrl}
            className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-aleph-blue hover:bg-aleph-blue/80 text-white rounded-lg font-medium transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download File
          </a>

          <div className="mt-4 text-center">
            <Link
              href="/"
              className="text-gray-400 hover:text-white text-sm transition-colors"
            >
              ← Upload your own files
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
