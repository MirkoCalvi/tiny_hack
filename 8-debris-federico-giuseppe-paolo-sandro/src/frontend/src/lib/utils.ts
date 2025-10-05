import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import type { SatelliteData } from "./types";
import * as satellite from 'satellite.js';
import { EARTH_RADIUS_KM } from "./const";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function getPosFromSatRec(d: SatelliteData, gmst: satellite.GMSTime, time: Date) {
  const eci = satellite.propagate(d.satrec, time);
  if (eci?.position) {
    const gdPos = satellite.eciToGeodetic(eci.position, gmst);
    const lat = satellite.radiansToDegrees(gdPos.latitude);
    const lng = satellite.radiansToDegrees(gdPos.longitude);
    const alt = gdPos.height / EARTH_RADIUS_KM;
    return { ...d, lat, lng, alt };
  } else {
    return { ...d, lat: NaN, lng: NaN, alt: NaN };
  }
}
