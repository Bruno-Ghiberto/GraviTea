import { useInfiniteQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";

interface PaginatedResponse<T> {
  results: T[];
  next: string | null;
}

function extractCursor(nextUrl: string | null): string | undefined {
  if (!nextUrl) return undefined;
  try {
    const url = new URL(nextUrl);
    return url.searchParams.get("cursor") ?? undefined;
  } catch {
    return undefined;
  }
}

export function usePagination<T>(
  basePath: string,
  params?: Record<string, string>,
) {
  const queryKey = [basePath, params];

  const query = useInfiniteQuery({
    queryKey,
    queryFn: async ({ pageParam }) => {
      const searchParams = new URLSearchParams(params);
      if (pageParam) {
        searchParams.set("cursor", pageParam as string);
      }
      const qs = searchParams.toString();
      const url = qs ? `${basePath}?${qs}` : basePath;
      return apiClient<PaginatedResponse<T>>(url);
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => extractCursor(lastPage.next),
  });

  const allItems = query.data?.pages.flatMap((page) => page.results) ?? [];

  return {
    data: allItems,
    isLoading: query.isLoading,
    hasNextPage: query.hasNextPage,
    fetchNextPage: query.fetchNextPage,
    isFetchingNextPage: query.isFetchingNextPage,
    error: query.error,
    refetch: query.refetch,
  };
}
