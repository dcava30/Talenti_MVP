import { useState, useEffect, useRef, useCallback } from "react";
/**
 * Hook for browser-native speech recognition using the Web Speech API.
 *
 * Provides a fallback speech-to-text solution when Azure Speech is not available.
 * Supports continuous listening with interim and final results.
 *
 * @param options - Configuration options for speech recognition
 * @returns Object with recognition controls and state
 *
 * @example
 * ```tsx
 * const {
 *   isListening,
 *   transcript,
 *   interimTranscript,
 *   isSupported,
 *   startListening,
 *   stopListening,
 *   resetTranscript,
 * } = useSpeechRecognition({
 *   onResult: (text) => console.log("Heard:", text),
 *   continuous: true,
 * });
 *
 * return (
 *   <div>
 *     <button onClick={isListening ? stopListening : startListening}>
 *       {isListening ? "Stop" : "Start"} Listening
 *     </button>
 *     <p>Final: {transcript}</p>
 *     <p>Interim: {interimTranscript}</p>
 *   </div>
 * );
 * ```
 */
export const useSpeechRecognition = (options = {}) => {
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState("");
    const [interimTranscript, setInterimTranscript] = useState("");
    const [isSupported, setIsSupported] = useState(false);
    const recognitionRef = useRef(null);
    useEffect(() => {
        const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
        setIsSupported(!!SpeechRecognitionAPI);
        if (SpeechRecognitionAPI) {
            const recognition = new SpeechRecognitionAPI();
            recognition.continuous = options.continuous ?? true;
            recognition.interimResults = options.interimResults ?? true;
            recognition.lang = "en-US";
            recognition.onresult = (event) => {
                let finalTranscript = "";
                let interimText = "";
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const result = event.results[i];
                    if (result.isFinal) {
                        finalTranscript += result[0].transcript;
                    }
                    else {
                        interimText += result[0].transcript;
                    }
                }
                if (finalTranscript) {
                    setTranscript((prev) => prev + " " + finalTranscript);
                    options.onResult?.(finalTranscript);
                }
                setInterimTranscript(interimText);
            };
            recognition.onend = () => {
                setIsListening(false);
                options.onEnd?.();
            };
            recognition.onerror = (event) => {
                console.error("Speech recognition error:", event.error);
                if (event.error !== "aborted") {
                    setIsListening(false);
                }
            };
            recognitionRef.current = recognition;
        }
        return () => {
            recognitionRef.current?.abort();
        };
    }, []);
    /**
     * Starts speech recognition.
     * Clears previous transcript before starting.
     */
    const startListening = useCallback(() => {
        if (recognitionRef.current && !isListening) {
            setTranscript("");
            setInterimTranscript("");
            try {
                recognitionRef.current.start();
                setIsListening(true);
            }
            catch (error) {
                console.error("Failed to start speech recognition:", error);
            }
        }
    }, [isListening]);
    /**
     * Stops speech recognition.
     */
    const stopListening = useCallback(() => {
        if (recognitionRef.current && isListening) {
            recognitionRef.current.stop();
            setIsListening(false);
        }
    }, [isListening]);
    /**
     * Clears both final and interim transcripts.
     */
    const resetTranscript = useCallback(() => {
        setTranscript("");
        setInterimTranscript("");
    }, []);
    return {
        /** Whether speech recognition is currently active */
        isListening,
        /** Accumulated final transcript text */
        transcript: transcript.trim(),
        /** Current interim (in-progress) transcript */
        interimTranscript,
        /** Whether the browser supports speech recognition */
        isSupported,
        /** Starts listening for speech */
        startListening,
        /** Stops listening for speech */
        stopListening,
        /** Clears all transcript data */
        resetTranscript,
    };
};
