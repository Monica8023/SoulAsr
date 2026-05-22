import { computed, onBeforeUnmount, ref, shallowRef } from "vue";

type SocketStatus = "idle" | "connecting" | "open" | "closed" | "error";

interface UseWebSocketOptions {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  autoReconnect?: boolean;
  onMessage?: (event: MessageEvent<string | ArrayBuffer>) => void;
  onError?: (event: Event) => void;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
}

export function useWebSocket(options: UseWebSocketOptions) {
  const socket = shallowRef<WebSocket | null>(null);
  const status = ref<SocketStatus>("idle");
  const errorMessage = ref("");
  const reconnectCount = ref(0);
  const manuallyClosed = ref(false);

  const canReconnect = computed(
    () => reconnectCount.value < (options.maxReconnectAttempts ?? 5),
  );

  const scheduleReconnect = () => {
    if (options.autoReconnect === false) {
      return;
    }
    if (!canReconnect.value || manuallyClosed.value) {
      return;
    }
    reconnectCount.value += 1;
    window.setTimeout(() => {
      void connect();
    }, options.reconnectInterval ?? 2000);
  };

  const connect = () =>
    new Promise<void>((resolve, reject) => {
      manuallyClosed.value = false;
      status.value = "connecting";

      const ws = new WebSocket(options.url);
      ws.binaryType = "arraybuffer";

      ws.onopen = (event) => {
        socket.value = ws;
        status.value = "open";
        errorMessage.value = "";
        reconnectCount.value = 0;
        options.onOpen?.(event);
        resolve();
      };

      ws.onmessage = (event) => {
        options.onMessage?.(event as MessageEvent<string | ArrayBuffer>);
      };

      ws.onerror = (event) => {
        status.value = "error";
        errorMessage.value = "WebSocket 连接失败";
        options.onError?.(event);
        reject(event);
      };

      ws.onclose = (event) => {
        socket.value = null;
        status.value = "closed";
        options.onClose?.(event);
        if (!manuallyClosed.value) {
          scheduleReconnect();
        }
      };
    });

  const send = (payload: string | ArrayBuffer | Blob | ArrayBufferView) => {
    if (!socket.value || socket.value.readyState !== WebSocket.OPEN) {
      throw new Error("WebSocket 尚未连接");
    }
    socket.value.send(payload);
  };

  const sendJson = (payload: object) => {
    send(JSON.stringify(payload));
  };

  const close = (code?: number, reason?: string) => {
    manuallyClosed.value = true;
    socket.value?.close(code, reason);
  };

  onBeforeUnmount(() => {
    close(1000, "component unmount");
  });

  return {
    status,
    errorMessage,
    connect,
    send,
    sendJson,
    close,
  };
}
