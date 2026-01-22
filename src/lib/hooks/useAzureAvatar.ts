import { useState, useRef, useCallback, useEffect } from "react";
import * as SpeechSDK from "microsoft-cognitiveservices-speech-sdk";
import { supabase } from "@/integrations/supabase/client";

/**
 * Configuration options for the Azure Avatar hook.
 */
interface UseAzureAvatarOptions {
  /** Avatar character name (default: "lisa") */
  character?: string;
  /** Avatar style (default: "casual-sitting") */
  style?: string;
  /** TTS voice name (default: "en-AU-NatashaNeural") */
  voice?: string;
  /** Video output width in pixels (default: 1280) */
  videoWidth?: number;
  /** Video output height in pixels (default: 720) */
  videoHeight?: number;
  /** Callback when avatar connection is established */
  onAvatarStarted?: () => void;
  /** Callback when avatar connection is closed */
  onAvatarStopped?: () => void;
  /** Callback when avatar starts speaking */
  onSpeakingStart?: () => void;
  /** Callback when avatar finishes speaking */
  onSpeakingEnd?: () => void;
  /** Callback when an error occurs */
  onError?: (error: string) => void;
}

/**
 * ICE server configuration for WebRTC connection.
 */
interface IceServerInfo {
  /** TURN/STUN server URLs */
  urls: string[];
  /** Authentication username */
  username: string;
  /** Authentication credential */
  credential: string;
}

/**
 * Hook for Azure AI Avatar integration.
 * 
 * Provides a realistic animated avatar that lip-syncs with speech.
 * Uses WebRTC for video/audio streaming from Azure.
 * 
 * Features:
 * - Photorealistic avatar rendering
 * - Real-time lip sync with TTS
 * - Multiple character and style options
 * - Transparent background support
 * 
 * @param options - Configuration options for the avatar
 * @returns Object with avatar controls and media streams
 * 
 * @example
 * ```tsx
 * const {
 *   isInitialized,
 *   videoStream,
 *   speak,
 *   initialize,
 *   close,
 * } = useAzureAvatar({
 *   character: "lisa",
 *   style: "casual-sitting",
 *   onSpeakingEnd: () => console.log("Avatar finished speaking"),
 * });
 * 
 * // Initialize on mount
 * useEffect(() => {
 *   initialize();
 *   return () => close();
 * }, []);
 * 
 * // Render video stream
 * if (videoStream) {
 *   videoRef.current.srcObject = videoStream;
 * }
 * 
 * // Make avatar speak
 * await speak("Hello! I'm your AI interviewer today.");
 * ```
 */
export const useAzureAvatar = (options: UseAzureAvatarOptions = {}) => {
  const {
    character = "lisa",
    style = "casual-sitting",
    voice = "en-AU-NatashaNeural",
    videoWidth = 1280,
    videoHeight = 720,
    onAvatarStarted,
    onAvatarStopped,
    onSpeakingStart,
    onSpeakingEnd,
    onError,
  } = options;

  const [isInitialized, setIsInitialized] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [videoStream, setVideoStream] = useState<MediaStream | null>(null);
  const [audioStream, setAudioStream] = useState<MediaStream | null>(null);

  const avatarSynthesizerRef = useRef<SpeechSDK.AvatarSynthesizer | null>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const speechConfigRef = useRef<SpeechSDK.SpeechConfig | null>(null);

  /**
   * Fetches ICE server configuration from Azure.
   * 
   * @param region - Azure region
   * @param authToken - Authorization token
   * @returns ICE server info on success, or null on failure
   */
  const fetchIceServerInfo = async (region: string, authToken: string): Promise<IceServerInfo | null> => {
    try {
      const response = await fetch(
        `https://${region}.tts.speech.microsoft.com/cognitiveservices/avatar/relay/token/v1`,
        {
          method: "GET",
          headers: {
            "Authorization": `Bearer ${authToken}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch ICE server info: ${response.status}`);
      }

      const data = await response.json();
      return {
        urls: data.urls || [data.url],
        username: data.username,
        credential: data.credential,
      };
    } catch (err) {
      console.error("[AzureAvatar] Failed to fetch ICE server info:", err);
      return null;
    }
  };

  /**
   * Initializes the avatar connection.
   * 
   * Sets up WebRTC peer connection, creates avatar synthesizer,
   * and establishes the video/audio stream.
   * 
   * @returns true on success, false on failure
   */
  const initialize = useCallback(async (): Promise<boolean> => {
    if (isInitialized || isConnecting) return isInitialized;

    setIsConnecting(true);
    setError(null);

    try {
      // Fetch speech token from edge function
      const { data: tokenData, error: tokenError } = await supabase.functions.invoke("azure-speech-token");

      if (tokenError || !tokenData?.token || !tokenData?.region) {
        throw new Error(tokenError?.message || "Failed to fetch Azure Speech token");
      }

      const { token, region } = tokenData;

      // Create speech config with the token
      speechConfigRef.current = SpeechSDK.SpeechConfig.fromAuthorizationToken(token, region);
      speechConfigRef.current.speechSynthesisVoiceName = voice;

      // Fetch ICE server info using authorization token
      const iceInfo = await fetchIceServerInfo(region, token);
      if (!iceInfo) {
        throw new Error("Failed to get ICE server configuration");
      }

      // Create WebRTC peer connection
      peerConnectionRef.current = new RTCPeerConnection({
        iceServers: [
          {
            urls: iceInfo.urls.filter((url: string) => url.startsWith("turn")),
            username: iceInfo.username,
            credential: iceInfo.credential,
          },
        ],
      });

      // Handle incoming tracks (video and audio)
      peerConnectionRef.current.ontrack = (event) => {
        console.log("[AzureAvatar] Received track:", event.track.kind);
        
        if (event.track.kind === "video") {
          setVideoStream(event.streams[0]);
        } else if (event.track.kind === "audio") {
          setAudioStream(event.streams[0]);
        }
      };

      // Handle connection state changes
      peerConnectionRef.current.onconnectionstatechange = () => {
        const state = peerConnectionRef.current?.connectionState;
        console.log("[AzureAvatar] Connection state:", state);
        
        if (state === "connected") {
          setIsInitialized(true);
          onAvatarStarted?.();
        } else if (state === "disconnected" || state === "failed") {
          setIsInitialized(false);
          onAvatarStopped?.();
        }
      };

      // Add transceivers for receiving video and audio
      peerConnectionRef.current.addTransceiver("video", { direction: "sendrecv" });
      peerConnectionRef.current.addTransceiver("audio", { direction: "sendrecv" });

      // Create video format
      const videoFormat = new SpeechSDK.AvatarVideoFormat();
      videoFormat.width = videoWidth;
      videoFormat.height = videoHeight;

      // Create avatar config with video format
      const avatarConfig = new SpeechSDK.AvatarConfig(character, style, videoFormat);
      avatarConfig.backgroundColor = "#00000000"; // Transparent background

      // Create avatar synthesizer
      avatarSynthesizerRef.current = new SpeechSDK.AvatarSynthesizer(
        speechConfigRef.current,
        avatarConfig
      );

      // Start avatar connection
      await avatarSynthesizerRef.current.startAvatarAsync(peerConnectionRef.current);
      
      console.log("[AzureAvatar] Avatar started successfully");
      setIsInitialized(true);
      setIsConnecting(false);
      return true;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to initialize avatar";
      console.error("[AzureAvatar] Initialization error:", errorMessage);
      setError(errorMessage);
      setIsConnecting(false);
      onError?.(errorMessage);
      return false;
    }
  }, [character, style, voice, videoWidth, videoHeight, isInitialized, isConnecting, onAvatarStarted, onAvatarStopped, onError]);

  /**
   * Makes the avatar speak plain text.
   * 
   * @param text - The text for the avatar to speak
   * @returns true on success, false on failure
   */
  const speak = useCallback(async (text: string): Promise<boolean> => {
    if (!avatarSynthesizerRef.current || !isInitialized) {
      console.warn("[AzureAvatar] Avatar not initialized");
      return false;
    }

    setIsSpeaking(true);
    onSpeakingStart?.();

    try {
      const result = await avatarSynthesizerRef.current.speakTextAsync(text);

      if (result.reason === SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
        console.log("[AzureAvatar] Speech completed successfully");
        setIsSpeaking(false);
        onSpeakingEnd?.();
        return true;
      } else {
        console.error("[AzureAvatar] Speech failed:", result.reason);
        if (result.reason === SpeechSDK.ResultReason.Canceled) {
          console.error("[AzureAvatar] Synthesis canceled, error code:", result.errorDetails);
        }
        setIsSpeaking(false);
        onSpeakingEnd?.();
        return false;
      }
    } catch (err) {
      console.error("[AzureAvatar] Speak error:", err);
      setIsSpeaking(false);
      onSpeakingEnd?.();
      return false;
    }
  }, [isInitialized, onSpeakingStart, onSpeakingEnd]);

  /**
   * Makes the avatar speak using SSML for advanced control.
   * 
   * @param ssml - SSML markup for speech synthesis
   * @returns true on success, false on failure
   */
  const speakSsml = useCallback(async (ssml: string): Promise<boolean> => {
    if (!avatarSynthesizerRef.current || !isInitialized) {
      console.warn("[AzureAvatar] Avatar not initialized");
      return false;
    }

    setIsSpeaking(true);
    onSpeakingStart?.();

    try {
      const result = await avatarSynthesizerRef.current.speakSsmlAsync(ssml);

      if (result.reason === SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
        setIsSpeaking(false);
        onSpeakingEnd?.();
        return true;
      } else {
        setIsSpeaking(false);
        onSpeakingEnd?.();
        return false;
      }
    } catch (err) {
      console.error("[AzureAvatar] Speak SSML error:", err);
      setIsSpeaking(false);
      onSpeakingEnd?.();
      return false;
    }
  }, [isInitialized, onSpeakingStart, onSpeakingEnd]);

  /**
   * Stops any ongoing avatar speech.
   */
  const stopSpeaking = useCallback(async (): Promise<void> => {
    if (!avatarSynthesizerRef.current) return;

    try {
      await avatarSynthesizerRef.current.stopSpeakingAsync();
      setIsSpeaking(false);
      onSpeakingEnd?.();
    } catch (err) {
      console.error("[AzureAvatar] Stop speaking error:", err);
    }
  }, [onSpeakingEnd]);

  /**
   * Closes the avatar connection and cleans up resources.
   */
  const close = useCallback((): void => {
    if (avatarSynthesizerRef.current) {
      avatarSynthesizerRef.current.close();
      avatarSynthesizerRef.current = null;
    }

    if (peerConnectionRef.current) {
      peerConnectionRef.current.close();
      peerConnectionRef.current = null;
    }

    setVideoStream(null);
    setAudioStream(null);
    setIsInitialized(false);
    setIsSpeaking(false);
    onAvatarStopped?.();
  }, [onAvatarStopped]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      close();
    };
  }, [close]);

  return {
    /** Whether the avatar is fully initialized and connected */
    isInitialized,
    /** Whether the avatar is currently connecting */
    isConnecting,
    /** Whether the avatar is currently speaking */
    isSpeaking,
    /** Error message from the last failed operation */
    error,
    /** MediaStream containing the avatar video */
    videoStream,
    /** MediaStream containing the avatar audio */
    audioStream,
    /** Initializes the avatar connection */
    initialize,
    /** Makes the avatar speak plain text */
    speak,
    /** Makes the avatar speak SSML */
    speakSsml,
    /** Stops current speech */
    stopSpeaking,
    /** Closes the avatar connection */
    close,
  };
};
