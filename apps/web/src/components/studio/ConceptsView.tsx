import { useState, useEffect } from "react";
import { api, type CreativeConcept } from "@/lib/api";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Check, X, Edit3, ArrowRight } from "lucide-react";

export function ConceptsView({ projectId, onStateChange }: { projectId: string, onStateChange: (state: string) => void }) {
  const [concepts, setConcepts] = useState<CreativeConcept[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState("");
  const [showDisagreement, setShowDisagreement] = useState<any>(null); // To store DisagreementContext

  useEffect(() => {
    async function load() {
      try {
        const data = await api.getConcepts(projectId);
        setConcepts(data || []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [projectId]);

  const handleApprove = async () => {
    setLoading(true);
    try {
      const res = await api.submitApproval(projectId, "approved", concepts[selectedIdx].concept_id);
      onStateChange(res.workflow_state);
    } catch (err) {
      console.error(err);
    } finally {
       setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    try {
      const res = await api.submitApproval(projectId, "rejected", undefined, "User rejected all concepts");
      onStateChange(res.workflow_state);
    } catch (err) {
      console.error(err);
    } finally {
       setLoading(false);
    }
  };

  const handleRevision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!revision.trim()) return;
    setLoading(true);
    try {
      const res = await api.submitRevision(projectId, "concept", concepts[selectedIdx].concept_id, revision);
      if (res.has_disagreement) {
         setShowDisagreement(res.revision.disagreement);
      } else {
         // Reload concepts
         const data = await api.getConcepts(projectId);
         setConcepts(data || []);
         setRevision("");
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const resolveDisagreement = async (decision: string) => {
     setLoading(true);
     try {
       // Since we didn't store revision_id locally in state, we might need a quick refactor
       // but for UI sake, we can assume API will fetch latest un-resolved revision or we pass it
       // Assuming backend handles latest unresolved logic if we pass a generic ID, or we fetch state.
       const state = await api.getState(projectId);
       const latestRev = state.revision_requests?.[state.revision_requests.length - 1];
       if (latestRev) {
          const res = await api.resolveDisagreement(projectId, latestRev.revision_id, decision, "User selected via UI");
          // Reload concepts
          const data = await api.getConcepts(projectId);
          setConcepts(data || []);
          setShowDisagreement(null);
          setRevision("");
       }
     } catch (err) { }
     setLoading(false);
  };

  if (loading && concepts.length === 0) {
     return <div className="p-8 text-center text-zinc-500 font-mono">Loading concept recommendations...</div>
  }

  if (concepts.length === 0) {
    return <div className="p-8 text-center text-zinc-500">No concepts generated yet.</div>
  }

  const active = concepts[selectedIdx];

  return (
    <div className="h-full flex flex-col bg-zinc-950 text-zinc-300">
      <div className="p-4 border-b border-zinc-900 bg-zinc-900/20 font-mono text-sm flex gap-4 overflow-x-auto">
        {concepts.map((c, i) => (
          <button 
            key={i} 
            onClick={() => setSelectedIdx(i)}
            className={`px-4 py-2 shrink-0 border-b-2 transition-colors ${i === selectedIdx ? 'border-[#EADDFF] text-[#EADDFF]' : 'border-transparent text-zinc-500 hover:text-zinc-300'}`}
          >
            Concept {i+1}: {c.title.substring(0, 20)}...
          </button>
        ))}
      </div>
      
      <ScrollArea className="flex-1 p-8">
        <div className="max-w-4xl mx-auto space-y-12">
          
          {/* Main Concept Header */}
          <div className="space-y-4">
            <h1 className="text-4xl text-[#EADDFF] font-light">{active.title}</h1>
            <p className="text-xl text-white font-medium italic border-l-4 border-[#EADDFF]/50 pl-4 py-2 bg-[#EADDFF]/5">
              "{active.hook}"
            </p>
          </div>

          <div className="grid grid-cols-2 gap-8">
             {/* Left Col */}
             <div className="space-y-8">
               <section>
                 <h3 className="text-xs uppercase tracking-widest text-[#EADDFF]/50 font-mono mb-3">Narrative Structure</h3>
                 <p className="font-light text-zinc-300 leading-relaxed bg-zinc-900/30 p-4 rounded-xl border border-zinc-800/50">
                    {active.narrative_structure}
                 </p>
               </section>
               
               <section>
                 <h3 className="text-xs uppercase tracking-widest text-[#EADDFF]/50 font-mono mb-3">Call to Action</h3>
                 <div className="inline-block px-4 py-2 bg-[#EADDFF]/10 text-[#EADDFF] rounded-lg">
                   {active.cta}
                 </div>
               </section>
             </div>

             {/* Right Col */}
             <div className="space-y-8">
               <section>
                 <h3 className="text-xs uppercase tracking-widest text-[#EADDFF]/50 font-mono mb-3">Why This Works</h3>
                 <p className="font-light text-zinc-400">
                    {active.rationale}
                 </p>
               </section>

               <section>
                 <h3 className="text-xs uppercase tracking-widest text-[#EADDFF]/50 font-mono mb-3">Production Direction</h3>
                 <p className="font-light text-zinc-400">
                   {active.production_direction}
                 </p>
                 <div className="mt-4 flex gap-4 text-sm font-mono text-zinc-500">
                   <div className="bg-zinc-900 px-3 py-1 rounded">~{active.estimated_duration_seconds}s</div>
                   <div className="bg-zinc-900 px-3 py-1 rounded">{active.creative_format}</div>
                 </div>
               </section>
             </div>
          </div>

          <div className="border-t border-zinc-900 pt-8 flex gap-4 justify-between items-center bg-zinc-950 sticky bottom-0 p-4">
            <div className="flex-1">
              <form onSubmit={handleRevision} className="flex gap-2 relative">
                <input 
                  type="text" 
                  value={revision}
                  onChange={e => setRevision(e.target.value)}
                  placeholder="Request a revision (e.g. 'Make the tone edgier')..."
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-full px-6 py-3 text-sm focus:border-[#EADDFF] focus:outline-none transition-colors"
                />
                <button type="submit" disabled={loading || !revision} className="absolute right-2 top-2 p-1.5 bg-[#EADDFF] text-zinc-900 rounded-full disabled:opacity-50">
                   <ArrowRight className="w-4 h-4" />
                </button>
              </form>
            </div>
            
            <div className="flex gap-4">
               <button onClick={handleReject} disabled={loading} className="px-6 py-3 rounded-full font-medium text-red-400 hover:bg-red-950/30 transition-colors border border-transparent hover:border-red-900/50 flex gap-2 items-center">
                 <X className="w-4 h-4" /> Reject All
               </button>
               <button onClick={handleApprove} disabled={loading} className="px-8 py-3 rounded-full font-medium bg-[#EADDFF] text-[#21005D] hover:bg-[#D0BCFF] transition-colors flex gap-2 items-center shadow-lg shadow-[#EADDFF]/10">
                 <Check className="w-4 h-4" /> Approve Concept
               </button>
            </div>
          </div>
        </div>
      </ScrollArea>

      {/* Disagreement Modal */}
      {showDisagreement && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
           <div className="bg-zinc-950 border border-zinc-800 p-8 rounded-2xl max-w-2xl w-full space-y-6 shadow-2xl">
              <div className="flex items-center gap-3 text-orange-400">
                <Edit3 className="w-6 h-6" />
                <h2 className="text-xl font-medium">Creative Disagreement Detected</h2>
              </div>
              <p className="text-zinc-300 font-light leading-relaxed">
                {showDisagreement.trade_off_explanation}
              </p>
              
              <div className="bg-zinc-900 p-4 rounded-lg font-mono text-sm text-[#EADDFF]/80 whitespace-pre-wrap">
                 Recommendation: {showDisagreement.agent_recommendation}
              </div>

              <div className="space-y-3 pt-4">
                <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-mono">How would you like to proceed?</h3>
                {showDisagreement.options.map((opt: string, i: number) => (
                  <button 
                    key={i} 
                    onClick={() => resolveDisagreement(opt)}
                    className="w-full text-left p-4 border border-zinc-800 rounded-xl hover:border-[#EADDFF]/50 hover:bg-zinc-900 transition-colors font-light text-zinc-200"
                  >
                    {opt}
                  </button>
                ))}
              </div>
           </div>
        </div>
      )}
    </div>
  );
}
