import { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useNavigate, useParams } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { useAzureSpeech } from "@/hooks/useAzureSpeech";
import { useAzureAvatar } from "@/hooks/useAzureAvatar";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "@/hooks/useSpeechSynthesis";
import { useInterviewPersistence } from "@/hooks/useInterviewPersistence";
import { useInterviewContext } from "@/hooks/useInterviewContext";
import { useAcsToken } from "@/hooks/useAcsToken";
import { useAcsCall } from "@/hooks/useAcsCall";
import { interviewsApi } from "@/api/interviews";
import { VideoTile } from "@/components/VideoRenderer";
import { AvatarRenderer } from "@/components/AvatarRenderer";
import { CallControls } from "@/components/CallControls";
import { LocalVideoStream } from "@azure/communication-calling";
import { Mic, MicOff, Loader2, Volume2, Clock, AlertTriangle, WifiOff, VolumeX, Video, Cloud, User } from "lucide-react";
const LiveInterview = () => {
    const navigate = useNavigate();
    const { inviteId } = useParams();
    const { toast } = useToast();
    // Interview state
    const [status, setStatus] = useState("connecting");
    const [currentQuestion, setCurrentQuestion] = useState(0);
    const [elapsedTime, setElapsedTime] = useState(0);
    const [messages, setMessages] = useState([]);
    const [antiCheatSignals, setAntiCheatSignals] = useState([]);
    const [connectionStatus, setConnectionStatus] = useState("connected");
    const [silenceSeconds, setSilenceSeconds] = useState(0);
    const [applicationId, setApplicationId] = useState(null);
    const [competenciesCovered, setCompetenciesCovered] = useState([]);
    const [useAcsMode, setUseAcsMode] = useState(false);
    const [useAzureSpeechMode, setUseAzureSpeechMode] = useState(false);
    const [useAvatarMode, setUseAvatarMode] = useState(false);
    const [localVideoStream, setLocalVideoStream] = useState(null);
    const [remoteVideoStreams, setRemoteVideoStreams] = useState([]);
    // Refs
    const streamRef = useRef(null);
    const timerRef = useRef(null);
    const silenceTimerRef = useRef(null);
    const lastSpeechRef = useRef(new Date());
    const messagesEndRef = useRef(null);
    const isProcessingRef = useRef(false);
    const interviewStartTimeRef = useRef(Date.now());
    const currentInterviewIdRef = useRef(null);
    // Persistence hooks
    const { createInterview, saveTranscriptSegment, updateAntiCheatSignals, completeInterview, getOrCreateDemoApplication, } = useInterviewPersistence();
    // CAG context
    const { context, isLoading: isContextLoading, markCompetencyCovered } = useInterviewContext(applicationId || undefined);
    // ACS hooks
    const { token: acsToken, isLoading: isTokenLoading, error: tokenError, fetchToken } = useAcsToken({
        userId: applicationId || 'demo-user',
        scopes: ['voip'],
        autoRefresh: true,
    });
    const { callState, isInitialized: isAcsInitialized, isMuted, isVideoOn, error: acsError, remoteParticipants, initialize: initializeAcs, joinCall, hangup: acsHangup, toggleMute: acsToggleMute, toggleVideo: acsToggleVideo, getDeviceManager, cleanup: cleanupAcs, } = useAcsCall({
        displayName: 'Interview Candidate',
        onCallStateChange: (state) => {
            console.log('[LiveInterview] ACS call state:', state);
            if (state === 'connected') {
                setConnectionStatus('connected');
            }
            else if (state === 'disconnected') {
                setConnectionStatus('disconnected');
            }
        },
        onParticipantJoined: (participant) => {
            console.log('[LiveInterview] Participant joined:', participant.displayName);
            // Get video streams from participant
            participant.videoStreams.forEach(stream => {
                if (stream.isAvailable) {
                    setRemoteVideoStreams(prev => [...prev, {
                            stream: stream,
                            participantId: participant.identifier.toString(),
                            displayName: participant.displayName,
                        }]);
                }
            });
        },
        onParticipantLeft: (participant) => {
            setRemoteVideoStreams(prev => prev.filter(s => s.participantId !== participant.identifier.toString()));
        },
    });
    const totalQuestions = 6;
    const maxDuration = 15 * 60;
    const silenceThreshold = 5;
    // Azure Avatar hook
    const { isInitialized: avatarInitialized, isConnecting: avatarConnecting, isSpeaking: avatarSpeaking, videoStream: avatarVideoStream, audioStream: avatarAudioStream, initialize: initializeAvatar, speak: avatarSpeak, stopSpeaking: avatarStopSpeaking, close: closeAvatar, } = useAzureAvatar({
        character: "lisa",
        style: "casual-sitting",
        voice: "en-AU-NatashaNeural",
        onSpeakingEnd: () => {
            if (status !== "completed" && status !== "error") {
                setStatus("listening");
                startListening();
            }
        },
        onError: (err) => {
            console.error("[LiveInterview] Avatar error:", err);
            setUseAvatarMode(false);
        },
    });
    // Azure Speech hook (primary)
    const { isListening: azureIsListening, isSpeaking: azureIsSpeaking, transcript: azureTranscript, interimTranscript: azureInterimTranscript, isInitialized: azureSpeechInitialized, error: azureSpeechError, initialize: initializeAzureSpeech, startListening: azureStartListening, stopListening: azureStopListening, speak: azureSpeak, stopSpeaking: azureStopSpeaking, resetTranscript: azureResetTranscript, } = useAzureSpeech({
        voice: "en-AU-NatashaNeural",
        onSpeechResult: (text, isFinal) => {
            if (isFinal) {
                lastSpeechRef.current = new Date();
                setSilenceSeconds(0);
            }
        },
        onTTSEnd: () => {
            if (status !== "completed" && status !== "error") {
                setStatus("listening");
                if (useAzureSpeechMode) {
                    azureStartListening();
                }
                else {
                    browserStartListening();
                }
            }
        },
        onError: (err) => {
            console.error("[LiveInterview] Azure Speech error:", err);
            // Fall back to browser speech on error
            if (useAzureSpeechMode) {
                console.log("[LiveInterview] Falling back to browser speech...");
                setUseAzureSpeechMode(false);
            }
        },
    });
    // Browser Speech recognition hook (fallback)
    const { isListening: browserIsListening, transcript: browserTranscript, interimTranscript: browserInterimTranscript, isSupported: browserSttSupported, startListening: browserStartListening, stopListening: browserStopListening, resetTranscript: browserResetTranscript, } = useSpeechRecognition({
        onResult: () => {
            lastSpeechRef.current = new Date();
            setSilenceSeconds(0);
        },
    });
    // Browser Speech synthesis hook (fallback)
    const { isSpeaking: browserIsSpeaking, isSupported: browserTtsSupported, speak: browserSpeak, stop: browserStopSpeaking, } = useSpeechSynthesis({
        rate: 1,
        pitch: 1,
        onEnd: () => {
            if (status !== "completed" && status !== "error") {
                setStatus("listening");
                if (useAzureSpeechMode) {
                    azureStartListening();
                }
                else {
                    browserStartListening();
                }
            }
        },
    });
    // Unified speech interface
    const isListening = useAzureSpeechMode ? azureIsListening : browserIsListening;
    const isSpeaking = useAvatarMode ? avatarSpeaking : (useAzureSpeechMode ? azureIsSpeaking : browserIsSpeaking);
    const transcript = useAzureSpeechMode ? azureTranscript : browserTranscript;
    const interimTranscript = useAzureSpeechMode ? azureInterimTranscript : browserInterimTranscript;
    const sttSupported = useAzureSpeechMode || browserSttSupported;
    const ttsSupported = useAvatarMode || useAzureSpeechMode || browserTtsSupported;
    const startListening = useCallback(() => {
        if (useAzureSpeechMode) {
            azureStartListening();
        }
        else {
            browserStartListening();
        }
    }, [useAzureSpeechMode, azureStartListening, browserStartListening]);
    const stopListening = useCallback(() => {
        if (useAzureSpeechMode) {
            azureStopListening();
        }
        else {
            browserStopListening();
        }
    }, [useAzureSpeechMode, azureStopListening, browserStopListening]);
    const speak = useCallback((text) => {
        // Use avatar if available, otherwise fall back to Azure Speech or browser
        if (useAvatarMode && avatarInitialized) {
            avatarSpeak(text);
        }
        else if (useAzureSpeechMode) {
            azureSpeak(text);
        }
        else {
            browserSpeak(text);
        }
    }, [useAvatarMode, avatarInitialized, avatarSpeak, useAzureSpeechMode, azureSpeak, browserSpeak]);
    const stopSpeaking = useCallback(() => {
        if (useAvatarMode && avatarInitialized) {
            avatarStopSpeaking();
        }
        else if (useAzureSpeechMode) {
            azureStopSpeaking();
        }
        else {
            browserStopSpeaking();
        }
    }, [useAvatarMode, avatarInitialized, avatarStopSpeaking, useAzureSpeechMode, azureStopSpeaking, browserStopSpeaking]);
    const resetTranscript = useCallback(() => {
        if (useAzureSpeechMode) {
            azureResetTranscript();
        }
        else {
            browserResetTranscript();
        }
    }, [useAzureSpeechMode, azureResetTranscript, browserResetTranscript]);
    // Initialize interview
    useEffect(() => {
        initializeInterview();
        return () => cleanup();
    }, []);
    // Initialize ACS when token is available
    useEffect(() => {
        if (acsToken && useAcsMode && !isAcsInitialized) {
            initializeAcs(acsToken).then((success) => {
                if (success) {
                    console.log('[LiveInterview] ACS initialized successfully');
                    // Get local video stream
                    const deviceManager = getDeviceManager();
                    if (deviceManager) {
                        deviceManager.getCameras().then(cameras => {
                            if (cameras.length > 0) {
                                const stream = new LocalVideoStream(cameras[0]);
                                setLocalVideoStream(stream);
                            }
                        });
                    }
                }
            });
        }
    }, [acsToken, useAcsMode, isAcsInitialized, initializeAcs, getDeviceManager]);
    // Start AI greeting once context is loaded and we're in greeting state
    useEffect(() => {
        if (status === "greeting" && !isContextLoading && applicationId) {
            getAIResponse([]);
        }
    }, [status, isContextLoading, applicationId]);
    // Timer for interview duration
    useEffect(() => {
        timerRef.current = setInterval(() => {
            setElapsedTime(prev => {
                if (prev >= maxDuration) {
                    handleEndInterview();
                    return prev;
                }
                return prev + 1;
            });
        }, 1000);
        return () => {
            if (timerRef.current)
                clearInterval(timerRef.current);
        };
    }, []);
    // Silence detection for auto-submit
    useEffect(() => {
        if (status === "listening" && isListening && transcript) {
            silenceTimerRef.current = setInterval(() => {
                const silenceDuration = (new Date().getTime() - lastSpeechRef.current.getTime()) / 1000;
                setSilenceSeconds(Math.floor(silenceDuration));
                if (silenceDuration >= silenceThreshold && !isProcessingRef.current) {
                    handleSubmitResponse();
                }
            }, 1000);
        }
        else {
            setSilenceSeconds(0);
        }
        return () => {
            if (silenceTimerRef.current)
                clearInterval(silenceTimerRef.current);
        };
    }, [status, isListening, transcript]);
    // Tab visibility detection (anti-cheat)
    useEffect(() => {
        const handleVisibilityChange = () => {
            if (document.hidden) {
                const newSignal = {
                    type: "tab_switch",
                    timestamp: new Date(),
                };
                setAntiCheatSignals(prev => {
                    const updated = [...prev, newSignal];
                    if (currentInterviewIdRef.current) {
                        updateAntiCheatSignals(currentInterviewIdRef.current, updated);
                    }
                    return updated;
                });
            }
        };
        document.addEventListener("visibilitychange", handleVisibilityChange);
        return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
    }, [updateAntiCheatSignals]);
    // Scroll to bottom of messages
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);
    const initializeInterview = async () => {
        try {
            interviewStartTimeRef.current = Date.now();
            // Get media stream for browser-based audio (fallback)
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
                video: true, // Request video for ACS
            });
            streamRef.current = stream;
            // Create interview record
            let appId = inviteId;
            if (!appId) {
                appId = await getOrCreateDemoApplication() || undefined;
            }
            if (appId) {
                setApplicationId(appId);
                const interviewId = await createInterview(appId);
                if (interviewId) {
                    currentInterviewIdRef.current = interviewId;
                    console.log("Interview initialized with ID:", interviewId);
                }
                // Try to initialize Azure Speech first (preferred)
                try {
                    console.log("[LiveInterview] Attempting Azure Speech initialization...");
                    const azureInitialized = await initializeAzureSpeech();
                    if (azureInitialized) {
                        setUseAzureSpeechMode(true);
                        console.log("[LiveInterview] Azure Speech initialized successfully");
                        toast({
                            title: "Azure Speech Connected",
                            description: "Using high-quality Azure AI Speech for the interview.",
                        });
                    }
                    else {
                        console.log("[LiveInterview] Azure Speech not available, using browser speech");
                    }
                }
                catch (err) {
                    console.log("[LiveInterview] Azure Speech init failed, using browser speech:", err);
                }
                // Try to initialize Azure Avatar (animated interviewer)
                try {
                    console.log("[LiveInterview] Attempting Azure Avatar initialization...");
                    const avatarInit = await initializeAvatar();
                    if (avatarInit) {
                        setUseAvatarMode(true);
                        console.log("[LiveInterview] Azure Avatar initialized successfully");
                        toast({
                            title: "AI Avatar Connected",
                            description: "You'll be interviewed by an AI avatar.",
                        });
                    }
                    else {
                        console.log("[LiveInterview] Avatar not available, using audio-only mode");
                    }
                }
                catch (err) {
                    console.log("[LiveInterview] Avatar init failed:", err);
                }
                // Try to initialize ACS for video
                try {
                    const token = await fetchToken();
                    if (token) {
                        setUseAcsMode(true);
                        console.log("[LiveInterview] ACS token obtained, switching to ACS mode");
                    }
                }
                catch (err) {
                    console.log("[LiveInterview] ACS not available, using browser audio");
                }
            }
            // Check browser speech support as fallback
            if (!useAzureSpeechMode && (!browserSttSupported || !browserTtsSupported)) {
                toast({
                    title: "Limited Speech Support",
                    description: "Using browser speech. Chrome or Edge recommended.",
                    variant: "destructive",
                });
            }
            setStatus("greeting");
        }
        catch (error) {
            console.error("Failed to initialize interview:", error);
            setStatus("error");
            toast({
                title: "Connection Error",
                description: "Failed to start the interview. Please check microphone permissions.",
                variant: "destructive",
            });
        }
    };
    const getAIResponse = async (conversationHistory) => {
        try {
            const jobContext = context.job
                ? {
                    job_title: context.job.title,
                    job_description: context.job.description,
                }
                : {
                    job_title: "Software Engineer",
                    job_description: undefined,
                };
            const data = await interviewsApi.aiInterviewer({
                interview_id: (() => {
                    if (!currentInterviewIdRef.current) {
                        throw new Error("Interview is not initialized yet.");
                    }
                    return currentInterviewIdRef.current;
                })(),
                messages: conversationHistory.map(m => ({
                    role: m.role === "ai" ? "assistant" : "user",
                    content: m.content,
                })),
                ...jobContext,
            });
            const responseText = data.reply || data.message;
            if (!responseText) {
                throw new Error("AI response missing content");
            }
            const aiMessage = {
                id: crypto.randomUUID(),
                role: "ai",
                content: responseText,
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, aiMessage]);
            setCurrentQuestion(prev => prev + 1);
            if (data.competencyCovered && markCompetencyCovered) {
                markCompetencyCovered(data.competencyCovered);
                setCompetenciesCovered(prev => [...prev, data.competencyCovered]);
            }
            if (currentInterviewIdRef.current) {
                const currentTimeMs = Date.now() - interviewStartTimeRef.current;
                await saveTranscriptSegment(currentInterviewIdRef.current, {
                    speaker: "ai",
                    content: responseText,
                    startTimeMs: currentTimeMs,
                });
            }
            if (ttsSupported) {
                setStatus("questioning");
                speak(responseText);
            }
            else {
                setStatus("listening");
                startListening();
            }
            if (currentQuestion >= totalQuestions - 1) {
                setTimeout(() => {
                    setStatus("completed");
                    stopListening();
                    setTimeout(() => handleEndInterview(), 3000);
                }, 5000);
            }
        }
        catch (error) {
            console.error("AI response error:", error);
            toast({
                title: "AI Error",
                description: error instanceof Error ? error.message : "Failed to get AI response",
                variant: "destructive",
            });
            setStatus("error");
        }
    };
    const handleSubmitResponse = useCallback(async () => {
        if (isProcessingRef.current || !transcript.trim())
            return;
        isProcessingRef.current = true;
        stopListening();
        setStatus("processing");
        const responseStartTime = Date.now() - interviewStartTimeRef.current;
        const silenceDuration = (new Date().getTime() - lastSpeechRef.current.getTime()) / 1000;
        if (silenceDuration > 10) {
            const newSignal = {
                type: "silence",
                timestamp: new Date(),
                duration: silenceDuration,
            };
            setAntiCheatSignals(prev => {
                const updated = [...prev, newSignal];
                if (currentInterviewIdRef.current) {
                    updateAntiCheatSignals(currentInterviewIdRef.current, updated);
                }
                return updated;
            });
        }
        const userMessage = {
            id: crypto.randomUUID(),
            role: "user",
            content: transcript,
            timestamp: new Date(),
        };
        const updatedMessages = [...messages, userMessage];
        setMessages(updatedMessages);
        if (currentInterviewIdRef.current) {
            await saveTranscriptSegment(currentInterviewIdRef.current, {
                speaker: "candidate",
                content: transcript,
                startTimeMs: responseStartTime,
                endTimeMs: Date.now() - interviewStartTimeRef.current,
            });
        }
        resetTranscript();
        await getAIResponse(updatedMessages);
        lastSpeechRef.current = new Date();
        isProcessingRef.current = false;
    }, [transcript, messages, stopListening, resetTranscript, saveTranscriptSegment, updateAntiCheatSignals]);
    const handleEndInterview = async () => {
        const completedInterviewId = currentInterviewIdRef.current;
        if (completedInterviewId) {
            await completeInterview(completedInterviewId, elapsedTime, antiCheatSignals);
        }
        cleanup();
        const interviewParam = completedInterviewId ? `?interview=${completedInterviewId}` : "";
        navigate(`/candidate/complete${interviewParam}`);
    };
    const cleanup = () => {
        stopListening();
        stopSpeaking();
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
        }
        if (timerRef.current) {
            clearInterval(timerRef.current);
        }
        if (silenceTimerRef.current) {
            clearInterval(silenceTimerRef.current);
        }
        if (useAvatarMode) {
            closeAvatar();
        }
        if (useAcsMode) {
            cleanupAcs();
        }
    };
    const handleToggleMute = () => {
        if (useAcsMode && isAcsInitialized) {
            acsToggleMute();
        }
        else {
            if (isMuted) {
                startListening();
            }
            else {
                stopListening();
            }
        }
    };
    const handleToggleVideo = () => {
        if (useAcsMode && isAcsInitialized) {
            acsToggleVideo();
        }
    };
    const handleHangup = () => {
        if (useAcsMode && isAcsInitialized) {
            acsHangup();
        }
        handleEndInterview();
    };
    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, "0")}`;
    };
    const progress = (currentQuestion / totalQuestions) * 100;
    const effectiveIsMuted = useAcsMode ? isMuted : !isListening;
    return (<div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <span className="text-primary-foreground font-bold">T</span>
              </div>
              <div>
                <span className="font-semibold">Live AI Interview</span>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Clock className="w-3 h-3"/>
                  {formatTime(elapsedTime)} / {formatTime(maxDuration)}
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              {useAvatarMode && (<Badge variant="outline" className="flex items-center gap-1 text-primary border-primary/50">
                  <User className="w-3 h-3"/>
                  AI Avatar
                </Badge>)}
              {useAzureSpeechMode && !useAvatarMode && (<Badge variant="outline" className="flex items-center gap-1 text-primary border-primary/50">
                  <Cloud className="w-3 h-3"/>
                  Azure Speech
                </Badge>)}
              {useAcsMode && (<Badge variant="outline" className="flex items-center gap-1">
                  <Video className="w-3 h-3"/>
                  ACS
                </Badge>)}
              {connectionStatus !== "connected" && (<Badge variant="destructive" className="flex items-center gap-1">
                  <WifiOff className="w-3 h-3"/>
                  {connectionStatus === "reconnecting" ? "Reconnecting..." : "Disconnected"}
                </Badge>)}
              <Badge variant="secondary">
                Q{Math.min(currentQuestion, totalQuestions)} of {totalQuestions}
              </Badge>
            </div>
          </div>
          <Progress value={progress} className="h-1 mt-2"/>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 container mx-auto px-4 py-6 max-w-6xl flex flex-col lg:flex-row gap-6">
        {/* Video Panel - Avatar or ACS */}
        <div className="lg:w-1/3 space-y-4">
          {/* AI Avatar */}
          <AvatarRenderer videoStream={avatarVideoStream} audioStream={avatarAudioStream} isConnecting={avatarConnecting} isSpeaking={avatarSpeaking || isSpeaking} fallbackName="AI Interviewer" className="aspect-video"/>

          {/* Local Video (ACS mode) */}
          {useAcsMode && localVideoStream && (<div className="aspect-video rounded-lg overflow-hidden bg-muted">
              <VideoTile stream={localVideoStream} isLocal displayName="You" isMuted={effectiveIsMuted} className="w-full h-full"/>
            </div>)}

          {/* Remote Videos */}
          {useAcsMode && remoteVideoStreams.length > 0 && (<div className="space-y-2">
              {remoteVideoStreams.map((remote) => (<VideoTile key={remote.participantId} stream={remote.stream} displayName={remote.displayName || 'Participant'} className="w-full aspect-video"/>))}
            </div>)}

          {/* Connection status */}
          {isTokenLoading && (<div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="w-4 h-4 animate-spin"/>
              Connecting to video service...
            </div>)}
          {(tokenError || acsError) && (<div className="flex items-center justify-center gap-2 text-sm text-destructive">
              <AlertTriangle className="w-4 h-4"/>
              Video connection issue
            </div>)}
        </div>

        {/* Conversation Panel */}
        <div className="flex-1 flex flex-col lg:w-2/3">
          {/* Status Indicator */}
          <div className="flex justify-center mb-4">
            <div className={`flex items-center gap-2 px-4 py-2 rounded-full ${status === "connecting" ? "bg-yellow-500/10 text-yellow-500" :
            status === "listening" ? "bg-green-500/10 text-green-500" :
                status === "processing" ? "bg-blue-500/10 text-blue-500" :
                    status === "error" ? "bg-destructive/10 text-destructive" :
                        status === "completed" ? "bg-primary/10 text-primary" :
                            "bg-primary/10 text-primary"}`}>
              {status === "connecting" && <Loader2 className="w-4 h-4 animate-spin"/>}
              {status === "listening" && <Mic className="w-4 h-4 animate-pulse"/>}
              {status === "processing" && <Loader2 className="w-4 h-4 animate-spin"/>}
              {(status === "greeting" || status === "questioning") && <Volume2 className="w-4 h-4 animate-pulse"/>}
              {status === "error" && <AlertTriangle className="w-4 h-4"/>}
              {status === "completed" && <Badge variant="default">Complete</Badge>}
              <span className="text-sm font-medium capitalize">
                {status === "questioning" ? "AI Speaking" : status}
              </span>
            </div>
          </div>

          {/* Conversation Area */}
          <Card className="flex-1 p-6 overflow-hidden flex flex-col">
            <div className="flex-1 overflow-y-auto space-y-4 mb-4">
              {status === "connecting" && (<div className="flex items-center justify-center h-full">
                  <div className="text-center space-y-4">
                    <Loader2 className="w-12 h-12 text-primary animate-spin mx-auto"/>
                    <p className="text-muted-foreground">Starting AI interviewer...</p>
                  </div>
                </div>)}

              {messages.map((message) => (<div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[80%] p-4 rounded-2xl ${message.role === "user"
                ? "bg-primary text-primary-foreground rounded-br-sm"
                : "bg-accent rounded-bl-sm"}`}>
                    <p className="text-sm">{message.content}</p>
                    <span className="text-xs opacity-70 mt-1 block">
                      {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                </div>))}

              {isSpeaking && (<div className="flex justify-start">
                  <div className="bg-accent p-4 rounded-2xl rounded-bl-sm">
                    <div className="flex items-center gap-2">
                      <Volume2 className="w-4 h-4 text-primary animate-pulse"/>
                      <span className="text-sm text-muted-foreground">Speaking...</span>
                    </div>
                  </div>
                </div>)}

              <div ref={messagesEndRef}/>
            </div>

            {/* Voice Input Area */}
            {status === "listening" && (<div className="border-t border-border pt-4 space-y-3">
                <div className="min-h-[60px] p-3 bg-accent/50 rounded-lg">
                  <p className="text-sm">
                    {transcript}
                    <span className="text-muted-foreground italic">{interimTranscript}</span>
                    {!transcript && !interimTranscript && (<span className="text-muted-foreground">Speak your answer...</span>)}
                  </p>
                </div>
                
                <div className="flex items-center justify-center gap-4">
                  <div className="flex-1 h-2 bg-accent rounded-full overflow-hidden">
                    <div className={`h-full bg-primary transition-all ${isListening ? "animate-pulse" : ""}`} style={{ width: isListening ? "60%" : "0%" }}/>
                  </div>
                  {transcript && silenceSeconds > 0 && (<span className="text-xs text-muted-foreground">
                      Submitting in {silenceThreshold - silenceSeconds}s...
                    </span>)}
                </div>
              </div>)}
          </Card>

          {/* Controls */}
          <div className="mt-6">
            {useAcsMode ? (<CallControls isMuted={effectiveIsMuted} isVideoOn={isVideoOn} isConnected={isAcsInitialized || status !== "connecting"} isConnecting={status === "connecting"} onToggleMute={handleToggleMute} onToggleVideo={handleToggleVideo} onHangup={handleHangup} variant="default"/>) : (<div className="flex items-center justify-center gap-4">
                <Button variant="outline" size="lg" className="rounded-full w-14 h-14" onClick={handleToggleMute} disabled={status === "connecting" || status === "completed" || status === "processing"}>
                  {effectiveIsMuted ? (<MicOff className="w-6 h-6 text-destructive"/>) : (<Mic className="w-6 h-6"/>)}
                </Button>

                {status === "listening" && transcript && (<Button size="lg" className="rounded-full px-8" onClick={handleSubmitResponse} disabled={!transcript.trim()}>
                    Submit Response
                  </Button>)}

                {isSpeaking && (<Button variant="outline" size="lg" className="rounded-full w-14 h-14" onClick={stopSpeaking}>
                    <VolumeX className="w-6 h-6"/>
                  </Button>)}

                <Button variant="destructive" size="lg" className="rounded-full w-14 h-14" onClick={handleEndInterview}>
                  <Loader2 className="w-6 h-6 hidden"/>
                  <span className="sr-only">End Interview</span>
                  ✕
                </Button>
              </div>)}
          </div>

          {/* Anti-cheat warning */}
          {antiCheatSignals.length > 0 && (<div className="mt-4 flex items-center justify-center gap-2 text-xs text-yellow-500">
              <AlertTriangle className="w-3 h-3"/>
              <span>Focus issues detected ({antiCheatSignals.length}) - please stay on this tab</span>
            </div>)}
        </div>
      </div>
    </div>);
};
export default LiveInterview;
