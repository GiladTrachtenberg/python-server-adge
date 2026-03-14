import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { userSseUrl } from "./api";

export interface JobEvent {
  job_id: string;
  status: string;
  download_url: string | null;
}

type EventMap = ReadonlyMap<string, JobEvent>;

const SseContext = createContext<EventMap>(new Map());

interface ProviderProps {
  token: string;
  children: ReactNode;
}

export function SseProvider({ token, children }: ProviderProps) {
  const [events, setEvents] = useState<EventMap>(new Map());
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource(userSseUrl(token));
    esRef.current = es;

    es.addEventListener("status", (e: MessageEvent<string>) => {
      const parsed = JSON.parse(e.data) as JobEvent;
      setEvents((prev) => {
        const next = new Map(prev);
        next.set(parsed.job_id, parsed);
        return next;
      });
    });

    es.onerror = () => {
      es.close();
    };

    return () => {
      es.close();
      esRef.current = null;
    };
  }, [token]);

  return <SseContext.Provider value={events}>{children}</SseContext.Provider>;
}

export function useJobEvents(): EventMap {
  return useContext(SseContext);
}

export function useJobEvent(jobId: string): JobEvent | undefined {
  const events = useContext(SseContext);
  return useMemo(() => events.get(jobId), [events, jobId]);
}
