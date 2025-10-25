import React, { useState, useCallback, useEffect } from 'react';
// Note: We need a basic type definition for ArtifactType and HistoryItem
// Since you are running in AI Studio, we'll define them here for simplicity.

// We must explicitly define the types used in the file
enum ArtifactType {
    UserStory = 'User Story',
    Bug = 'Bug',
    Feature = 'Feature',
    Epic = 'Epic',
}

interface HistoryItem {
    id: string;
    title: string;
    type: ArtifactType;
    generatedDate: string;
    content: string;
}

// NOTE: THE BACKEND IS RUNNING ON PORT 8000
const API_BASE_URL = 'ai-artifact-generator-production.up.railway.app'; 

import { CogIcon, CopyIcon, ExportIcon } from './icons'; 

// --- Input Section Component (Updated for Light Mode) ---

const InputSection: React.FC<{
    label: string;
    placeholder: string;
    value: string;
    onChange: (e: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) => void;
    isTextArea?: boolean;
    maxLength?: number;
}> = ({ label, placeholder, value, onChange, isTextArea = true, maxLength }) => (
    <div className="mb-6">
        <div className="flex justify-between items-baseline mb-2">
            <label className="block text-sm font-medium text-gray-700">{label}</label>
            {maxLength && (
                <span className="text-xs text-gray-500">
                    {value.length}/{maxLength}
                </span>
            )}
        </div>
        {isTextArea ? (
             <textarea
                rows={4}
                // Updated Tailwind classes for a light, clean input look
                className="w-full bg-gray-50 border border-gray-300 rounded-lg p-3 text-gray-800 placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 ease-in-out shadow-inner"
                placeholder={placeholder}
                value={value}
                onChange={onChange}
                maxLength={maxLength}
            />
        ) : (
            <input
                 // Updated Tailwind classes for a light, clean input look
                 className="w-full bg-gray-50 border border-gray-300 rounded-lg p-3 text-gray-800 placeholder-gray-400 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition duration-150 ease-in-out shadow-inner"
                placeholder={placeholder}
                value={value}
                onChange={onChange}
                maxLength={maxLength}
            />
        )}
    </div>
);


// --- Main ArtifactGenerator Component (Updated Logic and Styles) ---

const ArtifactGenerator: React.FC = () => {
    const [scenario, setScenario] = useState('');
    const [persona, setPersona] = useState('');
    const [techInfo, setTechInfo] = useState('');
    const [artifactType, setArtifactType] = useState<ArtifactType>(ArtifactType.UserStory);
    const [generatedArtifact, setGeneratedArtifact] = useState<string>('The generated artifact will appear here...');
    const [history, setHistory] = useState<HistoryItem[]>([]); 
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [copySuccess, setCopySuccess] = useState<string>('');

    // --- History Fetching Logic (No change needed) ---
    const fetchHistory = useCallback(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/history`);
            if (!response.ok) throw new Error("Failed to fetch history.");
            const data = await response.json();
            
            const mappedHistory: HistoryItem[] = data.map((item: any) => ({
                id: item.id.toString(),
                title: item.title,
                type: item.type as ArtifactType,
                generatedDate: new Date(item.created_at).toLocaleDateString(undefined, {
                    month: 'numeric', day: 'numeric', year: '2-digit'
                }), 
                content: item.artifact_data.raw_output, 
            }));
            setHistory(mappedHistory);
        } catch (error) {
            console.error("Error fetching history:", error);
        }
    }, []);

    useEffect(() => {
        fetchHistory();
    }, [fetchHistory]);


    // --- Generation Logic (No change needed) ---
    const handleGenerate = useCallback(async () => {
        if (!scenario || isLoading) return;
        setIsLoading(true);
        setGeneratedArtifact('Generating...');
        
        try {
            const response = await fetch(`${API_BASE_URL}/generate-artifact`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    business_use_case: scenario,
                    persona: persona,
                    technical_info: techInfo,
                    artifact_type: artifactType,
                }),
            });

            const data = await response.json();
            console.log('API Response Status:', response.status);
            console.log('API Response Data:', data);
            
            if (!response.ok) {
                throw new Error(data.detail || `HTTP error! Status: ${response.status}`);
            }

            const artifact = data.artifact; 
            setGeneratedArtifact(artifact.raw_output);
            await fetchHistory();

        } catch (error) {
            console.error("Generation Error:", error);
            const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred.';
            setGeneratedArtifact(`Failed to generate artifact. Error: ${errorMessage}`);
        } finally {
            setIsLoading(false);
        }
    }, [scenario, persona, techInfo, artifactType, isLoading, fetchHistory]);
    
    // --- UI Actions (No change needed) ---
    const handleCopy = () => {
        navigator.clipboard.writeText(generatedArtifact).then(() => {
            setCopySuccess('Copied!');
            setTimeout(() => setCopySuccess(''), 2000);
        }, () => {
            setCopySuccess('Failed to copy');
            setTimeout(() => setCopySuccess(''), 2000);
        });
    };

    const handleHistoryClick = (item: HistoryItem) => {
        setGeneratedArtifact(item.content);
    };

    const handleClear = useCallback(() => {
        setScenario('');
        setPersona('');
        setTechInfo('');
    }, []);

    const isClearable = scenario || persona || techInfo;

    // --- RENDER (Updated Styles) ---
    return (
        // Changed bg-black to bg-gray-50 and text-slate-200 to text-gray-800
        <div className="p-4 sm:p-6 lg:p-8 flex flex-col h-screen bg-gray-50 text-gray-800">
            <header className="flex justify-between items-center pb-4 border-b border-gray-200 mb-6">
                <h1 className="text-2xl font-bold text-black">AI Artifact Generator</h1>
                <button className="text-gray-500 hover:text-gray-900 transition-colors">
                    <CogIcon />
                </button>
            </header>

            <main className="flex-grow grid grid-cols-1 lg:grid-cols-10 gap-6 min-h-0">
                {/* Left Column - Changed bg-gray-950 to bg-white and added shadow */}
                <div className="lg:col-span-3 bg-white p-6 rounded-xl shadow-lg flex flex-col overflow-y-auto">
                    <div className='flex-grow'>
                        <InputSection
                            label="Business Use Case / Scenario"
                            placeholder="Describe the business context or user journey..."
                            value={scenario}
                            onChange={(e) => setScenario(e.target.value)}
                            maxLength={1000}
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
                         <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Select Artifact Type</label>
                            <div className="grid grid-cols-2 gap-2">
                                {Object.values(ArtifactType).map((type) => (
                                    <button
                                        key={type}
                                        onClick={() => setArtifactType(type)}
                                        className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors shadow-sm ${
                                            // Changed accent color from blue-600 to indigo-600
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
                    </div>
                     <div className="mt-6 flex items-center space-x-4">
                        <button
                            onClick={handleClear}
                            disabled={!isClearable}
                            // Updated clear button style for light mode
                            className="w-1/3 bg-gray-200 text-gray-700 font-bold py-3 px-4 rounded-xl hover:bg-gray-300 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors shadow-md"
                        >
                            Clear
                        </button>
                        <button
                            onClick={handleGenerate}
                            disabled={isLoading || !scenario}
                            // Changed accent color from blue-600 to indigo-600
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

                {/* Center Column - Changed bg-gray-950 to bg-white and added shadow */}
                <div className="lg:col-span-5 bg-white p-6 rounded-xl shadow-lg flex flex-col">
                    <div className="flex justify-between items-center mb-4 border-b border-gray-100 pb-3">
                        <h2 className="text-lg font-semibold text-black">Generated Artifact</h2>
                        <div className="flex items-center space-x-4">
                            {copySuccess && <span className="text-sm text-green-600">{copySuccess}</span>}
                            <button onClick={handleCopy} className="flex items-center space-x-2 text-gray-500 hover:text-indigo-600 transition-colors">
                                <CopyIcon />
                                <span>Copy</span>
                            </button>
                            <button className="flex items-center space-x-2 text-gray-500 hover:text-indigo-600 transition-colors">
                                <ExportIcon />
                                <span>Export</span>
                            </button>
                        </div>
                    </div>
                    {/* Changed bg-black to bg-gray-50 and text-slate-300 to text-gray-800 */}
                    <div className="flex-grow bg-gray-50 rounded-lg border border-gray-200 p-4 overflow-y-auto font-mono text-gray-800 text-sm leading-relaxed">
                        <pre className="whitespace-pre-wrap font-sans">{generatedArtifact}</pre>
                    </div>
                </div>

                {/* Right Column - Changed bg-gray-950 to bg-white and added shadow */}
                <div className="lg:col-span-2 bg-white p-6 rounded-xl shadow-lg flex flex-col">
                    <h2 className="text-lg font-semibold text-black mb-4 border-b border-gray-100 pb-3">History</h2>
                    <div className="overflow-y-auto space-y-3">
                        {history.length === 0 && <p className="text-gray-500 text-sm">History is empty. Generate your first artifact!</p>}
                        {history.map((item) => (
                            <div
                                key={item.id}
                                onClick={() => handleHistoryClick(item)}
                                // Updated list item style
                                className="bg-gray-50 p-3 rounded-lg cursor-pointer hover:bg-gray-100 transition-colors border border-gray-200 shadow-sm"
                            >
                                <p className="font-semibold text-sm text-gray-800 truncate">{item.title}</p>
                                <p className="text-xs text-gray-500">Generated: {item.generatedDate}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </main>
        </div>
    );
};

export default ArtifactGenerator;