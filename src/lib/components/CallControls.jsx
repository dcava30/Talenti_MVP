import React from 'react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Mic, MicOff, Video, VideoOff, PhoneOff, Settings, Monitor, MonitorOff, } from 'lucide-react';
import { cn } from '@/lib/utils';
export const CallControls = ({ isMuted, isVideoOn, isScreenSharing = false, isConnected, isConnecting = false, onToggleMute, onToggleVideo, onToggleScreenShare, onHangup, onOpenSettings, showScreenShare = false, showSettings = false, className, variant = 'default', }) => {
    const isDisabled = !isConnected && !isConnecting;
    const containerStyles = {
        default: 'flex items-center justify-center gap-3 p-4 bg-background/95 backdrop-blur-sm border-t',
        minimal: 'flex items-center justify-center gap-2',
        floating: 'flex items-center justify-center gap-3 p-4 rounded-full bg-background/90 backdrop-blur-md shadow-lg',
    };
    const buttonBaseStyles = {
        default: 'h-12 w-12 rounded-full',
        minimal: 'h-10 w-10 rounded-full',
        floating: 'h-14 w-14 rounded-full',
    };
    const iconSize = variant === 'floating' ? 'h-6 w-6' : variant === 'minimal' ? 'h-4 w-4' : 'h-5 w-5';
    return (<div className={cn(containerStyles[variant], className)}>
      {/* Mute Button */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant={isMuted ? 'destructive' : 'secondary'} size="icon" className={cn(buttonBaseStyles[variant], 'transition-all duration-200', isMuted && 'bg-destructive hover:bg-destructive/90', !isMuted && 'bg-secondary hover:bg-secondary/80')} onClick={onToggleMute} disabled={isDisabled}>
            {isMuted ? (<MicOff className={iconSize}/>) : (<Mic className={iconSize}/>)}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">
          <p>{isMuted ? 'Unmute microphone' : 'Mute microphone'}</p>
        </TooltipContent>
      </Tooltip>

      {/* Video Button */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant={!isVideoOn ? 'destructive' : 'secondary'} size="icon" className={cn(buttonBaseStyles[variant], 'transition-all duration-200', !isVideoOn && 'bg-destructive hover:bg-destructive/90', isVideoOn && 'bg-secondary hover:bg-secondary/80')} onClick={onToggleVideo} disabled={isDisabled}>
            {isVideoOn ? (<Video className={iconSize}/>) : (<VideoOff className={iconSize}/>)}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">
          <p>{isVideoOn ? 'Turn off camera' : 'Turn on camera'}</p>
        </TooltipContent>
      </Tooltip>

      {/* Screen Share Button */}
      {showScreenShare && onToggleScreenShare && (<Tooltip>
          <TooltipTrigger asChild>
            <Button variant={isScreenSharing ? 'default' : 'secondary'} size="icon" className={cn(buttonBaseStyles[variant], 'transition-all duration-200', isScreenSharing && 'bg-primary hover:bg-primary/90')} onClick={onToggleScreenShare} disabled={isDisabled}>
              {isScreenSharing ? (<MonitorOff className={iconSize}/>) : (<Monitor className={iconSize}/>)}
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top">
            <p>{isScreenSharing ? 'Stop sharing' : 'Share screen'}</p>
          </TooltipContent>
        </Tooltip>)}

      {/* Settings Button */}
      {showSettings && onOpenSettings && (<Tooltip>
          <TooltipTrigger asChild>
            <Button variant="outline" size="icon" className={cn(buttonBaseStyles[variant], 'transition-all duration-200')} onClick={onOpenSettings}>
              <Settings className={iconSize}/>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top">
            <p>Settings</p>
          </TooltipContent>
        </Tooltip>)}

      {/* Hangup Button */}
      <Tooltip>
        <TooltipTrigger asChild>
          <Button variant="destructive" size="icon" className={cn(buttonBaseStyles[variant], 'bg-destructive hover:bg-destructive/90 transition-all duration-200', variant === 'floating' && 'px-8')} onClick={onHangup} disabled={isDisabled}>
            <PhoneOff className={iconSize}/>
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top">
          <p>End call</p>
        </TooltipContent>
      </Tooltip>
    </div>);
};
export const CallControlsInline = ({ isMuted, isVideoOn, onToggleMute, onToggleVideo, onHangup, disabled = false, className, }) => {
    return (<div className={cn('flex items-center gap-2', className)}>
      <Button variant={isMuted ? 'destructive' : 'ghost'} size="sm" onClick={onToggleMute} disabled={disabled} className="h-8 w-8 p-0">
        {isMuted ? <MicOff className="h-4 w-4"/> : <Mic className="h-4 w-4"/>}
      </Button>

      <Button variant={!isVideoOn ? 'destructive' : 'ghost'} size="sm" onClick={onToggleVideo} disabled={disabled} className="h-8 w-8 p-0">
        {isVideoOn ? <Video className="h-4 w-4"/> : <VideoOff className="h-4 w-4"/>}
      </Button>

      <Button variant="destructive" size="sm" onClick={onHangup} disabled={disabled} className="h-8">
        <PhoneOff className="h-4 w-4 mr-1"/>
        End
      </Button>
    </div>);
};
export default CallControls;
