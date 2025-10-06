import { useCallback, useState } from 'react';
import type { AppNotification, NotificationType } from '../types';

export function useNotifications(maxItems = 5) {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);

  const add = useCallback((text: string, type: NotificationType = 'info') => {
    setNotifications((prev) => [
      { id: Date.now(), text, type, time: new Date() },
      ...prev.slice(0, Math.max(0, maxItems - 1)),
    ]);
  }, [maxItems]);

  return { notifications, add };
}
