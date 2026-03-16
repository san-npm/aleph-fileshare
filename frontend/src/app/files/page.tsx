"use client";

import dynamic from "next/dynamic";

const FileList = dynamic(() => import("@/components/FileList").then((m) => m.FileList), {
  ssr: false,
});

export default function FilesPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">My Files</h1>
        <p className="text-gray-400">
          Manage all your uploaded files on Aleph Cloud.
        </p>
      </div>

      <FileList />
    </div>
  );
}
