'use client';

import React from 'react';
import { TimelineEvent } from '@/services/api';
import { Clock, AlertTriangle, User, Box, ShieldAlert } from 'lucide-react';

interface IncidentTimelineProps {
  events: TimelineEvent[];
  onSeek?: (timestamp: number) => void;
}

export const IncidentTimeline: React.FC<IncidentTimelineProps> = ({ events, onSeek }) => {
  if (!events || events.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-900/50 border border-slate-800 rounded-xl">
        <Clock className="w-8 h-8 text-slate-600 mx-auto mb-2" />
        <p className="text-sm text-slate-400 font-medium">No Unsafe Incidents Detected</p>
        <p className="text-xs text-slate-500 mt-1">The railway track remained clear throughout this video feed.</p>
      </div>
    );
  }

  const getEventIcon = (type: string, zone: string) => {
    if (zone === 'HAZARD') return <ShieldAlert className="w-4 h-4 text-rose-400" />;
    if (type === 'HUMAN') return <User className="w-4 h-4 text-amber-400" />;
    if (type === 'OBSTACLE') return <Box className="w-4 h-4 text-sky-400" />;
    return <AlertTriangle className="w-4 h-4 text-amber-400" />;
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Clock className="w-4 h-4 text-sky-400" />
          <span>Incident Detection Timeline</span>
        </h3>
        <span className="text-xs text-slate-400">{events.length} events logged</span>
      </div>

      <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
        {events.map((evt, idx) => {
          const isHazard = evt.zone === 'HAZARD';
          return (
            <div
              key={idx}
              onClick={() => onSeek && onSeek(evt.timestamp)}
              className={`p-3 rounded-lg border transition-all flex items-center justify-between cursor-pointer ${
                isHazard
                  ? 'bg-rose-500/10 border-rose-500/30 hover:bg-rose-500/20'
                  : 'bg-slate-950/60 border-slate-800/80 hover:bg-slate-800/60'
              }`}
            >
              <div className="flex items-center space-x-3">
                <div className="px-2 py-1 bg-slate-900 border border-slate-800 rounded text-xs font-mono text-sky-400 font-bold">
                  {evt.time_formatted}
                </div>

                <div className="flex items-center space-x-2">
                  {getEventIcon(evt.type, evt.zone)}
                  <div>
                    <p className="text-xs font-semibold text-slate-200">
                      {evt.class_name} {isHazard ? 'Intrusion on Track' : 'Detected near Zone'}
                    </p>
                    <p className="text-[10px] text-slate-400">
                      Zone: <span className={isHazard ? 'text-rose-400 font-bold' : 'text-slate-300'}>{evt.zone}</span> • Dist: ~{evt.distance_m}m
                    </p>
                  </div>
                </div>
              </div>

              <div className="text-right">
                <span className="text-[11px] font-mono bg-slate-900 px-2 py-0.5 rounded text-slate-400 border border-slate-800">
                  {(evt.confidence * 100).toFixed(0)}% conf
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
