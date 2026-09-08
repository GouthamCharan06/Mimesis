import { useState, useRef, useEffect } from "react";
import { useAgentStream } from "@/lib/api"; 
import { Mic, Search, Send, RadioReceiver, Download, Play, Pause, Loader2, FastForward, Rewind, Sparkles, User, MessageCircle, CheckCircle, Circle } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

type PlaybackState = 'setup' | 'generating_initial' | 'playing' | 'paused' | 'interrupt_input' | 'researching' | 'resuming';

export function PodcastStudio() {
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [turns, setTurns] = useState<any[]>([]);
    const [researchEvidence, setResearchEvidence] = useState<any[]>([]);
    const [question, setQuestion] = useState("");
    const [topicInput, setTopicInput] = useState("Agentic Workflows");
    const [isBuffering, setIsBuffering] = useState(false);
    const [processedEventCount, setProcessedEventCount] = useState(0);
    const [adaptationPayload, setAdaptationPayload] = useState<any>(null);
    
    // Audio State Machine
    const [playbackState, setPlaybackState] = useState<PlaybackState>('setup');
    const [currentTurnIndex, setCurrentTurnIndex] = useState<number>(-1);
    const [returnStack, setReturnStack] = useState<{turnIndex: number, time: number} | null>(null);
    const [progress, setProgress] = useState(0);
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    
    const audioRef = useRef<HTMLAudioElement>(null);
    const transcriptRef = useRef<HTMLDivElement>(null);

    const { events } = useAgentStream(sessionId);

    // Initial Fetch
    const initPodcast = async (selectedTopic: string) => {
        setPlaybackState('generating_initial');
        setProcessedEventCount(0); // reset streaming cursor
        try {
            const res = await fetch("http://localhost:8001/api/sessions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ expert_id: "mimesis", topic: selectedTopic })
            });
            const data = await res.json();
            setSessionId(data.session_id);
            // We now aggressively rely on SSE events to trigger playback once `podcast_ready` fires!
        } catch(e) {
            console.error(e);
            setPlaybackState('setup');
        }
    };

    // Auto-advance core logic
    useEffect(() => {
        if (playbackState === 'playing' && turns.length > 0 && currentTurnIndex >= 0 && currentTurnIndex < turns.length) {
            const turn = turns[currentTurnIndex];
            
            if (turn.speaker === 'User') {
                // Instantly fast-forward over user questions directly to the response
                setCurrentTurnIndex(idx => idx + 1);
                return;
            }

            if (turn.audio_path && audioRef.current) {
                const targetUrl = `http://localhost:8001${turn.audio_path}`;
                // Avoid reloading the same audio src
                if (!audioRef.current.src.endsWith(turn.audio_path)) {
                     audioRef.current.src = targetUrl;
                     
                     // Resume logic: if we are returning from an interruption to this exact turn
                     if (returnStack && returnStack.turnIndex === currentTurnIndex) {
                         audioRef.current.currentTime = returnStack.time;
                         setReturnStack(null);
                     } else {
                         audioRef.current.currentTime = 0;
                     }
                }
                
                const playPromise = audioRef.current.play();
                if (playPromise !== undefined) {
                    playPromise.catch(e => {
                        console.warn("Audio playback gracefully caught Autoplay or Abort error", e);
                        setPlaybackState('paused'); // Gracefully pause so the user can manually click Play
                    });
                }
            }
        }
    }, [currentTurnIndex, playbackState, turns, returnStack]);

    // Track Backend Streaming SSE Events For Live Progression
    useEffect(() => {
        if (!events || events.length === 0 || events.length <= processedEventCount) return;

        let requiresStateUpdate = false;
        
        for (let i = processedEventCount; i < events.length; i++) {
            const ev = events[i];
            
            if (ev.event_type === 'podcast_ready') {
                if (ev.data?.turns) {
                     setTurns(ev.data.turns);
                     setCurrentTurnIndex(0);
                     setPlaybackState('playing');
                }
            }
            else if (ev.event_type === 'comparing_evidence') {
                if (ev.data?.evidence) {
                     setResearchEvidence(ev.data.evidence);
                }
            }
            else if (ev.event_type === 'adaptation_proposed') {
                if (ev.data) {
                     setAdaptationPayload(ev.data);
                     if (audioRef.current) audioRef.current.pause();
                }
            }
            else if (ev.event_type === 'completed') {
                requiresStateUpdate = true;
            }
        }
        
        if (requiresStateUpdate && sessionId) {
            fetch(`http://localhost:8001/api/sessions/${sessionId}`)
               .then(res => res.json())
               .then(data => {
                   if (data.turns) {
                       setTurns(data.turns);
                       setCurrentTurnIndex(data.turns.length - 1);
                       setPlaybackState('playing');
                   }
               })
               .catch(err => console.error("Could not trace back interruption stream", err));
        }

        setProcessedEventCount(events.length);
    }, [events, processedEventCount, sessionId]);

    // Handle seamless advancing
    const handleAudioEnded = () => {
        if (playbackState !== 'playing') return;
        
        // If we just finished an interruption response (a newly appended turn at the very end of the array),
        // we heavily rely on the returnStack mapping to jump us back to the original spot!
        if (returnStack && currentTurnIndex >= turns.length - 1) {
             setPlaybackState('resuming');
             setTimeout(() => {
                 setCurrentTurnIndex(returnStack.turnIndex);
                 setPlaybackState('playing');
             }, 1500); // smooth UX resume delay
             return;
        }
        
        // Normal sequential advancement
        if (currentTurnIndex < turns.length - 1) {
            setCurrentTurnIndex(prev => prev + 1);
        } else {
            setPlaybackState('paused'); // Reached end of currently generated content
        }
    };

    // Time update for Progress Bar
    const handleTimeUpdate = () => {
        if (audioRef.current) {
            setCurrentTime(audioRef.current.currentTime);
            setDuration(audioRef.current.duration || 0);
            setProgress(audioRef.current.duration ? (audioRef.current.currentTime / audioRef.current.duration) * 100 : 0);
        }
    };

    // The Interruption Flow ("Ask Mimesis")
    const triggerInterrupt = () => {
        if (playbackState === 'playing' && audioRef.current) {
            audioRef.current.pause();
            setReturnStack({
                turnIndex: currentTurnIndex,
                time: audioRef.current.currentTime
            });
        }
        setPlaybackState('interrupt_input');
    };

    const submitQuestion = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!question.trim() || !sessionId) return;
        
        const text = question;
        setQuestion("");
        setPlaybackState('researching');
        
        try {
            const res = await fetch(`http://localhost:8001/api/sessions/${sessionId}/ask`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    text_content: text,
                    turn_index: currentTurnIndex,
                    time_seconds: audioRef.current?.currentTime || 0
                })
            });
            
            if (!res.ok) {
                console.error("Backend returned an error. The session may have been cleared by a server restart.");
                setPlaybackState('paused');
            }
            // We now aggressively rely on the SSE events mapped above to trigger playback once `completed` fires!
        } catch(e) {
            console.error("Graceful network fallback", e);
            setPlaybackState('paused'); 
        }
    };

    // Format mm:ss
    const formatTime = (secs: number) => {
        const m = Math.floor(secs / 60);
        const s = Math.floor(secs % 60);
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    // Render genuine progressing states from SSE
    const renderProgressChecklist = (stages: {id: string, label: string}[]) => {
        const eventIds = events.map(e => e.event_type);
        const stageIndexes = stages.map(s => eventIds.lastIndexOf(s.id));
        const highestMatched = Math.max(...stageIndexes.filter(i => i !== -1));

        return (
            <div className="flex flex-col gap-4 mt-8 w-full max-w-sm animate-in fade-in slide-in-from-bottom-2">
                {stages.map((stage, idx) => {
                    const localStageIndex = stageIndexes[idx];
                    const isActive = localStageIndex !== -1 && localStageIndex === highestMatched;
                    const isCompleted = localStageIndex !== -1 && !isActive;
                    const isPending = localStageIndex === -1 && highestMatched < Math.max(...stageIndexes);

                    return (
                        <div key={stage.id} className={`flex items-center gap-4 transition-all duration-500 ${isPending ? 'opacity-30' : 'opacity-100'}`}>
                            {isCompleted ? <CheckCircle className="w-5 h-5 text-emerald-500" /> :
                             isActive ? <Loader2 className="w-5 h-5 text-indigo-400 animate-spin" /> :
                             <Circle className="w-5 h-5 text-zinc-700" />}
                            <span className={`text-[15px] ${isCompleted ? 'text-zinc-500' : isActive ? 'text-white font-medium drop-shadow-[0_0_8px_rgba(129,140,248,0.5)]' : 'text-zinc-600 font-light'}`}>
                                {stage.label}
                            </span>
                        </div>
                    );
                })}
            </div>
        );
    };

    const GENERATION_STAGES = [
        { id: 'preparing_topic', label: 'Preparing episode topic' },
        { id: 'structuring_conversation', label: 'Structuring the conversation' },
        { id: 'writing_dialogue', label: 'Writing Host / Expert dialogue' },
        { id: 'generating_voices', label: 'Generating vocal personas' },
        { id: 'podcast_ready', label: 'Preparing audio buffers' }
    ];

    const QUESTION_STAGES = [
        { id: 'capturing_context', label: 'Capturing exact playhead context' },
        { id: 'evaluating_gaps', label: 'Evaluating for knowledge gaps' },
        { id: 'planning_research', label: 'Planning research strategy' },
        { id: 'executing_search', label: 'Searching live internet vectors' },
        { id: 'comparing_evidence', label: 'Comparing dynamic evidence' },
        { id: 'reasoning_with_gemini', label: 'Reasoning with Gemini Flash' },
        { id: 'generating_expert_voice', label: 'Rendering Mimesis voice' },
        { id: 'returning_to_story', label: 'Returning to the story' }
    ];

    // Auto-scroll transcript to active turn
    useEffect(() => {
        const el = document.getElementById(`turn-${currentTurnIndex}`);
        if (el && transcriptRef.current) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }, [currentTurnIndex]);

    // Derive elegant string for the UI State
    const getDisplayState = () => {
        if (playbackState === 'setup') return "Ready for Broadcast";
        if (playbackState === 'generating_initial') return "Generating Episode Script...";
        if (playbackState === 'interrupt_input') return "Listening to Mimesis (User Input)";
        if (playbackState === 'researching') {
            const ev = events.length > 0 ? events[events.length - 1] : null;
            if (ev?.event_type === 'executing_search') return "Researching with Parallel";
            if (ev?.event_type === 'reasoning_with_gemini') return "Reasoning with Gemini";
            if (ev?.event_type === 'generating_expert_voice') return "Generating Voice";
            return "Routing Intelligence...";
        }
        if (playbackState === 'resuming') return "Resuming Episode...";
        if (playbackState === 'paused') return "Paused";
        
        const currentSpeaker = turns[currentTurnIndex]?.speaker;
        return currentSpeaker === 'User' ? 'Processing Input' : `Listening to ${currentSpeaker}`;
    };

    const handleConsent = async (approved: boolean) => {
        if (!sessionId) return;
        setAdaptationPayload(null);
        if (approved) {
             setPlaybackState('generating_initial');
             const r = await fetch(`http://localhost:8001/api/sessions/${sessionId}/adapt`, { method: "POST" });
             if (!r.ok) setPlaybackState('paused');
        } else {
             // Treat it as a standard simple question if user rejects the major overhaul
             setPlaybackState('researching');
             const r = await fetch(`http://localhost:8001/api/sessions/${sessionId}/ask`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ 
                    text_content: question + " (Please just answer this briefly without changing the entire topic.)",
                    turn_index: currentTurnIndex,
                    time_seconds: audioRef.current?.currentTime || 0
                })
            });
            if (!r.ok) setPlaybackState('paused');
        }
    };

    return (
        <div className="flex flex-col w-full h-screen bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
            <audio 
                ref={audioRef} 
                onEnded={handleAudioEnded} 
                onTimeUpdate={handleTimeUpdate}
                onWaiting={() => setIsBuffering(true)}
                onPlaying={() => setIsBuffering(false)}
                onStalled={() => setIsBuffering(true)}
                onError={(e) => {
                    console.warn("Media Error tracked. Fallbacking to paused state.", e);
                    setIsBuffering(false);
                    setPlaybackState('paused');
                }} 
            />

            {/* Adaptation Consent Modal - Absolute Overlay */}
            {adaptationPayload && (
                <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md">
                    <div className="bg-zinc-900 border border-indigo-500/50 p-8 rounded-2xl w-full max-w-lg shadow-2xl animate-in fade-in zoom-in-95">
                        <Sparkles className="w-8 h-8 text-indigo-400 mb-4" />
                        <h2 className="text-xl font-medium text-white mb-2">Pardon the Interruption</h2>
                        <p className="text-zinc-400 text-sm mb-6 leading-relaxed">
                            Based on your question, Mimesis thinks you are looking for foundational clarity on this topic before proceeding further.
                        </p>
                        
                        <div className="bg-black/50 rounded-xl p-4 border border-zinc-800 mb-8 space-y-3">
                            <p className="text-sm font-medium text-indigo-300">Proposed Change:</p>
                            <p className="text-[15px] font-light text-zinc-300 italic">
                                "{adaptationPayload.suggested_consent_message}"
                            </p>
                            <div className="text-xs font-mono text-zinc-500 pt-2 border-t border-zinc-800">
                                Directed Action: {adaptationPayload.proposed_adaptation_direction}
                            </div>
                        </div>

                        <div className="flex gap-4">
                            <button onClick={() => handleConsent(false)} className="flex-1 px-4 py-3 rounded-xl border border-zinc-700 text-zinc-300 hover:bg-zinc-800 transition-colors font-medium text-sm">
                                No, stick to the script
                            </button>
                            <button onClick={() => handleConsent(true)} className="flex-1 px-4 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-[0_0_20px_rgba(79,70,229,0.3)] transition-all font-medium text-sm">
                                Yes, adapt the episode
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Top Navigation */}
            <div className="flex justify-between items-center px-8 py-6 border-b border-zinc-900/50 bg-zinc-900/80 backdrop-blur z-10 shrink-0">
                <div className="flex items-center gap-4">
                    <Sparkles className="w-6 h-6 text-indigo-400" />
                    <div>
                         <h1 className="text-xl font-medium tracking-tight text-white">Mimesis Interactive</h1>
                         <div className="flex items-center gap-2 mt-1">
                             {playbackState === 'playing' ? (
                                 <span className="flex h-2 w-2 relative">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                                 </span>
                             ) : (
                                 <span className="h-2 w-2 rounded-full bg-zinc-600"></span>
                             )}
                             <p className="text-xs tracking-wider text-zinc-400 uppercase font-medium">{getDisplayState()}</p>
                         </div>
                    </div>
                </div>
                
                {!sessionId && playbackState === 'setup' && (
                    <button type="button" onClick={() => initPodcast(topicInput || "Agentic Workflows")} className="bg-indigo-600 hover:bg-indigo-500 text-sm font-medium px-6 py-2.5 rounded-full transition-all flex items-center gap-2">
                        <Play className="w-4 h-4" fill="currentColor" /> Play Episode
                    </button>
                )}
                {playbackState === 'generating_initial' && (
                    <div className="text-indigo-400 flex items-center gap-2 text-sm font-medium">
                        <Loader2 className="w-4 h-4 animate-spin" /> Generating
                    </div>
                )}
            </div>

            {/* Main Stage */}
            {(playbackState === 'setup' || playbackState === 'generating_initial') ? (
                <div className="flex-1 flex flex-col items-center justify-center p-12 relative bg-gradient-to-b from-zinc-950 to-black overflow-hidden transform-gpu">
                    <div className="absolute inset-0 flex items-center justify-center opacity-[0.02] pointer-events-none">
                         <RadioReceiver className="w-[800px] h-[800px]" />
                    </div>
                    
                    <div className="z-10 text-center w-full max-w-2xl animate-in fade-in slide-in-from-bottom-8 duration-700">
                        <Sparkles className="w-10 h-10 text-indigo-500 mx-auto mb-4 animate-pulse opacity-80" />
                        <h1 className="text-4xl font-semibold mb-3 tracking-tight text-white drop-shadow-sm">Mimesis Interactive</h1>
                        <p className="text-zinc-400 text-[17px] tracking-wide mb-10">An autonomous, seamlessly grounded agentic podcast.</p>
                        
                        {playbackState === 'setup' && !sessionId ? (
                            <div className="bg-zinc-900/60 backdrop-blur-xl border border-zinc-800/80 p-8 rounded-3xl shadow-2xl space-y-6">
                                <h3 className="text-sm font-medium text-zinc-300 text-left tracking-wide">What topic do you want to explore?</h3>
                                
                                <form onSubmit={(e) => { e.preventDefault(); if(topicInput.trim()) initPodcast(topicInput); }} className="flex gap-3">
                                    <input 
                                       type="text" 
                                       value={topicInput} 
                                       onChange={e => setTopicInput(e.target.value)} 
                                       placeholder="Enter a custom topic..." 
                                       className="flex-1 bg-black/40 border border-zinc-800 rounded-xl px-5 py-3 text-[15px] outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition-all font-medium text-white placeholder:text-zinc-600 placeholder:font-light shadow-inner"
                                    />
                                    <button type="submit" disabled={!topicInput.trim()} className="bg-indigo-600 hover:bg-indigo-500 px-8 rounded-xl disabled:opacity-50 text-white font-semibold shadow-lg shadow-indigo-600/20 transition-transform active:scale-95 flex items-center gap-2">
                                        <Play className="w-4 h-4 ml-0.5" fill="currentColor"/> Generate
                                    </button>
                                </form>

                                <div className="pt-5 border-t border-zinc-800/60">
                                    <p className="text-xs text-zinc-500 uppercase tracking-widest font-mono mb-4 text-left">Trending Explorations</p>
                                    <div className="flex flex-wrap gap-2.5">
                                        {["Agentic Workflows", "Future of AI Agents", "Next.js 15 Features", "Serverless Architecture"].map(t => (
                                            <button 
                                                type="button" 
                                                key={t} 
                                                onClick={() => setTopicInput(t)} 
                                                className={`text-[13px] font-medium px-4 py-2 rounded-full transition-all border ${topicInput === t ? 'bg-indigo-600/10 border-indigo-500/50 text-indigo-300 shadow-[0_0_15px_rgba(99,102,241,0.15)] scale-[1.02]' : 'bg-zinc-800/30 hover:bg-zinc-800 text-zinc-400 border-zinc-700/50 hover:border-zinc-600'}`}
                                            >
                                                {t}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="bg-zinc-900/60 backdrop-blur-xl border border-zinc-800/80 p-8 rounded-3xl shadow-2xl flex flex-col items-center animate-in fade-in slide-in-from-bottom-4">
                                <div className="text-indigo-400 flex items-center gap-3 text-lg font-medium mb-6">
                                    <Loader2 className="w-5 h-5 animate-spin" /> Booting Mimesis Live Engine...
                                </div>
                                <div className="w-full max-w-sm text-left">
                                    {renderProgressChecklist(GENERATION_STAGES)}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            ) : (
            <div className="flex-1 flex overflow-hidden animate-in fade-in duration-500">
                
                {/* Visualizer & Left Controls */}
                <div className="h-full w-3/5 flex flex-col items-center justify-center p-12 relative bg-gradient-to-b from-zinc-900 to-black">
                    
                    {/* Abstract Album Art / Visualizer */}
                    <div className="w-80 h-80 rounded-2xl bg-zinc-900 shadow-2xl relative overflow-hidden flex items-center justify-center border border-zinc-800/50">
                         {playbackState === 'playing' && !isBuffering ? (
                             <div className="absolute inset-0 bg-indigo-500/10 animate-pulse"></div>
                         ) : null}
                         {isBuffering && <Loader2 className="absolute top-6 right-6 w-6 h-6 animate-spin text-zinc-600" />}
                         <RadioReceiver className={`w-24 h-24 ${playbackState === 'playing' ? 'text-indigo-400' : 'text-zinc-700'}`} />
                    </div>

                    <div className="mt-12 text-center w-full max-w-md">
                        {playbackState === 'researching' && renderProgressChecklist(QUESTION_STAGES)}
                        {(playbackState === 'playing' || playbackState === 'paused' || playbackState === 'interrupt_input' || playbackState === 'resuming') && turns[currentTurnIndex] && (
                            <div className="animate-in fade-in slide-in-from-bottom-2">
                                <h2 className="text-2xl font-semibold mb-1">
                                    {turns[currentTurnIndex].speaker === 'Host' ? 'The Host' : 'Mimesis'}
                                </h2>
                                <p className="text-zinc-500 text-sm tracking-wide">
                                    {turns[currentTurnIndex].speaker === 'Host' ? 'Leading the broadcast' : 'Systems Expert'}
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full max-w-md mt-8 flex flex-col gap-3">
                        <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden w-full relative">
                            <div className="absolute top-0 left-0 h-full bg-indigo-500 rounded-full transition-all duration-300" style={{ width: `${progress}%` }}></div>
                        </div>
                        <div className="flex justify-between text-xs font-mono text-zinc-500">
                            <span>{formatTime(currentTime)}</span>
                            <span>{formatTime(duration)}</span>
                        </div>
                    </div>

                    {/* Playback Controls */}
                    <div className="flex items-center gap-8 mt-6">
                        <button type="button" className="text-zinc-400 hover:text-white transition-colors"><Rewind className="w-6 h-6" /></button>
                        
                        <button 
                            type="button"
                            onClick={() => {
                                if (playbackState === 'playing') {
                                    audioRef.current?.pause();
                                    setPlaybackState('paused');
                                } else if (playbackState === 'paused' && audioRef.current) {
                                    audioRef.current.play();
                                    setPlaybackState('playing');
                                }
                            }}
                            className="bg-white text-black p-4 rounded-full hover:scale-105 transition-transform"
                        >
                            {playbackState === 'playing' ? <Pause className="w-6 h-6" fill="currentColor" /> : <Play className="w-6 h-6 ml-0.5" fill="currentColor" />}
                        </button>

                        <button type="button" className="text-zinc-400 hover:text-white transition-colors"><FastForward className="w-6 h-6" /></button>
                    </div>

                    {/* The Interruption Control */}
                    {sessionId && (
                        <div className="mt-12 w-full max-w-md">
                            {playbackState === 'interrupt_input' ? (
                                <div className="animate-in fade-in slide-in-from-bottom-4">
                                    <form onSubmit={submitQuestion} className="bg-zinc-900 border border-indigo-500/50 rounded-xl flex overflow-hidden shadow-2xl p-2 mb-4">
                                        <input 
                                           type="text" 
                                           autoFocus
                                           value={question} 
                                           onChange={e => setQuestion(e.target.value)}
                                           placeholder="Ask a clarifying question..." 
                                           className="flex-1 bg-transparent px-4 py-2 outline-none text-sm placeholder:text-zinc-500"
                                        />
                                        <button type="submit" disabled={!question.trim()} className="bg-indigo-600 px-4 py-2 rounded-lg hover:bg-indigo-500 transition-colors disabled:opacity-50">
                                            <Send className="w-4 h-4" />
                                        </button>
                                    </form>
                                    <div className="flex flex-wrap gap-2 justify-center">
                                        {["Wait, why is that important?", "Can you explain that deeper?", "Give me a real-world example."].map(q => (
                                            <button type="button" key={q} onClick={() => setQuestion(q)} className="text-xs bg-zinc-800 hover:bg-zinc-700 text-zinc-300 px-3 py-1.5 rounded-full transition-colors border border-zinc-700">
                                                {q}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            ) : (
                                <button 
                                    type="button"
                                    onClick={triggerInterrupt}
                                    disabled={playbackState === 'researching'}
                                    className="w-full flex items-center justify-center gap-2 bg-zinc-900/50 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 py-3 rounded-xl transition-all font-medium disabled:opacity-50"
                                >
                                    <MessageCircle className="w-4 h-4 text-indigo-400" /> Ask Mimesis
                                </button>
                            )}
                        </div>
                    )}
                    {/* End Left Controls Column */}
                </div>

                {/* Right Context & Transcript (Lyrics style) */}
                <div className="h-full w-2/5 flex flex-col border-l border-zinc-900 bg-zinc-950">
                     
                     <div className="h-1/2 overflow-hidden border-b border-zinc-900 relative">
                         <div className="absolute top-0 w-full h-12 bg-gradient-to-b from-zinc-950 to-transparent z-10"></div>
                         <ScrollArea className="h-full px-12 py-16" ref={transcriptRef}>
                             <div className="space-y-12 pb-32">
                                 {turns.map((t, idx) => (
                                     <div key={idx} id={`turn-${idx}`} className={`transition-all duration-500 ${currentTurnIndex === idx ? 'opacity-100 scale-100' : 'opacity-40 scale-95 blur-[0.5px]'}`}>
                                        <div className="flex items-center gap-3 mb-3 text-sm font-medium tracking-wide">
                                            {t.speaker === 'User' ? (
                                                <span className="text-zinc-500 flex items-center gap-2"><User className="w-4 h-4"/> You Asked:</span>
                                            ) : (
                                                <span className={t.speaker === 'Host' ? 'text-indigo-400' : 'text-emerald-400'}>{t.speaker}</span>
                                            )}
                                        </div>
                                        <p className={`text-xl leading-relaxed whitespace-pre-wrap ${currentTurnIndex === idx ? 'text-white' : 'text-zinc-400'}`}>
                                            {t.text_content}
                                        </p>
                                     </div>
                                 ))}
                             </div>
                         </ScrollArea>
                         <div className="absolute bottom-0 w-full h-12 bg-gradient-to-t from-zinc-950 to-transparent z-10"></div>
                     </div>

                     {/* Live Parallel Evidence Viewer */}
                     <div className="h-1/2 p-8 bg-black/20 flex flex-col overflow-hidden">
                         <h3 className="text-xs uppercase tracking-widest text-zinc-500 font-mono mb-6 flex items-center gap-2">
                             <Search className="w-3.5 h-3.5" /> Background Intelligence Grid
                         </h3>
                         
                         {researchEvidence.length === 0 ? (
                             <div className="flex-1 flex flex-col items-center justify-center opacity-30 text-center">
                                 <Search className="w-8 h-8 mb-4 stroke-[1.5]" />
                                 <p className="text-sm font-light">Grounding evidence will stream here conditionally if you interrupt.</p>
                             </div>
                         ) : (
                             <ScrollArea className="flex-1 pr-6">
                                 <div className="space-y-8 pb-12">
                                     {researchEvidence.map((ev, i) => (
                                         <div key={i} className="bg-zinc-900/40 rounded-xl p-5 border border-zinc-800">
                                            <div className="text-sm font-mono text-indigo-300 mb-4 bg-indigo-900/20 inline-block px-3 py-1 rounded">
                                                {">"} {ev.query}
                                            </div>
                                            <div className="space-y-4">
                                                {ev.sources.map((src: any, j: number) => (
                                                    <div key={j} className="pl-4 border-l-[3px] border-zinc-700">
                                                        <div className="text-sm font-medium text-zinc-200 mb-1">{src.title}</div>
                                                        <div className="text-xs text-zinc-500 leading-relaxed font-light">{src.retrieved_content}</div>
                                                    </div>
                                                ))}
                                            </div>
                                         </div>
                                     ))}
                                 </div>
                             </ScrollArea>
                         )}
                     </div>

                </div>
            </div>
            )}
        </div>
    );
}
