import { SimulationSnapshot } from '../types';

export class SimulationWebSocket {
  private socket: WebSocket | null = null;
  private url: string;
  private onSnapshot: (snapshot: SimulationSnapshot) => void;
  private onStatusChange: (status: 'connected' | 'connecting' | 'disconnected') => void;
  private reconnectTimer: number | null = null;
  private shouldReconnect: boolean = true;

  constructor(
    onSnapshot: (snapshot: SimulationSnapshot) => void,
    onStatusChange: (status: 'connected' | 'connecting' | 'disconnected') => void
  ) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    this.url = `${protocol}//${window.location.host}/ws/simulation`;
    this.onSnapshot = onSnapshot;
    this.onStatusChange = onStatusChange;
  }

  public connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.onStatusChange('connecting');
    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        this.onStatusChange('connected');
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.socket.onmessage = (event) => {
        try {
          const data: SimulationSnapshot = JSON.parse(event.data);
          this.onSnapshot(data);
        } catch (err) {
          console.error('Failed to parse WebSocket message', err);
        }
      };

      this.socket.onclose = () => {
        this.onStatusChange('disconnected');
        if (this.shouldReconnect) {
          this.scheduleReconnect();
        }
      };

      this.socket.onerror = () => {
        this.onStatusChange('disconnected');
      };
    } catch (err) {
      this.onStatusChange('disconnected');
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 2000);
  }

  public disconnect(): void {
    this.shouldReconnect = false;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.onStatusChange('disconnected');
  }
}
