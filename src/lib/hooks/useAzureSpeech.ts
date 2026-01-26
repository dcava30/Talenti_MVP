import { useState, useEffect, useRef, useCallback } from "react";
import { apiClient } from "@/lib/apiClient";
import * as SpeechSDK from "microsoft-cognitiveservices-speech-sdk";

/**
 * Configuration options for the Azure Speech hook.
 */
interface UseAzureSpeechOptions {
  /** Callback when speech recognition produces a result */
  onSpeechResult?: (text: string, isFinal: boolean) => void;
  /** Callback when speech recognition session ends */
  onSpeechEnd?: () => void;
  /** Callback when speech recognition starts */
  onSpeechStart?: () => void;
  /** Callback when text-to-speech completes */
  onTTSEnd?: () => void;
  /** Callback when text-to-speech starts */
  onTTSStart?: () => void;
  /** Callback when an error occurs */
  onError?: (error: string) => void;
  /** Azure voice name for TTS (default: "en-AU-NatashaNeural") */
  voice?: string;
}

/**
 * Azure Speech service authentication token.
 */
interface SpeechToken {
  /** JWT access token */
  token: string;
  /** Azure region (e.g., "australiaeast") */
  region: string;
  /** Token lifetime in seconds */
  expiresIn: number;
}

/**
 * Hook for Azure Cognitive Services Speech integration.
 * 
 * Provides high-quality speech-to-text and text-to-speech using
 * Azure's neural speech services. Features include:
 * - Real-time speech recognition with interim results
 * - High-quality neural TTS voices
 * - Automatic token refresh
 * - Low-latency configuration
 * 
 * @param options - Configuration options for speech services
 * @returns Object with speech controls and state
 * 
 * @example
 * ```tsx
 * const {
 *   isListening,
 *   isSpeaking,
 *   transcript,
 *   startListening,
 *   stopListening,
 *   speak,
 *   initialize,
 * } = useAzureSpeech({
 *   onSpeechResult: (text, isFinal) => {
 *     if (isFinal) handleFinalTranscript(text);
 *   },
 *   onTTSEnd: () => startListening(),
 *   voice: "en-US-JennyNeural",
 * });
 * 
 * // Initialize on mount
 * useEffect(() => {
 *   initialize();
 * }, []);
 * 
 * // Speak AI response
 * const handleAIResponse = (text: string) => {
 *   speak(text);
 * };
 * ```
 */
export const useAzureSpeech = (options: UseAzureSpeechOptions = {}) => {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [isInitialized, setIsInitialized] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const speechConfigRef = useRef<SpeechSDK.SpeechConfig | null>(null);
  const recognizerRef = useRef<SpeechSDK.SpeechRecognizer | null>(null);
  const synthesizerRef = useRef<SpeechSDK.SpeechSynthesizer | null>(null);
  const audioConfigRef = useRef<SpeechSDK.AudioConfig | null>(null);
  const tokenExpiryRef = useRef<number>(0);

  const voice = options.voice || "en-AU-NatashaNeural";

  /**
   * Fetches an Azure Speech access token from the backend.
   * 
   * @returns The speech token on success, or null on failure
   */
  const fetchToken = useCallback(async (): Promise<SpeechToken | null> => {
    try {
      console.log("[useAzureSpeech] Fetching speech token...");
      const data = await apiClient.post<SpeechToken>("/api/azure/speech/token");

      console.log("[useAzureSpeech] Token obtained for region:", data.region);
      tokenExpiryRef.current = Date.now() + (data.expiresIn * 1000);
      return data as SpeechToken;
    } catch (err) {
      console.error("[useAzureSpeech] Token fetch exception:", err);
      setError(err instanceof Error ? err.message : "Failed to fetch token");
      return null;
    }
  }, []);

  /**
   * Initializes the Azure Speech SDK with a fresh token.
   * 
   * @returns true on success, false on failure
   */
  const initialize = useCallback(async (): Promise<boolean> => {
    try {
      const tokenData = await fetchToken();
      if (!tokenData) return false;

      console.log("[useAzureSpeech] Initializing speech config...");
      
      speechConfigRef.current = SpeechSDK.SpeechConfig.fromAuthorizationToken(
        tokenData.token,
        tokenData.region
      );
      
      // Configure for low latency
      speechConfigRef.current.speechRecognitionLanguage = "en-US";
      speechConfigRef.current.speechSynthesisVoiceName = voice;
      speechConfigRef.current.setProperty(
        SpeechSDK.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs,
        "5000"
      );
      speechConfigRef.current.setProperty(
        SpeechSDK.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs,
        "1000"
      );

      setIsInitialized(true);
      setError(null);
      console.log("[useAzureSpeech] Initialized successfully");
      return true;
    } catch (err) {
      console.error("[useAzureSpeech] Initialization error:", err);
      setError(err instanceof Error ? err.message : "Failed to initialize");
      return false;
    }
  }, [fetchToken, voice]);

  /**
   * Ensures the token is valid, refreshing if necessary.
   * 
   * @returns true if token is valid or was refreshed successfully
   */
  const ensureValidToken = useCallback(async (): Promise<boolean> => {
    if (tokenExpiryRef.current - Date.now() < 60000) {
      console.log("[useAzureSpeech] Token expiring soon, refreshing...");
      return await initialize();
    }
    return true;
  }, [initialize]);

  /**
   * Starts continuous speech recognition.
   * Initializes if not already done.
   */
  const startListening = useCallback(async (): Promise<void> => {
    if (!speechConfigRef.current) {
      const initialized = await initialize();
      if (!initialized) return;
    }

    await ensureValidToken();

    try {
      console.log("[useAzureSpeech] Starting speech recognition...");
      
      // Create audio config from default microphone
      audioConfigRef.current = SpeechSDK.AudioConfig.fromDefaultMicrophoneInput();
      
      recognizerRef.current = new SpeechSDK.SpeechRecognizer(
        speechConfigRef.current!,
        audioConfigRef.current
      );

      // Handle recognition events
      recognizerRef.current.recognizing = (_, event) => {
        console.log("[useAzureSpeech] Recognizing:", event.result.text);
        setInterimTranscript(event.result.text);
        options.onSpeechResult?.(event.result.text, false);
      };

      recognizerRef.current.recognized = (_, event) => {
        if (event.result.reason === SpeechSDK.ResultReason.RecognizedSpeech) {
          console.log("[useAzureSpeech] Recognized:", event.result.text);
          setTranscript(prev => prev + " " + event.result.text);
          setInterimTranscript("");
          options.onSpeechResult?.(event.result.text, true);
        }
      };

      recognizerRef.current.canceled = (_, event) => {
        console.log("[useAzureSpeech] Recognition canceled:", event.reason);
        if (event.reason === SpeechSDK.CancellationReason.Error) {
          setError(event.errorDetails);
          options.onError?.(event.errorDetails);
        }
      };

      recognizerRef.current.sessionStopped = () => {
        console.log("[useAzureSpeech] Session stopped");
        setIsListening(false);
        options.onSpeechEnd?.();
      };

      // Start continuous recognition
      await recognizerRef.current.startContinuousRecognitionAsync(
        () => {
          console.log("[useAzureSpeech] Recognition started");
          setIsListening(true);
          options.onSpeechStart?.();
        },
        (err) => {
          console.error("[useAzureSpeech] Failed to start recognition:", err);
          setError(err);
          options.onError?.(err);
        }
      );
    } catch (err) {
      console.error("[useAzureSpeech] Start listening error:", err);
      setError(err instanceof Error ? err.message : "Failed to start listening");
    }
  }, [initialize, ensureValidToken, options]);

  /**
   * Stops continuous speech recognition.
   */
  const stopListening = useCallback(async (): Promise<void> => {
    if (recognizerRef.current) {
      try {
        await recognizerRef.current.stopContinuousRecognitionAsync(
          () => {
            console.log("[useAzureSpeech] Recognition stopped");
            setIsListening(false);
          },
          (err) => {
            console.error("[useAzureSpeech] Failed to stop recognition:", err);
          }
        );
      } catch (err) {
        console.error("[useAzureSpeech] Stop listening error:", err);
      }
    }
    setIsListening(false);
  }, []);

  /**
   * Speaks text using Azure neural TTS.
   * 
   * @param text - The text to speak
   */
  const speak = useCallback(async (text: string): Promise<void> => {
    if (!speechConfigRef.current) {
      const initialized = await initialize();
      if (!initialized) return;
    }

    await ensureValidToken();

    try {
      console.log("[useAzureSpeech] Starting TTS:", text.substring(0, 50) + "...");
      
      // Create synthesizer with speaker output
      const audioOutput = SpeechSDK.AudioConfig.fromDefaultSpeakerOutput();
      synthesizerRef.current = new SpeechSDK.SpeechSynthesizer(
        speechConfigRef.current!,
        audioOutput
      );

      setIsSpeaking(true);
      options.onTTSStart?.();

      synthesizerRef.current.speakTextAsync(
        text,
        (result) => {
          if (result.reason === SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
            console.log("[useAzureSpeech] TTS completed");
          } else {
            console.error("[useAzureSpeech] TTS failed:", result.errorDetails);
            setError(result.errorDetails);
            options.onError?.(result.errorDetails);
          }
          setIsSpeaking(false);
          options.onTTSEnd?.();
          synthesizerRef.current?.close();
        },
        (err) => {
          console.error("[useAzureSpeech] TTS error:", err);
          setError(err);
          setIsSpeaking(false);
          options.onError?.(err);
          synthesizerRef.current?.close();
        }
      );
    } catch (err) {
      console.error("[useAzureSpeech] Speak error:", err);
      setError(err instanceof Error ? err.message : "Failed to speak");
      setIsSpeaking(false);
    }
  }, [initialize, ensureValidToken, options]);

  /**
   * Stops any ongoing TTS playback.
   */
  const stopSpeaking = useCallback((): void => {
    if (synthesizerRef.current) {
      synthesizerRef.current.close();
      synthesizerRef.current = null;
    }
    setIsSpeaking(false);
  }, []);

  /**
   * Resets both final and interim transcripts.
   */
  const resetTranscript = useCallback((): void => {
    setTranscript("");
    setInterimTranscript("");
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      console.log("[useAzureSpeech] Cleaning up...");
      recognizerRef.current?.close();
      synthesizerRef.current?.close();
    };
  }, []);

  return {
    /** Whether speech recognition is active */
    isListening,
    /** Whether TTS is playing */
    isSpeaking,
    /** Accumulated final transcript */
    transcript: transcript.trim(),
    /** Current interim transcript */
    interimTranscript,
    /** Whether the SDK is initialized */
    isInitialized,
    /** Error message from the last failed operation */
    error,
    /** Initializes the speech SDK */
    initialize,
    /** Starts continuous speech recognition */
    startListening,
    /** Stops speech recognition */
    stopListening,
    /** Speaks text using TTS */
    speak,
    /** Stops TTS playback */
    stopSpeaking,
    /** Clears all transcripts */
    resetTranscript,
    /** Azure Speech is always supported */
    isSupported: true,
  };
};
