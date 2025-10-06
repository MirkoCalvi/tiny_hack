import type * as satellite from 'satellite.js';

export type SatelliteAlert = {
  timestamp: number;
  classification: number[];
  image: string;
}

export type SatelliteData = {
  lng?: number;
  lat?: number;
  alt?: number;
  name: string;
  satrec: satellite.SatRec;
}

export type SatelliteTLE = {
  line1: string;
  line2: string;
  name: string;
}
