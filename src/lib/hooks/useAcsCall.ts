import { useState, useCallback, useRef, useEffect } from 'react';
import {
  CallClient,
  CallAgent,
  Call,
  LocalVideoStream,
  RemoteParticipant,
  CallState,
  DeviceManager,
} from '@azure/communication-calling';
import { AzureCommunicationTokenCredential } from '@azure/communication-common';
import { AcsToken } from './useAcsToken';

/**
 * Possible states of an ACS call.
 */
export type AcsCallState = 
  | 'none'
  | 'connecting'
  | 'ringing'
  | 'connected'
  | 'localHold'
  | 'remoteHold'
  | 'inLobby'
  | 'disconnecting'
  | 'disconnected'
  | 'earlyMedia';

/**
 * Configuration options for the ACS call hook.
 */
export interface UseAcsCallOptions {
  /** Display name shown to other participants (default: "Interview Participant") */
  displayName?: string;
  /** Callback when call state changes */
  onCallStateChange?: (state: AcsCallState) => void;
  /** Callback when a participant joins the call */
  onParticipantJoined?: (participant: RemoteParticipant) => void;
  /** Callback when a participant leaves the call */
  onParticipantLeft?: (participant: RemoteParticipant) => void;
}

/**
 * Return type for the useAcsCall hook.
 */
export interface UseAcsCallReturn {
  /** Current state of the call */
  callState: AcsCallState;
  /** Whether the call client is initialized */
  isInitialized: boolean;
  /** Whether local audio is muted */
  isMuted: boolean;
  /** Whether local video is enabled */
  isVideoOn: boolean;
  /** Error message from the last failed operation */
  error: string | null;
  /** List of remote participants in the call */
  remoteParticipants: RemoteParticipant[];
  /** Initializes the call client with an ACS token */
  initialize: (token: AcsToken) => Promise<boolean>;
  /** Joins an existing group call */
  joinCall: (groupId: string) => Promise<boolean>;
  /** Starts a new call with specified participants */
  startCall: (participantIds: string[]) => Promise<boolean>;
  /** Ends the current call */
  hangup: () => Promise<void>;
  /** Toggles local audio mute state */
  toggleMute: () => Promise<void>;
  /** Toggles local video on/off */
  toggleVideo: () => Promise<void>;
  /** Gets the device manager for camera/mic selection */
  getDeviceManager: () => DeviceManager | null;
  /** Cleans up all ACS resources */
  cleanup: () => void;
}

/**
 * Hook for Azure Communication Services video/audio calling.
 * 
 * Provides full call management including:
 * - Call initialization and joining
 * - Audio/video controls
 * - Participant tracking
 * - Device management
 * 
 * @param options - Configuration options for call behavior
 * @returns Object with call controls and state
 * 
 * @example
 * ```tsx
 * const {
 *   callState,
 *   isInitialized,
 *   isMuted,
 *   isVideoOn,
 *   remoteParticipants,
 *   initialize,
 *   joinCall,
 *   hangup,
 *   toggleMute,
 *   toggleVideo,
 *   cleanup,
 * } = useAcsCall({
 *   displayName: "Candidate",
 *   onCallStateChange: (state) => console.log("Call state:", state),
 *   onParticipantJoined: (p) => console.log("Joined:", p.displayName),
 * });
 * 
 * // Initialize with token from useAcsToken
 * useEffect(() => {
 *   if (token) {
 *     initialize(token).then(() => {
 *       joinCall(interviewGroupId);
 *     });
 *   }
 *   return () => cleanup();
 * }, [token]);
 * 
 * // Render call controls
 * return (
 *   <div>
 *     <button onClick={toggleMute}>{isMuted ? "Unmute" : "Mute"}</button>
 *     <button onClick={toggleVideo}>{isVideoOn ? "Stop Video" : "Start Video"}</button>
 *     <button onClick={hangup}>End Call</button>
 *   </div>
 * );
 * ```
 */
export const useAcsCall = ({
  displayName = 'Interview Participant',
  onCallStateChange,
  onParticipantJoined,
  onParticipantLeft,
}: UseAcsCallOptions = {}): UseAcsCallReturn => {
  const [callState, setCallState] = useState<AcsCallState>('none');
  const [isInitialized, setIsInitialized] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoOn, setIsVideoOn] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [remoteParticipants, setRemoteParticipants] = useState<RemoteParticipant[]>([]);

  const callClientRef = useRef<CallClient | null>(null);
  const callAgentRef = useRef<CallAgent | null>(null);
  const callRef = useRef<Call | null>(null);
  const deviceManagerRef = useRef<DeviceManager | null>(null);
  const localVideoStreamRef = useRef<LocalVideoStream | null>(null);
  const tokenCredentialRef = useRef<AzureCommunicationTokenCredential | null>(null);

  /**
   * Updates call state and notifies callback.
   */
  const updateCallState = useCallback((state: CallState): void => {
    const mappedState = state as AcsCallState;
    console.log(`[useAcsCall] Call state changed: ${mappedState}`);
    setCallState(mappedState);
    onCallStateChange?.(mappedState);
  }, [onCallStateChange]);

  /**
   * Handles participant join/leave events.
   */
  const handleParticipantsUpdated = useCallback((args: { added: RemoteParticipant[]; removed: RemoteParticipant[] }): void => {
    args.added.forEach(participant => {
      console.log(`[useAcsCall] Participant joined: ${participant.displayName}`);
      onParticipantJoined?.(participant);
    });

    args.removed.forEach(participant => {
      console.log(`[useAcsCall] Participant left: ${participant.displayName}`);
      onParticipantLeft?.(participant);
    });

    setRemoteParticipants(prev => {
      const updated = prev.filter(p => !args.removed.includes(p));
      return [...updated, ...args.added];
    });
  }, [onParticipantJoined, onParticipantLeft]);

  /**
   * Initializes the ACS call client with an access token.
   * 
   * @param token - ACS access token from useAcsToken
   * @returns true on success, false on failure
   */
  const initialize = useCallback(async (token: AcsToken): Promise<boolean> => {
    try {
      console.log('[useAcsCall] Initializing call client...');
      setError(null);

      // Create token credential
      tokenCredentialRef.current = new AzureCommunicationTokenCredential(token.token);

      // Create call client
      callClientRef.current = new CallClient();

      // Get device manager
      deviceManagerRef.current = await callClientRef.current.getDeviceManager();
      await deviceManagerRef.current.askDevicePermission({ audio: true, video: true });

      // Create call agent
      callAgentRef.current = await callClientRef.current.createCallAgent(
        tokenCredentialRef.current,
        { displayName }
      );

      // Listen for incoming calls
      callAgentRef.current.on('incomingCall', async (args) => {
        console.log('[useAcsCall] Incoming call received');
        // Auto-accept for interview context
        callRef.current = await args.incomingCall.accept();
        setupCallListeners(callRef.current);
      });

      setIsInitialized(true);
      console.log('[useAcsCall] Call client initialized successfully');
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to initialize call client';
      console.error('[useAcsCall] Initialization error:', message);
      setError(message);
      return false;
    }
  }, [displayName]);

  /**
   * Sets up event listeners on a call instance.
   */
  const setupCallListeners = useCallback((call: Call): void => {
    call.on('stateChanged', () => {
      updateCallState(call.state);
      
      if (call.state === 'Disconnected') {
        setRemoteParticipants([]);
        callRef.current = null;
      }
    });

    call.on('isMutedChanged', () => {
      setIsMuted(call.isMuted);
    });

    call.on('remoteParticipantsUpdated', handleParticipantsUpdated);

    // Set initial participants
    setRemoteParticipants([...call.remoteParticipants]);
    updateCallState(call.state);
  }, [updateCallState, handleParticipantsUpdated]);

  /**
   * Joins an existing group call.
   * 
   * @param groupId - The group call ID to join
   * @returns true on success, false on failure
   */
  const joinCall = useCallback(async (groupId: string): Promise<boolean> => {
    if (!callAgentRef.current) {
      setError('Call agent not initialized');
      return false;
    }

    try {
      console.log(`[useAcsCall] Joining group call: ${groupId}`);
      setError(null);

      const callOptions: any = {
        audioOptions: { muted: false },
      };

      // Add video if available
      if (deviceManagerRef.current) {
        const cameras = await deviceManagerRef.current.getCameras();
        if (cameras.length > 0) {
          localVideoStreamRef.current = new LocalVideoStream(cameras[0]);
          callOptions.videoOptions = { localVideoStreams: [localVideoStreamRef.current] };
          setIsVideoOn(true);
        }
      }

      callRef.current = callAgentRef.current.join(
        { groupId },
        callOptions
      );

      setupCallListeners(callRef.current);
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to join call';
      console.error('[useAcsCall] Join error:', message);
      setError(message);
      return false;
    }
  }, [setupCallListeners]);

  /**
   * Starts a new call with specified participants.
   * 
   * @param participantIds - Array of ACS user IDs to call
   * @returns true on success, false on failure
   */
  const startCall = useCallback(async (participantIds: string[]): Promise<boolean> => {
    if (!callAgentRef.current) {
      setError('Call agent not initialized');
      return false;
    }

    try {
      console.log(`[useAcsCall] Starting call with participants: ${participantIds.join(', ')}`);
      setError(null);

      const callOptions: any = {
        audioOptions: { muted: false },
      };

      // Add video if available
      if (deviceManagerRef.current) {
        const cameras = await deviceManagerRef.current.getCameras();
        if (cameras.length > 0) {
          localVideoStreamRef.current = new LocalVideoStream(cameras[0]);
          callOptions.videoOptions = { localVideoStreams: [localVideoStreamRef.current] };
          setIsVideoOn(true);
        }
      }

      const participants = participantIds.map(id => ({ communicationUserId: id }));
      callRef.current = callAgentRef.current.startCall(participants, callOptions);

      setupCallListeners(callRef.current);
      return true;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start call';
      console.error('[useAcsCall] Start call error:', message);
      setError(message);
      return false;
    }
  }, [setupCallListeners]);

  /**
   * Ends the current call.
   */
  const hangup = useCallback(async (): Promise<void> => {
    if (!callRef.current) {
      console.log('[useAcsCall] No active call to hang up');
      return;
    }

    try {
      console.log('[useAcsCall] Hanging up call...');
      await callRef.current.hangUp();
      callRef.current = null;
      setCallState('disconnected');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to hang up';
      console.error('[useAcsCall] Hangup error:', message);
      setError(message);
    }
  }, []);

  /**
   * Toggles local audio mute state.
   */
  const toggleMute = useCallback(async (): Promise<void> => {
    if (!callRef.current) return;

    try {
      if (callRef.current.isMuted) {
        await callRef.current.unmute();
      } else {
        await callRef.current.mute();
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to toggle mute';
      console.error('[useAcsCall] Mute toggle error:', message);
      setError(message);
    }
  }, []);

  /**
   * Toggles local video on/off.
   */
  const toggleVideo = useCallback(async (): Promise<void> => {
    if (!callRef.current || !deviceManagerRef.current) return;

    try {
      if (isVideoOn && localVideoStreamRef.current) {
        await callRef.current.stopVideo(localVideoStreamRef.current);
        localVideoStreamRef.current = null;
        setIsVideoOn(false);
      } else {
        const cameras = await deviceManagerRef.current.getCameras();
        if (cameras.length > 0) {
          localVideoStreamRef.current = new LocalVideoStream(cameras[0]);
          await callRef.current.startVideo(localVideoStreamRef.current);
          setIsVideoOn(true);
        }
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to toggle video';
      console.error('[useAcsCall] Video toggle error:', message);
      setError(message);
    }
  }, [isVideoOn]);

  /**
   * Gets the device manager for camera/microphone selection.
   * 
   * @returns The DeviceManager instance, or null if not initialized
   */
  const getDeviceManager = useCallback((): DeviceManager | null => {
    return deviceManagerRef.current;
  }, []);

  /**
   * Cleans up all ACS resources.
   * Should be called when the component unmounts.
   */
  const cleanup = useCallback((): void => {
    console.log('[useAcsCall] Cleaning up...');
    
    if (callRef.current) {
      callRef.current.hangUp().catch(console.error);
      callRef.current = null;
    }

    if (callAgentRef.current) {
      callAgentRef.current.dispose();
      callAgentRef.current = null;
    }

    if (tokenCredentialRef.current) {
      tokenCredentialRef.current.dispose();
      tokenCredentialRef.current = null;
    }

    callClientRef.current = null;
    deviceManagerRef.current = null;
    localVideoStreamRef.current = null;

    setIsInitialized(false);
    setCallState('none');
    setRemoteParticipants([]);
    setIsMuted(false);
    setIsVideoOn(false);
    setError(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, [cleanup]);

  return {
    callState,
    isInitialized,
    isMuted,
    isVideoOn,
    error,
    remoteParticipants,
    initialize,
    joinCall,
    startCall,
    hangup,
    toggleMute,
    toggleVideo,
    getDeviceManager,
    cleanup,
  };
};
