import { writable } from 'svelte/store';
import type { Notification, NotificationType, BackendApiResponse } from '../types.js';

const createNotificationStore = () => {
  const { subscribe, set, update } = writable<Notification[]>([]);

  let nextId = 1;

  return {
    subscribe,
    
    add(type: NotificationType, message: string, duration: number = 5000) {
      const notification: Notification = {
        id: (nextId++).toString(),
        type,
        message,
        timestamp: Date.now()
      };

      update(notifications => [...notifications, notification]);

      if (duration > 0) {
        setTimeout(() => {
          this.remove(notification.id);
        }, duration);
      }

      return notification.id;
    },

    remove(id: string) {
      update(notifications => notifications.filter(n => n.id !== id));
    },

    clear() {
      set([]);
    },

    showError(message: string, duration?: number) {
      return this.add('error', message, duration);
    },

    showWarning(message: string, duration?: number) {
      return this.add('warning', message, duration);
    },

    showInfo(message: string, duration?: number) {
      return this.add('info', message, duration);
    },

    showSuccess(message: string, duration?: number) {
      return this.add('success', message, duration);
    },

    handleApiResponse(response: BackendApiResponse<any>) {
      // Handle legacy single message format
      if (response.message && response.level) {
        const type = response.level as NotificationType;
        this.add(type, response.message);
        return;
      }

      // Handle enhanced notification format
      if (response.notifications && response.notifications.length > 0) {
        response.notifications.forEach(notification => {
          this.add(notification.level || 'info', notification.message || 'Notification');
        });
      }
    }
  };
};

export const notifications = createNotificationStore();