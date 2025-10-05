import { useMutation } from '@tanstack/react-query';
import type { StartJobRequest, StartJobResponse } from '../types';

const API_URL = 'http://localhost:3002';

export const useStartJob = () => {
  return useMutation<StartJobResponse, Error, StartJobRequest>({
    mutationFn: async (data: StartJobRequest) => {
      const response = await fetch(`${API_URL}/api/jobs/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        throw new Error('Failed to start job');
      }

      return response.json();
    },
  });
};

