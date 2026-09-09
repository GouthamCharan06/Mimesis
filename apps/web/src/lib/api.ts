/**
 * Mimesis API Client and SSE Stream listener.
 */
import { useEffect, useState } from 'react';

const API_BASE = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001'}/api`;
console.log("[Mimesis Boot Config] api.ts initialized. Target API_BASE =>", API_BASE);

export interface ProjectState {
  project_id: string;
  workflow_state: string;
  [key: string]: any; // fallback for complete state
}

export interface AgentEvent {
  event_id: string;
  event_type: string;
  agent_name: string;
  data: Record<string, any>;
  message: string;
  timestamp: string;
}

export interface TrendOpportunity {
  opportunity_id: string;
  title: string;
  description: string;
  user_facing_rationale: string;
  rank: number;
  evaluation: any;
  supporting_evidence: any[];
}

export interface CreativeConcept {
  concept_id: string;
  title: string;
  hook: string;
  creative_format: string;
  target_audience: string;
  trend_abstraction: string;
  rationale: string;
  narrative_structure: string;
  estimated_duration_seconds: number;
  cta: string;
  creative_risks: string[];
  production_direction: string;
}

export const api = {
  async createProject(name: string, mode: 'creator' | 'company') {
    const res = await fetch(`${API_BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, mode }),
    });
    return res.json();
  },

  async getState(projectId: string) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/state`);
    return res.json();
  },

  async submitConversationTurn(projectId: string, message: string) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/conversation`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    return res.json();
  },

  async startResearch(projectId: string) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/research`, {
      method: 'POST',
    });
    return res.json();
  },

  async generateConcepts(projectId: string) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/concepts/generate`, {
      method: 'POST',
    });
    return res.json();
  },

  async submitApproval(projectId: string, decision: 'approved' | 'rejected' | 'revision_requested', conceptId?: string, feedback?: string) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, selected_concept_id: conceptId, feedback }),
    });
    return res.json();
  },

  async submitRevision(projectId: string, targetType: string, targetId: string, requestedChange: string) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/revisions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_type: targetType, target_id: targetId, requested_change: requestedChange }),
    });
    return res.json();
  },

  async resolveDisagreement(projectId: string, revisionId: string, userDecision: string, decisionRationale: string) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/revisions/${revisionId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ revision_id: revisionId, user_decision: userDecision, decision_rationale: decisionRationale }),
    });
    return res.json();
  },

  async generateScript(projectId: string) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/script/generate`, {
      method: 'POST',
    });
    return res.json();
  },

  async getBlueprint(projectId: string) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/blueprint`);
    return res.json();
  },

  async getTranscreationOptions(projectId: string) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/transcreation/options`);
    return res.json();
  },

  async submitVoiceConsent(projectId: string, speakerId: string, consentGiven: boolean, rationale: string) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/consent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ speaker_id: speakerId, consent_given: consentGiven, rationale }),
    });
    return res.json();
  }
};

/**
 * Hook to stream SSE events from a given project.
 */
export function useAgentStream(projectId: string | null, dynamicApiBaseUrl: string = "http://localhost:8001") {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [currentState, setCurrentState] = useState<string>('UNKNOWN');
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    if (!projectId) return;

    const eventSource = new EventSource(`${dynamicApiBaseUrl}/api/sessions/${projectId}/events`);

    eventSource.onopen = () => setIsConnected(true);

    eventSource.onerror = () => {
      setIsConnected(false);
      // Wait to reconnect or leave it to standard EventSource backoff
    };

    // Listen to standard message
    eventSource.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data);
        if (payload.type === 'heartbeat') return;
      } catch (err) { }
    };

    const handleEventPayload = (e: MessageEvent) => {
      try {
        const ev: AgentEvent = JSON.parse(e.data);
        setEvents((prev) => [...prev, ev]);

        if (ev.event_type === 'workflow_state_changed' && ev.data?.new_state) {
          setCurrentState(ev.data.new_state);
        } else if (ev.event_type === 'workflow_state_changed' && ev.data?.state) {
          setCurrentState(ev.data.state);
        }
      } catch (err) { }
    };

    // Register listeners for custom event types
    ['agent_started', 'agent_completed', 'tool_called', 'tool_result',
      'reasoning_summary', 'workflow_state_changed', 'approval_required',
      'asset_generated', 'error', 'completed',
      'preparing_topic', 'structuring_conversation', 'writing_dialogue', 'generating_voices', 'podcast_ready',
      'capturing_context', 'executing_search', 'comparing_evidence', 'reasoning_with_gemini', 'generating_expert_voice', 'returning_to_story'
    ].forEach(type => {
      eventSource.addEventListener(type, handleEventPayload as any);
    });

    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, [projectId]);

  return { events, currentState, isConnected };
}
