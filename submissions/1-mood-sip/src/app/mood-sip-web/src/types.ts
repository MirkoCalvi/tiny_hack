export interface MoodAnalysis {
  needs_hydration: boolean;
  detected_signs?: string[];
  confidence: number;
}

export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface AppNotification {
  id: number;
  text: string;
  type: NotificationType;
  time: Date;
}
