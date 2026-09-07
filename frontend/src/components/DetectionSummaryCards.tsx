'use client';

import React from 'react';
import { Users, AlertOctagon, ShieldAlert, Activity } from 'lucide-react';
import { AnalysisSummary } from '@/services/api';

interface DetectionSummaryCardsProps {
  summary: AnalysisSummary;
}

export const DetectionSummaryCards: React.FC<DetectionSummaryCardsProps> = ({ summary }) => {
  const cards = [
    {
      title: 'People Detected',
      value: summary.people_detected,
      icon: Users,
      color: 'text-sky-400',
      bg: 'bg-sky-500/10',
      border: 'border-sky-500/20',
    },
    {
      title: 'Track Intrusions',
      value: summary.track_intrusions,
      icon: ShieldAlert,
      color: 'text-rose-400',
      bg: 'bg-rose-500/10',
      border: 'border-rose-500/20',
    },
    {
      title: 'Obstacles / Objects',
      value: summary.obstacles_detected,
      icon: AlertOctagon,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
    },
    {
      title: 'Total Unsafe Events',
      value: summary.total_incidents,
      icon: Activity,
      color: 'text-indigo-400',
      bg: 'bg-indigo-500/10',
      border: 'border-indigo-500/20',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        return (
          <div
            key={idx}
            className={`p-4 rounded-xl bg-slate-900 border ${card.border} flex items-center space-x-4`}
          >
            <div className={`p-3 rounded-lg ${card.bg} ${card.color}`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-slate-400 font-medium">{card.title}</p>
              <p className={`text-xl font-bold mt-0.5 ${card.color}`}>{card.value}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
};
