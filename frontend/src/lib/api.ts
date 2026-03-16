import { config } from "./config";

const BASE_URL = config.apiUrl;

export type AuthHeaders = Record<string, string> & {
  "X-Wallet-Address": string;
  "X-Wallet-Signature": string;
  "X-Wallet-Nonce": string;
};

export interface ChallengeResponse {
  nonce: string;
  message: string;
  expires_at: number;
}

export interface FileUploadResponse {
  hash: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  public: boolean;
  share_url: string;
  uploaded_at: string;
}

export interface FileMetadata {
  hash: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  public: boolean;
  uploader: string;
  uploaded_at: string;
  scan_status: string;
  tags: string[];
  description: string;
}

export interface FileListItem {
  hash: string;
  filename: string;
  size_bytes: number;
  uploaded_at: string;
  scan_status: string;
  tags: string[];
}

export interface ScanStatusResponse {
  hash: string;
  scan_status: string;
  tags: string[];
  description: string;
}

export interface FileListResponse {
  total: number;
  limit: number;
  offset: number;
  files: FileListItem[];
}

export async function getChallenge(
  address: string
): Promise<ChallengeResponse> {
  const res = await fetch(
    `${BASE_URL}/auth/challenge?address=${encodeURIComponent(address)}`
  );
  if (!res.ok) throw new Error("Failed to get challenge");
  return res.json();
}

export async function uploadFile(
  file: File,
  authHeaders: AuthHeaders,
  isPublic: boolean = true,
  onProgress?: (pct: number) => void
): Promise<FileUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("public", String(isPublic));

  // Use XMLHttpRequest for progress tracking
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE_URL}/files/upload`);

    // Set auth headers
    xhr.setRequestHeader("X-Wallet-Address", authHeaders["X-Wallet-Address"]);
    xhr.setRequestHeader(
      "X-Wallet-Signature",
      authHeaders["X-Wallet-Signature"]
    );
    xhr.setRequestHeader("X-Wallet-Nonce", authHeaders["X-Wallet-Nonce"]);

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status === 201) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(xhr.responseText || "Upload failed"));
      }
    };

    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(formData);
  });
}

export async function getScanStatus(hash: string): Promise<ScanStatusResponse> {
  const res = await fetch(`${BASE_URL}/files/${hash}/scan-status`);
  if (!res.ok) throw new Error("Failed to get scan status");
  return res.json();
}

export async function getFileMetadata(hash: string): Promise<FileMetadata> {
  const res = await fetch(`${BASE_URL}/files/${hash}`);
  if (!res.ok) throw new Error("File not found");
  return res.json();
}

export async function getFileDownloadUrl(hash: string): Promise<string> {
  return `${BASE_URL}/files/${hash}/download`;
}

export async function listFiles(
  authHeaders: AuthHeaders,
  limit: number = 20,
  offset: number = 0,
  sort: string = "uploaded_at_desc"
): Promise<FileListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    sort,
  });
  const res = await fetch(`${BASE_URL}/files?${params}`, {
    headers: authHeaders,
  });
  if (!res.ok) throw new Error("Failed to list files");
  return res.json();
}

export async function deleteFile(
  hash: string,
  authHeaders: AuthHeaders
): Promise<void> {
  const res = await fetch(`${BASE_URL}/files/${hash}`, {
    method: "DELETE",
    headers: authHeaders,
  });
  if (!res.ok) throw new Error("Failed to delete file");
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}
