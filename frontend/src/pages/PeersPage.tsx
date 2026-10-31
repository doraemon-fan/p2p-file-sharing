import React from 'react';
import { Users, Info } from 'lucide-react';
import type { NodeStatus } from '../types';

interface PeersPageProps {
  status: NodeStatus | null;
}

export const PeersPage: React.FC<PeersPageProps> = ({ status }) => {
  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold text-white">Available Peers</h2>
        <p className="text-sm text-slate-400 mt-1">
          Peer discovery and swarm coordination.
        </p>
      </div>

      {/* Honest state callout */}
      <div className="p-5 bg-indigo-950/30 border border-indigo-800/40 rounded-2xl flex items-start gap-3">
        <Info className="h-5 w-5 text-indigo-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h3 className="text-sm font-semibold text-indigo-300">Phase 2 Tracker Integration Pending</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Centralized tracker discovery is being prepared in Phase 2. Currently, you can connect directly to any peer via IP and TCP port on the <strong>Send Files</strong> page without requiring a tracker.
          </p>
        </div>
      </div>

      {/* Current Local Peer Card */}
      <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <Users className="h-4 w-4 text-emerald-400" />
          This Local Peer
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
            <span className="text-xs text-slate-500 font-medium uppercase">Peer Identifier</span>
            <p className="text-sm font-mono text-indigo-400 font-semibold">{status?.peer_id || 'peer-local'}</p>
          </div>
          <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-1">
            <span className="text-xs text-slate-500 font-medium uppercase">TCP Listening Address</span>
            <p className="text-sm font-mono text-emerald-400 font-semibold">0.0.0.0:{status?.p2p_port || 5000}</p>
          </div>
        </div>
      </div>

      {/* Discovered Peers Section */}
      <div className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl text-center py-12 space-y-3">
        <div className="h-12 w-12 rounded-2xl bg-slate-800/60 text-slate-500 flex items-center justify-center mx-auto">
          <Users className="h-6 w-6" />
        </div>
        <p className="text-sm font-medium text-slate-300">Waiting for Tracker Integration</p>
        <p className="text-xs text-slate-500 max-w-sm mx-auto">
          Once the Phase 2 tracker server is launched, live peers broadcasting on the network will automatically register and appear in this table.
        </p>
      </div>
    </div>
  );
};
