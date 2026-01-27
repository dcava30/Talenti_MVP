import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { candidatesApi } from "@/api/candidates";
import { toast } from "sonner";

/**
 * Represents a data deletion request for GDPR compliance.
 */
interface DeletionRequest {
  /** Unique identifier for the deletion request */
  id: string;
  /** ID of the user who made the request */
  user_id: string;
  /** Type of deletion: "full_deletion", "recording_only", or "anonymize" */
  request_type: string;
  /** Current status of the request */
  status: string;
  /** Optional reason provided by the user */
  reason: string | null;
  /** Timestamp when the request was made */
  requested_at: string;
  /** Timestamp when the request was processed (if applicable) */
  processed_at: string | null;
  /** ID of the admin who processed the request (if applicable) */
  processed_by: string | null;
  /** Additional notes from processing */
  notes: string | null;
}

/**
 * Hook for fetching the current user's data deletion requests.
 * 
 * Used for GDPR compliance to allow users to view their pending
 * and historical deletion requests.
 * 
 * @returns React Query result with array of deletion requests
 * 
 * @example
 * ```tsx
 * const { data: requests, isLoading } = useDeletionRequests();
 * 
 * return (
 *   <ul>
 *     {requests?.map(req => (
 *       <li key={req.id}>{req.request_type} - {req.status}</li>
 *     ))}
 *   </ul>
 * );
 * ```
 */
export const useDeletionRequests = () => {
  return useQuery({
    queryKey: ["deletion-requests"],
    queryFn: async (): Promise<DeletionRequest[]> => {
      const data = await candidatesApi.listDeletionRequests();
      return data as DeletionRequest[];
    },
  });
};

/**
 * Hook for creating new data deletion requests.
 * 
 * Provides a mutation to submit GDPR deletion requests with
 * automatic cache invalidation and toast notifications.
 * 
 * @returns React Query mutation for creating deletion requests
 * 
 * @example
 * ```tsx
 * const createRequest = useCreateDeletionRequest();
 * 
 * const handleDelete = async () => {
 *   await createRequest.mutateAsync({
 *     requestType: "full_deletion",
 *     reason: "No longer using the service"
 *   });
 * };
 * ```
 */
export const useCreateDeletionRequest = () => {
  const queryClient = useQueryClient();

  return useMutation({
    /**
     * Creates a new deletion request in the database.
     * 
     * @param params - The deletion request parameters
     * @param params.requestType - Type of deletion to perform
     * @param params.reason - Optional reason for the request
     * @returns The created deletion request record
     */
    mutationFn: async ({ 
      requestType, 
      reason 
    }: { 
      requestType: "full_deletion" | "recording_only" | "anonymize";
      reason?: string;
    }) => {
      return candidatesApi.createDeletionRequest({
        request_type: requestType,
        reason: reason || null,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["deletion-requests"] });
      toast.success("Deletion request submitted successfully");
    },
    onError: (error) => {
      console.error("Error creating deletion request:", error);
      toast.error("Failed to submit deletion request");
    },
  });
};
