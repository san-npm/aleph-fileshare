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
  expires_at: string | null;
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
  expires_at: string | null;
  password_protected: boolean;
  is_expired: boolean;
}

export interface FileListItem {
  hash: string;
  filename: string;
  size_bytes: number;
  uploaded_at: string;
  scan_status: string;
  tags: string[];
  expires_at: string | null;
  password_protected: boolean;
  is_expired: boolean;
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

export interface AccessLogEntry {
  file_hash: string;
  action: string;
  actor: string;
  ip: string;
  timestamp: string;
}

export interface UploadOptions {
  isPublic?: boolean;
  expiresInHours?: number;
  password?: string;
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
  options: UploadOptions = {},
  onProgress?: (pct: number) => void
): Promise<FileUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("public", String(options.isPublic ?? true));
  if (options.expiresInHours && options.expiresInHours > 0) {
    formData.append("expires_in_hours", String(options.expiresInHours));
  }
  if (options.password) {
    formData.append("password", options.password);
  }

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

export async function downloadFileWithPassword(
  hash: string,
  password: string
): Promise<Response> {
  return fetch(`${BASE_URL}/files/${hash}/download`, {
    headers: { "X-Download-Password": password },
  });
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

export async function getAccessLog(
  hash: string,
  authHeaders: AuthHeaders
): Promise<AccessLogEntry[]> {
  const res = await fetch(`${BASE_URL}/files/${hash}/access-log`, {
    headers: authHeaders,
  });
  if (!res.ok) throw new Error("Failed to get access log");
  return res.json();
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

export function formatTimeRemaining(expiresAt: string | null): string | null {
  if (!expiresAt) return null;
  const expiry = new Date(expiresAt).getTime();
  const now = Date.now();
  const diff = expiry - now;
  if (diff <= 0) return "Expired";
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(hours / 24);
  if (days > 0) return `Expires in ${days}d`;
  if (hours > 0) return `Expires in ${hours}h`;
  const minutes = Math.floor(diff / (1000 * 60));
  return `Expires in ${minutes}m`;
}
