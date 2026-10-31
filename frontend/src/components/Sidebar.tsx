import React from 'react';
import { 
  LayoutDashboard, 
  UploadCloud, 
  DownloadCloud, 
  Users, 
  FolderSync, 
  History, 
  Settings, 
  Zap,
  Activity
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  activeTransfersCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, setCurrentTab, activeTransfersCount }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'send', label: 'Send Files', icon: UploadCloud },
    { id: 'receive', label: 'Receive Files', icon: DownloadCloud },
    { id: 'peers', label: 'Available Peers', icon: Users },
    { id: 'shared', label: 'Shared Files', icon: FolderSync },
    { id: 'history', label: 'Transfer History', icon: History },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900/90 border-r border-slate-800/80 flex flex-col justify-between shrink-0 select-none backdrop-blur-md">
      <div>
        <div className="h-16 flex items-center px-6 gap-3 border-b border-slate-800/60">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-cyan-400 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Zap className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg tracking-tight text-white flex items-center gap-1.5">
              PeerShare
              <span className="text-[10px] font-semibold bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-1.5 py-0.5 rounded-full">v1.0</span>
            </h1>
            <p className="text-xs text-slate-400 font-medium">Decentralized P2P</p>
          </div>
        </div>

        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-150 ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`h-4 w-4 ${isActive ? 'text-white' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.id === 'send' && activeTransfersCount > 0 && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500 text-white animate-pulse">
                    {activeTransfersCount}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="p-4 border-t border-slate-800/60">
        <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800/60 flex items-center gap-3">
          <div className="relative">
            <Activity className="h-4 w-4 text-emerald-400" />
            <span className="absolute -top-0.5 -right-0.5 h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
          </div>
          <div className="text-xs">
            <p className="text-slate-200 font-medium">TCP Daemon Active</p>
            <p className="text-slate-400">Listening on 0.0.0.0</p>
          </div>
        </div>
      </div>
    </aside>
  );
};
