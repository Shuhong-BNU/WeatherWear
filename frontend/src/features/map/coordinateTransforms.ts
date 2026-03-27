import type { QueryCoords } from "../../shared/types";

const PI = Math.PI;
const AXIS = 6378245.0;
const OFFSET = 0.00669342162296594323;

function outOfChina(lat: number, lon: number) {
  return lon < 72.004 || lon > 137.8347 || lat < 0.8293 || lat > 55.8271;
}

function transformLat(x: number, y: number) {
  let result = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x));
  result += ((20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0) / 3.0;
  result += ((20.0 * Math.sin(y * PI) + 40.0 * Math.sin((y / 3.0) * PI)) * 2.0) / 3.0;
  result += ((160.0 * Math.sin((y / 12.0) * PI) + 320 * Math.sin((y * PI) / 30.0)) * 2.0) / 3.0;
  return result;
}

function transformLon(x: number, y: number) {
  let result = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x));
  result += ((20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0) / 3.0;
  result += ((20.0 * Math.sin(x * PI) + 40.0 * Math.sin((x / 3.0) * PI)) * 2.0) / 3.0;
  result += ((150.0 * Math.sin((x / 12.0) * PI) + 300.0 * Math.sin((x / 30.0) * PI)) * 2.0) / 3.0;
  return result;
}

export function wgs84ToGcj02(lat: number, lon: number): QueryCoords {
  if (outOfChina(lat, lon)) {
    return { lat, lon };
  }
  let dLat = transformLat(lon - 105.0, lat - 35.0);
  let dLon = transformLon(lon - 105.0, lat - 35.0);
  const radLat = (lat / 180.0) * PI;
  let magic = Math.sin(radLat);
  magic = 1 - OFFSET * magic * magic;
  const sqrtMagic = Math.sqrt(magic);
  dLat = (dLat * 180.0) / (((AXIS * (1 - OFFSET)) / (magic * sqrtMagic)) * PI);
  dLon = (dLon * 180.0) / ((AXIS / sqrtMagic) * Math.cos(radLat) * PI);
  return {
    lat: lat + dLat,
    lon: lon + dLon,
  };
}

export function gcj02ToWgs84(lat: number, lon: number): QueryCoords {
  if (outOfChina(lat, lon)) {
    return { lat, lon };
  }
  const converted = wgs84ToGcj02(lat, lon);
  return {
    lat: lat * 2 - converted.lat,
    lon: lon * 2 - converted.lon,
  };
}

export function gcj02ToBd09(lat: number, lon: number): QueryCoords {
  const z = Math.sqrt(lon * lon + lat * lat) + 0.00002 * Math.sin(lat * PI * 3000.0 / 180.0);
  const theta = Math.atan2(lat, lon) + 0.000003 * Math.cos(lon * PI * 3000.0 / 180.0);
  return {
    lat: z * Math.sin(theta) + 0.006,
    lon: z * Math.cos(theta) + 0.0065,
  };
}

export function bd09ToGcj02(lat: number, lon: number): QueryCoords {
  const x = lon - 0.0065;
  const y = lat - 0.006;
  const z = Math.sqrt(x * x + y * y) - 0.00002 * Math.sin(y * PI * 3000.0 / 180.0);
  const theta = Math.atan2(y, x) - 0.000003 * Math.cos(x * PI * 3000.0 / 180.0);
  return {
    lat: z * Math.sin(theta),
    lon: z * Math.cos(theta),
  };
}

export function wgs84ToBd09(lat: number, lon: number): QueryCoords {
  const gcj = wgs84ToGcj02(lat, lon);
  return gcj02ToBd09(gcj.lat, gcj.lon);
}

export function bd09ToWgs84(lat: number, lon: number): QueryCoords {
  const gcj = bd09ToGcj02(lat, lon);
  return gcj02ToWgs84(gcj.lat, gcj.lon);
}
