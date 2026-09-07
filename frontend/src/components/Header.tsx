'use client';

import React from 'react';
import { Activity, ShieldCheck, Bell } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-40">
      <div className="flex items-center space-x-3">
        <div className="bg-sky-500/10 border border-sky-500/30 p-2 rounded-lg text-sky-400">
          <Activity className="w-5 h-5 animate-pulse-subtle" />
        </div>
        <div>
          <h1 className="text-base font-semibold text-slate-100 flex items-center gap-2">
            RailAI <span className="text-xs bg-sky-500/10 text-sky-400 px-2 py-0.5 rounded border border-sky-500/20">v2.0</span>
          </h1>
          <p className="text-xs text-slate-400">Railway Safety Intelligence Platform</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2 text-xs bg-emerald-500/10 text-emerald-400 px-3 py-1.5 rounded-full border border-emerald-500/20">
          <ShieldCheck className="w-4 h-4" />
          <span className="font-medium">System Online</span>
        </div>

        <button className="p-2 text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800 rounded-lg hover:bg-slate-800 transition">
          <Bell className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
