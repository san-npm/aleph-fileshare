"use client";

import { useState, useCallback, useEffect } from "react";
import { useAccount, useSignMessage } from "wagmi";
import {
  getChallenge,
  listFiles,
  deleteFile,
  FileListItem,
} from "@/lib/api";

interface UseFilesReturn {
  files: FileListItem[];
  total: number;
  isLoading: boolean;
  error: string | null;
  fetchFiles: (offset?: number) => Promise<void>;
  removeFile: (hash: string) => Promise<void>;
}

export function useFiles(limit: number = 20): UseFilesReturn {
  const { address } = useAccount();
  const { signMessageAsync } = useSignMessage();
  const [files, setFiles] = useState<FileListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const getAuthHeaders = useCallback(async () => {
    if (!address) throw new Error("Wallet not connected");
    const challenge = await getChallenge(address);
    const signature = await signMessageAsync({
      message: challenge.message,
    });
    return {
      "X-Wallet-Address": address,
      "X-Wallet-Signature": signature,
      "X-Wallet-Nonce": challenge.nonce,
    };
  }, [address, signMessageAsync]);

  const fetchFiles = useCallback(
    async (offset: number = 0) => {
      if (!address) return;
      setIsLoading(true);
      setError(null);
      try {
        const auth = await getAuthHeaders();
        const result = await listFiles(auth, limit, offset);
        setFiles(result.files);
        setTotal(result.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load files");
      } finally {
        setIsLoading(false);
      }
    },
    [address, getAuthHeaders, limit]
  );

  const removeFile = useCallback(
    async (hash: string) => {
      try {
        const auth = await getAuthHeaders();
        await deleteFile(hash, auth);
        setFiles((prev) => prev.filter((f) => f.hash !== hash));
        setTotal((prev) => prev - 1);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to delete file");
      }
    },
    [getAuthHeaders]
  );

  return { files, total, isLoading, error, fetchFiles, removeFile };
}
