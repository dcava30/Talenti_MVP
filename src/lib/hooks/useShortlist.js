import { useState } from "react";
import { shortlistApi } from "@/api/shortlist";
import { toast } from "sonner";
/**
 * Hook for generating AI-powered candidate shortlists for job roles.
 *
 * Uses the AI backend to analyze candidates and rank them based on
 * job requirements, skills matching, and other relevant factors.
 *
 * @returns Object containing shortlist generation function and state
 *
 * @example
 * ```tsx
 * const { generateShortlist, isGenerating, shortlistData, clearShortlist } = useShortlist();
 *
 * const handleGenerate = async () => {
 *   const result = await generateShortlist(roleId);
 *   if (result) {
 *     console.log(`Found ${result.matches.length} candidates`);
 *   }
 * };
 * ```
 */
export function useShortlist() {
    const [isGenerating, setIsGenerating] = useState(false);
    const [shortlistData, setShortlistData] = useState(null);
    /**
     * Generates an AI-powered shortlist of candidates for a specific job role.
     *
     * @param roleId - The UUID of the job role to generate shortlist for
     * @returns The shortlist result on success, or null on failure
     */
    const generateShortlist = async (roleId) => {
        setIsGenerating(true);
        try {
            const data = await shortlistApi.generate({ roleId });
            if (data?.error) {
                if (data.error.includes('Rate limit')) {
                    toast.error('Rate limit exceeded. Please try again in a moment.');
                }
                else if (data.error.includes('Usage limit')) {
                    toast.error('AI usage limit reached. Please contact support.');
                }
                else {
                    toast.error(data.error);
                }
                return null;
            }
            setShortlistData(data);
            toast.success(`Generated shortlist with ${data.matches?.length || 0} candidates`);
            return data;
        }
        catch (err) {
            console.error('Error calling shortlist function:', err);
            toast.error('Failed to connect to AI service');
            return null;
        }
        finally {
            setIsGenerating(false);
        }
    };
    /**
     * Clears the current shortlist data from state.
     */
    const clearShortlist = () => {
        setShortlistData(null);
    };
    return {
        /** Generates a new AI shortlist for a role */
        generateShortlist,
        /** Clears the current shortlist */
        clearShortlist,
        /** Whether shortlist generation is in progress */
        isGenerating,
        /** The current shortlist data, or null if none */
        shortlistData,
    };
}
