import React, { useEffect, useState } from 'react';
import { FolderSync, FileText, RefreshCw, Upload } from 'lucide-react';
import { fetchSharedFiles, formatBytes } from '../services/api';
import type { SharedFileItem } from '../types';

interface SharedFilesPageProps {
  onNavigateToSend: () => void;
}

export const SharedFilesPage: React.FC<SharedFilesPageProps> = ({ onNavigateToSend }) => {
  const [files, setFiles] = useState<SharedFileItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

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
            onClick={onNavigateToSend}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm rounded-xl transition flex items-center gap-2"
          >
            <Upload className="h-4 w-4" />
            Add / Send File
          </button>
        </div>
      </div>

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
