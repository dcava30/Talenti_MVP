import { useState, useCallback } from "react";
import { authApi } from "@/api/auth";
import { interviewsApi } from "@/api/interviews";
import { rolesApi } from "@/api/roles";
import { candidatesApi } from "@/api/candidates";

/**
 * Represents a single segment of interview transcript.
 */
interface TranscriptSegment {
  /** Who spoke this segment: "ai" or "candidate" */
  speaker: "ai" | "candidate";
  /** The text content of what was said */
  content: string;
  /** Start time in milliseconds from interview start */
  startTimeMs: number;
  /** End time in milliseconds from interview start */
  endTimeMs?: number;
}

/**
 * Represents an anti-cheat signal detected during the interview.
 */
interface AntiCheatSignal {
  /** Type of suspicious activity detected */
  type: "silence" | "latency" | "tab_switch";
  /** When the signal was detected */
  timestamp: Date;
  /** Duration of the suspicious activity in milliseconds */
  duration?: number;
}

/**
 * Hook for managing interview data persistence.
 * 
 * Handles creating interview records, saving transcript segments,
 * recording anti-cheat signals, and completing interviews with scoring.
 * 
 * @returns Object with persistence functions and state
 * 
 * @example
 * ```tsx
 * const {
 *   createInterview,
 *   saveTranscriptSegment,
 *   completeInterview,
 *   interviewId,
 *   isLoading,
 * } = useInterviewPersistence();
 * 
 * // Start the interview
 * const id = await createInterview(applicationId);
 * 
 * // Save each transcript segment
 * await saveTranscriptSegment(id, {
 *   speaker: "candidate",
 *   content: transcript,
 *   startTimeMs: Date.now() - startTime,
 * });
 * 
 * // Complete the interview
 * await completeInterview(id, durationSeconds, antiCheatSignals);
 * ```
 */
export const useInterviewPersistence = () => {
  const [interviewId, setInterviewId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Creates a new interview record or resumes an existing one.
   * 
   * Checks for existing in-progress interviews for the application
   * and resumes them if found, otherwise creates a new record.
   * 
   * @param applicationId - The UUID of the application to create interview for
   * @returns The interview ID on success, or null on failure
   */
  const createInterview = useCallback(async (applicationId: string): Promise<string | null> => {
    setIsLoading(true);
    setError(null);

    try {
      // Check for existing in_progress interview
      const existing = await interviewsApi.findActive(applicationId);

      if (existing) {
        // Update to in_progress
        await interviewsApi.update(existing.id, {
          status: "in_progress",
          started_at: new Date().toISOString(),
        });
        setInterviewId(existing.id);
        console.log("Resumed existing interview:", existing.id);
        return existing.id;
      }

      // Create new interview
      const data = await interviewsApi.create({
        application_id: applicationId,
        status: "in_progress",
        started_at: new Date().toISOString(),
        anti_cheat_signals: [],
        metadata: {},
      });

      setInterviewId(data.id);
      console.log("Created new interview:", data.id);
      return data.id;
    } catch (err) {
      console.error("Failed to create interview:", err);
      setError(err instanceof Error ? err.message : "Failed to create interview");
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Saves a transcript segment to the database.
   * 
   * @param interviewIdParam - The UUID of the interview
   * @param segment - The transcript segment to save
   */
  const saveTranscriptSegment = useCallback(async (
    interviewIdParam: string,
    segment: TranscriptSegment
  ): Promise<void> => {
    try {
      await interviewsApi.addTranscript(interviewIdParam, {
        speaker: segment.speaker,
        content: segment.content,
        start_time_ms: segment.startTimeMs,
        end_time_ms: segment.endTimeMs,
      });
      console.log("Saved transcript segment:", segment.speaker);
    } catch (err) {
      console.error("Failed to save transcript segment:", err);
    }
  }, []);

  /**
   * Updates the anti-cheat signals for an interview.
   * 
   * @param interviewIdParam - The UUID of the interview
   * @param signals - Array of anti-cheat signals to store
   */
  const updateAntiCheatSignals = useCallback(async (
    interviewIdParam: string,
    signals: AntiCheatSignal[]
  ): Promise<void> => {
    try {
      await interviewsApi.update(interviewIdParam, {
        anti_cheat_signals: signals.map(s => ({
          type: s.type,
          timestamp: s.timestamp.toISOString(),
          duration: s.duration,
        })),
      });
      console.log("Updated anti-cheat signals:", signals.length);
    } catch (err) {
      console.error("Failed to update anti-cheat signals:", err);
    }
  }, []);

  /**
   * Completes an interview and triggers the scoring process.
   * 
   * Updates the interview status to "completed", sets the end time,
   * and updates the application status to "scoring".
   * 
   * @param interviewIdParam - The UUID of the interview
   * @param durationSeconds - Total duration of the interview in seconds
   * @param antiCheatSignals - Final anti-cheat signals to store
   * @returns true on success, false on failure
   */
  const completeInterview = useCallback(async (
    interviewIdParam: string,
    durationSeconds: number,
    antiCheatSignals: AntiCheatSignal[]
  ): Promise<boolean> => {
    setIsLoading(true);

    try {
      await interviewsApi.update(interviewIdParam, {
        status: "completed",
        ended_at: new Date().toISOString(),
        duration_seconds: durationSeconds,
        anti_cheat_signals: antiCheatSignals.map(s => ({
          type: s.type,
          timestamp: s.timestamp.toISOString(),
          duration: s.duration,
        })),
      });

      // Update application status to scoring
      const interview = await interviewsApi.getById(interviewIdParam);
      if (interview?.application_id) {
        await interviewsApi.updateApplication(interview.application_id, { status: "scoring" });
      }

      console.log("Interview completed:", interviewIdParam);
      return true;
    } catch (err) {
      console.error("Failed to complete interview:", err);
      setError(err instanceof Error ? err.message : "Failed to complete interview");
      return false;
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Gets or creates a demo application for testing purposes.
   * 
   * Checks for existing applications for the current user.
   * If none exist, creates a demo application using the first available job role.
   * 
   * @returns The application ID, or null if creation failed
   */
  const getOrCreateDemoApplication = useCallback(async (): Promise<string | null> => {
    try {
      const user = await authApi.me();
      if (!user) {
        console.log("No authenticated user");
        return null;
      }

      // Check for existing application
      const existingApplications = await interviewsApi.listCandidateApplications(user.id);
      const existing = existingApplications?.[0];
      if (existing?.id) {
        return existing.id;
      }

      // For demo, we need a job role - check if any exist
      const roles = await rolesApi.listAll({ limit: 1 });
      if (!roles || roles.length === 0) {
        console.log("No job roles available for demo application");
        return null;
      }

      // Create demo application
      const data = await candidatesApi.createApplication({
        candidate_id: user.id,
        job_role_id: roles[0].id,
        status: "invited",
      });
      return data.id;
    } catch (err) {
      console.error("Failed to get/create demo application:", err);
      return null;
    }
  }, []);

  return {
    /** Current interview ID, if one has been created */
    interviewId,
    /** Whether a persistence operation is in progress */
    isLoading,
    /** Error message from the last failed operation */
    error,
    /** Creates or resumes an interview */
    createInterview,
    /** Saves a transcript segment */
    saveTranscriptSegment,
    /** Updates anti-cheat signals */
    updateAntiCheatSignals,
    /** Completes the interview and triggers scoring */
    completeInterview,
    /** Gets or creates a demo application for testing */
    getOrCreateDemoApplication,
  };
};
