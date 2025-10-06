/**
 * Shared TypeScript types
 */

/**
 * An impression received from a Nicla device
 * Contains emotion detection result and optional camera frame
 */
export interface Impression {
  device_id: string;
  emotion: string;
  timestamp: number;
  frame_data?: string; // Optional: Base64-encoded frame (96x96 grayscale)
}

/**
 * Summary response from GET /api/summary
 * Contains all impressions and session metadata for the dashboard !
 */
export interface SummaryResponse {
  impressions: Impression[];
  total_count: number;
  frames_count: number;
  duration_ms: number;
  start_time: number | null;
  video_url: string | null;
}

/**
 * Current emotion state for a device
 */
export interface EmotionData {
  emotion: string;
}

/**
 * Request payload for POST /api/jobs/start
 */
export interface StartJobRequest {
  video_url: string;
}

/**
 * Response from POST /api/jobs/start
 */
export interface StartJobResponse {
  status: string;
  devices: Array<{
    device_id: string;
    status: string;
  }>;
}

/**
 * Centralized emotion to emoji mapping
 * TODO: change this when we have the final emotion list.
 */
export const emotionEmojis: Record<string, string> = {
  happy: '😊',
  sad: '😢',
  surprised: '😮',
  neutral: '😐',
  angry: '😠',
  disgusted: '🤢',
  fearful: '😨',
  impressed: '🤩',
  'not impressed': '😒',
};

/**
 * Centralized emotion to color mapping (for visualizations)
 */
export const emotionColors: Record<string, string> = {
  happy: '#4ade80',
  sad: '#60a5fa',
  surprised: '#fbbf24',
  neutral: '#9ca3af',
  angry: '#f87171',
  disgusted: '#a78bfa',
  fearful: '#c084fc',
  impressed: '#fb923c',
  'not impressed': '#94a3b8',
};
