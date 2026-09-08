"use client";

import { PodcastStudio } from "./PodcastStudio";

export function StudioClient() {
  return (
    <div className="flex h-screen w-full bg-zinc-950 text-zinc-100 overflow-hidden">
      <PodcastStudio />
    </div>
  );
}
