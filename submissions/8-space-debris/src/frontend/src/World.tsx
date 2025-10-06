import Globe from 'react-globe.gl';
import { useState, useEffect, useRef, useMemo } from 'react';
import * as satellite from 'satellite.js';
import { TIME_STEP } from './lib/const';
import * as THREE from 'three';
import type { SatelliteData, SatelliteTLE } from './lib/types';
import { getPosFromSatRec } from './lib/utils';

export const World = ({ satellites, selected }: { satellites: SatelliteTLE[]; selected: string | null; }) => {
  const globeEl = useRef<any>(null);
  const [satData, setSatData] = useState<SatelliteData[]>([]);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    setSatData(satellites.map(({ name, line1, line2 }) => ({
      name,
      satrec: satellite.twoline2satrec(line1, line2)
    })));
  }, [satellites]);

  useEffect(() => {
    (function frameTicker() {
      requestAnimationFrame(frameTicker);
      setTime(time => new Date(+time + TIME_STEP));
    })();
  }, []);

  const particlesData = useMemo(() => {
    if (!satData) return [];

    const base: {
      data: SatelliteData[];
      selected: boolean;
    }[] = [];
    const gmst = satellite.gstime(time);
    const selIndx = satData.findIndex(d => selected && d.name == selected);
    if (selIndx != -1)
      base.push({
        data: [getPosFromSatRec(satData[selIndx], gmst, time)],
        selected: true,
      });
    base.push({
      data: satData.filter((_, i) => i != selIndx).map((d: SatelliteData) => getPosFromSatRec(d, gmst, time)).filter((d: SatelliteData) => d.lat !== undefined && d.lng !== undefined && d.alt !== undefined && !isNaN(d.lat) && !isNaN(d.lng) && !isNaN(d.alt)),
      selected: false,
    });

    return base;
  }, [satData, time]);

  useEffect(() => {
    if (globeEl.current) {
      globeEl.current.pointOfView({ altitude: 3.5 });
    }
  }, []);

  const texture = useMemo(() => new THREE.TextureLoader().load("/cubesat_gray.png"), []);
  const textureSelected = useMemo(() => new THREE.TextureLoader().load("/cubesat.png"), []);

  const width = useMemo(() => window.innerWidth * 0.7, []);

  return <Globe
    ref={globeEl}
    width={width}
    globeImageUrl="/earth-blue-marble.jpg"
    particlesData={particlesData}
    particlesList={(d: any) => d["data"]}
    particleLabel="name"
    particleLat="lat"
    particleLng="lng"
    particleAltitude="alt"
    particlesSize={40}
    particlesSizeAttenuation={true}
    particlesTexture={(d: any) => {
      if (d.selected) return textureSelected;
      return texture;
    }}
  />
    ;
};
