/**
 * API Service for RailAI Safety Intelligence Backend
 */

// Use relative URLs so all requests go through Vercel's proxy rewrites (/api/* → Render backend)
// This avoids CORS issues entirely since requests appear same-origin to the browser.
// For local dev, NEXT_PUBLIC_API_URL can be set to the local FastAPI server.
const API_BASE_URL = (typeof window !== 'undefined' && !process.env.NEXT_PUBLIC_API_URL) ? '' : (process.env.NEXT_PUBLIC_API_URL || '');

export interface TimelineEvent {
  timestamp: number;
  time_formatted: string;
  type: string;
  class_name: string;
  zone: string;
  confidence: number;
  distance_m: number;
  is_critical: boolean;
}

export interface AnalysisSummary {
  people_detected: number;
  obstacles_detected: number;
  track_intrusions: number;
  total_incidents: number;
}

export interface AnalysisResult {
  job_id: string;
  filename: string;
  processed_video_url: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  duration_sec: number;
  summary: AnalysisSummary;
  timeline: TimelineEvent[];
}

export interface JobStatusResponse {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  error?: string;
  result?: AnalysisResult;
}

export interface IncidentItem {
  job_id: string;
  filename: string;
  created_at: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  duration_sec: number;
  total_incidents: number;
  people_detected: number;
  track_intrusions: number;
}

export interface AnalyticsResponse {
  total_videos_analyzed: number;
  total_incidents_detected: number;
  total_track_intrusions: number;
  risk_distribution: {
    CRITICAL: number;
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
}

export interface CalibrationParams {
  top_w_pct: number;
  bot_w_pct: number;
  top_y_pct: number;
  bot_y_pct: number;
  conf_thresh: number;
  show_heatmap: boolean;
  show_trajectory: boolean;
}

export const api = {
  /**
   * Upload video and start analysis job
   */
  async uploadVideo(file: File, params?: Partial<CalibrationParams>): Promise<{ job_id: string }> {
    const formData = new FormData();
    formData.append('file', file);
    
    if (params) {
      if (params.top_w_pct !== undefined) formData.append('top_w_pct', params.top_w_pct.toString());
      if (params.bot_w_pct !== undefined) formData.append('bot_w_pct', params.bot_w_pct.toString());
      if (params.top_y_pct !== undefined) formData.append('top_y_pct', params.top_y_pct.toString());
      if (params.bot_y_pct !== undefined) formData.append('bot_y_pct', params.bot_y_pct.toString());
      if (params.conf_thresh !== undefined) formData.append('conf_thresh', params.conf_thresh.toString());
      if (params.show_heatmap !== undefined) formData.append('show_heatmap', params.show_heatmap.toString());
      if (params.show_trajectory !== undefined) formData.append('show_trajectory', params.show_trajectory.toString());
    }

    const res = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Failed to upload video');
    }

    return res.json();
  },

  /**
   * Poll job progress status
   */
  async getJobStatus(jobId: string): Promise<JobStatusResponse> {
    const res = await fetch(`${API_BASE_URL}/api/job/${jobId}`);
    if (!res.ok) {
      throw new Error('Failed to fetch job status');
    }
    return res.json();
  },

  /**
   * Get list of all analyzed incidents
   */
  async getIncidents(): Promise<IncidentItem[]> {
    const res = await fetch(`${API_BASE_URL}/api/incidents`);
    if (!res.ok) {
      throw new Error('Failed to fetch incidents');
    }
    const data = await res.json();
    return data.incidents || [];
  },

  /**
   * Get analytics metrics
   */
  async getAnalytics(): Promise<AnalyticsResponse> {
    const res = await fetch(`${API_BASE_URL}/api/analytics`);
    if (!res.ok) {
      throw new Error('Failed to fetch analytics');
    }
    return res.json();
  },

  /**
   * Helper to construct full media URL
   */
  getMediaUrl(path: string): string {
    if (path.startsWith('http')) return path;
    return `${API_BASE_URL}${path}`;
  }
};
