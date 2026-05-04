import { apiRequest } from "./client";
import type { ProviderDefinition } from "../types/pipeline";

export function listProviders() {
  return apiRequest<ProviderDefinition[]>("/api/providers");
}
