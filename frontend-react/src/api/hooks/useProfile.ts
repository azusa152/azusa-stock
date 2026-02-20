import { useQuery } from "@tanstack/react-query"
import apiClient from "../client"

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: async () => {
      const { data } = await apiClient.get("/profiles")
      return data
    },
  })
}
