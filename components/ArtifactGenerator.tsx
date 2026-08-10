import React, { useState, useCallback, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { ArtifactType, HistoryItem, LLMSettings, PROVIDER_CATALOG } from '../types';
import { loadLLMSettings, saveLLMSettings, clearLLMSettings, llmHeaders } from '../llmSettings';
import { API_BASE_URL } from '../config';
import SettingsModal from './SettingsModal';
import { CogIcon, CopyIcon, ExportIcon } from './icons';

// Errors whose message is safe to show to the user verbatim
class UserFacingError extends Error {}

// Badge colors per artifact type, used in the history list
const TYPE_BADGE_STYLES: Record<ArtifactType, string> = {
    [ArtifactType.UserStory]: 'bg-indigo-100 text-indigo-700',
    [ArtifactType.Bug]: 'bg-red-100 text-red-700',
    [ArtifactType.Feature]: 'bg-green-100 text-green-700',
    [ArtifactType.Epic]: 'bg-purple-100 text-purple-700',
};

// Tailwind styling for rendered markdown elements (the CDN build has no typography plugin)
const markdownComponents = {
    h1: (props: any) => <h1 className="text-xl font-bold text-gray-900 mt-4 mb-2 first:mt-0" {...props} />,
    h2: (props: any) => <h2 className="text-lg font-semibold text-gray-900 mt-4 mb-2 first:mt-0" {...props} />,
    h3: (props: any) => <h3 className="text-base font-semibold text-gray-900 mt-3 mb-1.5 first:mt-0" {...props} />,
    p: (props: any) => <p className="mb-3 leading-relaxed" {...props} />,
    ul: (props: any) => <ul className="list-disc pl-5 mb-3 space-y-1" {...props} />,
    ol: (props: any) => <ol className="list-decimal pl-5 mb-3 space-y-1" {...props} />,
    li: (props: any) => <li className="leading-relaxed" {...props} />,
    strong: (props: any) => <strong className="font-semibold text-gray-900" {...props} />,
    code: (props: any) => <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono" {...props} />,
    hr: (props: any) => <hr className="my-4 border-gray-200" {...props} />,
};

// --- Input Section Component ---

const InputSection: React.FC<{
    label: string;
    placeholder: string;
    value: string;
    onChange: (e: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => void;
    isTextArea?: boolean;
    maxLength?: number;
    required?: boolean;
}> = ({ label, placeholder, value, onChange, isTextArea = true, maxLength, required = false }) => (
    <div className="mb-6">
        <div className="flex justify-between items-baseline mb-2">
            <label className="block text-sm font-medium text-gray-700">
                {label}
                {required
                    ? <span className="text-red-500 ml-1" title="Required">*</span>
                    : <span className="text-gray-400 ml-1 text-xs font-normal">(optional)</span>}
            </label>
            {maxLength && (
                <span className="text-xs text-gray-500">
                    {value.length}/{maxLength}
                </span>
            )}
        </div>
        {isTextArea ? (
             <textarea
                rows={4}
                className="w-full bg-gray-50 border border-gray-300 rounded-lg p-3 text-gray-800 placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 ease-in-out shadow-inner"
                placeholder={placeholder}
                value={value}
                onChange={onChange}
                maxLength={maxLength}
            />
        ) : (
            <input
                 className="w-full bg-gray-50 border border-gray-300 rounded-lg p-3 text-gray-800 placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 ease-in-out shadow-inner"
                placeholder={placeholder}
                value={value}
                onChange={onChange}
                maxLength={maxLength}
            />
        )}
    </div>
);


// --- Main ArtifactGenerator Component ---

const ArtifactGenerator: React.FC = () => {
    const [scenario, setScenario] = useState('');
    const [persona, setPersona] = useState('');
    const [techInfo, setTechInfo] = useState('');
    const [artifactType, setArtifactType] = useState<ArtifactType>(ArtifactType.UserStory);
    const [generatedArtifact, setGeneratedArtifact] = useState<string>('');
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [selectedHistoryId, setSelectedHistoryId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string>('');
    const [notice, setNotice] = useState<string>('');
    const [historyUnavailable, setHistoryUnavailable] = useState<boolean>(false);
    const [copySuccess, setCopySuccess] = useState<string>('');
    const [llmSettings, setLlmSettings] = useState<LLMSettings | null>(() => loadLLMSettings());
    const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);

    const handleSaveSettings = useCallback((settings: LLMSettings | null) => {
        if (settings) {
            saveLLMSettings(settings);
        } else {
            clearLLMSettings();
        }
        setLlmSettings(settings);
    }, []);

    // --- History Fetching Logic ---
    const fetchHistory = useCallback(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/history`);
            if (!response.ok) throw new Error("Failed to fetch history.");
            const payload = await response.json();
            // The backend wraps results as { status, data }; fall back to a bare array
            const items = Array.isArray(payload) ? payload : payload.data;
            if (!Array.isArray(items)) throw new Error("Unexpected history response shape.");

            const mappedHistory: HistoryItem[] = items.map((item: any) => ({
                id: item.id.toString(),
                title: item.title,
                type: item.type as ArtifactType,
                generatedDate: new Date(item.created_at).toLocaleDateString(undefined, {
                    month: 'numeric', day: 'numeric', year: '2-digit'
                }),
                content: item.artifact_data.raw_output,
            }));
            setHistory(mappedHistory);
            setHistoryUnavailable(false);
        } catch (error) {
            console.error("Error fetching history:", error);
            // Be honest in the UI: an unreachable history is not an empty history
            setHistoryUnavailable(true);
        }
    }, []);

    useEffect(() => {
        fetchHistory();
    }, [fetchHistory]);


    // --- Generation Logic ---
    const handleGenerate = useCallback(async () => {
        if (!scenario || isLoading) return;
        setIsLoading(true);
        setError('');
        setNotice('');

        try {
            const response = await fetch(`${API_BASE_URL}/generate-artifact`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...llmHeaders(llmSettings) },
                body: JSON.stringify({
                    business_use_case: scenario,
                    persona: persona,
                    technical_info: techInfo,
                    artifact_type: artifactType,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                // 400/401/429 carry curated, user-friendly messages from our backend
                if ([400, 401, 429].includes(response.status) && data.detail) {
                    throw new UserFacingError(data.detail);
                }
                throw new Error(data.detail || `HTTP error! Status: ${response.status}`);
            }

            setGeneratedArtifact(data.artifact.raw_output);
            setSelectedHistoryId(null);
            // Non-fatal backend warning (e.g. history unavailable) — the
            // artifact above is still valid, so this is a notice, not an error.
            setNotice(data.warning || '');
            await fetchHistory();

        } catch (error) {
            console.error("Generation Error:", error);
            setError(error instanceof UserFacingError
                ? error.message
                : 'Something went wrong while generating your artifact. Please try again in a moment.');
        } finally {
            setIsLoading(false);
        }
    }, [scenario, persona, techInfo, artifactType, isLoading, fetchHistory, llmSettings]);

    // --- UI Actions ---
    const handleCopy = () => {
        if (!generatedArtifact) return;
        navigator.clipboard.writeText(generatedArtifact).then(() => {
            setCopySuccess('Copied!');
            setTimeout(() => setCopySuccess(''), 2000);
        }, () => {
            setCopySuccess('Failed to copy');
            setTimeout(() => setCopySuccess(''), 2000);
        });
    };

    const handleExport = () => {
        if (!generatedArtifact) return;
        // Build a filename from the artifact's first line (its title)
        const firstLine = generatedArtifact.split('\n')[0].replace(/^#+\s*/, '').trim();
        const slug = firstLine.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 50) || 'artifact';
        const blob = new Blob([generatedArtifact], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${slug}.md`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    };

    const handleHistoryClick = (item: HistoryItem) => {
        setGeneratedArtifact(item.content);
        setSelectedHistoryId(item.id);
        setError('');
    };

    const handleClear = useCallback(() => {
        setScenario('');
        setPersona('');
        setTechInfo('');
    }, []);

    const isClearable = scenario || persona || techInfo;
    const hasArtifact = Boolean(generatedArtifact);

    // --- RENDER ---
    return (
        <div className="p-4 sm:p-6 lg:p-8 flex flex-col h-screen bg-gray-50 text-gray-800">
            <header className="flex justify-between items-center pb-4 border-b border-gray-200 mb-6">
                <h1 className="text-2xl font-bold text-black">AI Artifact Generator</h1>
                <div className="flex items-center space-x-3">
                    <button
                        onClick={() => setIsSettingsOpen(true)}
                        className={`hidden sm:inline-flex items-center px-3 py-1.5 text-xs font-semibold rounded-full transition-colors ${
                            llmSettings
                                ? 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200'
                                : 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200'
                        }`}
                    >
                        {llmSettings
                            ? `${PROVIDER_CATALOG[llmSettings.provider].label} · ${llmSettings.model}`
                            : 'No API key — add yours'}
                    </button>
                    <button
                        onClick={() => setIsSettingsOpen(true)}
                        aria-label="Settings"
                        className="text-gray-500 hover:text-gray-900 transition-colors"
                    >
                        <CogIcon />
                    </button>
                </div>
            </header>

            <SettingsModal
                isOpen={isSettingsOpen}
                settings={llmSettings}
                onSave={handleSaveSettings}
                onClose={() => setIsSettingsOpen(false)}
            />

            <main className="flex-grow grid grid-cols-1 lg:grid-cols-10 gap-6 min-h-0">
                {/* Left Column — inputs */}
                <div className="lg:col-span-3 bg-white p-6 rounded-xl shadow-lg flex flex-col overflow-y-auto">
                    <div className='flex-grow'>
                        <div className="mb-6">
                            <label className="block text-sm font-medium text-gray-700 mb-2">Select Artifact Type</label>
                            <div className="grid grid-cols-2 gap-2">
                                {Object.values(ArtifactType).map((type) => (
                                    <button
                                        key={type}
                                        onClick={() => setArtifactType(type)}
                                        className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors shadow-sm ${
                                            artifactType === type
                                                ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                                        }`}
                                    >
                                        {type}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <InputSection
                            label="Business Use Case / Scenario"
                            placeholder="Describe the business context or user journey..."
                            value={scenario}
                            onChange={(e) => setScenario(e.target.value)}
                            maxLength={1000}
                            required
                        />
                        <InputSection
                            label="Persona (e.g., User, Customer)"
                            placeholder="e.g., A busy project manager"
                            value={persona}
                            onChange={(e) => setPersona(e.target.value)}
                            isTextArea={false}
                            maxLength={100}
                        />
                        <InputSection
                            label="Technical Information (e.g., APIs, Tech Stack)"
                            placeholder="Mention any relevant APIs, frameworks, etc."
                            value={techInfo}
                            onChange={(e) => setTechInfo(e.target.value)}
                            maxLength={500}
                        />
                    </div>
                     <div className="mt-6 flex items-center space-x-4">
                        <button
                            onClick={handleClear}
                            disabled={!isClearable}
                            className="w-1/3 bg-gray-200 text-gray-700 font-bold py-3 px-4 rounded-xl hover:bg-gray-300 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors shadow-md"
                        >
                            Clear
                        </button>
                        <button
                            onClick={handleGenerate}
                            disabled={isLoading || !scenario}
                            className="w-2/3 bg-indigo-600 text-white font-bold py-3 px-4 rounded-xl hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-lg flex items-center justify-center"
                        >
                            {isLoading && <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>}
                            {isLoading ? 'Generating...' : 'Generate Artifact'}
                        </button>
                    </div>
                </div>

                {/* Center Column — output */}
                <div className="lg:col-span-5 bg-white p-6 rounded-xl shadow-lg flex flex-col">
                    <div className="flex justify-between items-center mb-4 border-b border-gray-100 pb-3">
                        <h2 className="text-lg font-semibold text-black">Generated Artifact</h2>
                        <div className="flex items-center space-x-4">
                            {copySuccess && <span aria-live="polite" className="text-sm text-green-600">{copySuccess}</span>}
                            <button
                                onClick={handleCopy}
                                disabled={!hasArtifact}
                                className="flex items-center space-x-2 text-gray-500 hover:text-indigo-600 disabled:text-gray-300 disabled:cursor-not-allowed transition-colors"
                            >
                                <CopyIcon />
                                <span>Copy</span>
                            </button>
                            <button
                                onClick={handleExport}
                                disabled={!hasArtifact}
                                className="flex items-center space-x-2 text-gray-500 hover:text-indigo-600 disabled:text-gray-300 disabled:cursor-not-allowed transition-colors"
                            >
                                <ExportIcon />
                                <span>Export</span>
                            </button>
                        </div>
                    </div>
                    {error && (
                        <div className="mb-4 flex items-start justify-between bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3" role="alert">
                            <span>{error}</span>
                            <button
                                onClick={() => setError('')}
                                aria-label="Dismiss error"
                                className="ml-3 font-bold text-red-500 hover:text-red-800"
                            >
                                &times;
                            </button>
                        </div>
                    )}
                    {notice && !error && (
                        <div className="mb-4 flex items-start justify-between bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-lg p-3" role="status">
                            <span>{notice}</span>
                            <button
                                onClick={() => setNotice('')}
                                aria-label="Dismiss notice"
                                className="ml-3 font-bold text-amber-600 hover:text-amber-900"
                            >
                                &times;
                            </button>
                        </div>
                    )}
                    <div className="relative flex-grow bg-gray-50 rounded-lg border border-gray-200 p-4 overflow-y-auto text-gray-800 text-sm">
                        {isLoading && (
                            <div className="absolute inset-0 bg-white/70 flex flex-col items-center justify-center rounded-lg z-10">
                                <svg className="animate-spin h-8 w-8 text-indigo-600 mb-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                <p className="text-sm text-gray-600">Generating your artifact…</p>
                            </div>
                        )}
                        {hasArtifact ? (
                            <ReactMarkdown components={markdownComponents}>{generatedArtifact}</ReactMarkdown>
                        ) : (
                            !isLoading && (
                                <div className="h-full flex flex-col items-center justify-center text-center text-gray-400 px-6">
                                    <ExportIcon className="h-10 w-10 mb-3" />
                                    <p className="font-medium text-gray-500 mb-1">No artifact yet</p>
                                    <p className="text-sm">Describe your business use case on the left, pick an artifact type, and click Generate.</p>
                                </div>
                            )
                        )}
                    </div>
                </div>

                {/* Right Column — history */}
                <div className="lg:col-span-2 bg-white p-6 rounded-xl shadow-lg flex flex-col">
                    <h2 className="text-lg font-semibold text-black mb-4 border-b border-gray-100 pb-3">History</h2>
                    <div className="overflow-y-auto space-y-3">
                        {history.length === 0 && (
                            historyUnavailable
                                ? <p className="text-amber-700 text-sm">History is unavailable right now. You can still generate artifacts — they just won't be saved.</p>
                                : <p className="text-gray-500 text-sm">History is empty. Generate your first artifact!</p>
                        )}
                        {history.map((item) => (
                            <button
                                key={item.id}
                                onClick={() => handleHistoryClick(item)}
                                className={`w-full text-left p-3 rounded-lg transition-colors border shadow-sm ${
                                    selectedHistoryId === item.id
                                        ? 'bg-indigo-50 border-indigo-300'
                                        : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                                }`}
                            >
                                <p className="font-semibold text-sm text-gray-800 truncate">{item.title}</p>
                                <div className="flex items-center justify-between mt-1">
                                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${TYPE_BADGE_STYLES[item.type] ?? 'bg-gray-100 text-gray-600'}`}>
                                        {item.type}
                                    </span>
                                    <span className="text-xs text-gray-500">{item.generatedDate}</span>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
            </main>
        </div>
    );
};

export default ArtifactGenerator;
