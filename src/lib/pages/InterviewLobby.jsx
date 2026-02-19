import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useNavigate, useParams } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
import { Video, Mic, VideoOff, CheckCircle2, XCircle, AlertCircle, Volume2, RefreshCw, Loader2 } from "lucide-react";
import { useInvitations } from "@/hooks/useInvitations";
const InterviewLobby = () => {
    const navigate = useNavigate();
    const { inviteId } = useParams();
    const { toast } = useToast();
    const { validateInvitation, isValidating } = useInvitations();
    const videoRef = useRef(null);
    const streamRef = useRef(null);
    const [deviceCheck, setDeviceCheck] = useState({
        camera: "checking",
        microphone: "checking",
        speaker: "checking",
    });
    const [consentGiven, setConsentGiven] = useState(false);
    const [isCheckingDevices, setIsCheckingDevices] = useState(true);
    const [audioLevel, setAudioLevel] = useState(0);
    const [interviewData, setInterviewData] = useState(null);
    const [loadError, setLoadError] = useState(null);
    useEffect(() => {
        if (inviteId) {
            loadInvitationData(inviteId);
        }
        checkDevices();
        return () => {
            if (streamRef.current) {
                streamRef.current.getTracks().forEach(track => track.stop());
            }
        };
    }, [inviteId]);
    const loadInvitationData = async (token) => {
        const result = await validateInvitation(token);
        if (result.valid && result.jobRole && result.invitation) {
            setInterviewData({
                roleTitle: result.jobRole.title,
                company: result.jobRole.organisation.name,
                duration: "10-15 minutes",
                questionCount: 5,
                expiresAt: result.invitation.expiresAt,
                applicationId: result.invitation.applicationId,
            });
        }
        else {
            setLoadError(result.error || "Failed to load interview data");
        }
    };
    const checkDevices = async () => {
        setIsCheckingDevices(true);
        setDeviceCheck({
            camera: "checking",
            microphone: "checking",
            speaker: "checking",
        });
        try {
            // Request camera and microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });
            streamRef.current = stream;
            // Set video preview
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
            }
            // Check for audio input levels
            const audioContext = new AudioContext();
            const analyser = audioContext.createAnalyser();
            const microphone = audioContext.createMediaStreamSource(stream);
            microphone.connect(analyser);
            analyser.fftSize = 256;
            const dataArray = new Uint8Array(analyser.frequencyBinCount);
            const checkAudioLevel = () => {
                analyser.getByteFrequencyData(dataArray);
                const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
                setAudioLevel(Math.min(100, average * 2));
                if (streamRef.current) {
                    requestAnimationFrame(checkAudioLevel);
                }
            };
            checkAudioLevel();
            setDeviceCheck({
                camera: "ready",
                microphone: "ready",
                speaker: "ready", // Assume speaker works if we can play audio
            });
        }
        catch (error) {
            console.error("Device access error:", error);
            if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
                setDeviceCheck({
                    camera: "denied",
                    microphone: "denied",
                    speaker: "ready",
                });
                toast({
                    title: "Permission Denied",
                    description: "Please allow camera and microphone access to proceed with the interview.",
                    variant: "destructive",
                });
            }
            else {
                setDeviceCheck({
                    camera: "error",
                    microphone: "error",
                    speaker: "ready",
                });
                toast({
                    title: "Device Error",
                    description: "Could not access camera or microphone. Please check your devices.",
                    variant: "destructive",
                });
            }
        }
        setIsCheckingDevices(false);
    };
    const testSpeaker = () => {
        const audio = new Audio();
        audio.src = "data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU";
        // Create a simple beep using oscillator
        const audioContext = new AudioContext();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        oscillator.frequency.value = 440;
        gainNode.gain.value = 0.3;
        oscillator.start();
        oscillator.stop(audioContext.currentTime + 0.3);
        toast({
            title: "Speaker Test",
            description: "You should have heard a beep sound.",
        });
    };
    const getStatusIcon = (status) => {
        switch (status) {
            case "checking":
                return <Loader2 className="w-5 h-5 text-muted-foreground animate-spin"/>;
            case "ready":
                return <CheckCircle2 className="w-5 h-5 text-green-500"/>;
            case "error":
                return <XCircle className="w-5 h-5 text-destructive"/>;
            case "denied":
                return <AlertCircle className="w-5 h-5 text-yellow-500"/>;
        }
    };
    const getStatusText = (status) => {
        switch (status) {
            case "checking":
                return "Checking...";
            case "ready":
                return "Ready";
            case "error":
                return "Not detected";
            case "denied":
                return "Permission denied";
        }
    };
    const allDevicesReady = deviceCheck.camera === "ready" &&
        deviceCheck.microphone === "ready";
    const canStartInterview = allDevicesReady && consentGiven && interviewData;
    const handleStartInterview = () => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
        }
        navigate(`/candidate/${inviteId}/live`, {
            state: { applicationId: interviewData?.applicationId }
        });
    };
    if (loadError) {
        return (<div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="p-8 max-w-md text-center">
          <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4"/>
          <h2 className="text-xl font-semibold mb-2">Unable to Load Interview</h2>
          <p className="text-muted-foreground mb-4">{loadError}</p>
          <Button variant="outline" onClick={() => navigate("/")}>Return Home</Button>
        </Card>
      </div>);
    }
    if (isValidating || !interviewData) {
        return (<div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary"/>
      </div>);
    }
    return (<div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <span className="text-primary-foreground font-bold">T</span>
              </div>
              <span className="font-semibold">Talenti Interview</span>
            </div>
            <Badge variant="outline">Interview Lobby</Badge>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-8 max-w-5xl">
        <div className="grid lg:grid-cols-2 gap-8">
          {/* Left: Video Preview */}
          <div className="space-y-4">
            <Card className="overflow-hidden">
              <div className="aspect-video bg-accent/50 relative">
                <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover"/>
                {deviceCheck.camera !== "ready" && (<div className="absolute inset-0 flex items-center justify-center bg-background/80">
                    {deviceCheck.camera === "checking" ? (<Loader2 className="w-12 h-12 text-muted-foreground animate-spin"/>) : (<VideoOff className="w-12 h-12 text-muted-foreground"/>)}
                  </div>)}
              </div>
            </Card>

            {/* Audio Level Indicator */}
            {deviceCheck.microphone === "ready" && (<Card className="p-4">
                <div className="flex items-center gap-3">
                  <Mic className="w-5 h-5 text-primary"/>
                  <div className="flex-1">
                    <div className="text-sm mb-1">Microphone Level</div>
                    <div className="h-2 bg-accent rounded-full overflow-hidden">
                      <div className="h-full bg-primary transition-all duration-100" style={{ width: `${audioLevel}%` }}/>
                    </div>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Speak to test your microphone
                </p>
              </Card>)}
          </div>

          {/* Right: Interview Details & Device Checks */}
          <div className="space-y-6">
            {/* Interview Info */}
            <Card className="p-6">
              <h1 className="text-2xl font-bold mb-2">{interviewData.roleTitle}</h1>
              <p className="text-muted-foreground mb-4">{interviewData.company}</p>
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-muted-foreground">Duration:</span>
                  <span className="ml-2 font-medium">{interviewData.duration}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Questions:</span>
                  <span className="ml-2 font-medium">{interviewData.questionCount}</span>
                </div>
              </div>
            </Card>

            {/* Device Checks */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Device Check</h2>
                <Button variant="ghost" size="sm" onClick={checkDevices} disabled={isCheckingDevices}>
                  <RefreshCw className={`w-4 h-4 mr-2 ${isCheckingDevices ? "animate-spin" : ""}`}/>
                  Retry
                </Button>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-3 rounded-lg bg-accent/50">
                  <div className="flex items-center gap-3">
                    <Video className="w-5 h-5 text-muted-foreground"/>
                    <span>Camera</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      {getStatusText(deviceCheck.camera)}
                    </span>
                    {getStatusIcon(deviceCheck.camera)}
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-accent/50">
                  <div className="flex items-center gap-3">
                    <Mic className="w-5 h-5 text-muted-foreground"/>
                    <span>Microphone</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-muted-foreground">
                      {getStatusText(deviceCheck.microphone)}
                    </span>
                    {getStatusIcon(deviceCheck.microphone)}
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 rounded-lg bg-accent/50">
                  <div className="flex items-center gap-3">
                    <Volume2 className="w-5 h-5 text-muted-foreground"/>
                    <span>Speaker</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={testSpeaker}>
                      Test
                    </Button>
                    {getStatusIcon(deviceCheck.speaker)}
                  </div>
                </div>
              </div>
            </Card>

            {/* Consent */}
            <Card className="p-6">
              <h2 className="text-lg font-semibold mb-4">Before You Begin</h2>
              
              <ul className="space-y-2 text-sm text-muted-foreground mb-6">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-primary mt-0.5 flex-shrink-0"/>
                  <span>This interview will be recorded for evaluation</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-primary mt-0.5 flex-shrink-0"/>
                  <span>AI will analyze your responses for scoring</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-primary mt-0.5 flex-shrink-0"/>
                  <span>Find a quiet space with good lighting</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-primary mt-0.5 flex-shrink-0"/>
                  <span>Voice-only interview - speak clearly</span>
                </li>
              </ul>

              <div className="flex items-start gap-2 mb-6">
                <Checkbox id="consent" checked={consentGiven} onCheckedChange={(checked) => setConsentGiven(checked)}/>
                <Label htmlFor="consent" className="text-sm leading-tight">
                  I consent to being recorded and understand that AI will be used to analyze my responses for hiring purposes.
                </Label>
              </div>

              <Button size="lg" className="w-full" disabled={!canStartInterview} onClick={handleStartInterview}>
                {!allDevicesReady ? ("Fix device issues to continue") : !consentGiven ? ("Please give consent to continue") : ("Start Interview")}
              </Button>
            </Card>
          </div>
        </div>
      </div>
    </div>);
};
export default InterviewLobby;
