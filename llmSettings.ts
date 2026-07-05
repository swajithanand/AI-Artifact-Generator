import { LLMSettings, PROVIDER_CATALOG } from './types';

// Keys live only in the user's browser storage — they are never persisted server-side.
const STORAGE_KEY = 'artifact-generator.llm-settings';

export function loadLLMSettings(): LLMSettings | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY) ?? localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (
      !parsed ||
      !PROVIDER_CATALOG[parsed.provider as keyof typeof PROVIDER_CATALOG] ||
      typeof parsed.apiKey !== 'string' ||
      typeof parsed.model !== 'string'
    ) {
      return null;
    }
    return {
      provider: parsed.provider,
      model: parsed.model,
      apiKey: parsed.apiKey,
      remember: Boolean(parsed.remember),
    };
  } catch {
    return null;
  }
}

export function saveLLMSettings(settings: LLMSettings): void {
  const raw = JSON.stringify(settings);
  if (settings.remember) {
    localStorage.setItem(STORAGE_KEY, raw);
    sessionStorage.removeItem(STORAGE_KEY);
  } else {
    sessionStorage.setItem(STORAGE_KEY, raw);
    localStorage.removeItem(STORAGE_KEY);
  }
}

export function clearLLMSettings(): void {
  localStorage.removeItem(STORAGE_KEY);
  sessionStorage.removeItem(STORAGE_KEY);
}

// Headers attached to API calls. The key travels only over HTTPS and only as a
// header (never in the URL, where it would end up in access logs).
export function llmHeaders(settings: LLMSettings | null): Record<string, string> {
  if (!settings || !settings.apiKey) return {};
  return {
    'X-LLM-Provider': settings.provider,
    'X-LLM-Model': settings.model,
    'X-LLM-Key': settings.apiKey,
  };
}
