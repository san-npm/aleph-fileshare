"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { formatBytes, formatTimeRemaining } from "@/lib/api";
import { config } from "@/lib/config";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface SimilarFileItem {
  hash: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
  tags: string[];
  score: number;
}

interface SimilarFilesResponse {
  file_hash: string;
  similar: SimilarFileItem[];
  total: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

async function fetchSimilarFiles(
  fileHash: string
): Promise<SimilarFileItem[]> {
  const res = await fetch(
    `${config.apiUrl}/api/recommendations/similar/${fileHash}`
  );
  if (!res.ok) return [];
  const data: SimilarFilesResponse = await res.json();
  return data.similar ?? [];
}

async function trackInteraction(
  fileHash: string,
  action: "view" | "download",
  walletAddress?: string
): Promise<void> {
  const params = new URLSearchParams({ file_hash: fileHash, action });
  const headers: Record<string, string> = {};
  if (walletAddress) {
    headers["X-Wallet-Address"] = walletAddress;
  }
  try {
    await fetch(`${config.apiUrl}/api/recommendations/track?${params}`, {
      method: "POST",
      headers,
    });
  } catch {
    // Fire-and-forget — ignore errors
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface SimilarFilesProps {
  /** Hash of the currently viewed file */
  fileHash: string;
  /** Optional: wallet address of the viewer for personalised tracking */
  walletAddress?: string;
}

/**
 * SimilarFiles sidebar component.
 *
 * Fetches recommendation data from the backend and renders a compact list
 * of files that other users who interacted with this file also accessed.
 * Silently hides itself when no recommendations are available.
 */
export default function SimilarFiles({
  fileHash,
  walletAddress,
}: SimilarFilesProps) {
  const [items, setItems] = useState<SimilarFileItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      try {
        const similar = await fetchSimilarFiles(fileHash);
        if (!cancelled) setItems(similar);
      } catch {
        // Silently ignore — recommendations are non-critical
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    // Track this view for the recommendation engine
    trackInteraction(fileHash, "view", walletAddress);

    load();
    return () => {
      cancelled = true;
    };
  }, [fileHash, walletAddress]);

  // Don't render anything while loading or when no data
  if (loading) {
    return (
      <div className="mt-6 bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <span className="text-base font-semibold text-white">Similar Files</span>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex items-center gap-3 animate-pulse"
            >
              <div className="w-9 h-9 bg-gray-800 rounded-lg shrink-0" />
              <div className="flex-1 min-w-0 space-y-1.5">
                <div className="h-3 bg-gray-800 rounded w-3/4" />
                <div className="h-2.5 bg-gray-800/70 rounded w-1/2" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (items.length === 0) return null;

  return (
    <div className="mt-6 bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white">Similar Files</span>
          <span className="text-xs text-gray-500 bg-gray-800 px-1.5 py-0.5 rounded-full">
            {items.length}
          </span>
        </div>
        <span className="text-xs text-gray-500">Powered by AI</span>
      </div>

      {/* File list */}
      <ul className="divide-y divide-gray-800/50">
        {items.map((item) => {
          const icon = getFileIcon(item.mime_type);
          const uploadedDate = new Date(item.uploaded_at).toLocaleDateString(
            undefined,
            { month: "short", day: "numeric" }
          );

          return (
            <li key={item.hash}>
              <Link
                href={`/d/${item.hash}`}
                className="flex items-center gap-3 px-5 py-3.5 hover:bg-gray-800/40 transition-colors group"
                onClick={() => trackInteraction(item.hash, "view", walletAddress)}
              >
                {/* Icon */}
                <div className="w-9 h-9 bg-gray-800/60 border border-gray-700/50 rounded-lg flex items-center justify-center shrink-0 group-hover:border-aleph-blue/30 transition-colors">
                  <span className="text-lg leading-none">{icon}</span>
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white font-medium truncate group-hover:text-aleph-blue transition-colors">
                    {item.filename}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-xs text-gray-500">
                      {formatBytes(item.size_bytes)}
                    </span>
                    <span className="text-gray-700">·</span>
                    <span className="text-xs text-gray-500">{uploadedDate}</span>
                  </div>
                  {/* Tags */}
                  {item.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {item.tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          className="text-[10px] px-1.5 py-0.5 bg-aleph-blue/10 text-aleph-blue border border-aleph-blue/20 rounded-full"
                        >
                          {tag}
                        </span>
                      ))}
                      {item.tags.length > 3 && (
                        <span className="text-[10px] text-gray-500">
                          +{item.tags.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Arrow */}
                <svg
                  className="w-4 h-4 text-gray-600 group-hover:text-aleph-blue shrink-0 transition-colors"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              </Link>
            </li>
          );
        })}
      </ul>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-800/50 bg-gray-900/50">
        <p className="text-xs text-gray-600 text-center">
          Based on what others who downloaded this file also accessed
        </p>
      </div>
    </div>
  );
}
