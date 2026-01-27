import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";
import { Video, Mic, Clock, Volume2, CheckCircle2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { useNavigate } from "react-router-dom";
import { useToast } from "@/hooks/use-toast";
const CandidateInterview = () => {
    const navigate = useNavigate();
    const { toast } = useToast();
    const [currentQuestion, setCurrentQuestion] = useState(0);
    const [isRecording, setIsRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    const [hasStarted, setHasStarted] = useState(false);
    const questions = [
        {
            id: 1,
            text: "Tell us about yourself and why you're interested in this role.",
            timeLimit: 90,
        },
        {
            id: 2,
            text: "Describe a challenging project you've worked on and how you overcame obstacles.",
            timeLimit: 120,
        },
        {
            id: 3,
            text: "What are your key strengths and how do they align with this position?",
            timeLimit: 90,
        },
        {
            id: 4,
            text: "Where do you see yourself in 3-5 years, and how does this role fit into your career goals?",
            timeLimit: 90,
        },
        {
            id: 5,
            text: "What questions do you have for us about the role or the company?",
            timeLimit: 60,
        },
    ];
    const progress = ((currentQuestion + 1) / questions.length) * 100;
    const handleStartInterview = () => {
        setHasStarted(true);
    };
    const handleStartRecording = () => {
        setIsRecording(true);
        // Simulate recording timer
        const interval = setInterval(() => {
            setRecordingTime((prev) => {
                if (prev >= questions[currentQuestion].timeLimit) {
                    clearInterval(interval);
                    handleStopRecording();
                    return prev;
                }
                return prev + 1;
            });
        }, 1000);
    };
    const handleStopRecording = () => {
        setIsRecording(false);
        toast({
            title: "Answer recorded!",
            description: "Your response has been saved.",
        });
    };
    const handleNextQuestion = () => {
        if (currentQuestion < questions.length - 1) {
            setCurrentQuestion(currentQuestion + 1);
            setRecordingTime(0);
            setIsRecording(false);
        }
        else {
            // Interview complete
            toast({
                title: "Interview completed!",
                description: "Thank you for your time. We'll review your responses and get back to you soon.",
            });
            navigate("/candidate/complete");
        }
    };
    const handlePlayAudio = () => {
        toast({
            title: "Playing question audio",
            description: "Text-to-speech feature would play here",
        });
    };
    if (!hasStarted) {
        return (<div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="max-w-2xl w-full p-8">
          <div className="text-center space-y-6">
            <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
              <Video className="w-8 h-8 text-primary"/>
            </div>
            
            <div>
              <h1 className="text-3xl font-bold mb-2">Senior Frontend Developer</h1>
              <p className="text-muted-foreground">Engineering Department • Remote</p>
            </div>

            <div className="bg-accent/50 rounded-lg p-6 space-y-4 text-left">
              <h2 className="font-semibold text-lg">Before you begin:</h2>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0"/>
                  <span>This interview will take approximately 15 minutes</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0"/>
                  <span>You'll answer 5 questions via video recording</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0"/>
                  <span>Each question has a time limit (60-120 seconds)</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0"/>
                  <span>Make sure your camera and microphone are working</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0"/>
                  <span>Find a quiet space with good lighting</span>
                </li>
              </ul>
            </div>

            <Button size="lg" className="w-full" onClick={handleStartInterview}>
              Start Interview
            </Button>

            <p className="text-xs text-muted-foreground">
              By continuing, you consent to being recorded for hiring purposes
            </p>
          </div>
        </Card>
      </div>);
    }
    return (<div className="min-h-screen bg-background">
      {/* Progress Header */}
      <div className="border-b border-border/40 bg-card/30 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <span className="text-primary-foreground font-bold">T</span>
              </div>
              <span className="font-semibold">Talenti Interview</span>
            </div>
            <Badge variant="secondary">
              Question {currentQuestion + 1} of {questions.length}
            </Badge>
          </div>
          <Progress value={progress} className="h-2"/>
        </div>
      </div>

      <div className="container mx-auto px-4 py-8 max-w-4xl">
        <Card className="p-8">
          {/* Question Section */}
          <div className="mb-8">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <h2 className="text-2xl font-semibold mb-4">
                  {questions[currentQuestion].text}
                </h2>
              </div>
              <Button variant="ghost" size="sm" onClick={handlePlayAudio} className="flex-shrink-0">
                <Volume2 className="w-4 h-4 mr-2"/>
                Play Audio
              </Button>
            </div>

            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4"/>
                Time limit: {questions[currentQuestion].timeLimit}s
              </div>
            </div>
          </div>

          {/* Video Preview / Recording Area */}
          <div className="mb-8">
            <div className="relative aspect-video bg-accent/50 rounded-lg overflow-hidden flex items-center justify-center">
              {isRecording ? (<div className="text-center space-y-4">
                  <div className="w-16 h-16 rounded-full bg-destructive/20 flex items-center justify-center animate-pulse mx-auto">
                    <div className="w-8 h-8 rounded-full bg-destructive"/>
                  </div>
                  <div className="space-y-2">
                    <p className="text-lg font-semibold">Recording...</p>
                    <p className="text-3xl font-bold text-primary">
                      {Math.floor(recordingTime / 60)}:
                      {(recordingTime % 60).toString().padStart(2, "0")}
                    </p>
                  </div>
                </div>) : (<div className="text-center space-y-4">
                  <Video className="w-16 h-16 text-muted-foreground mx-auto"/>
                  <p className="text-muted-foreground">
                    Your video will appear here when you start recording
                  </p>
                </div>)}
            </div>
          </div>

          {/* Controls */}
          <div className="space-y-4">
            {!isRecording ? (<Button size="lg" className="w-full" onClick={handleStartRecording} disabled={recordingTime > 0}>
                <Mic className="w-5 h-5 mr-2"/>
                {recordingTime > 0 ? "Answer Recorded" : "Start Recording"}
              </Button>) : (<Button size="lg" variant="destructive" className="w-full" onClick={handleStopRecording}>
                Stop Recording
              </Button>)}

            {recordingTime > 0 && !isRecording && (<Button size="lg" className="w-full" onClick={handleNextQuestion}>
                {currentQuestion < questions.length - 1
                ? "Next Question"
                : "Complete Interview"}
              </Button>)}
          </div>
        </Card>
      </div>
    </div>);
};
export default CandidateInterview;
