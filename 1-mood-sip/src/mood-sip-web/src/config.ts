// Centralized configuration for the webapp

export const API_BASE_URL = 'https://10.100.16.79:8001';
export const DEFAULT_MODEL = 'gemini';

// BLE UUIDs (service and characteristics)
export const BLE_SERVICE_UUID = '12345678-1234-5678-1234-56789abcdef0';
export const BLE_IMAGE_CHAR_UUID = 'abcdef01-1234-5678-1234-56789abcdef0';
export const BLE_COMMAND_CHAR_UUID = 'abcdef02-1234-5678-1234-56789abcdef0';

// Camera defaults
export const CAMERA_WIDTH = 640;
export const CAMERA_HEIGHT = 480;

// Grayscale frame specs
export const GRAY_WIDTH = 96;
export const GRAY_HEIGHT = 96;
export const FRAME_BYTES = GRAY_WIDTH * GRAY_HEIGHT; // 9216
