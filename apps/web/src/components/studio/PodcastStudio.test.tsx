import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PodcastStudio } from '../PodcastStudio';

describe('PodcastStudio Core Player Testing', () => {
  beforeEach(() => {
    // Mock HTML5 Audio element behavior
    window.HTMLMediaElement.prototype.play = jest.fn();
    window.HTMLMediaElement.prototype.pause = jest.fn();
    global.fetch = jest.fn() as jest.Mock;
  });

  it('verifies automatic sequential playback and speaker transitions', async () => {
    // Setup mock network for initial podcast generation fetching 2 turns
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      json: async () => ({ session_id: "s1", turns: [{speaker: 'Host'}, {speaker: 'Expert'}] })
    });

    render(<PodcastStudio />);
    fireEvent.click(screen.getByText('Play Episode'));
    
    // Test transition from Generating to Playing
    await waitFor(() => expect(screen.getByText(/Listening to Host/i)).toBeInTheDocument());
    
    // Simulate Host audio finishing organically (triggering onEnded)
    const audioEl = document.querySelector('audio');
    fireEvent.ended(audioEl!);
    
    // Test speaker transition automation without human interaction
    await waitFor(() => expect(screen.getByText(/Listening to Expert/i)).toBeInTheDocument());
  });

  it('verifies seamless interruption/pause/resume workflow', async () => {
    // Test the specific "Ask Mimesis" -> Researching -> Resuming lifecycle
    render(<PodcastStudio />);
    
    // Fast forward to playing state
    fireEvent.click(screen.getByText('Ask Mimesis'));
    
    // System should aggressively pause HTMLAudioElement
    expect(window.HTMLMediaElement.prototype.pause).toHaveBeenCalled();
    
    // Input state transition
    expect(screen.getByPlaceholderText(/Ask a clarifying question/i)).toBeInTheDocument();
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Why is that important?' } });
    fireEvent.click(screen.getByRole('button'));
    
    // Test graceful network failure recovery
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error("Network Error"));
    await waitFor(() => expect(screen.getByText(/Paused/i)).toBeInTheDocument()); // Fallback state instead of crash
  });

});
