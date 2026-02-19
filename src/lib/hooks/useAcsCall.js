import { useState, useCallback, useRef, useEffect } from 'react';
import { CallClient, LocalVideoStream, } from '@azure/communication-calling';
import { AzureCommunicationTokenCredential } from '@azure/communication-common';
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
export const useAcsCall = ({ displayName = 'Interview Participant', onCallStateChange, onParticipantJoined, onParticipantLeft, } = {}) => {
    const [callState, setCallState] = useState('none');
    const [isInitialized, setIsInitialized] = useState(false);
    const [isMuted, setIsMuted] = useState(false);
    const [isVideoOn, setIsVideoOn] = useState(false);
    const [error, setError] = useState(null);
    const [remoteParticipants, setRemoteParticipants] = useState([]);
    const callClientRef = useRef(null);
    const callAgentRef = useRef(null);
    const callRef = useRef(null);
    const deviceManagerRef = useRef(null);
    const localVideoStreamRef = useRef(null);
    const tokenCredentialRef = useRef(null);
    /**
     * Updates call state and notifies callback.
     */
    const updateCallState = useCallback((state) => {
        const mappedState = state;
        console.log(`[useAcsCall] Call state changed: ${mappedState}`);
        setCallState(mappedState);
        onCallStateChange?.(mappedState);
    }, [onCallStateChange]);
    /**
     * Handles participant join/leave events.
     */
    const handleParticipantsUpdated = useCallback((args) => {
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
    const initialize = useCallback(async (token) => {
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
            callAgentRef.current = await callClientRef.current.createCallAgent(tokenCredentialRef.current, { displayName });
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
        }
        catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to initialize call client';
            console.error('[useAcsCall] Initialization error:', message);
            setError(message);
            return false;
        }
    }, [displayName]);
    /**
     * Sets up event listeners on a call instance.
     */
    const setupCallListeners = useCallback((call) => {
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
    const joinCall = useCallback(async (groupId) => {
        if (!callAgentRef.current) {
            setError('Call agent not initialized');
            return false;
        }
        try {
            console.log(`[useAcsCall] Joining group call: ${groupId}`);
            setError(null);
            const callOptions = {
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
            callRef.current = callAgentRef.current.join({ groupId }, callOptions);
            setupCallListeners(callRef.current);
            return true;
        }
        catch (err) {
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
    const startCall = useCallback(async (participantIds) => {
        if (!callAgentRef.current) {
            setError('Call agent not initialized');
            return false;
        }
        try {
            console.log(`[useAcsCall] Starting call with participants: ${participantIds.join(', ')}`);
            setError(null);
            const callOptions = {
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
        }
        catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to start call';
            console.error('[useAcsCall] Start call error:', message);
            setError(message);
            return false;
        }
    }, [setupCallListeners]);
    /**
     * Ends the current call.
     */
    const hangup = useCallback(async () => {
        if (!callRef.current) {
            console.log('[useAcsCall] No active call to hang up');
            return;
        }
        try {
            console.log('[useAcsCall] Hanging up call...');
            await callRef.current.hangUp();
            callRef.current = null;
            setCallState('disconnected');
        }
        catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to hang up';
            console.error('[useAcsCall] Hangup error:', message);
            setError(message);
        }
    }, []);
    /**
     * Toggles local audio mute state.
     */
    const toggleMute = useCallback(async () => {
        if (!callRef.current)
            return;
        try {
            if (callRef.current.isMuted) {
                await callRef.current.unmute();
            }
            else {
                await callRef.current.mute();
            }
        }
        catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to toggle mute';
            console.error('[useAcsCall] Mute toggle error:', message);
            setError(message);
        }
    }, []);
    /**
     * Toggles local video on/off.
     */
    const toggleVideo = useCallback(async () => {
        if (!callRef.current || !deviceManagerRef.current)
            return;
        try {
            if (isVideoOn && localVideoStreamRef.current) {
                await callRef.current.stopVideo(localVideoStreamRef.current);
                localVideoStreamRef.current = null;
                setIsVideoOn(false);
            }
            else {
                const cameras = await deviceManagerRef.current.getCameras();
                if (cameras.length > 0) {
                    localVideoStreamRef.current = new LocalVideoStream(cameras[0]);
                    await callRef.current.startVideo(localVideoStreamRef.current);
                    setIsVideoOn(true);
                }
            }
        }
        catch (err) {
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
    const getDeviceManager = useCallback(() => {
        return deviceManagerRef.current;
    }, []);
    /**
     * Cleans up all ACS resources.
     * Should be called when the component unmounts.
     */
    const cleanup = useCallback(() => {
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
