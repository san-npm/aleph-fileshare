"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getFileMetadata,
  getFileDownloadUrl,
  formatBytes,
  FileMetadata,
} from "@/lib/api";

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
          <div className="animate-spin text-4xl mb-4">⬡</div>
          <p className="text-gray-400">Loading file info...</p>
        </div>
      </div>
    );
  }

  if (error || !metadata) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">😕</div>
          <p className="text-red-400 mb-4">{error || "File not found"}</p>
          <Link href="/" className="text-aleph-blue hover:underline">
            ← Back to home
          </Link>
        </div>
      </div>
    );
  }

  const downloadUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/files/${hash}/download`;
  const date = new Date(metadata.uploaded_at).toLocaleString();

  return (
    <div className="max-w-2xl mx-auto px-4 py-12">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-8">
        <div className="text-center mb-8">
          <div className="text-5xl mb-4">📄</div>
          <h1 className="text-2xl font-bold text-white mb-1">
            {metadata.filename}
          </h1>
          <p className="text-gray-400 text-sm">
            Shared via AlephFileShare
          </p>
        </div>

        <div className="space-y-3 text-sm mb-8">
          <div className="flex justify-between py-2 border-b border-gray-800">
            <span className="text-gray-400">Type</span>
            <span className="text-white">{metadata.mime_type}</span>
          </div>
          <div className="flex justify-between py-2 border-b border-gray-800">
            <span className="text-gray-400">Size</span>
            <span className="text-white">
              {formatBytes(metadata.size_bytes)}
            </span>
          </div>
          <div className="flex justify-between py-2 border-b border-gray-800">
            <span className="text-gray-400">Uploaded</span>
            <span className="text-white">{date}</span>
          </div>
          <div className="flex justify-between py-2 border-b border-gray-800">
            <span className="text-gray-400">Hash</span>
            <span className="text-white font-mono text-xs break-all">
              {metadata.hash}
            </span>
          </div>
          <div className="flex justify-between py-2 border-b border-gray-800">
            <span className="text-gray-400">Uploader</span>
            <span className="text-white font-mono text-xs">
              {metadata.uploader.slice(0, 6)}...{metadata.uploader.slice(-4)}
            </span>
          </div>
          {metadata.tags.length > 0 && (
            <div className="flex justify-between py-2 border-b border-gray-800">
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
              <span className="text-white text-sm">{metadata.description}</span>
            </div>
          )}
        </div>

        <a
          href={downloadUrl}
          className="block w-full py-3 px-4 bg-aleph-blue hover:bg-aleph-blue/80 text-white rounded-lg text-center font-medium transition-colors"
        >
          ⬇️ Download File
        </a>

        <div className="mt-4 text-center">
          <Link href="/" className="text-gray-400 hover:text-white text-sm">
            ← Upload your own files
          </Link>
        </div>
      </div>
    </div>
  );
}
