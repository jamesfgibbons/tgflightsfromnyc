import React, { useState, useCallback, useEffect } from 'react';
import { 
  Code, 
  Save, 
  Play, 
  CheckCircle, 
  AlertCircle, 
  Download,
  RotateCcw,
  Settings,
  Music,
  FileText
} from 'lucide-react';
import Editor from '@monaco-editor/react';
import { validateRulesYaml, getDefaultRulesYaml, getRuleSummary } from '../lib/yaml';
import MidiPlayer from '../components/MidiPlayer';
import LabelCueStrip from '../components/LabelCueStrip';

interface SaveResponse {
  ok: boolean;
  version_key?: string;
  error?: string;
}

interface PreviewResponse {
  midi_url?: string;
  mp3_url?: string;
  momentum_json?: any;
  label_summary?: Record<string, number>;
  error?: string;
}

const IdeRules: React.FC = () => {
  const [tenant, setTenant] = useState('demo-tenant');
  const [yamlContent, setYamlContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  
  const [validationResult, setValidationResult] = useState<any>(null);
  const [saveResult, setSaveResult] = useState<SaveResponse | null>(null);
  const [previewResult, setPreviewResult] = useState<PreviewResponse | null>(null);
  
  const [toast, setToast] = useState<{type: 'success' | 'error', message: string} | null>(null);

  // Load existing rules on mount
  useEffect(() => {
    loadRules();
  }, [tenant]);

  // Auto-dismiss toast
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const showToast = useCallback((type: 'success' | 'error', message: string) => {
    setToast({ type, message });
  }, []);

  // Load rules from backend
  const loadRules = useCallback(async () => {
    if (!tenant.trim()) return;
    
    setLoading(true);
    try {
      const response = await fetch(`/api/rules?tenant=${encodeURIComponent(tenant.trim())}`);
      
      if (response.ok) {
        const yamlText = await response.text();
        setYamlContent(yamlText);
        
        // Validate loaded YAML
        const validation = validateRulesYaml(yamlText);
        setValidationResult(validation);
      } else {
        // Load default template if no rules exist
        const defaultYaml = getDefaultRulesYaml();
        setYamlContent(defaultYaml);
        setValidationResult(validateRulesYaml(defaultYaml));
      }
    } catch (error) {
      showToast('error', 'Failed to load rules');
      // Fall back to default
      const defaultYaml = getDefaultRulesYaml();
      setYamlContent(defaultYaml);
      setValidationResult(validateRulesYaml(defaultYaml));
    } finally {
      setLoading(false);
    }
  }, [tenant, showToast]);

  // Validate YAML content
  const handleValidate = useCallback(() => {
    const result = validateRulesYaml(yamlContent);
    setValidationResult(result);
    
    if (result.valid) {
      showToast('success', 'YAML validation passed');
    } else {
      showToast('error', `Validation failed: ${result.error}`);
    }
  }, [yamlContent, showToast]);

  // Save rules to backend
  const handleSave = useCallback(async () => {
    if (!tenant.trim()) {
      showToast('error', 'Please enter a tenant name');
      return;
    }
    
    const validation = validateRulesYaml(yamlContent);
    if (!validation.valid) {
      showToast('error', `Cannot save: ${validation.error}`);
      return;
    }
    
    setSaving(true);
    setSaveResult(null);
    
    try {
      const response = await fetch('/api/rules', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant: tenant.trim(),
          yaml_text: yamlContent
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setSaveResult({ ok: true, version_key: data.version_key });
        showToast('success', `Rules saved successfully (version: ${data.version_key.split('/').pop()})`);
      } else {
        const errorData = await response.json().catch(() => ({ error: 'Save failed' }));
        setSaveResult({ ok: false, error: errorData.error });
        showToast('error', errorData.error || 'Failed to save rules');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Save failed';
      setSaveResult({ ok: false, error: message });
      showToast('error', message);
    } finally {
      setSaving(false);
    }
  }, [tenant, yamlContent, showToast]);

  // Preview rules with sample data
  const handlePreview = useCallback(async () => {
    if (!tenant.trim()) {
      showToast('error', 'Please enter a tenant name');
      return;
    }
    
    const validation = validateRulesYaml(yamlContent);
    if (!validation.valid) {
      showToast('error', `Cannot preview: ${validation.error}`);
      return;
    }
    
    setPreviewing(true);
    setPreviewResult(null);
    
    try {
      const response = await fetch('/api/preview', {
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant: tenant.trim(),
          source: 'demo',
          use_training: true,
          momentum: true,
          override_metrics: {
            ctr: 0.75,
            impressions: 0.8,
            position: 0.9,
            clicks: 0.7,
            volatility_index: 0.3
          }
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        setPreviewResult(data);
        showToast('success', 'Preview generated successfully');
      } else {
        const errorData = await response.json().catch(() => ({ error: 'Preview failed' }));
        setPreviewResult({ error: errorData.error });
        showToast('error', errorData.error || 'Preview failed');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Preview failed';
      setPreviewResult({ error: message });
      showToast('error', message);
    } finally {
      setPreviewing(false);
    }
  }, [tenant, yamlContent, showToast]);

  // Reset to default template
  const handleReset = useCallback(() => {
    const defaultYaml = getDefaultRulesYaml();
    setYamlContent(defaultYaml);
    setValidationResult(validateRulesYaml(defaultYaml));
    setSaveResult(null);
    setPreviewResult(null);
    showToast('success', 'Reset to default template');
  }, [showToast]);

  // Handle editor content change
  const handleEditorChange = useCallback((value: string | undefined) => {
    const newContent = value || '';
    setYamlContent(newContent);
    
    // Auto-validate on change (debounced)
    setTimeout(() => {
      const result = validateRulesYaml(newContent);
      setValidationResult(result);
    }, 500);
  }, []);

  const ruleSummary = validationResult?.valid ? getRuleSummary(validationResult.parsed) : [];

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Code className="w-6 h-6" />
          SERP Radio Rules IDE
        </h1>

        {/* Tenant Input */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tenant ID
          </label>
          <div className="flex gap-2">
            <input
              type="text"
              value={tenant}
              onChange={(e) => setTenant(e.target.value)}
              placeholder="Enter tenant identifier"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={loadRules}
              disabled={loading || !tenant.trim()}
              className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:bg-gray-400"
            >
              {loading ? 'Loading...' : 'Load'}
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2">
          <button
            onClick={handleValidate}
            disabled={!yamlContent.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400"
          >
            <CheckCircle className="w-4 h-4" />
            Validate
          </button>
          
          <button
            onClick={handlePreview}
            disabled={!yamlContent.trim() || previewing}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-400"
          >
            {previewing ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                Previewing...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Preview
              </>
            )}
          </button>
          
          <button
            onClick={handleSave}
            disabled={!yamlContent.trim() || saving}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:bg-gray-400"
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save
              </>
            )}
          </button>
          
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Editor Panel */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="bg-gray-50 px-4 py-2 border-b border-gray-200 flex items-center justify-between">
            <h2 className="font-medium text-gray-900 flex items-center gap-2">
              <FileText className="w-4 h-4" />
              YAML Rules Editor
            </h2>
            
            {validationResult && (
              <div className={`flex items-center gap-1 text-sm ${
                validationResult.valid ? 'text-green-600' : 'text-red-600'
              }`}>
                {validationResult.valid ? (
                  <CheckCircle className="w-4 h-4" />
                ) : (
                  <AlertCircle className="w-4 h-4" />
                )}
                {validationResult.valid ? 'Valid' : 'Invalid'}
              </div>
            )}
          </div>
          
          <div className="h-96">
            <Editor
              language="yaml"
              theme="vs-light"
              value={yamlContent}
              onChange={handleEditorChange}
              options={{
                minimap: { enabled: false },
                lineNumbers: 'on',
                wordWrap: 'on',
                automaticLayout: true,
                scrollBeyondLastLine: false,
                fontSize: 14,
                tabSize: 2,
                insertSpaces: true
              }}
            />
          </div>
          
          {/* Validation Error */}
          {validationResult && !validationResult.valid && (
            <div className="p-4 bg-red-50 border-t border-red-200 flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
              <span className="text-red-700 text-sm">{validationResult.error}</span>
            </div>
          )}
        </div>

        {/* Info Panel */}
        <div className="space-y-6">
          {/* Rule Summary */}
          {validationResult?.valid && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Settings className="w-5 h-5" />
                Rule Summary
              </h3>
              
              <div className="space-y-2">
                {ruleSummary.map((summary, index) => (
                  <div key={index} className="text-sm text-gray-700 bg-gray-50 p-2 rounded">
                    {summary}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Save Status */}
          {saveResult && (
            <div className={`p-4 rounded-lg ${
              saveResult.ok ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
            }`}>
              <div className="flex items-start gap-2">
                {saveResult.ok ? (
                  <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                )}
                <div>
                  <div className={`font-medium ${saveResult.ok ? 'text-green-800' : 'text-red-800'}`}>
                    {saveResult.ok ? 'Rules Saved' : 'Save Failed'}
                  </div>
                  {saveResult.version_key && (
                    <div className="text-sm text-green-700 mt-1">
                      Version: {saveResult.version_key.split('/').pop()}
                    </div>
                  )}
                  {saveResult.error && (
                    <div className="text-sm text-red-700 mt-1">
                      {saveResult.error}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Preview Results */}
      {previewResult && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Music className="w-5 h-5" />
            Preview Results
          </h2>

          {previewResult.error ? (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
              <span className="text-red-700">{previewResult.error}</span>
            </div>
          ) : (
            <>
              {/* Label Summary */}
              {previewResult.label_summary && (
                <div className="mb-6">
                  <LabelCueStrip 
                    labelSummary={previewResult.label_summary}
                    className="mb-4"
                  />
                </div>
              )}

              {/* MIDI Player */}
              {previewResult.midi_url && (
                <div className="mb-6">
                  <MidiPlayer 
                    midiUrl={previewResult.midi_url}
                    title={`${tenant} - Rules Preview`}
                  />
                </div>
              )}

              {/* Download Links */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {previewResult.midi_url && (
                  <a
                    href={previewResult.midi_url}
                    download
                    className="flex items-center justify-center gap-2 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
                  >
                    <Download className="w-4 h-4" />
                    Download MIDI
                  </a>
                )}
                
                {previewResult.mp3_url && (
                  <a
                    href={previewResult.mp3_url}
                    download
                    className="flex items-center justify-center gap-2 bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700"
                  >
                    <Download className="w-4 h-4" />
                    Download MP3
                  </a>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className={`fixed top-4 right-4 p-4 rounded-lg shadow-lg ${
          toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'
        } text-white z-50`}>
          <div className="flex items-center gap-2">
            {toast.type === 'success' ? (
              <CheckCircle className="w-5 h-5" />
            ) : (
              <AlertCircle className="w-5 h-5" />
            )}
            {toast.message}
          </div>
        </div>
      )}
    </div>
  );
};

export default IdeRules;