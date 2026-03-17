"use client";

import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getFileMetadata,
  getScanStatus,
  downloadFileWithPassword,
  formatBytes,
  formatTimeRemaining,
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

const SCAN_BADGE_STYLES: Record<string, string> = {
  clean: "bg-green-900/50 text-green-300 border border-green-800/50",
  pending: "bg-yellow-900/50 text-yellow-300 border border-yellow-800/50 animate-pulse",
  flagged: "bg-red-900/50 text-red-300 border border-red-800/50",
  error: "bg-gray-900/50 text-gray-400 border border-gray-700/50",
};

const SCAN_LABELS: Record<string, string> = {
  clean: "✓ Clean",
  pending: "⏳ Scanning...",
  flagged: "⚠ Flagged",
  error: "✗ Scan Error",
};

export default function DownloadPage() {
  const params = useParams();
  const hash = params.hash as string;
  const [metadata, setMetadata] = useState<FileMetadata | null>(null);
  const [scanStatus, setScanStatus] = useState<string>("pending");
  const [tags, setTags] = useState<string[]>([]);
  const [description, setDescription] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Password state
  const [password, setPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await getFileMetadata(hash);
        setMetadata(data);
        setScanStatus(data.scan_status);
        setTags(data.tags || []);
        setDescription(data.description || "");
      } catch {
        setError("File not found or unavailable.");
      } finally {
        setIsLoading(false);
      }
    }
    if (hash) load();
  }, [hash]);

  // Auto-refresh scan status while pending
  useEffect(() => {
    if (scanStatus !== "pending") {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    intervalRef.current = setInterval(async () => {
      try {
        const data = await getScanStatus(hash);
        setScanStatus(data.scan_status);
        if (data.tags && data.tags.length > 0) setTags(data.tags);
        if (data.description) setDescription(data.description);
        if (data.scan_status !== "pending" && intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } catch {
        // Continue polling
      }
    }, 5000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [scanStatus, hash]);

  // Poll for tags after scan completes
  useEffect(() => {
    if (scanStatus !== "clean" || tags.length > 0) return;

    const tagInterval = setInterval(async () => {
      try {
        const data = await getScanStatus(hash);
        if (data.tags && data.tags.length > 0) {
          setTags(data.tags);
          if (data.description) setDescription(data.description);
          clearInterval(tagInterval);
        }
      } catch {
        // Continue
      }
    }, 5000);

    return () => clearInterval(tagInterval);
  }, [scanStatus, tags, hash]);

  const handlePasswordDownload = async () => {
    setPasswordError(null);
    setIsDownloading(true);
    try {
      const res = await downloadFileWithPassword(hash, password);
      if (!res.ok) {
        if (res.status === 401) {
          setPasswordError("Incorrect password.");
        } else if (res.status === 410) {
          setPasswordError("This link has expired.");
        } else {
          setPasswordError("Download failed.");
        }
        return;
      }
      // Trigger browser download
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = metadata?.filename || "download";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      setPasswordError("Download failed.");
    } finally {
      setIsDownloading(false);
    }
  };

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
  const badgeStyle = SCAN_BADGE_STYLES[scanStatus] || SCAN_BADGE_STYLES.pending;
  const badgeLabel = SCAN_LABELS[scanStatus] || SCAN_LABELS.pending;
  const expiryLabel = formatTimeRemaining(metadata.expires_at);

  const isExpired = metadata.is_expired;
  const needsPassword = metadata.password_protected;

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
          {/* Expiry + Password badges */}
          <div className="flex items-center justify-center gap-2 mt-3">
            {expiryLabel && (
              <span
                className={`text-xs px-2.5 py-1 rounded-full border ${
                  isExpired
                    ? "bg-red-900/50 text-red-300 border-red-800/50"
                    : "bg-yellow-900/30 text-yellow-300 border-yellow-800/30"
                }`}
              >
                {expiryLabel}
              </span>
            )}
            {needsPassword && (
              <span className="text-xs px-2.5 py-1 rounded-full border bg-aleph-blue/10 text-aleph-blue border-aleph-blue/20">
                Password Protected
              </span>
            )}
          </div>
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
            {/* Always show scan status */}
            <div className="flex justify-between items-center py-2 border-b border-gray-800/50">
              <span className="text-gray-400">Scan Status</span>
              <span className={`text-xs px-2.5 py-1 rounded-full ${badgeStyle}`}>
                {badgeLabel}
              </span>
            </div>
            {/* Tags */}
            {tags.length > 0 && (
              <div className="flex justify-between items-start py-2 border-b border-gray-800/50">
                <span className="text-gray-400 pt-0.5">Tags</span>
                <div className="flex gap-1.5 flex-wrap justify-end max-w-[70%]">
                  {tags.map((tag) => (
                    <span
                      key={tag}
                      className="text-xs px-2 py-0.5 bg-aleph-blue/10 text-aleph-blue border border-aleph-blue/20 rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {/* AI Description */}
            {description && (
              <div className="py-3 border-b border-gray-800/50">
                <span className="text-gray-400 block mb-2 text-xs uppercase tracking-wide">
                  AI Description
                </span>
                <p className="text-white text-sm leading-relaxed">
                  {description}
                </p>
              </div>
            )}
          </div>

          {isExpired ? (
            <div className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-red-900/30 text-red-300 rounded-lg font-medium border border-red-800/30">
              <span>⏰</span>
              <span>This link has expired</span>
            </div>
          ) : scanStatus === "flagged" ? (
            <div className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-red-900/30 text-red-300 rounded-lg font-medium border border-red-800/30">
              <span>⚠</span>
              <span>This file has been flagged and is unavailable for download</span>
            </div>
          ) : needsPassword ? (
            <div>
              <div className="flex gap-2 mb-2">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    setPasswordError(null);
                  }}
                  placeholder="Enter download password"
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm placeholder-gray-500 focus:outline-none focus:border-aleph-blue transition-colors"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && password) handlePasswordDownload();
                  }}
                />
                <button
                  onClick={handlePasswordDownload}
                  disabled={!password || isDownloading}
                  className="flex items-center gap-2 py-3 px-6 bg-aleph-blue hover:bg-aleph-blue/80 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  {isDownloading ? "Downloading..." : "Download"}
                </button>
              </div>
              {passwordError && (
                <p className="text-red-400 text-sm mt-1">{passwordError}</p>
              )}
            </div>
          ) : (
            <a
              href={downloadUrl}
              className="flex items-center justify-center gap-2 w-full py-3 px-4 bg-aleph-blue hover:bg-aleph-blue/80 text-white rounded-lg font-medium transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download File
            </a>
          )}

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
