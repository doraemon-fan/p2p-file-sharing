import React, { useEffect, useState } from 'react';
import { History, ArrowUpRight, ArrowDownLeft, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { fetchHistory, formatBytes } from '../services/api';
import type { TransferHistoryRecord } from '../types';

export const HistoryPage: React.FC = () => {
  const [history, setHistory] = useState<TransferHistoryRecord[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const loadHistory = async () => {
    setIsLoading(true);
    try {
      const data = await fetchHistory();
      setHistory(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Transfer History</h2>
          <p className="text-sm text-slate-400 mt-1">
            Audit log of all completed and attempted peer-to-peer transmissions stored in SQLite.
          </p>
        </div>
        <button
          onClick={loadHistory}
          className="p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-400 hover:text-white transition"
          title="Refresh"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl overflow-x-auto">
        {history.length === 0 ? (
          <div className="py-12 text-center text-slate-500 space-y-2">
            <History className="h-10 w-10 mx-auto text-slate-600 stroke-[1.5]" />
            <p className="text-sm">No transfer history recorded yet.</p>
          </div>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs uppercase tracking-wider text-slate-400">
                <th className="pb-3 font-semibold">Direction</th>
                <th className="pb-3 font-semibold">File</th>
                <th className="pb-3 font-semibold">Peer Address</th>
                <th className="pb-3 font-semibold">Size</th>
                <th className="pb-3 font-semibold">Duration / Speed</th>
                <th className="pb-3 font-semibold">Status & SHA-256</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {history.map((record) => (
                <tr key={record.id} className="text-slate-300 hover:bg-slate-800/20">
                  <td className="py-3.5">
                    <div className="flex items-center gap-2">
                      {record.direction === 'upload' ? (
                        <span className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                          <ArrowUpRight className="h-4 w-4" />
                        </span>
                      ) : (
                        <span className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
                          <ArrowDownLeft className="h-4 w-4" />
                        </span>
                      )}
                      <span className="capitalize text-xs font-semibold">{record.direction}</span>
                    </div>
                  </td>
                  <td className="py-3.5 font-medium text-white max-w-xs truncate">{record.filename}</td>
                  <td className="py-3.5 font-mono text-xs text-slate-400">{record.peer_address}</td>
                  <td className="py-3.5 font-mono text-xs">{formatBytes(record.file_size)}</td>
                  <td className="py-3.5 text-xs text-slate-400">
                    {record.duration.toFixed(2)}s • <span className="text-indigo-400">{record.average_speed.toFixed(2)} MB/s</span>
                  </td>
                  <td className="py-3.5">
                    <div className="flex items-center gap-1.5">
                      {record.status === 'completed' ? (
                        <span className="flex items-center gap-1 text-emerald-400 text-xs font-medium">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Success
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-rose-400 text-xs font-medium">
                          <AlertCircle className="h-3.5 w-3.5" /> Failed
                        </span>
                      )}
                    </div>
                    {record.sha256 && (
                      <p className="text-[10px] font-mono text-slate-500 truncate max-w-xs mt-0.5" title={record.sha256}>
                        {record.sha256.slice(0, 16)}...
                      </p>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
