import React, { useEffect, useState } from 'react';
import { 
  Users, 
  Radio, 
  RefreshCw, 
  Search, 
  Send, 
  AlertCircle,
  FileBox,
  HardDrive,
  Download
} from 'lucide-react';
import { fetchTrackerPeers, fetchTrackerFiles, formatBytes, downloadChunkedFile } from '../services/api';
import type { NodeStatus, TrackerPeer, TrackerFile } from '../types';

interface PeersPageProps {
  status: NodeStatus | null;
  onSelectPeerForSend?: (host: string, port: number) => void;
}

export const PeersPage: React.FC<PeersPageProps> = ({ status, onSelectPeerForSend }) => {
  const [peers, setPeers] = useState<TrackerPeer[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<TrackerFile[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [hasSearched, setHasSearched] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadPeers = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await fetchTrackerPeers();
      setPeers(data);
    } catch (e: any) {
      setErrorMsg('Central tracker offline or unreachable.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setIsLoading(true);
    setHasSearched(true);
    try {
      const results = await fetchTrackerFiles(searchQuery.trim());
      setSearchResults(results);
    } catch (e: any) {
      setErrorMsg('Failed to search tracker catalog.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPeers();
    const interval = setInterval(loadPeers, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white">Available Peers & Swarm Discovery</h2>
          <p className="text-sm text-slate-400 mt-1">
            Real-time peer discovery and shared files catalog coordinated via Central Tracker.
          </p>
        </div>
        <button
          onClick={loadPeers}
          disabled={isLoading}
          className="p-2.5 bg-slate-900 border border-slate-800 rounded-xl text-slate-400 hover:text-white transition w-fit flex items-center gap-2 text-xs"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh Peers
        </button>
      </div>

      {errorMsg && (
        <div className="p-4 bg-amber-950/40 border border-amber-800 rounded-xl flex items-center gap-3 text-amber-300 text-xs">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{errorMsg} Check that the tracker server is running on port 8001. Direct IP transfers still work.</span>
        </div>
      )}

      {/* Local Peer Identification Card */}
      <div className="p-5 bg-gradient-to-r from-indigo-950/40 via-slate-900 to-slate-900 border border-indigo-900/40 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-indigo-600/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
            <Radio className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-semibold text-emerald-400">Local Registered Peer</span>
              <span className="text-slate-600">•</span>
              <span className="text-xs text-slate-400">{status?.peer_name || 'My Node'}</span>
            </div>
            <p className="font-mono text-sm font-semibold text-white mt-0.5">{status?.peer_id}</p>
          </div>
        </div>
        <div className="text-right font-mono text-xs text-slate-400">
          Listening: <span className="text-emerald-400 font-semibold">0.0.0.0:{status?.p2p_port || 5000}</span>
        </div>
      </div>

      {/* Global File Search Across All Peers */}
      <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Search className="h-4 w-4 text-indigo-400" />
          Search Files Across Online Peers
        </h3>
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search file name, keyword, or SHA-256..."
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
            />
            <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-500" />
          </div>
          <button
            type="submit"
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm rounded-xl transition shadow-lg shadow-indigo-600/20 flex items-center gap-2"
          >
            Search
          </button>
        </form>

        {hasSearched && (
          <div className="mt-4 pt-4 border-t border-slate-800/80">
            {searchResults.length === 0 ? (
              <p className="text-xs text-slate-500 py-3 text-center">No files found matching your search query.</p>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {searchResults.map((file) => (
                  <div key={file.id} className="py-3 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                        <FileBox className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-slate-200">{file.filename}</p>
                        <p className="text-xs text-slate-500 font-mono mt-0.5">
                          Peer: <span className="text-slate-300">{file.peer_name}</span> ({file.host}:{file.port})
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-slate-300 mr-2">{formatBytes(file.file_size)}</span>
                      <button
                        onClick={async () => {
                          try {
                            await downloadChunkedFile(file.host, 5002, file.filename);
                            alert(`Initiated chunked download for ${file.filename}`);
                          } catch (err: any) {
                            alert(err.message);
                          }
                        }}
                        className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition flex items-center gap-1.5 shadow-md shadow-emerald-600/20"
                      >
                        <Download className="h-3 w-3" />
                        Download
                      </button>
                      {onSelectPeerForSend && (
                        <button
                          onClick={() => onSelectPeerForSend(file.host, file.port)}
                          className="px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-medium transition flex items-center gap-1.5"
                        >
                          <Send className="h-3 w-3" />
                          Connect
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Discovered Active Peers Table */}
      <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Users className="h-4 w-4 text-emerald-400" />
            Online Peers Registered with Tracker ({peers.length})
          </h3>
          <span className="text-xs text-slate-500 font-mono">Heartbeat interval: 15s</span>
        </div>

        {peers.length === 0 ? (
          <div className="py-12 text-center text-slate-500 space-y-2">
            <Users className="h-10 w-10 mx-auto text-slate-600 stroke-[1.5]" />
            <p className="text-sm">No other peers online right now.</p>
            <p className="text-xs text-slate-600">Ensure the tracker service is running and other nodes are pointed to it.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60">
            {peers.map((peer) => {
              const isSelf = peer.peer_id === status?.peer_id;
              return (
                <div key={peer.peer_id} className="py-3.5 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2.5 rounded-xl ${isSelf ? 'bg-indigo-500/10 text-indigo-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                      <HardDrive className="h-5 w-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-white">{peer.peer_name}</p>
                        {isSelf && (
                          <span className="text-[10px] font-semibold bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-1.5 py-0.5 rounded-full">
                            This Device
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 font-mono mt-0.5">
                        {peer.host}:{peer.port} • ID: {peer.peer_id}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                      Online
                    </span>

                    {!isSelf && onSelectPeerForSend && (
                      <button
                        onClick={() => onSelectPeerForSend(peer.host, peer.port)}
                        className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-medium transition flex items-center gap-1.5 shadow-md shadow-indigo-600/20"
                      >
                        <Send className="h-3.5 w-3.5" />
                        Send File
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
