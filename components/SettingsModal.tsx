import React, { useState, useEffect, useCallback } from 'react';
import { LLMSettings, LLMProviderId, PROVIDER_CATALOG } from '../types';
import { llmHeaders } from '../llmSettings';
import { API_BASE_URL } from '../config';

type TestState =
  | { status: 'idle' }
  | { status: 'testing' }
  | { status: 'ok'; message: string }
  | { status: 'fail'; message: string };

const SettingsModal: React.FC<{
  isOpen: boolean;
  settings: LLMSettings | null;
  onSave: (settings: LLMSettings | null) => void;
  onClose: () => void;
}> = ({ isOpen, settings, onSave, onClose }) => {
  const [provider, setProvider] = useState<LLMProviderId>('gemini');
  const [model, setModel] = useState<string>(PROVIDER_CATALOG.gemini.models[0]);
  const [apiKey, setApiKey] = useState('');
  const [remember, setRemember] = useState(true);
  const [showKey, setShowKey] = useState(false);
  const [test, setTest] = useState<TestState>({ status: 'idle' });

  // Sync the draft with the saved settings each time the modal opens
  useEffect(() => {
    if (isOpen) {
      setProvider(settings?.provider ?? 'gemini');
      setModel(settings?.model ?? PROVIDER_CATALOG[settings?.provider ?? 'gemini'].models[0]);
      setApiKey(settings?.apiKey ?? '');
      setRemember(settings?.remember ?? true);
      setShowKey(false);
      setTest({ status: 'idle' });
    }
  }, [isOpen, settings]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, onClose]);

  const handleProviderChange = (id: LLMProviderId) => {
    setProvider(id);
    setModel(PROVIDER_CATALOG[id].models[0]);
    setTest({ status: 'idle' });
  };

  const handleTest = useCallback(async () => {
    const trimmed = apiKey.trim();
    if (!trimmed) return;
    setTest({ status: 'testing' });
    try {
      const response = await fetch(`${API_BASE_URL}/validate-key`, {
        method: 'POST',
        headers: llmHeaders({ provider, model, apiKey: trimmed, remember }),
      });
      const data = await response.json().catch(() => ({}));
      if (response.ok) {
        setTest({ status: 'ok', message: `Key works — connected to ${PROVIDER_CATALOG[provider].label}.` });
      } else {
        setTest({ status: 'fail', message: data.detail || 'The provider rejected this key.' });
      }
    } catch {
      setTest({ status: 'fail', message: 'Could not reach the server to test the key.' });
    }
  }, [apiKey, provider, model, remember]);

  const handleSave = () => {
    const trimmed = apiKey.trim();
    if (!trimmed) {
      onSave(null);
    } else {
      onSave({ provider, model, apiKey: trimmed, remember });
    }
    onClose();
  };

  if (!isOpen) return null;

  const info = PROVIDER_CATALOG[provider];

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="LLM API key settings"
        className="bg-white rounded-xl shadow-2xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold text-black">Settings — your AI provider</h2>
          <button
            onClick={onClose}
            aria-label="Close settings"
            className="text-gray-400 hover:text-gray-700 text-xl leading-none"
          >
            &times;
          </button>
        </div>

        <p className="text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-lg p-3 mb-5">
          Your API key is stored only in this browser and sent over HTTPS with each request.
          It is never saved or logged on our servers.
        </p>

        <label className="block text-sm font-medium text-gray-700 mb-2">Provider</label>
        <div className="grid grid-cols-3 gap-2 mb-4">
          {(Object.keys(PROVIDER_CATALOG) as LLMProviderId[]).map((id) => (
            <button
              key={id}
              onClick={() => handleProviderChange(id)}
              className={`px-2 py-2 text-xs font-semibold rounded-lg transition-colors ${
                provider === id
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {PROVIDER_CATALOG[id].label}
            </button>
          ))}
        </div>

        <label htmlFor="llm-model" className="block text-sm font-medium text-gray-700 mb-2">Model</label>
        <select
          id="llm-model"
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="w-full bg-gray-50 border border-gray-300 rounded-lg p-2.5 text-gray-800 mb-4 focus:ring-2 focus:ring-indigo-500"
        >
          {info.models.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>

        <div className="flex justify-between items-baseline mb-2">
          <label htmlFor="llm-key" className="block text-sm font-medium text-gray-700">API key</label>
          <a
            href={info.consoleUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-indigo-600 hover:underline"
          >
            Get a key
          </a>
        </div>
        <div className="flex gap-2 mb-2">
          <input
            id="llm-key"
            type={showKey ? 'text' : 'password'}
            autoComplete="off"
            spellCheck={false}
            placeholder={info.keyHint}
            value={apiKey}
            onChange={(e) => { setApiKey(e.target.value); setTest({ status: 'idle' }); }}
            className="flex-grow bg-gray-50 border border-gray-300 rounded-lg p-2.5 text-gray-800 placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
          />
          <button
            onClick={() => setShowKey(!showKey)}
            className="px-3 text-xs font-semibold text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200"
          >
            {showKey ? 'Hide' : 'Show'}
          </button>
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-600 mb-4 cursor-pointer">
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          Remember on this device (uncheck on shared computers — kept for this tab only)
        </label>

        <div className="min-h-[24px] mb-4" aria-live="polite">
          {test.status === 'testing' && <span className="text-sm text-gray-500">Testing your key…</span>}
          {test.status === 'ok' && <span className="text-sm text-green-600">✓ {test.message}</span>}
          {test.status === 'fail' && <span className="text-sm text-red-600">✗ {test.message}</span>}
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleTest}
            disabled={!apiKey.trim() || test.status === 'testing'}
            className="flex-1 bg-gray-200 text-gray-700 font-semibold py-2.5 px-4 rounded-lg hover:bg-gray-300 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            Test connection
          </button>
          <button
            onClick={handleSave}
            className="flex-1 bg-indigo-600 text-white font-semibold py-2.5 px-4 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Save
          </button>
        </div>
        {settings?.apiKey && (
          <button
            onClick={() => { onSave(null); onClose(); }}
            className="w-full mt-3 text-xs text-red-500 hover:text-red-700 hover:underline"
          >
            Remove saved key from this browser
          </button>
        )}
      </div>
    </div>
  );
};

export default SettingsModal;
