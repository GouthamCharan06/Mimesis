import { useState, useRef, useEffect } from "react";
import { api } from "@/lib/api";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User } from "lucide-react";

export function ChatInterface({ projectId, onStateChange }: { projectId: string, onStateChange: (state: string) => void }) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<{ role: 'user' | 'agent', content: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMsg = input;
    setInput("");
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const result = await api.submitConversationTurn(projectId, userMsg);
      setMessages(prev => [...prev, { role: 'agent', content: result.agent_message }]);
      onStateChange(result.workflow_state);
      
      if (result.workflow_state === 'PROFILE_READY' && result.agent_message) {
        // Last message handled nicely.
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-zinc-950">
      <div className="p-4 border-b border-zinc-900 bg-zinc-900/20 text-zinc-300 font-mono text-sm">
        Profile Extraction & Onboarding
      </div>

      <ScrollArea className="flex-1 p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 && (
            <div className="text-center text-zinc-500 py-10 font-light">
              <Bot className="w-12 h-12 mx-auto mb-4 opacity-20" />
              Agent ready. Please describe your brand, industry, and marketing goals.
            </div>
          )}
          
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'agent' && (
                <div className="w-8 h-8 rounded-full bg-[#EADDFF]/10 text-[#EADDFF] flex items-center justify-center shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
              )}
              <div 
                className={`max-w-[80%] rounded-2xl p-4 font-light text-sm leading-relaxed ${
                  msg.role === 'user' 
                    ? 'bg-zinc-800 text-zinc-200 rounded-tr-none' 
                    : 'bg-zinc-900 text-[#EADDFF] border border-[#EADDFF]/20 rounded-tl-none'
                }`}
              >
                {msg.content}
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center shrink-0">
                  <User className="w-4 h-4 text-zinc-400" />
                </div>
              )}
            </div>
          ))}
          {loading && (
             <div className="flex gap-4">
               <div className="w-8 h-8 rounded-full bg-[#EADDFF]/10 text-[#EADDFF] flex items-center justify-center">
                 <Bot className="w-4 h-4 animate-pulse" />
               </div>
               <div className="bg-zinc-900 border border-[#EADDFF]/20 rounded-2xl rounded-tl-none p-4 w-24 flex gap-1 items-center justify-center">
                 <div className="w-2 h-2 bg-[#EADDFF]/50 rounded-full animate-bounce"></div>
                 <div className="w-2 h-2 bg-[#EADDFF]/50 rounded-full animate-bounce delay-75"></div>
                 <div className="w-2 h-2 bg-[#EADDFF]/50 rounded-full animate-bounce delay-150"></div>
               </div>
             </div>
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-zinc-900 bg-zinc-950">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder="Type your response..."
            className="flex-1 bg-zinc-900 border border-zinc-800 rounded-full px-6 py-4 text-sm font-light focus:outline-none focus:border-[#EADDFF]/50 disabled:opacity-50 transition-colors"
          />
          <button 
            type="submit" 
            disabled={loading || !input.trim()}
            className="w-14 h-14 bg-[#EADDFF] text-[#21005D] rounded-full flex items-center justify-center hover:bg-[#D0BCFF] disabled:opacity-50 transition-colors shrink-0"
          >
            <Send className="w-5 h-5 ml-1" />
          </button>
        </form>
      </div>
    </div>
  );
}
