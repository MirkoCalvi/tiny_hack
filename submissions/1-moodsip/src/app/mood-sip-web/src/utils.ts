// Utility helpers

export const bytesToPgmBase64 = (grayData: Uint8Array, width: number, height: number): string => {
  const header = `P5\n${width} ${height}\n255\n`;
  let binaryString = '';
  for (let i = 0; i < grayData.length; i++) {
    binaryString += String.fromCharCode(grayData[i]);
  }
  const base64Encoded = btoa(header + binaryString);
  return base64Encoded;
};

export const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};
