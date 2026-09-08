import { api, type TranscreationOption } from "@/lib/api";
import { useState } from "react";
import { ArrowRight, Lock, CheckCircle, Search, Edit3 } from "lucide-react";

export function DubbingStudio({ projectId, onStateChange }: { projectId: string, onStateChange: (state: string) => void }) {
  const [loading, setLoading] = useState(false);
  const [options, setOptions] = useState<any>(null);

  // We fetch options when reaching TRANSCREATION_READY
  const fetchOptions = async () => {
    setLoading(true);
    try {
      const data = await api.getTranscreationOptions(projectId);
      setOptions(data);
    } catch(e) {}
    setLoading(false);
  };

  const submitConsent = async (speakerId: string) => {
    await api.submitVoiceConsent(projectId, speakerId, true, "Hackathon Demo");
    alert("Consent verified and immutably logged to Provenance.");
  };

  return (
    <div className="flex flex-col h-full bg-zinc-950 p-8 space-y-8 overflow-y-auto w-full text-zinc-100">
      
      <div className="border-b border-zinc-900 pb-4">
        <h1 className="text-3xl font-light text-[#EADDFF]">Mimesis Studio</h1>
        <p className="text-zinc-500 font-mono text-xs uppercase mt-2">Transcreation & Responsible Dubbing</p>
      </div>

      <div className="flex gap-4">
        <button onClick={fetchOptions} className="bg-zinc-900 hover:bg-zinc-800 px-6 py-3 rounded-lg border border-zinc-800 transition-colors flex gap-2">
          <Search className="w-5 h-5 text-[#EADDFF]" /> Load Transcreation Engine
        </button>
      </div>

      {options && (
        <div className="space-y-12">
            
          {/* CULTURAL CONTEXT */}
          <section className="space-y-4">
             <h2 className="text-xl font-light border-b border-zinc-900 pb-2">Cultural Research (Parallel Search MCP)</h2>
             {options.cultural_references.map((cr: any, i: number) => (
                <div key={i} className="bg-zinc-900/50 p-6 rounded-xl border border-zinc-800">
                  <div className="flex gap-4 items-center">
                    <span className="bg-blue-500/20 text-blue-400 px-3 py-1 rounded-full text-xs font-mono">{cr.reference_type}</span>
                    <h3 className="text-lg font-medium">"{cr.original_phrase}"</h3>
                  </div>
                  <p className="text-zinc-400 mt-4 leading-relaxed font-light">{cr.explanation}</p>
                </div>
             ))}
          </section>

          {/* TRANSCREATIONS */}
          <section className="space-y-4">
             <h2 className="text-xl font-light border-b border-zinc-900 pb-2">Transcreation Adaptation</h2>
             {options.segments.map((seg: any) => (
                <div key={seg.segment_id} className="space-y-4 pt-4">
                   <div className="p-4 bg-zinc-900/80 rounded-xl text-zinc-300">
                     <div className="text-xs text-zinc-500 font-mono uppercase mb-2">Original Telugu</div>
                     <p className="text-lg font-medium">{seg.original_text}</p>
                   </div>
                   
                   <div className="grid grid-cols-3 gap-6">
                     {(options.options[seg.segment_id] || []).map((opt: any, j: number) => (
                       <div key={j} className="border border-zinc-800 bg-zinc-950 p-6 rounded-xl hover:border-[#EADDFF]/50 transition-colors flex flex-col cursor-pointer">
                         <div className="text-xs uppercase tracking-widest text-[#EADDFF]/50 font-mono mb-4 border-b border-zinc-900 pb-2">{opt.option_type}</div>
                         <p className="text-white mb-6 flex-1 italic font-light">"{opt.target_text}"</p>
                         
                         <div className="space-y-2 mb-6">
                           <div className="text-xs text-zinc-500 flex justify-between"><span>Humor Status</span> <span className="text-zinc-300">{opt.humor_preservation}</span></div>
                           <div className="text-xs text-zinc-500 flex justify-between"><span>Timing Impact</span> <span className="text-zinc-300">{opt.timing_impact}</span></div>
                         </div>
                         
                         <button className="w-full bg-[#EADDFF] text-[#21005D] py-2 rounded font-medium hover:bg-[#D0BCFF]">Select Option</button>
                       </div>
                     ))}
                   </div>
                </div>
             ))}
          </section>
          
          <section className="space-y-4 border border-red-900/30 bg-red-950/10 p-8 rounded-2xl">
             <h2 className="text-xl font-light text-red-400 flex items-center gap-2 border-b border-red-900/30 pb-2">
               <Lock className="w-5 h-5" /> Voice Consent Gate
             </h2>
             <p className="text-sm text-zinc-400">Mimesis blocks voice generation for cloned/fictional profiles lacking explicit cryptographic provenance.</p>
             <button onClick={() => submitConsent('speaker_1')} className="bg-red-900/40 text-red-300 px-6 py-3 rounded-lg border border-red-800 hover:bg-red-900 hover:text-white transition-colors">
               Approve Voice Consent for Speaker 1
             </button>
          </section>

        </div>
      )}

    </div>
  );
}
