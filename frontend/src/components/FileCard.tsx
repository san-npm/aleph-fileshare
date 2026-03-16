"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { FileListItem, formatBytes, getScanStatus } from "@/lib/api";

interface FileCardProps {
  file: FileListItem;
  onDelete?: (hash: string) => void;
}

const SCAN_BADGE: Record<string, { color: string; label: string; icon: string }> = {
  clean: {
    color: "bg-green-900/50 text-green-300 border-green-800/50",
    label: "Clean",
    icon: "✓",
  },
  pending: {
    color: "bg-yellow-900/50 text-yellow-300 border-yellow-800/50 animate-pulse",
    label: "Scanning...",
    icon: "⏳",
  },
  flagged: {
    color: "bg-red-900/50 text-red-300 border-red-800/50",
    label: "Flagged",
    icon: "⚠",
  },
  error: {
    color: "bg-gray-900/50 text-gray-400 border-gray-700/50",
    label: "Error",
    icon: "✗",
  },
};

export function FileCard({ file, onDelete }: FileCardProps) {
  const [scanStatus, setScanStatus] = useState(file.scan_status);
  const [tags, setTags] = useState<string[]>(file.tags || []);
  const [copied, setCopied] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-refresh scan status every 5 seconds while pending
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
        const data = await getScanStatus(file.hash);
        setScanStatus(data.scan_status);
        if (data.tags && data.tags.length > 0) {
          setTags(data.tags);
        }
        if (data.scan_status !== "pending" && intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      } catch {
        // Silently continue polling
      }
    }, 5000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [scanStatus, file.hash]);

  // Also poll for tags if scan is clean but tags are empty
  useEffect(() => {
    if (scanStatus !== "clean" || tags.length > 0) return;

    const tagInterval = setInterval(async () => {
      try {
        const data = await getScanStatus(file.hash);
        if (data.tags && data.tags.length > 0) {
          setTags(data.tags);
          clearInterval(tagInterval);
        }
      } catch {
        // Silently continue
      }
    }, 5000);

    return () => clearInterval(tagInterval);
  }, [scanStatus, tags, file.hash]);

  const badge = SCAN_BADGE[scanStatus] || SCAN_BADGE.pending;
  const date = new Date(file.uploaded_at).toLocaleDateString();

  const copyLink = () => {
    navigator.clipboard.writeText(`${window.location.origin}/d/${file.hash}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDelete = async () => {
    if (!showConfirmDelete) {
      setShowConfirmDelete(true);
      setTimeout(() => setShowConfirmDelete(false), 3000);
      return;
    }
    if (!onDelete) return;
    setIsDeleting(true);
    try {
      await onDelete(file.hash);
    } finally {
      setIsDeleting(false);
      setShowConfirmDelete(false);
    }
  };

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-all duration-200 group">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-white font-medium truncate pr-4 max-w-[70%]" title={file.filename}>
          {file.filename}
        </h3>
        <span className={`text-xs px-2 py-0.5 rounded-full border whitespace-nowrap ${badge.color}`}>
          {badge.icon} {badge.label}
        </span>
      </div>

      <div className="flex items-center gap-3 text-sm text-gray-400 mb-3">
        <span>{formatBytes(file.size_bytes)}</span>
        <span className="text-gray-600">·</span>
        <span>{date}</span>
      </div>

      {/* Tags */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          {tags.map((tag) => (
            <span
              key={tag}
              className="text-xs px-2 py-0.5 bg-aleph-blue/10 text-aleph-blue border border-aleph-blue/20 rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

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
          title={copied ? "Copied!" : "Copy share link"}
        >
          {copied ? "✓" : "📋"}
        </button>
        {onDelete && (
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className={`py-2 px-3 text-sm rounded-lg transition-colors ${
              showConfirmDelete
                ? "bg-red-600 hover:bg-red-700 text-white"
                : "bg-red-900/30 hover:bg-red-900/60 text-red-300"
            } ${isDeleting ? "opacity-50 cursor-not-allowed" : ""}`}
            title={showConfirmDelete ? "Click again to confirm" : "Delete file"}
          >
            {isDeleting ? "..." : showConfirmDelete ? "Sure?" : "🗑️"}
          </button>
        )}
      </div>
    </div>
  );
}
