import { useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { Loader2, User } from "lucide-react";
export const AvatarRenderer = ({ videoStream, audioStream, isConnecting = false, isSpeaking = false, className, fallbackName = "AI Interviewer", }) => {
    const videoRef = useRef(null);
    const audioRef = useRef(null);
    // Attach video stream
    useEffect(() => {
        if (videoRef.current && videoStream) {
            videoRef.current.srcObject = videoStream;
        }
    }, [videoStream]);
    // Attach audio stream
    useEffect(() => {
        if (audioRef.current && audioStream) {
            audioRef.current.srcObject = audioStream;
        }
    }, [audioStream]);
    const hasVideo = !!videoStream;
    return (<div className={cn("relative rounded-lg overflow-hidden bg-muted flex items-center justify-center", className)}>
      {/* Video element for avatar */}
      <video ref={videoRef} autoPlay playsInline muted={false} className={cn("w-full h-full object-cover transition-opacity duration-300", hasVideo ? "opacity-100" : "opacity-0")}/>

      {/* Hidden audio element */}
      <audio ref={audioRef} autoPlay/>

      {/* Fallback avatar placeholder */}
      {!hasVideo && !isConnecting && (<div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-gradient-to-b from-primary/20 to-primary/10">
          <div className="w-24 h-24 rounded-full bg-primary/20 flex items-center justify-center">
            <User className="w-12 h-12 text-primary"/>
          </div>
          <span className="text-sm font-medium text-muted-foreground">
            {fallbackName}
          </span>
        </div>)}

      {/* Connecting state */}
      {isConnecting && (<div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-background/80 backdrop-blur-sm">
          <Loader2 className="w-10 h-10 text-primary animate-spin"/>
          <span className="text-sm text-muted-foreground">
            Connecting to AI Avatar...
          </span>
        </div>)}

      {/* Speaking indicator */}
      {isSpeaking && hasVideo && (<div className="absolute bottom-3 left-1/2 -translate-x-1/2">
          <div className="flex items-center gap-1 px-3 py-1.5 rounded-full bg-primary/90 backdrop-blur-sm">
            <div className="flex gap-0.5">
              <span className="w-1 h-3 bg-primary-foreground rounded-full animate-pulse" style={{ animationDelay: "0ms" }}/>
              <span className="w-1 h-4 bg-primary-foreground rounded-full animate-pulse" style={{ animationDelay: "150ms" }}/>
              <span className="w-1 h-2 bg-primary-foreground rounded-full animate-pulse" style={{ animationDelay: "300ms" }}/>
              <span className="w-1 h-3 bg-primary-foreground rounded-full animate-pulse" style={{ animationDelay: "450ms" }}/>
            </div>
            <span className="text-xs font-medium text-primary-foreground ml-1">
              Speaking
            </span>
          </div>
        </div>)}

      {/* Avatar name badge */}
      {hasVideo && !isConnecting && (<div className="absolute bottom-3 left-3">
          <div className="px-2 py-1 rounded bg-background/70 backdrop-blur-sm">
            <span className="text-xs font-medium">{fallbackName}</span>
          </div>
        </div>)}
    </div>);
};
export default AvatarRenderer;
