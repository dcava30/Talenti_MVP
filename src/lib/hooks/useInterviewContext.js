import { useState, useEffect } from "react";
import { interviewsApi } from "@/api/interviews";
/**
 * Hook for loading and managing interview context (CAG).
 *
 * Fetches job requirements, organisation values, and candidate
 * information to provide the AI interviewer with full context.
 * Tracks which competencies have been covered during the interview.
 *
 * @param applicationId - The UUID of the application being interviewed
 * @returns Object with context data, loading state, and control functions
 *
 * @example
 * ```tsx
 * const { context, isLoading, markCompetencyCovered } = useInterviewContext(appId);
 *
 * // Pass context to AI
 * const aiResponse = await callAIInterviewer({
 *   context,
 *   candidateResponse: transcript,
 * });
 *
 * // Mark competencies as covered
 * markCompetencyCovered("React Experience");
 * ```
 */
export const useInterviewContext = (applicationId) => {
    const [context, setContext] = useState({
        job: null,
        org: null,
        candidate: null,
        competenciesCovered: [],
        competenciesToCover: [],
    });
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    useEffect(() => {
        if (applicationId) {
            loadContext();
        }
        else {
            setIsLoading(false);
        }
    }, [applicationId]);
    /**
     * Loads all context data from the database.
     * Fetches application, job role, organisation, and candidate data.
     */
    const loadContext = async () => {
        try {
            setIsLoading(true);
            setError(null);
            const contextData = await interviewsApi.getContext(applicationId);
            setContext({
                job: contextData?.job ?? null,
                org: contextData?.org ?? null,
                candidate: contextData?.candidate ?? null,
                competenciesCovered: contextData?.competencies_covered ?? [],
                competenciesToCover: contextData?.competencies_to_cover ?? [],
            });
        }
        catch (err) {
            console.error("Error loading interview context:", err);
            setError(err instanceof Error ? err.message : "Failed to load context");
        }
        finally {
            setIsLoading(false);
        }
    };
    /**
     * Marks a competency as covered during the interview.
     * Moves it from competenciesToCover to competenciesCovered.
     *
     * @param competency - The competency name to mark as covered
     */
    const markCompetencyCovered = (competency) => {
        setContext(prev => ({
            ...prev,
            competenciesCovered: [...prev.competenciesCovered, competency],
            competenciesToCover: prev.competenciesToCover.filter(c => c !== competency),
        }));
    };
    return {
        /** The loaded CAG context */
        context,
        /** Whether context is still loading */
        isLoading,
        /** Error message if loading failed */
        error,
        /** Marks a competency as covered */
        markCompetencyCovered,
        /** Reloads the context data */
        reload: loadContext,
    };
};
