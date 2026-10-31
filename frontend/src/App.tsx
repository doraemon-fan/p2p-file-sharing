import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './pages/DashboardPage';
import { SendFilesPage } from './pages/SendFilesPage';
import { ReceiveFilesPage } from './pages/ReceiveFilesPage';
import { PeersPage } from './pages/PeersPage';
import { SharedFilesPage } from './pages/SharedFilesPage';
import { HistoryPage } from './pages/HistoryPage';
import { SettingsPage } from './pages/SettingsPage';
import { fetchStatus, fetchTransfers } from './services/api';
import type { NodeStatus, TransferItem } from './types';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [status, setStatus] = useState<NodeStatus | null>(null);
  const [transfers, setTransfers] = useState<TransferItem[]>([]);

  // Load initial backend status
  const loadStatus = async () => {
    try {
      const data = await fetchStatus();
      setStatus(data);
    } catch (e) {
      console.warn('Backend not yet reachable on /api/status');
    }
  };

  useEffect(() => {
    loadStatus();
    const statusInterval = setInterval(loadStatus, 5000);
    return () => clearInterval(statusInterval);
  }, []);

  // Real-time WebSocket connection for live transfers
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;

    const connectWs = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/transfers`;
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (Array.isArray(data)) {
            setTransfers(data);
          }
        } catch (e) {
          console.error('Error parsing WS message:', e);
        }
      };

      ws.onclose = () => {
        reconnectTimeout = setTimeout(connectWs, 3000);
      };

      ws.onerror = () => {
        if (ws) ws.close();
      };
    };

    connectWs();

    // Fallback polling in case WS is unavailable
    const pollInterval = setInterval(async () => {
      try {
        const data = await fetchTransfers();
        setTransfers(data);
      } catch (e) {
        // ignore
      }
    }, 2000);

    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      clearInterval(pollInterval);
    };
  }, []);

  const [selectedTargetPeer, setSelectedTargetPeer] = useState<{ host: string; port: number } | null>(null);

  const activeTransfersCount = transfers.filter(t => t.status === 'active').length;

  const handleSelectPeerForSend = (host: string, port: number) => {
    setSelectedTargetPeer({ host, port });
    setCurrentTab('send');
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <Sidebar 
        currentTab={currentTab} 
        setCurrentTab={setCurrentTab} 
        activeTransfersCount={activeTransfersCount} 
      />

      <main className="flex-1 overflow-y-auto p-8 relative">
        <div className="max-w-6xl mx-auto">
          {currentTab === 'dashboard' && (
            <Dashboard 
              status={status} 
              transfers={transfers} 
              onNavigate={(tab) => setCurrentTab(tab)} 
            />
          )}

          {currentTab === 'send' && (
            <SendFilesPage 
              transfers={transfers} 
              initialTargetHost={selectedTargetPeer?.host} 
              initialTargetPort={selectedTargetPeer?.port} 
            />
          )}

          {currentTab === 'receive' && (
            <ReceiveFilesPage 
              transfers={transfers} 
              downloadsDir={status?.downloads_dir} 
              p2pPort={status?.p2p_port} 
            />
          )}

          {currentTab === 'peers' && (
            <PeersPage 
              status={status} 
              onSelectPeerForSend={handleSelectPeerForSend} 
            />
          )}

          {currentTab === 'shared' && (
            <SharedFilesPage onNavigateToSend={() => setCurrentTab('send')} />
          )}

          {currentTab === 'history' && (
            <HistoryPage />
          )}

          {currentTab === 'settings' && (
            <SettingsPage />
          )}
        </div>
      </main>
    </div>
  );
};

export default App;
