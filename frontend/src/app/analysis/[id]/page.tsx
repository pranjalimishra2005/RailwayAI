'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { api, AnalysisResult } from '@/services/api';
import { RiskBadge } from '@/components/RiskBadge';
import { DetectionSummaryCards } from '@/components/DetectionSummaryCards';
import { IncidentTimeline } from '@/components/IncidentTimeline';
import { ArrowLeft, Film, Clock, Download, RefreshCw } from 'lucide-react';

export default function AnalysisResultsPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!id) return;

    const fetchResult = async () => {
      try {
        setLoading(true);
        const res = await api.getJobStatus(id);

        if (res.status === 'completed' && res.result) {
          setResult(res.result);
        } else if (res.status === 'failed') {
          setError(res.error || 'Video analysis failed');
        } else {
          setError('Analysis is still in progress or not found.');
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load analysis result');
      } finally {
        setLoading(false);
      }
    };

    fetchResult();
  }, [id]);

  const handleSeek = (timestamp: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = timestamp;
      videoRef.current.play();
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center space-y-3 bg-slate-900 border border-slate-800 rounded-2xl">
        <RefreshCw className="w-8 h-8 text-sky-400 animate-spin mx-auto" />
        <p className="text-sm font-semibold text-slate-200">Loading Analysis Results...</p>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="p-12 text-center space-y-4 bg-slate-900 border border-slate-800 rounded-2xl">
        <p className="text-sm font-semibold text-rose-400">{error || 'Analysis results not found'}</p>
        <button
          onClick={() => router.push('/')}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold"
        >
          Return to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Bar Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => router.push('/')}
          className="flex items-center space-x-2 text-xs font-semibold text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800 px-3 py-2 rounded-lg transition"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </button>

        <div className="flex items-center space-x-3">
          <RiskBadge level={result.risk_level} size="lg" />
          <a
            href={api.getMediaUrl(result.processed_video_url)}
            download
            className="flex items-center space-x-2 text-xs font-semibold text-slate-300 hover:text-white bg-slate-900 border border-slate-800 px-3 py-2 rounded-lg transition"
          >
            <Download className="w-4 h-4" />
            <span>Export Processed Video</span>
          </a>
        </div>
      </div>

      {/* Summary Cards */}
      <DetectionSummaryCards summary={result.summary} />

      {/* Main Video & Timeline Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Processed Video Player */}
        <div className="lg:col-span-2 space-y-3">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
                <Film className="w-4 h-4 text-sky-400" />
                <span>AI Annotated Video Output</span>
              </h3>
              <div className="flex items-center space-x-2 text-xs text-slate-400 font-mono">
                <Clock className="w-3.5 h-3.5" />
                <span>{result.duration_sec}s Duration</span>
              </div>
            </div>

            <div className="relative rounded-xl overflow-hidden bg-black aspect-video border border-slate-800">
              <video
                ref={videoRef}
                src={api.getMediaUrl(result.processed_video_url)}
                controls
                className="w-full h-full object-contain"
              />
            </div>

            <p className="text-[11px] text-slate-500 italic">
              Note: Click any timestamp in the incident timeline to jump to the exact moment in the video.
            </p>
          </div>
        </div>

        {/* Timeline Events Column */}
        <div>
          <IncidentTimeline events={result.timeline} onSeek={handleSeek} />
        </div>
      </div>
    </div>
  );
}
