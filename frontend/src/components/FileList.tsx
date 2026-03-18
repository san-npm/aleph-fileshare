"use client";

import { useEffect } from "react";
import { useAccount } from "wagmi";
import { useFiles } from "@/hooks/useFiles";
import { FileCard } from "./FileCard";

export function FileList() {
  const { isConnected } = useAccount();
  const { files, total, isLoading, error, fetchFiles, removeFile, toggleLink, fetchAccessLog } =
    useFiles();

  useEffect(() => {
    if (isConnected) {
      fetchFiles();
    }
  }, [isConnected]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!isConnected) {
    return (
      <div className="text-center py-20">
        <p className="text-gray-400">Connect your wallet to see your files.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="text-center py-20">
        <div className="animate-spin text-4xl mb-4">⬡</div>
        <p className="text-gray-400">Loading your files...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-400 mb-4">{error}</p>
        <button
          onClick={() => fetchFiles()}
          className="text-aleph-blue hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="text-center py-20">
        <div className="text-4xl mb-4">📭</div>
        <p className="text-gray-400 mb-2">No files yet</p>
        <p className="text-gray-500 text-sm">
          Upload your first file from the home page.
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-white">
          Your Files ({total})
        </h2>
        <button
          onClick={() => fetchFiles()}
          className="text-sm text-gray-400 hover:text-white transition-colors"
        >
          ↻ Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {files.map((file) => (
          <FileCard
            key={file.hash}
            file={file}
            onDelete={removeFile}
            onToggleLink={toggleLink}
            onGetAccessLog={fetchAccessLog}
          />
        ))}
      </div>
    </div>
  );
}
