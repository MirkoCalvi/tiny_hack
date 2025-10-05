import { useQuery } from '@tanstack/react-query';
import type { SummaryResponse } from '../types';

const API_URL = 'http://localhost:3002';

export const useSummary = () => {
  return useQuery<SummaryResponse>({
    queryKey: ['summary'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/summary`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch summary');
      }
      
      return response.json();
    },
    staleTime: 0, 
    refetchOnMount: true,
  });
};

