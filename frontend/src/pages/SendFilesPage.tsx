import React, { useState } from 'react';
import { 
  UploadCloud, 
  FileText, 
  Send, 
  CheckCircle2, 
  AlertCircle, 
  Network 
} from 'lucide-react';
import { formatBytes, formatSpeed, uploadAndSendFile, sendLocalFilePath } from '../services/api';
import type { TransferItem } from '../types';

interface SendFilesProps {
  transfers: TransferItem[];
}

export const SendFilesPage: React.FC<SendFilesProps> = ({ transfers }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [localPath, setLocalPath] = useState<string>('');
  const [peerHost, setPeerHost] = useState<string>('127.0.0.1');
  const [peerPort, setPeerPort] = useState<number>(5000);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const activeUploads = transfers.filter(t => t.direction === 'upload');

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setSelectedFile(e.dataTransfer.files[0]);
      setLocalPath('');
    }
  };

  const handleSend = async () => {
    setFeedback(null);
    setIsSending(true);
    try {
      if (selectedFile) {
        await uploadAndSendFile(selectedFile, peerHost, peerPort);
        setFeedback({ type: 'success', message: `Initiated transfer of ${selectedFile.name} to ${peerHost}:${peerPort}` });
      } else if (localPath.trim()) {
        await sendLocalFilePath(localPath.trim(), peerHost, peerPort);
        setFeedback({ type: 'success', message: `Initiated transfer of local file to ${peerHost}:${peerPort}` });
      } else {
        throw new Error('Please select a file or specify a local file path');
      }
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Transfer initiation failed' });
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold text-white">Send Files to Peer</h2>
        <p className="text-sm text-slate-400 mt-1">
          Direct peer-to-peer TCP file transfer with on-the-fly SHA-256 verification.
        </p>
      </div>

      {feedback && (
        <div className={`p-4 rounded-xl border flex items-center gap-3 ${
          feedback.type === 'success' 
            ? 'bg-emerald-950/40 border-emerald-800 text-emerald-300' 
            : 'bg-rose-950/40 border-rose-800 text-rose-300'
        }`}>
          {feedback.type === 'success' ? <CheckCircle2 className="h-5 w-5" /> : <AlertCircle className="h-5 w-5" />}
          <span className="text-sm font-medium">{feedback.message}</span>
        </div>
      )}

      {/* Target Peer Configuration */}
      <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Network className="h-4 w-4 text-indigo-400" />
          Target Peer Destination
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Target Host / IP</label>
            <input
              type="text"
              value={peerHost}
              onChange={(e) => setPeerHost(e.target.value)}
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              placeholder="127.0.0.1 or LAN IP"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">Target TCP Port</label>
            <input
              type="number"
              value={peerPort}
              onChange={(e) => setPeerPort(parseInt(e.target.value) || 5000)}
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
              placeholder="5000"
            />
          </div>
        </div>
      </div>

      {/* Drag & Drop Area */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleFileDrop}
        className={`border-2 border-dashed rounded-2xl p-8 text-center transition-all ${
          selectedFile
            ? 'border-indigo-500/80 bg-indigo-950/20'
            : 'border-slate-800 hover:border-slate-700 bg-slate-900/40'
        }`}
      >
        <div className="max-w-md mx-auto space-y-3">
          <div className="h-12 w-12 rounded-2xl bg-indigo-600/10 text-indigo-400 flex items-center justify-center mx-auto">
            <UploadCloud className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-200">
              Drag and drop any file here, or{' '}
              <label className="text-indigo-400 hover:text-indigo-300 cursor-pointer font-semibold underline">
                browse
                <input
                  type="file"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setSelectedFile(e.target.files[0]);
                      setLocalPath('');
                    }
                  }}
                />
              </label>
            </p>
            <p className="text-xs text-slate-500 mt-1">Supports large videos, archives, and binaries</p>
          </div>

          {selectedFile && (
            <div className="mt-4 p-3 bg-slate-950/80 border border-indigo-500/30 rounded-xl flex items-center justify-between text-left">
              <div className="flex items-center gap-3">
                <FileText className="h-5 w-5 text-indigo-400" />
                <div>
                  <p className="text-sm font-semibold text-slate-200 truncate max-w-xs">{selectedFile.name}</p>
                  <p className="text-xs text-slate-400">{formatBytes(selectedFile.size)}</p>
                </div>
              </div>
              <button
                onClick={() => setSelectedFile(null)}
                className="text-xs text-slate-400 hover:text-rose-400 transition"
              >
                Clear
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Or Local Disk File Path */}
      <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-3">
        <label className="block text-xs font-medium text-slate-400">
          Or specify local path on disk (instant zero-copy stream):
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={localPath}
            onChange={(e) => {
              setLocalPath(e.target.value);
              if (e.target.value) setSelectedFile(null);
            }}
            placeholder="e.g. test.txt or D:\Movies\sample.mkv"
            className="flex-1 bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono"
          />
        </div>
      </div>

      <button
        onClick={handleSend}
        disabled={isSending || (!selectedFile && !localPath.trim())}
        className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white font-medium text-sm rounded-xl transition shadow-lg shadow-indigo-600/20 flex items-center justify-center gap-2 cursor-pointer disabled:cursor-not-allowed"
      >
        <Send className="h-4 w-4" />
        {isSending ? 'Initiating TCP stream...' : 'Start Transfer to Peer'}
      </button>

      {/* Live Upload Progress */}
      {activeUploads.length > 0 && (
        <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
          <h3 className="text-sm font-semibold text-white">Active Upload Sessions</h3>
          <div className="space-y-4">
            {activeUploads.map((t) => (
              <div key={t.id} className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2">
                <div className="flex justify-between items-center text-sm">
                  <span className="font-semibold text-slate-200">{t.filename}</span>
                  <span className="font-mono text-indigo-400">{t.progress_percent.toFixed(1)}%</span>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-indigo-500 h-full transition-all duration-200"
                    style={{ width: `${t.progress_percent}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-400 font-mono pt-1">
                  <span>{formatBytes(t.transferred_bytes)} / {formatBytes(t.total_bytes)}</span>
                  <span>{formatSpeed(t.speed_bytes_sec)}</span>
                  <span>Peer: {t.peer_address}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
