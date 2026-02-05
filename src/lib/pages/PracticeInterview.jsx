import { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "@/hooks/useSpeechSynthesis";
import { authApi } from "@/api/auth";
import { candidatesApi } from "@/api/candidates";
import { interviewsApi } from "@/api/interviews";
import { Mic, MicOff, Phone, Loader2, Volume2, Clock, AlertTriangle, VolumeX, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
// Sample practice roles
const PRACTICE_ROLES = {
    "software-engineer": {
        title: "Software Engineer",
        description: "Build and maintain software applications",
        skills: ["JavaScript", "React", "Node.js", "Problem Solving"],
    },
    "marketing-manager": {
        title: "Marketing Manager",
        description: "Lead marketing campaigns and strategy",
        skills: ["Campaign Management", "Analytics", "Brand Strategy", "Team Leadership"],
    },
    "customer-success": {
        title: "Customer Success Manager",
        description: "Ensure customer satisfaction and retention",
        skills: ["Communication", "Relationship Building", "Problem Solving", "Product Knowledge"],
    },
};
const PracticeInterview = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const roleType = searchParams.get("role") || "software-engineer";
    const { toast } = useToast();
    const role = PRACTICE_ROLES[roleType] || PRACTICE_ROLES["software-engineer"];
    const [status, setStatus] = useState("connecting");
    const [isMuted, setIsMuted] = useState(false);
    const [currentQuestion, setCurrentQuestion] = useState(0);
    const [elapsedTime, setElapsedTime] = useState(0);
    const [messages, setMessages] = useState([]);
    const [silenceSeconds, setSilenceSeconds] = useState(0);
    const [practiceId, setPracticeId] = useState(null);
    const practiceIdRef = useRef(null);
    const streamRef = useRef(null);
    const timerRef = useRef(null);
    const silenceTimerRef = useRef(null);
    const lastSpeechRef = useRef(new Date());
    const messagesEndRef = useRef(null);
    const isProcessingRef = useRef(false);
    const totalQuestions = 5;
    const maxDuration = 10 * 60; // 10 minutes for practice
    const silenceThreshold = 5;
    const { isListening, transcript, interimTranscript, isSupported: sttSupported, startListening, stopListening, resetTranscript, } = useSpeechRecognition({
        onResult: () => {
            lastSpeechRef.current = new Date();
            setSilenceSeconds(0);
        },
    });
    const { isSpeaking, isSupported: ttsSupported, speak, stop: stopSpeaking, } = useSpeechSynthesis({
        rate: 1,
        pitch: 1,
        onEnd: () => {
            if (status !== "completed" && status !== "error") {
                setStatus("listening");
                startListening();
            }
        },
    });
    useEffect(() => {
        initializePractice();
        return () => cleanup();
    }, []);
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
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);
    const initializePractice = async () => {
        try {
            if (!sttSupported || !ttsSupported) {
                toast({
                    title: "Browser Not Supported",
                    description: "Please use Chrome or Edge for the best experience.",
                    variant: "destructive",
                });
            }
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
            });
            streamRef.current = stream;
            // Create practice interview record
            const user = await authApi.me();
            if (user) {
                const practice = await candidatesApi.createPracticeInterview({
                    user_id: user.id,
                    sample_role_type: roleType,
                    status: "in_progress",
                    started_at: new Date().toISOString(),
                });
                if (practice) {
                    setPracticeId(practice.id);
                    practiceIdRef.current = practice.id;
                }
            }
            setStatus("greeting");
            await getAIResponse([], practiceIdRef.current);
        }
        catch (error) {
            console.error("Failed to initialize practice:", error);
            setStatus("error");
            toast({
                title: "Connection Error",
                description: "Failed to start practice. Please check microphone permissions.",
                variant: "destructive",
            });
        }
    };
    const getAIResponse = async (conversationHistory, interviewId = practiceIdRef.current) => {
        try {
            if (!interviewId) {
                throw new Error("Practice interview is not initialized yet.");
            }
            const data = await interviewsApi.aiInterviewer({
                interview_id: interviewId,
                messages: conversationHistory.map(m => ({
                    role: m.role === "ai" ? "assistant" : "user",
                    content: m.content,
                })),
                job_title: role.title,
                job_description: role.description,
                company_name: "Practice Company",
                current_question_index: currentQuestion,
                is_practice: true,
            });
            const aiMessage = {
                id: crypto.randomUUID(),
                role: "ai",
                content: data.reply || data.message,
                timestamp: new Date(),
            };
            setMessages(prev => [...prev, aiMessage]);
            setCurrentQuestion(prev => prev + 1);
            if (ttsSupported) {
                setStatus("questioning");
                speak(data.message);
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
        const userMessage = {
            id: crypto.randomUUID(),
            role: "user",
            content: transcript,
            timestamp: new Date(),
        };
        const updatedMessages = [...messages, userMessage];
        setMessages(updatedMessages);
        resetTranscript();
        await getAIResponse(updatedMessages);
        lastSpeechRef.current = new Date();
        isProcessingRef.current = false;
    }, [transcript, messages, stopListening, resetTranscript]);
    const handleEndInterview = async () => {
        // Update practice record
        if (practiceId) {
            await candidatesApi.updatePracticeInterview(practiceId, {
                status: "completed",
                ended_at: new Date().toISOString(),
                duration_seconds: elapsedTime,
                feedback: {
                    questionsAnswered: currentQuestion,
                    totalDuration: elapsedTime,
                },
            });
        }
        cleanup();
        navigate(`/candidate/practice/complete?practiceId=${practiceId}`);
    };
    const cleanup = () => {
        stopListening();
        stopSpeaking();
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
        }
        if (timerRef.current)
            clearInterval(timerRef.current);
        if (silenceTimerRef.current)
            clearInterval(silenceTimerRef.current);
    };
    const toggleMute = () => {
        if (isMuted) {
            startListening();
            setIsMuted(false);
        }
        else {
            stopListening();
            setIsMuted(true);
        }
    };
    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, "0")}`;
    };
    const progress = (currentQuestion / totalQuestions) * 100;
    return (<div className="min-h-screen bg-background flex flex-col">
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" asChild>
                <Link to="/candidate/portal">
                  <ArrowLeft className="w-4 h-4"/>
                </Link>
              </Button>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold">Practice Interview</span>
                  <Badge variant="secondary">Practice Mode</Badge>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <Clock className="w-3 h-3"/>
                  {formatTime(elapsedTime)} / {formatTime(maxDuration)}
                </div>
              </div>
            </div>
            
            <Badge variant="outline">
              Q{Math.min(currentQuestion, totalQuestions)} of {totalQuestions}
            </Badge>
          </div>
          <Progress value={progress} className="h-1 mt-2"/>
        </div>
      </header>

      <div className="flex-1 container mx-auto px-4 py-6 max-w-4xl flex flex-col">
        <Card className="mb-4 p-4 bg-primary/5 border-primary/20">
          <p className="text-sm text-muted-foreground">
            <strong>Practice Role:</strong> {role.title}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Skills: {role.skills.join(", ")}
          </p>
        </Card>

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

        <Card className="flex-1 p-6 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto space-y-4 mb-4">
            {status === "connecting" && (<div className="flex items-center justify-center h-full">
                <div className="text-center space-y-4">
                  <Loader2 className="w-12 h-12 text-primary animate-spin mx-auto"/>
                  <p className="text-muted-foreground">Starting practice interview...</p>
                </div>
              </div>)}

            {messages.map((message) => (<div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[80%] p-4 rounded-2xl ${message.role === "user"
                ? "bg-primary text-primary-foreground rounded-br-sm"
                : "bg-accent rounded-bl-sm"}`}>
                  <p className="text-sm">{message.content}</p>
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

          {/* Voice Input */}
          <div className="border-t border-border pt-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {isListening && (<Badge variant="outline" className="animate-pulse">
                    <Mic className="w-3 h-3 mr-1"/>
                    Listening...
                  </Badge>)}
                {transcript && (<p className="text-sm text-muted-foreground truncate max-w-[300px]">
                    "{transcript}"
                  </p>)}
              </div>
              {silenceSeconds > 0 && transcript && (<span className="text-xs text-muted-foreground">
                  Auto-submit in {silenceThreshold - silenceSeconds}s
                </span>)}
            </div>

            <div className="flex items-center justify-center gap-4">
              <Button variant={isMuted ? "destructive" : "outline"} size="icon" onClick={toggleMute} disabled={status !== "listening"}>
                {isMuted ? <MicOff className="w-5 h-5"/> : <Mic className="w-5 h-5"/>}
              </Button>

              <Button onClick={handleSubmitResponse} disabled={!transcript.trim() || status !== "listening"} className="px-8">
                Submit Response
              </Button>

              {isSpeaking && (<Button variant="outline" size="icon" onClick={stopSpeaking}>
                  <VolumeX className="w-5 h-5"/>
                </Button>)}

              <Button variant="destructive" onClick={handleEndInterview}>
                <Phone className="w-4 h-4 mr-2"/>
                End Practice
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>);
};
export default PracticeInterview;
