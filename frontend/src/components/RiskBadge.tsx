'use client';

import React from 'react';
import { AlertCircle, AlertTriangle, ShieldCheck, Zap } from 'lucide-react';

interface RiskBadgeProps {
  level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, showIcon = true, size = 'md' }) => {
  const config = {
    LOW: {
      label: 'LOW RISK',
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/30',
      text: 'text-emerald-400',
      icon: ShieldCheck,
    },
    MEDIUM: {
      label: 'MEDIUM RISK',
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/30',
      text: 'text-amber-400',
      icon: AlertTriangle,
    },
    HIGH: {
      label: 'HIGH RISK',
      bg: 'bg-orange-500/10',
      border: 'border-orange-500/30',
      text: 'text-orange-400',
      icon: AlertCircle,
    },
    CRITICAL: {
      label: 'CRITICAL INTRUSION',
      bg: 'bg-rose-500/20',
      border: 'border-rose-500/50 shadow-lg shadow-rose-500/20 animate-pulse',
      text: 'text-rose-400 font-bold',
      icon: Zap,
    },
  }[level] || {
    label: level,
    bg: 'bg-slate-800',
    border: 'border-slate-700',
    text: 'text-slate-300',
    icon: AlertCircle,
  };

  const Icon = config.icon;

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-xs',
    lg: 'px-4 py-1.5 text-sm font-semibold',
  }[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${config.bg} ${config.border} ${config.text} ${sizeClasses}`}
    >
      {showIcon && <Icon className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />}
      <span>{config.label}</span>
    </span>
  );
};
