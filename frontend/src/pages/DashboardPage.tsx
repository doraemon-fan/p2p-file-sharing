import React from 'react';
import { 
  ArrowUpRight, 
  ArrowDownLeft, 
  HardDrive, 
  Radio, 
  ShieldCheck, 
  Clock, 
  CheckCircle2, 
  AlertCircle 
} from 'lucide-react';
import type { NodeStatus, TransferItem } from '../types';
import { formatBytes, formatSpeed } from '../services/api';

interface DashboardProps {
  status: NodeStatus | null;
  transfers: TransferItem[];
  onNavigate: (tab: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ status, transfers, onNavigate }) => {
  const activeTransfers = transfers.filter(t => t.status === 'active');
  const recentTransfers = transfers.slice(0, 5);

  const totalCurrentUploadSpeed = activeTransfers
    .filter(t => t.direction === 'upload')
    .reduce((acc, t) => acc + t.speed_bytes_sec, 0);

  const totalCurrentDownloadSpeed = activeTransfers
    .filter(t => t.direction === 'download')
    .reduce((acc, t) => acc + t.speed_bytes_sec, 0);

  return (
    <div className="space-y-6">
      {/* Top Banner / Status Overview */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800/80 rounded-2xl shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">Node Online</span>
            <span className="text-slate-600">•</span>
            <span className="text-xs text-slate-400">Port {status?.p2p_port || 5000}</span>
          </div>
          <h2 className="text-2xl font-bold text-white tracking-tight">
            {status?.peer_name || 'Local Node'}
          </h2>
          <div className="flex items-center gap-2 font-mono text-xs text-slate-400 bg-slate-950/60 px-3 py-1.5 rounded-lg border border-slate-800 w-fit">
            <span>Peer ID:</span>
            <span className="text-indigo-400 font-semibold">{status?.peer_id || 'Generating...'}</span>
          </div>
        </div>

        <div className="flex gap-3">
          <button 
            onClick={() => onNavigate('send')}
            className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-medium text-sm rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2"
          >
            <ArrowUpRight className="h-4 w-4" />
            Send File
          </button>
          <button 
            onClick={() => onNavigate('receive')}
            className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 active:scale-95 text-slate-200 font-medium text-sm rounded-xl border border-slate-700/80 transition flex items-center gap-2"
          >
            <ArrowDownLeft className="h-4 w-4" />
            Incoming Transfers
          </button>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-medium uppercase tracking-wider">Current Upload</span>
            <ArrowUpRight className="h-5 w-5 text-indigo-400" />
          </div>
          <p className="text-2xl font-bold text-white tracking-tight">{formatSpeed(totalCurrentUploadSpeed)}</p>
          <p className="text-xs text-slate-500 mt-1">Total sent: {formatBytes(status?.total_uploaded || 0)}</p>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-medium uppercase tracking-wider">Current Download</span>
            <ArrowDownLeft className="h-5 w-5 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white tracking-tight">{formatSpeed(totalCurrentDownloadSpeed)}</p>
          <p className="text-xs text-slate-500 mt-1">Total received: {formatBytes(status?.total_downloaded || 0)}</p>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-medium uppercase tracking-wider">Active Transfers</span>
            <Radio className="h-5 w-5 text-cyan-400" />
          </div>
          <p className="text-2xl font-bold text-white tracking-tight">{activeTransfers.length}</p>
          <p className="text-xs text-slate-500 mt-1">{transfers.length} total sessions tracked</p>
        </div>

        <div className="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm">
          <div className="flex items-center justify-between text-slate-400 mb-3">
            <span className="text-xs font-medium uppercase tracking-wider">Integrity Engine</span>
            <ShieldCheck className="h-5 w-5 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white tracking-tight">SHA-256</p>
          <p className="text-xs text-slate-500 mt-1">On-the-fly streaming verification</p>
        </div>
      </div>

      {/* Live & Recent Transfers Section */}
      <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-white">Live Activity</h3>
          <button 
            onClick={() => onNavigate('history')}
            className="text-xs font-medium text-indigo-400 hover:text-indigo-300 transition"
          >
            View Full History →
          </button>
        </div>

        {recentTransfers.length === 0 ? (
          <div className="py-12 text-center text-slate-500 space-y-2">
            <HardDrive className="h-10 w-10 mx-auto text-slate-600 stroke-[1.5]" />
            <p className="text-sm">No transfer activity yet.</p>
            <p className="text-xs text-slate-600">Send a file or wait for an incoming connection on TCP port {status?.p2p_port || 5000}.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {recentTransfers.map((t) => (
              <div key={t.id} className="py-3.5 flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className={`p-2.5 rounded-xl ${
                    t.direction === 'upload' ? 'bg-indigo-500/10 text-indigo-400' : 'bg-emerald-500/10 text-emerald-400'
                  }`}>
                    {t.direction === 'upload' ? <ArrowUpRight className="h-4 w-4" /> : <ArrowDownLeft className="h-4 w-4" />}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-100">{t.filename}</p>
                    <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                      <span className="capitalize">{t.direction}</span>
                      <span>•</span>
                      <span>{t.peer_address}</span>
                      <span>•</span>
                      <span>{formatBytes(t.total_bytes)}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-6 self-end md:self-center">
                  <div className="text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {t.status === 'completed' && <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />}
                      {t.status === 'failed' && <AlertCircle className="h-3.5 w-3.5 text-rose-400" />}
                      {t.status === 'active' && <Clock className="h-3.5 w-3.5 text-cyan-400 animate-spin" />}
                      <span className="text-xs font-medium capitalize text-slate-300">{t.status}</span>
                    </div>
                    <p className="text-xs font-mono text-slate-400 mt-0.5">
                      {t.status === 'active' ? formatSpeed(t.speed_bytes_sec) : `${t.elapsed_time.toFixed(1)}s`}
                    </p>
                  </div>

                  <div className="w-28 bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-300 ${
                        t.status === 'completed' ? 'bg-emerald-500' : t.status === 'failed' ? 'bg-rose-500' : 'bg-indigo-500'
                      }`}
                      style={{ width: `${t.progress_percent}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
