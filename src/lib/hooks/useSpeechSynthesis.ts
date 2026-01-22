import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Configuration options for the speech synthesis hook.
 */
interface UseSpeechSynthesisOptions {
  /** Specific voice to use for synthesis */
  voice?: SpeechSynthesisVoice | null;
  /** Speech rate (0.1 to 10, default: 1) */
  rate?: number;
  /** Voice pitch (0 to 2, default: 1) */
  pitch?: number;
  /** Callback when speech ends */
  onEnd?: () => void;
  /** Callback when speech starts */
  onStart?: () => void;
}

/**
 * Hook for browser-native text-to-speech using the Web Speech API.
 * 
 * Provides a fallback TTS solution when Azure Speech is not available.
 * Automatically selects high-quality English voices when available.
 * 
 * @param options - Configuration options for speech synthesis
 * @returns Object with TTS controls and state
 * 
 * @example
 * ```tsx
 * const { speak, stop, isSpeaking, isSupported, voices } = useSpeechSynthesis({
 *   onEnd: () => console.log("Finished speaking"),
 *   rate: 1.1,
 * });
 * 
 * const handleSpeak = () => {
 *   if (isSupported) {
 *     speak("Hello, this is a test message.");
 *   }
 * };
 * ```
 */
export const useSpeechSynthesis = (options: UseSpeechSynthesisOptions = {}) => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    setIsSupported("speechSynthesis" in window);

    if ("speechSynthesis" in window) {
      const loadVoices = () => {
        const availableVoices = window.speechSynthesis.getVoices();
        setVoices(availableVoices);
      };

      loadVoices();
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }

    return () => {
      window.speechSynthesis?.cancel();
    };
  }, []);

  /**
   * Speaks the provided text using text-to-speech.
   * Cancels any ongoing speech before starting.
   * 
   * @param text - The text to speak
   */
  const speak = useCallback(
    (text: string): void => {
      if (!isSupported || !text) return;

      // Cancel any ongoing speech
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utteranceRef.current = utterance;

      // Find a good English voice
      const englishVoices = voices.filter(
        (v) => v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Microsoft") || v.name.includes("Samantha"))
      );
      utterance.voice = options.voice || englishVoices[0] || voices.find((v) => v.lang.startsWith("en")) || null;
      utterance.rate = options.rate ?? 1;
      utterance.pitch = options.pitch ?? 1;

      utterance.onstart = () => {
        setIsSpeaking(true);
        options.onStart?.();
      };

      utterance.onend = () => {
        setIsSpeaking(false);
        options.onEnd?.();
      };

      utterance.onerror = (event) => {
        console.error("Speech synthesis error:", event);
        setIsSpeaking(false);
      };

      window.speechSynthesis.speak(utterance);
    },
    [isSupported, voices, options]
  );

  /**
   * Stops any ongoing speech synthesis.
   */
  const stop = useCallback((): void => {
    if (isSupported) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, [isSupported]);

  /**
   * Pauses the current speech synthesis.
   */
  const pause = useCallback((): void => {
    if (isSupported) {
      window.speechSynthesis.pause();
    }
  }, [isSupported]);

  /**
   * Resumes paused speech synthesis.
   */
  const resume = useCallback((): void => {
    if (isSupported) {
      window.speechSynthesis.resume();
    }
  }, [isSupported]);

  return {
    /** Whether speech is currently being spoken */
    isSpeaking,
    /** Whether the browser supports speech synthesis */
    isSupported,
    /** Available speech synthesis voices */
    voices,
    /** Speaks the provided text */
    speak,
    /** Stops current speech */
    stop,
    /** Pauses current speech */
    pause,
    /** Resumes paused speech */
    resume,
  };
};
