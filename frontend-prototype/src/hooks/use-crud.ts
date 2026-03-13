import {
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface ListResponse<T> {
  results: T[];
  next: string | null;
}

export function useCrud<T extends { id: string }>(basePath: string) {
  const queryClient = useQueryClient();
  const queryKey = [basePath];

  const listQuery = useQuery({
    queryKey,
    queryFn: () => apiClient<ListResponse<T>>(basePath),
  });

  const createMutation = useMutation({
    mutationFn: (data: Partial<T>) =>
      apiClient<T>(basePath, { method: "POST", body: data }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<T> }) =>
      apiClient<T>(`${basePath}${id}/`, { method: "PATCH", body: data }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) =>
      apiClient<void>(`${basePath}${id}/`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  return {
    items: listQuery.data?.results ?? [],
    isLoading: listQuery.isLoading,
    error: listQuery.error,
    create: createMutation.mutateAsync,
    update: updateMutation.mutateAsync,
    remove: removeMutation.mutateAsync,
    isCreating: createMutation.isPending,
    isUpdating: updateMutation.isPending,
    isRemoving: removeMutation.isPending,
    refetch: listQuery.refetch,
  };
}
