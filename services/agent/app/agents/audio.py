"""Audio Agent for generating TTS and assembling FFmpeg recordings."""

import os
from app.domain.models import PodcastSession
from app.providers.media import GeminiTTSProvider

class AudioAgent:
    def __init__(self):
        self.tts = GeminiTTSProvider()

    async def generate_tts(self, session: PodcastSession, on_turn_ready=None) -> PodcastSession:
        """Invokes TTS for all recent expert conversational turns that lack audio."""
        
        try:
             # Ensure media dir exists
             media_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "media"))
             os.makedirs(media_dir, exist_ok=True)

             import asyncio
             sem = asyncio.Semaphore(10)

             async def _generate_audio_for_turn(turn):
                 async with sem:
                     if turn.speaker != "User" and not turn.audio_path:
                         voice_target = "Aoede" if turn.speaker == "Host" else "Kore"
                         # Invoke real TTS
                         audio_asset = await self.tts.generate_speech(turn.text_content, voice=voice_target)
                         
                         if audio_asset.raw_bytes:
                             artifact_path = os.path.join(media_dir, audio_asset.filename)
                             with open(artifact_path, "wb") as f:
                                 f.write(audio_asset.raw_bytes)
                             
                             turn.audio_path = f"/api/media/{audio_asset.filename}"
                             if on_turn_ready:
                                 on_turn_ready()

             tasks = [_generate_audio_for_turn(turn) for turn in session.turns]
             await asyncio.gather(*tasks)
                         
        except Exception as e:
             from app.core.logging import get_logger
             get_logger(__name__).error("fatal_tts_error_bypassed", error=str(e))
             session.error_message = f"TTS Audio generation failed: {e}"
             
        return session

    async def generate_background_score(self, session: PodcastSession, topic: str) -> None:
        """Fire-and-forget background job to generate Lyria music, saving to session state."""
        try:
             from app.providers.media import LyriaProvider
             import os
             
             provider = LyriaProvider()
             prompt = f"Ambient, lo-fi, chill background score for an intellectual podcast about {topic}"
             asset = await provider.generate_music(prompt, duration_seconds=120, mood="intellectual")
             
             media_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "media"))
             os.makedirs(media_dir, exist_ok=True)
             
             if asset.raw_bytes:
                 path = os.path.join(media_dir, asset.filename)
                 with open(path, "wb") as f:
                     f.write(asset.raw_bytes)
                 
                 session.background_music_path = f"/api/media/{asset.filename}"
                 from app.core.logging import get_logger
                 get_logger(__name__).info("lyria_background_score_ready", session_id=session.session_id)
        except Exception as e:
             from app.core.logging import get_logger
             get_logger(__name__).warning("lyria_background_score_failed", err=str(e))
             # Fails gracefully without breaking podcast TTS flow
