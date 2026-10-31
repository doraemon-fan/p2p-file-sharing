import React, { useEffect, useState } from 'react';
import { FolderSync, FileText, RefreshCw, Upload, Radio } from 'lucide-react';
import { fetchSharedFiles, formatBytes, announceSharedFiles } from '../services/api';
import type { SharedFileItem } from '../types';

interface SharedFilesPageProps {
  onNavigateToSend: () => void;
}

export const SharedFilesPage: React.FC<SharedFilesPageProps> = ({ onNavigateToSend }) => {
  const [files, setFiles] = useState<SharedFileItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [announcing, setAnnouncing] = useState<boolean>(false);
  const [announceMsg, setAnnounceMsg] = useState<string | null>(null);

  const loadFiles = async () => {
    setIsLoading(true);
    try {
      const data = await fetchSharedFiles();
      setFiles(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAnnounce = async () => {
    setAnnouncing(true);
    setAnnounceMsg(null);
    try {
      await announceSharedFiles();
      setAnnounceMsg('Shared folder catalog broadcast to tracker successfully!');
      setTimeout(() => setAnnounceMsg(null), 4000);
    } catch (e: any) {
      setAnnounceMsg('Failed to broadcast to tracker. Ensure tracker server is up.');
    } finally {
      setAnnouncing(false);
    }
  };

  useEffect(() => {
    loadFiles();
  }, []);

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Shared Files</h2>
          <p className="text-sm text-slate-400 mt-1">
            Files currently indexed in your shared directory available for peers to download.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadFiles}
            className="p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-400 hover:text-white transition"
            title="Refresh"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleAnnounce}
            disabled={announcing}
            className="px-3.5 py-2 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 font-medium text-xs rounded-xl transition flex items-center gap-2"
          >
            <Radio className={`h-3.5 w-3.5 ${announcing ? 'animate-spin' : ''}`} />
            Broadcast to Tracker
          </button>
          <button
            onClick={onNavigateToSend}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm rounded-xl transition flex items-center gap-2"
          >
            <Upload className="h-4 w-4" />
            Add / Send File
          </button>
        </div>
      </div>

      {announceMsg && (
        <div className="p-3 bg-indigo-950/40 border border-indigo-800 text-indigo-300 rounded-xl text-xs">
          {announceMsg}
        </div>
      )}

      <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl">
        {files.length === 0 ? (
          <div className="py-12 text-center text-slate-500 space-y-2">
            <FolderSync className="h-10 w-10 mx-auto text-slate-600 stroke-[1.5]" />
            <p className="text-sm">No files in your shared directory yet.</p>
            <p className="text-xs text-slate-600">Files placed in the shared directory or uploaded via Send Files will appear here.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {files.map((file) => (
              <div key={file.path} className="py-3.5 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400">
                    <FileText className="h-5 w-5" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-200">{file.name}</p>
                    <p className="text-xs text-slate-500 font-mono mt-0.5 truncate max-w-md">{file.path}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-mono text-slate-300 font-medium">{formatBytes(file.size)}</p>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mt-1">
                    Ready to Seed
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
