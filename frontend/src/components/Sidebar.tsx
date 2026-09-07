'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, AlertTriangle, BarChart3, Train } from 'lucide-react';

export const Sidebar: React.FC = () => {
  const pathname = usePathname();

  const navItems = [
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Incidents History', href: '/incidents', icon: AlertTriangle },
    { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-950 flex flex-col justify-between shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-6">
        <div className="flex items-center space-x-2 px-3 py-2 text-sky-400 font-semibold tracking-wide text-sm border-b border-slate-800/60 pb-4">
          <Train className="w-5 h-5 text-sky-400" />
          <span>RAIL CONTROL ROOM</span>
        </div>

        <nav className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-sky-500/10 text-sky-400 border border-sky-500/20 shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-sky-400' : 'text-slate-400'}`} />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="p-4 border-t border-slate-800/60">
        <div className="bg-slate-900/80 border border-slate-800 p-3 rounded-lg text-xs space-y-1">
          <div className="text-slate-300 font-medium">YOLOv8 ByteTrack Core</div>
          <div className="text-slate-500">Homography & Kalman Filter IPM Enabled</div>
        </div>
      </div>
    </aside>
  );
};
