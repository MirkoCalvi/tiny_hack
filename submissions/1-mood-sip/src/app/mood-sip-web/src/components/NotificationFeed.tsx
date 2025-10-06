import React from 'react';
import type { AppNotification } from '../types';

export function NotificationFeed({ notifications }: { notifications: AppNotification[] }) {
  return (
    <div className="bg-white rounded-2xl sm:rounded-3xl shadow-lg p-4 sm:p-6 mb-4">
      <div className="flex items-center gap-2 mb-3 sm:mb-4">
        <span className="text-teal-600">🔔</span>
        <h2 className="text-base sm:text-lg font-bold text-gray-800">Activity</h2>
      </div>

      <div className="space-y-2 max-h-64 overflow-y-auto">
        {notifications.length === 0 ? (
          <p className="text-gray-400 text-sm text-center py-4">No activity yet</p>
        ) : (
          notifications.map((notif) => (
            <div
              key={notif.id}
              className={`p-2 sm:p-3 rounded-lg sm:rounded-xl text-xs sm:text-sm ${
                notif.type === 'success'
                  ? 'bg-green-50 text-green-800'
                  : notif.type === 'error'
                  ? 'bg-red-50 text-red-800'
                  : notif.type === 'warning'
                  ? 'bg-amber-50 text-amber-800'
                  : 'bg-blue-50 text-blue-800'
              }`}
            >
              <div className="flex justify-between items-start gap-2">
                <span className="flex-1 break-words">{notif.text}</span>
                <span className="text-xs opacity-60 whitespace-nowrap">
                  {notif.time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default NotificationFeed;
