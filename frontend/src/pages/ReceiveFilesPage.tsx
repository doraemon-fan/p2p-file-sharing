import React, { useEffect, useState } from 'react';
import { 
  DownloadCloud, 
  FolderDown, 
  FileCheck2, 
  Clock, 
  Radio, 
  HardDrive 
} from 'lucide-react';
import { formatBytes, formatSpeed, fetchDownloadedFiles } from '../services/api';
import type { TransferItem, DownloadedFileItem } from '../types';

interface ReceiveFilesProps {
  transfers: TransferItem[];
  downloadsDir?: string;
  p2pPort?: number;
}

export const ReceiveFilesPage: React.FC<ReceiveFilesProps> = ({ transfers, downloadsDir, p2pPort }) => {
  const [downloadedFiles, setDownloadedFiles] = useState<DownloadedFileItem[]>([]);
  const incomingTransfers = transfers.filter(t => t.direction === 'download');

  const loadFiles = async () => {
    try {
      const files = await fetchDownloadedFiles();
      setDownloadedFiles(files);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadFiles();
    const interval = setInterval(loadFiles, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold text-white">Receive Files</h2>
        <p className="text-sm text-slate-400 mt-1">
          PeerShare daemon automatically accepts, streams to temporary storage, verifies SHA-256 checksums, and saves completed files.
        </p>
      </div>

      {/* Receiver Daemon Status Banner */}
      <div className="p-5 bg-gradient-to-r from-emerald-950/30 to-slate-900 border border-emerald-900/40 rounded-2xl flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Radio className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-emerald-300">TCP Daemon Active & Listening</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Listening on port <span className="font-mono text-emerald-400 font-semibold">{p2pPort || 5000}</span> • Saving to: <span className="font-mono text-slate-300">{downloadsDir || 'downloads/'}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Incoming / Active Streams */}
      <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <DownloadCloud className="h-4 w-4 text-emerald-400" />
          Incoming Transfers
        </h3>

        {incomingTransfers.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-sm">
            No incoming transfers right now. When another peer connects to this node, live streaming will appear here.
          </div>
        ) : (
          <div className="space-y-3">
            {incomingTransfers.map((t) => (
              <div key={t.id} className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                <div className="flex justify-between items-center text-sm">
                  <div className="flex items-center gap-2">
                    {t.status === 'active' && <Clock className="h-4 w-4 text-emerald-400 animate-spin" />}
                    {t.status === 'completed' && <FileCheck2 className="h-4 w-4 text-emerald-400" />}
                    <span className="font-semibold text-slate-200">{t.filename}</span>
                  </div>
                  <span className="font-mono text-xs text-emerald-400 font-semibold">{t.progress_percent.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-full transition-all duration-200"
                    style={{ width: `${t.progress_percent}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-400 font-mono pt-1">
                  <span>{formatBytes(t.transferred_bytes)} / {formatBytes(t.total_bytes)}</span>
                  <span>{formatSpeed(t.speed_bytes_sec)}</span>
                  <span>From: {t.peer_address}</span>
                </div>
                {t.sha256 && (
                  <p className="text-[11px] font-mono text-slate-500 truncate pt-1">
                    SHA-256: {t.sha256}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Completed Downloaded Files on Disk */}
      <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <FolderDown className="h-4 w-4 text-indigo-400" />
            Completed Files in Downloads Directory ({downloadedFiles.length})
          </h3>
          <button
            onClick={loadFiles}
            className="text-xs text-indigo-400 hover:text-indigo-300 transition"
          >
            Refresh
          </button>
        </div>

        {downloadedFiles.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-sm">
            Downloads folder is currently empty.
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {downloadedFiles.map((file) => (
              <div key={file.path} className="py-3 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-slate-800/80 text-slate-400">
                    <HardDrive className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-200">{file.name}</p>
                    <p className="text-xs text-slate-500 font-mono mt-0.5">{file.path}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs font-mono text-slate-300">{formatBytes(file.size)}</span>
                  <p className="text-[10px] text-slate-500">Verified</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
