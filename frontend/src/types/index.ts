export interface NodeStatus {
  peer_id: string;
  peer_name: string;
  p2p_port: number;
  status: string;
  downloads_dir: string;
  shared_dir: string;
  total_uploaded: number;
  total_downloaded: number;
  active_transfers_count: number;
}

export interface TransferItem {
  id: string;
  filename: string;
  direction: 'upload' | 'download';
  total_bytes: number;
  transferred_bytes: number;
  speed_bytes_sec: number;
  progress_percent: number;
  status: 'pending' | 'active' | 'completed' | 'failed';
  peer_address: string;
  sha256?: string;
  error?: string;
  start_time: number;
  elapsed_time: number;
}

export interface TransferHistoryRecord {
  id: string;
  filename: string;
  direction: 'upload' | 'download';
  file_size: number;
  peer_address: string;
  sha256: string;
  status: string;
  duration: number;
  average_speed: number;
  timestamp: number;
}

export interface SharedFileItem {
  name: string;
  path: string;
  size: number;
  modified: number;
  status: string;
}

export interface DownloadedFileItem {
  name: string;
  path: string;
  size: number;
  modified: number;
}

export interface AppSettings {
  peer_id: string;
  peer_name: string;
  p2p_port: number;
  api_port: number;
  downloads_dir: string;
  shared_dir: string;
  tracker_url: string;
}

export interface TrackerPeer {
  peer_id: string;
  peer_name: string;
  host: string;
  port: number;
  last_heartbeat: number;
  status: string;
}

export interface TrackerFile {
  id: number;
  file_id: string;
  filename: string;
  file_size: number;
  sha256: string;
  peer_id: string;
  peer_name: string;
  host: string;
  port: number;
  announced_at: number;
}
