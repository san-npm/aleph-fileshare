"use client";

import Link from "next/link";
import { FileListItem, formatBytes } from "@/lib/api";

interface FileCardProps {
  file: FileListItem;
  onDelete?: (hash: string) => void;
}

const SCAN_BADGE: Record<string, { color: string; label: string }> = {
  clean: { color: "bg-green-900 text-green-300", label: "Clean" },
  pending: { color: "bg-yellow-900 text-yellow-300", label: "Pending" },
  flagged: { color: "bg-red-900 text-red-300", label: "Flagged" },
};

export function FileCard({ file, onDelete }: FileCardProps) {
  const badge = SCAN_BADGE[file.scan_status] || SCAN_BADGE.pending;
  const date = new Date(file.uploaded_at).toLocaleDateString();

  const copyLink = () => {
    navigator.clipboard.writeText(`${window.location.origin}/d/${file.hash}`);
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-white font-medium truncate pr-4 max-w-[70%]">
          {file.filename}
        </h3>
        <span className={`text-xs px-2 py-0.5 rounded-full ${badge.color}`}>
          {badge.label}
        </span>
      </div>

      <div className="flex items-center gap-4 text-sm text-gray-400 mb-4">
        <span>{formatBytes(file.size_bytes)}</span>
        <span>·</span>
        <span>{date}</span>
      </div>

      <div className="flex items-center gap-2">
        <Link
          href={`/d/${file.hash}`}
          className="flex-1 text-center py-2 text-sm bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors"
        >
          View
        </Link>
        <button
          onClick={copyLink}
          className="py-2 px-3 text-sm bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors"
          title="Copy share link"
        >
          📋
        </button>
        {onDelete && (
          <button
            onClick={() => onDelete(file.hash)}
            className="py-2 px-3 text-sm bg-red-900/50 hover:bg-red-900 text-red-300 rounded-lg transition-colors"
            title="Delete file"
          >
            🗑️
          </button>
        )}
      </div>
    </div>
  );
}
