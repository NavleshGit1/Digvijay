/**
 * AirOps Nexus Full-Duplex WebSocket Client
 * Provides resilient, auto-reconnecting real-time bidirectional communication
 * across /api/v1/ws and /ws endpoints.
 */

export type WebSocketStatus = "connecting" | "connected" | "disconnected" | "error";

export interface WebSocketMessage<T = unknown> {
  type: string;
  channel?: string;
  data?: T;
  payload?: T;
  timestamp?: string;
  protocol?: string;
  message?: string;
}

export type MessageHandler<T = unknown> = (data: T) => void;
export type StatusHandler = (status: WebSocketStatus) => void;

export class AirOpsWebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private status: WebSocketStatus = "disconnected";
  private channelSubscribers: Map<string, Set<MessageHandler<any>>> = new Map();
  private statusSubscribers: Set<StatusHandler> = new Set();
  private reconnectTimer: number | null = null;
  private pingTimer: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 10000;
  private shouldReconnect = true;

  constructor(endpoint = "/api/v1/ws") {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host || "localhost:5173";
    this.url = `${protocol}//${host}${endpoint}`;
  }

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.shouldReconnect = true;
    this.setStatus("connecting");

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.setStatus("connected");
        this.reconnectAttempts = 0;
        this.startHeartbeat();

        // Resubscribe to existing channels on reconnect
        for (const channel of this.channelSubscribers.keys()) {
          this.sendAction("subscribe", { channel });
        }
      };

      this.ws.onmessage = (event: MessageEvent) => {
        try {
          const payload: WebSocketMessage = JSON.parse(event.data);
          this.handleIncomingMessage(payload);
        } catch {
          // Non-JSON raw text message
          if (event.data === "pong") {
            // Heartbeat acknowledged
          }
        }
      };

      this.ws.onclose = () => {
        this.cleanupSocket();
        this.setStatus("disconnected");
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.setStatus("error");
      };
    } catch {
      this.setStatus("error");
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.shouldReconnect = false;
    this.clearTimers();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus("disconnected");
  }

  public getStatus(): WebSocketStatus {
    return this.status;
  }

  public isConnected(): boolean {
    return this.status === "connected";
  }

  public subscribe<T = unknown>(channel: string, handler: MessageHandler<T>): () => void {
    if (!this.channelSubscribers.has(channel)) {
      this.channelSubscribers.set(channel, new Set());
      if (this.isConnected()) {
        this.sendAction("subscribe", { channel });
      }
    }

    this.channelSubscribers.get(channel)!.add(handler as MessageHandler<any>);

    return () => {
      const subscribers = this.channelSubscribers.get(channel);
      if (subscribers) {
        subscribers.delete(handler as MessageHandler<any>);
        if (subscribers.size === 0) {
          this.channelSubscribers.delete(channel);
        }
      }
    };
  }

  public onStatusChange(handler: StatusHandler): () => void {
    this.statusSubscribers.add(handler);
    handler(this.status);
    return () => {
      this.statusSubscribers.delete(handler);
    };
  }

  public sendAction(action: string, payload: Record<string, unknown> = {}): boolean {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action, ...payload }));
      return true;
    }
    return false;
  }

  private handleIncomingMessage(msg: WebSocketMessage): void {
    if (msg.type === "message" && msg.channel) {
      const subscribers = this.channelSubscribers.get(msg.channel);
      if (subscribers) {
        subscribers.forEach((handler) => {
          try {
            handler(msg.data);
          } catch (err) {
            console.error(`Error in WebSocket subscriber for channel ${msg.channel}:`, err);
          }
        });
      }
    } else if (msg.type === "pong") {
      // Keepalive acknowledged
    }
  }

  private setStatus(newStatus: WebSocketStatus): void {
    if (this.status !== newStatus) {
      this.status = newStatus;
      this.statusSubscribers.forEach((handler) => {
        try {
          handler(newStatus);
        } catch (err) {
          console.error("Error in WebSocket status subscriber:", err);
        }
      });
    }
  }

  private startHeartbeat(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
    }
    this.pingTimer = window.setInterval(() => {
      if (this.isConnected()) {
        this.sendAction("ping");
      }
    }, 20000);
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect || this.reconnectTimer) {
      return;
    }

    const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), this.maxReconnectDelay);
    this.reconnectAttempts++;

    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private clearTimers(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private cleanupSocket(): void {
    this.clearTimers();
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onmessage = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws = null;
    }
  }
}

export const wsClient = new AirOpsWebSocketClient();
