'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { FileDropzone } from '@/components/FileDropzone';
import { api, CalibrationParams } from '@/services/api';
import { Play, Loader2, Cpu, AlertTriangle, ShieldCheck, Film } from 'lucide-react';

export default function DashboardPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [params, setParams] = useState<CalibrationParams>({
    top_w_pct: 30,
    bot_w_pct: 80,
    top_y_pct: 45,
    bot_y_pct: 95,
    conf_thresh: 0.35,
    show_heatmap: false,
    show_trajectory: true,
  });

  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Poll job status when processing
  useEffect(() => {
    if (!jobId || !isProcessing) return;

    const interval = setInterval(async () => {
      try {
        const res = await api.getJobStatus(jobId);
        setProgress(res.progress);

        if (res.status === 'completed') {
          setIsProcessing(false);
          clearInterval(interval);
          router.push(`/analysis/${jobId}`);
        } else if (res.status === 'failed') {
          setIsProcessing(false);
          setError(res.error || 'Video analysis failed.');
          clearInterval(interval);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [jobId, isProcessing, router]);

  const handleStartAnalysis = async () => {
    if (!file) {
      setError('Please select or drag a video file first.');
      return;
    }

    try {
      setError(null);
      setIsProcessing(true);
      setProgress(0);

      const res = await api.uploadVideo(file, params);
      setJobId(res.job_id);
    } catch (err: any) {
      setIsProcessing(false);
      setError(err.message || 'Failed to start video analysis');
    }
  };

  return (
    <div className="space-y-6">
      {/* Hero Banner */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 relative overflow-hidden">
        <div className="max-w-2xl space-y-2">
          <div className="inline-flex items-center space-x-2 text-xs font-semibold px-2.5 py-1 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20">
            <Cpu className="w-3.5 h-3.5" />
            <span>YOLOv8 ByteTrack + Homography IPM Engine</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100">
            Railway Track Safety Intelligence & Hazard Analytics
          </h2>
          <p className="text-sm text-slate-400 leading-relaxed">
            Upload pre-recorded railway surveillance video to perform real-time Computer Vision analysis.
            RailAI detects pedestrians, animals, and obstacles inside active track zones, calculates Time-to-Collision (TTC),
            and generates comprehensive hazard timelines.
          </p>
        </div>
      </div>

      {/* Upload & Configuration Section */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              <Film className="w-5 h-5 text-sky-400" />
              <span>Video Surveillance Analysis</span>
            </h3>
            <p className="text-xs text-slate-400">Upload a video clip to run full AI detection & graphics pipeline</p>
          </div>
        </div>

        <FileDropzone
          onFileSelect={(f) => setFile(f)}
          onParamsChange={(p) => setParams(p)}
          isUploading={isProcessing}
        />

        {error && (
          <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-xs font-medium flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <div className="flex justify-end pt-2">
          <button
            onClick={handleStartAnalysis}
            disabled={!file || isProcessing}
            className={`px-6 py-3 rounded-xl font-semibold text-sm flex items-center space-x-2 shadow-lg transition-all ${
              !file || isProcessing
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold shadow-sky-500/20'
            }`}
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Analyzing Video... ({progress.toFixed(0)}%)</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Analyze Railway Video</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Processing Overlay Modal */}
      {isProcessing && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl max-w-md w-full text-center space-y-4 shadow-2xl">
            <div className="w-12 h-12 bg-sky-500/10 border border-sky-500/30 text-sky-400 rounded-full flex items-center justify-center mx-auto">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>

            <div>
              <h3 className="text-base font-bold text-slate-100">AI Video Processing in Progress</h3>
              <p className="text-xs text-slate-400 mt-1">
                Running YOLOv8 ByteTrack, Homography coordinate conversion, and Computer Graphics compositing...
              </p>
            </div>

            {/* Progress bar */}
            <div className="space-y-1">
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-sky-500 to-indigo-500 h-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs font-mono text-sky-400 font-bold">{progress.toFixed(1)}% Completed</p>
            </div>

            <p className="text-[11px] text-slate-500">Please wait. Results page will open automatically upon completion.</p>
          </div>
        </div>
      )}
    </div>
  );
}
