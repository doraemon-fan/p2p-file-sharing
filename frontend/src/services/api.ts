import type { NodeStatus, TransferItem, TransferHistoryRecord, SharedFileItem, DownloadedFileItem, AppSettings } from '../types';

const API_BASE = '/api';

export async function fetchStatus(): Promise<NodeStatus> {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error('Failed to fetch status');
  return res.json();
}

export async function fetchTransfers(): Promise<TransferItem[]> {
  const res = await fetch(`${API_BASE}/transfers`);
  if (!res.ok) throw new Error('Failed to fetch transfers');
  return res.json();
}

export async function fetchHistory(): Promise<TransferHistoryRecord[]> {
  const res = await fetch(`${API_BASE}/history`);
  if (!res.ok) throw new Error('Failed to fetch history');
  return res.json();
}

export async function fetchSharedFiles(): Promise<SharedFileItem[]> {
  const res = await fetch(`${API_BASE}/shared-files`);
  if (!res.ok) throw new Error('Failed to fetch shared files');
  return res.json();
}

export async function fetchDownloadedFiles(): Promise<DownloadedFileItem[]> {
  const res = await fetch(`${API_BASE}/downloaded-files`);
  if (!res.ok) throw new Error('Failed to fetch downloaded files');
  return res.json();
}

export async function fetchSettings(): Promise<AppSettings> {
  const res = await fetch(`${API_BASE}/settings`);
  if (!res.ok) throw new Error('Failed to fetch settings');
  return res.json();
}

export async function updateSettings(settings: Partial<AppSettings>): Promise<void> {
  const res = await fetch(`${API_BASE}/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to update settings');
}

export async function sendLocalFilePath(filePath: string, peerHost: string, peerPort: number): Promise<{ transfer_id: string }> {
  const res = await fetch(`${API_BASE}/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      file_path: filePath,
      peer_host: peerHost,
      peer_port: peerPort,
    }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(errorData.detail || 'Failed to send file');
  }
  return res.json();
}

export async function uploadAndSendFile(file: File, peerHost: string, peerPort: number): Promise<{ transfer_id: string }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('peer_host', peerHost);
  formData.append('peer_port', peerPort.toString());

  const res = await fetch(`${API_BASE}/upload-and-send`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(errorData.detail || 'Failed to upload and send file');
  }
  return res.json();
}

export function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

export function formatSpeed(bytesPerSec: number): string {
  return `${formatBytes(bytesPerSec)}/s`;
}
