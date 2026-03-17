"use client";

import { useState, useCallback } from "react";
import { useAccount, useSignMessage } from "wagmi";
import {
  getChallenge,
  uploadFile,
  FileUploadResponse,
  UploadOptions,
} from "@/lib/api";

interface UseFileUploadReturn {
  upload: (file: File, options?: UploadOptions) => Promise<FileUploadResponse | null>;
  isUploading: boolean;
  progress: number;
  error: string | null;
  result: FileUploadResponse | null;
  reset: () => void;
}

export function useFileUpload(): UseFileUploadReturn {
  const { address } = useAccount();
  const { signMessageAsync } = useSignMessage();
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FileUploadResponse | null>(null);

  const reset = useCallback(() => {
    setIsUploading(false);
    setProgress(0);
    setError(null);
    setResult(null);
  }, []);

  const upload = useCallback(
    async (
      file: File,
      options: UploadOptions = {}
    ): Promise<FileUploadResponse | null> => {
      if (!address) {
        setError("Please connect your wallet first.");
        return null;
      }

      setIsUploading(true);
      setProgress(0);
      setError(null);
      setResult(null);

      try {
        // 1. Get challenge
        const challenge = await getChallenge(address);

        // 2. Sign the message
        const signature = await signMessageAsync({
          message: challenge.message,
        });

        // 3. Upload with auth headers
        const authHeaders = {
          "X-Wallet-Address": address,
          "X-Wallet-Signature": signature,
          "X-Wallet-Nonce": challenge.nonce,
        };

        const uploadResult = await uploadFile(
          file,
          authHeaders,
          options,
          (pct) => setProgress(pct)
        );

        setResult(uploadResult);
        setProgress(100);
        return uploadResult;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Upload failed";
        setError(message);
        return null;
      } finally {
        setIsUploading(false);
      }
    },
    [address, signMessageAsync]
  );

  return { upload, isUploading, progress, error, result, reset };
}
