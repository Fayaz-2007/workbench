/** Real local system/network/security status (see backend/app/monitoring/
 * and backend/app/security/status.py) — no mock data.
 */

export interface SystemStatus {
  hostname: string;
  operatingSystem: string;
  localIp: string | null;
  cpuPercent: number;
  ramPercent: number;
  ramUsedGb: number;
  ramTotalGb: number;
  diskPercent: number;
  diskUsedGb: number;
  diskTotalGb: number;
  processCount: number;
  uptimeSeconds: number;
}

export interface NetworkConnectionInfo {
  localAddress: string;
  remoteAddress: string | null;
  status: string;
  isLocal: boolean;
  flags: string[];
}

export interface NetworkStatus {
  available: boolean;
  detail: string;
  localCount: number;
  externalCount: number;
  connections: NetworkConnectionInfo[];
}

export interface SecurityStatusItem {
  label: string;
  value: string;
  detail: string;
}

export interface SecurityStatus {
  items: SecurityStatusItem[];
  summary: string;
}
