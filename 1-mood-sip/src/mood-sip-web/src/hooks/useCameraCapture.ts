import { useCallback, useState } from 'react';
import { CAMERA_HEIGHT, CAMERA_WIDTH } from '../config';

export function useCameraCapture() {
  const [active, setActive] = useState(false);

  const capture = useCallback(async (): Promise<string> => {
    setActive(true);
    try {
      const canvas = document.createElement('canvas');
      canvas.width = CAMERA_WIDTH;
      canvas.height = CAMERA_HEIGHT;
      const ctx = canvas.getContext('2d');

      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: CAMERA_WIDTH, height: CAMERA_HEIGHT } });
      const video = document.createElement('video');
      video.srcObject = stream as any;
      video.autoplay = true;
      await new Promise((resolve) => (video.onloadedmetadata = resolve as any));
      await video.play();

      await new Promise((r) => setTimeout(r, 2000));
      if (ctx) {
        ctx.drawImage(video, 0, 0, CAMERA_WIDTH, CAMERA_HEIGHT);
        const dataUrl = canvas.toDataURL('image/jpeg', 0.8);
        const base64 = dataUrl.split(',')[1];
        stream.getTracks().forEach((t) => t.stop());
        setActive(false);
        return base64;
      }
      stream.getTracks().forEach((t) => t.stop());
      setActive(false);
      throw new Error('Canvas 2D context is unavailable');
    } catch (e: any) {
      setActive(false);
      throw e;
    }
  }, []);

  return { active, capture };
}
