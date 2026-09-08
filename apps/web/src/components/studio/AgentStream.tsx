import { useAgentStream } from "@/lib/api";
import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Zap, Brain, CheckCircle2, AlertTriangle, Workflow } from "lucide-react";

export function AgentStream({ projectId, onStateChange }: { projectId: string, onStateChange: (state: string) => void }) {
  const { events, currentState, isConnected } = useAgentStream(projectId);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  useEffect(() => {
    if (currentState) onStateChange(currentState);
  }, [currentState, onStateChange]);

  const renderIcon = (type: string) => {
    switch (type) {
      case 'agent_started': return <Brain className="w-4 h-4 text-blue-400" />;
      case 'tool_called': return <Zap className="w-4 h-4 text-yellow-500" />;
      case 'tool_result': return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'approval_required': return <AlertTriangle className="w-4 h-4 text-orange-400" />;
      case 'workflow_state_changed': return <Workflow className="w-4 h-4 text-[#EADDFF]" />;
      default: return <div className="w-2 h-2 rounded-full bg-zinc-600" />;
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="px-4 py-2 bg-zinc-950 border-b border-zinc-800 text-xs font-mono text-zinc-500 flex justify-between items-center">
        <span>Execution Trace</span>
        <span>{isConnected ? "Connected" : "Disconnected"}</span>
      </div>
      
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-6">
          {events.map((e, idx) => (
            <div key={idx} className="flex gap-4 group">
              <div className="mt-1 opacity-50 group-hover:opacity-100 transition-opacity">
                {renderIcon(e.event_type)}
              </div>
              <div className="flex-1 space-y-1">
                <div className="flex text-xs items-center justify-between font-mono text-zinc-500">
                  <span className="text-zinc-300">{e.agent_name || 'System'}</span>
                  <span>{new Date(e.timestamp || Date.now()).toLocaleTimeString()}</span>
                </div>
                <div className="text-sm text-zinc-300 font-light">
                  {e.message}
                </div>
                
                {e.data && Object.keys(e.data).length > 0 && e.event_type !== 'workflow_state_changed' && (
                  <pre className="mt-2 p-2 rounded bg-zinc-950 border border-zinc-800 text-[10px] text-zinc-500 overflow-x-auto">
                    {JSON.stringify(e.data, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
      </ScrollArea>
    </div>
  );
}
