'use client';

import React, { useState, useRef } from 'react';
import { UploadCloud, FileVideo, X, Settings2 } from 'lucide-react';
import { CalibrationParams } from '@/services/api';

interface FileDropzoneProps {
  onFileSelect: (file: File) => void;
  onParamsChange: (params: CalibrationParams) => void;
  isUploading: boolean;
}

export const FileDropzone: React.FC<FileDropzoneProps> = ({
  onFileSelect,
  onParamsChange,
  isUploading,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Calibration Sliders state
  const [params, setParams] = useState<CalibrationParams>({
    top_w_pct: 30,
    bot_w_pct: 80,
    top_y_pct: 45,
    bot_y_pct: 95,
    conf_thresh: 0.35,
    show_heatmap: false,
    show_trajectory: true,
  });

  const handleParamsUpdate = (newParams: Partial<CalibrationParams>) => {
    const updated = { ...params, ...newParams };
    setParams(updated);
    onParamsChange(updated);
  };

  const validateAndSetFile = (file: File) => {
    const validTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska'];
    const ext = file.name.split('.').pop()?.toLowerCase();
    
    if (!validTypes.includes(file.type) && !['mp4', 'avi', 'mov', 'mkv'].includes(ext || '')) {
      setError('Unsupported video format. Please upload an MP4, AVI, or MOV video.');
      return;
    }

    if (file.size > 500 * 1024 * 1024) {
      setError('File size exceeds 500 MB limit.');
      return;
    }

    setError(null);
    setSelectedFile(file);
    onFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleClear = () => {
    setSelectedFile(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-6">
      {/* Drag and Drop Box */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !selectedFile && fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer ${
          isDragOver
            ? 'border-sky-500 bg-sky-500/10'
            : selectedFile
            ? 'border-slate-700 bg-slate-900/60 cursor-default'
            : 'border-slate-800 bg-slate-900/30 hover:border-slate-700 hover:bg-slate-900/50'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/mp4,video/avi,video/quicktime,video/x-matroska"
          className="hidden"
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              validateAndSetFile(e.target.files[0]);
            }
          }}
        />

        {!selectedFile ? (
          <div className="space-y-3 pointer-events-none">
            <div className="w-12 h-12 bg-sky-500/10 border border-sky-500/20 text-sky-400 rounded-full flex items-center justify-center mx-auto">
              <UploadCloud className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-200">
                Drag and drop your railway video here, or <span className="text-sky-400">browse</span>
              </p>
              <p className="text-xs text-slate-500 mt-1">Supports MP4, AVI, MOV (Up to 500 MB)</p>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between p-2">
            <div className="flex items-center space-x-3 text-left">
              <div className="p-3 bg-sky-500/10 border border-sky-500/20 rounded-lg text-sky-400">
                <FileVideo className="w-6 h-6" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-200 truncate max-w-xs sm:max-w-md">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-slate-500">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>

            {!isUploading && (
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); handleClear(); }}
                className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition"
              >
                <X className="w-5 h-5" />
              </button>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs font-medium">
          {error}
        </div>
      )}

      {/* ROI & Calibration Controls */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-xs font-semibold text-slate-300 flex items-center gap-2">
            <Settings2 className="w-4 h-4 text-sky-400" />
            <span>Track ROI & Detection Calibration</span>
          </h3>
          <span className="text-[10px] text-slate-500">Adjust Cyan Track Line Polygon</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          <div>
            <label className="text-slate-400 block mb-1">Top Track Width ({params.top_w_pct}%)</label>
            <input
              type="range"
              min="10"
              max="90"
              value={params.top_w_pct}
              onChange={(e) => handleParamsUpdate({ top_w_pct: Number(e.target.value) })}
              className="w-full accent-sky-500 bg-slate-800 h-1.5 rounded"
            />
          </div>

          <div>
            <label className="text-slate-400 block mb-1">Bottom Track Width ({params.bot_w_pct}%)</label>
            <input
              type="range"
              min="20"
              max="100"
              value={params.bot_w_pct}
              onChange={(e) => handleParamsUpdate({ bot_w_pct: Number(e.target.value) })}
              className="w-full accent-sky-500 bg-slate-800 h-1.5 rounded"
            />
          </div>

          <div>
            <label className="text-slate-400 block mb-1">Top Y Level ({params.top_y_pct}%)</label>
            <input
              type="range"
              min="10"
              max="80"
              value={params.top_y_pct}
              onChange={(e) => handleParamsUpdate({ top_y_pct: Number(e.target.value) })}
              className="w-full accent-sky-500 bg-slate-800 h-1.5 rounded"
            />
          </div>

          <div>
            <label className="text-slate-400 block mb-1">Confidence Thresh ({params.conf_thresh})</label>
            <input
              type="range"
              min="0.15"
              max="0.85"
              step="0.05"
              value={params.conf_thresh}
              onChange={(e) => handleParamsUpdate({ conf_thresh: Number(e.target.value) })}
              className="w-full accent-sky-500 bg-slate-800 h-1.5 rounded"
            />
          </div>
        </div>

        <div className="flex items-center space-x-6 pt-2 border-t border-slate-800/60 text-xs">
          <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={params.show_heatmap}
              onChange={(e) => handleParamsUpdate({ show_heatmap: e.target.checked })}
              className="rounded border-slate-700 bg-slate-800 text-sky-500 focus:ring-0"
            />
            <span>Enable Intrusion Heatmap</span>
          </label>

          <label className="flex items-center space-x-2 text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={params.show_trajectory}
              onChange={(e) => handleParamsUpdate({ show_trajectory: e.target.checked })}
              className="rounded border-slate-700 bg-slate-800 text-sky-500 focus:ring-0"
            />
            <span>Kalman Trajectory Vectors</span>
          </label>
        </div>
      </div>
    </div>
  );
};
