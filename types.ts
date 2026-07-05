
export enum ArtifactType {
  UserStory = "User Story",
  Bug = "Bug",
  Feature = "Feature",
  Epic = "Epic",
}

export interface HistoryItem {
  id: string;
  title: string;
  generatedDate: string;
  content: string;
  type: ArtifactType;
}

// --- Bring-your-own-key (BYOK) types ---

export type LLMProviderId = 'gemini' | 'openai' | 'anthropic';

export interface LLMSettings {
  provider: LLMProviderId;
  model: string;
  apiKey: string;
  // true = persist across sessions (localStorage), false = this tab only (sessionStorage)
  remember: boolean;
}

export interface ProviderInfo {
  label: string;
  models: string[];
  keyHint: string;
  consoleUrl: string;
}

export const PROVIDER_CATALOG: Record<LLMProviderId, ProviderInfo> = {
  gemini: {
    label: 'Google Gemini',
    models: ['gemini-2.5-flash', 'gemini-2.5-pro'],
    keyHint: 'AIza…',
    consoleUrl: 'https://aistudio.google.com/apikey',
  },
  openai: {
    label: 'OpenAI',
    models: ['gpt-4o-mini', 'gpt-4o'],
    keyHint: 'sk-…',
    consoleUrl: 'https://platform.openai.com/api-keys',
  },
  anthropic: {
    label: 'Anthropic Claude',
    models: ['claude-haiku-4-5', 'claude-sonnet-5'],
    keyHint: 'sk-ant-…',
    consoleUrl: 'https://console.anthropic.com/settings/keys',
  },
};
