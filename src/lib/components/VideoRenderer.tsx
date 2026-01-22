import React, { useEffect, useRef, useState } from 'react';
import {
  LocalVideoStream,
  RemoteVideoStream,
  VideoStreamRenderer,
  VideoStreamRendererView,
} from '@azure/communication-calling';
import { User, Video, VideoOff } from 'lucide-react';
import { cn } from '@/lib/utils';

interface VideoTileProps {
  stream: LocalVideoStream | RemoteVideoStream | null;
  isLocal?: boolean;
  displayName?: string;
  isMuted?: boolean;
  className?: string;
}

export const VideoTile: React.FC<VideoTileProps> = ({
  stream,
  isLocal = false,
  displayName = 'Participant',
  isMuted = false,
  className,
}) => {
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<VideoStreamRenderer | null>(null);
  const viewRef = useRef<VideoStreamRendererView | null>(null);
  const [isRendering, setIsRendering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const startRendering = async () => {
      if (!stream || !videoContainerRef.current) {
        return;
      }

      try {
        setError(null);
        
        // Clean up existing renderer
        if (viewRef.current) {
          viewRef.current.dispose();
          viewRef.current = null;
        }
        if (rendererRef.current) {
          rendererRef.current.dispose();
          rendererRef.current = null;
        }

        // Clear container
        if (videoContainerRef.current) {
          videoContainerRef.current.innerHTML = '';
        }

        // Create new renderer
        rendererRef.current = new VideoStreamRenderer(stream);
        viewRef.current = await rendererRef.current.createView({
          scalingMode: 'Crop',
          isMirrored: isLocal,
        });

        // Append to container
        if (videoContainerRef.current && viewRef.current.target) {
          videoContainerRef.current.appendChild(viewRef.current.target);
          setIsRendering(true);
        }

        console.log(`[VideoTile] Started rendering ${isLocal ? 'local' : 'remote'} video`);
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to render video';
        console.error('[VideoTile] Rendering error:', message);
        setError(message);
        setIsRendering(false);
      }
    };

    startRendering();

    return () => {
      if (viewRef.current) {
        viewRef.current.dispose();
        viewRef.current = null;
      }
      if (rendererRef.current) {
        rendererRef.current.dispose();
        rendererRef.current = null;
      }
      setIsRendering(false);
    };
  }, [stream, isLocal]);

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-lg bg-muted',
        isLocal ? 'aspect-video' : 'aspect-video',
        className
      )}
    >
      {/* Video container */}
      <div
        ref={videoContainerRef}
        className="absolute inset-0 w-full h-full [&>div]:w-full [&>div]:h-full [&>video]:w-full [&>video]:h-full [&>video]:object-cover"
      />

      {/* Placeholder when no video */}
      {!isRendering && !error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-muted">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted-foreground/20">
            <User className="h-8 w-8 text-muted-foreground" />
          </div>
          <span className="mt-2 text-sm text-muted-foreground">{displayName}</span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-destructive/10">
          <VideoOff className="h-8 w-8 text-destructive" />
          <span className="mt-2 text-xs text-destructive">Video unavailable</span>
        </div>
      )}

      {/* Overlay with name and mute indicator */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white truncate">
            {isLocal ? 'You' : displayName}
          </span>
          {isMuted && (
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-destructive">
              <VideoOff className="h-3 w-3 text-white" />
            </span>
          )}
        </div>
      </div>

      {/* Local video indicator */}
      {isLocal && (
        <div className="absolute top-2 right-2">
          <span className="flex h-6 items-center gap-1 rounded-full bg-primary/80 px-2 text-xs text-primary-foreground">
            <Video className="h-3 w-3" />
            Live
          </span>
        </div>
      )}
    </div>
  );
};

interface VideoRendererProps {
  localStream: LocalVideoStream | null;
  remoteStreams: Array<{
    stream: RemoteVideoStream;
    participantId: string;
    displayName?: string;
    isMuted?: boolean;
  }>;
  localDisplayName?: string;
  isLocalMuted?: boolean;
  layout?: 'grid' | 'spotlight' | 'pip';
  className?: string;
}

export const VideoRenderer: React.FC<VideoRendererProps> = ({
  localStream,
  remoteStreams,
  localDisplayName = 'You',
  isLocalMuted = false,
  layout = 'grid',
  className,
}) => {
  const hasRemoteParticipants = remoteStreams.length > 0;

  if (layout === 'pip') {
    // Picture-in-picture: Remote large, local small overlay
    return (
      <div className={cn('relative w-full h-full', className)}>
        {/* Main video (first remote or placeholder) */}
        {hasRemoteParticipants ? (
          <VideoTile
            stream={remoteStreams[0].stream}
            displayName={remoteStreams[0].displayName}
            isMuted={remoteStreams[0].isMuted}
            className="w-full h-full"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-muted">
            <div className="text-center">
              <User className="mx-auto h-16 w-16 text-muted-foreground" />
              <p className="mt-4 text-muted-foreground">Waiting for others to join...</p>
            </div>
          </div>
        )}

        {/* Local video overlay */}
        <div className="absolute bottom-4 right-4 w-32 sm:w-48">
          <VideoTile
            stream={localStream}
            isLocal
            displayName={localDisplayName}
            isMuted={isLocalMuted}
            className="shadow-lg ring-2 ring-background"
          />
        </div>
      </div>
    );
  }

  if (layout === 'spotlight') {
    // Spotlight: One main video, others in sidebar
    const mainStream = remoteStreams[0] || null;
    const sideStreams = remoteStreams.slice(1);

    return (
      <div className={cn('flex gap-4 h-full', className)}>
        {/* Main video area */}
        <div className="flex-1">
          {mainStream ? (
            <VideoTile
              stream={mainStream.stream}
              displayName={mainStream.displayName}
              isMuted={mainStream.isMuted}
              className="w-full h-full"
            />
          ) : (
            <VideoTile
              stream={localStream}
              isLocal
              displayName={localDisplayName}
              isMuted={isLocalMuted}
              className="w-full h-full"
            />
          )}
        </div>

        {/* Sidebar with other participants */}
        {(sideStreams.length > 0 || mainStream) && (
          <div className="flex w-48 flex-col gap-2 overflow-y-auto">
            {mainStream && (
              <VideoTile
                stream={localStream}
                isLocal
                displayName={localDisplayName}
                isMuted={isLocalMuted}
              />
            )}
            {sideStreams.map((remote) => (
              <VideoTile
                key={remote.participantId}
                stream={remote.stream}
                displayName={remote.displayName}
                isMuted={remote.isMuted}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // Grid layout (default)
  const allParticipants = [
    { id: 'local', stream: localStream, isLocal: true, displayName: localDisplayName, isMuted: isLocalMuted },
    ...remoteStreams.map((r) => ({
      id: r.participantId,
      stream: r.stream,
      isLocal: false,
      displayName: r.displayName,
      isMuted: r.isMuted,
    })),
  ];

  const gridCols = allParticipants.length <= 1 ? 1 : allParticipants.length <= 4 ? 2 : 3;

  return (
    <div
      className={cn(
        'grid gap-4 h-full w-full',
        gridCols === 1 && 'grid-cols-1',
        gridCols === 2 && 'grid-cols-2',
        gridCols === 3 && 'grid-cols-3',
        className
      )}
    >
      {allParticipants.map((participant) => (
        <VideoTile
          key={participant.id}
          stream={participant.stream as LocalVideoStream | RemoteVideoStream}
          isLocal={participant.isLocal}
          displayName={participant.displayName}
          isMuted={participant.isMuted}
        />
      ))}
    </div>
  );
};

export default VideoRenderer;
