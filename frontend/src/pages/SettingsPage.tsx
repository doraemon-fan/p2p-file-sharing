import React, { useEffect, useState } from 'react';
import { Save, CheckCircle2, AlertCircle } from 'lucide-react';
import { fetchSettings, updateSettings } from '../services/api';

export const SettingsPage: React.FC = () => {
  const [peerName, setPeerName] = useState<string>('');
  const [downloadsDir, setDownloadsDir] = useState<string>('');
  const [sharedDir, setSharedDir] = useState<string>('');
  const [trackerUrl, setTrackerUrl] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    fetchSettings().then((data) => {
      setPeerName(data.peer_name);
      setDownloadsDir(data.downloads_dir);
      setSharedDir(data.shared_dir);
      setTrackerUrl(data.tracker_url);
    }).catch(console.error);
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setFeedback(null);
    try {
      await updateSettings({
        peer_name: peerName,
        downloads_dir: downloadsDir,
        shared_dir: sharedDir,
        tracker_url: trackerUrl,
      });
      setFeedback({ type: 'success', message: 'Settings saved successfully' });
    } catch (err: any) {
      setFeedback({ type: 'error', message: err.message || 'Failed to update settings' });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2 className="text-xl font-bold text-white">Node Settings</h2>
        <p className="text-sm text-slate-400 mt-1">
          Configure directories, peer identity, and future tracker coordinates.
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

      <form onSubmit={handleSave} className="p-6 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-5">
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Peer Name / Alias</label>
          <input
            type="text"
            value={peerName}
            onChange={(e) => setPeerName(e.target.value)}
            className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Downloads Directory Path</label>
          <input
            type="text"
            value={downloadsDir}
            onChange={(e) => setDownloadsDir(e.target.value)}
            className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono text-xs"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Shared Files Directory Path</label>
          <input
            type="text"
            value={sharedDir}
            onChange={(e) => setSharedDir(e.target.value)}
            className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono text-xs"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Central Tracker URL</label>
          <input
            type="text"
            value={trackerUrl}
            onChange={(e) => setTrackerUrl(e.target.value)}
            className="w-full bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 font-mono text-xs"
          />
          <p className="text-xs text-slate-500 mt-1">Configured for Phase 2 tracker discovery.</p>
        </div>

        <div className="pt-2">
          <button
            type="submit"
            disabled={isSaving}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white font-medium text-sm rounded-xl transition shadow-lg shadow-indigo-600/25 flex items-center gap-2"
          >
            <Save className="h-4 w-4" />
            {isSaving ? 'Saving...' : 'Save Configuration'}
          </button>
        </div>
      </form>
    </div>
  );
};
