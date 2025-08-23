import React, { useState, useCallback } from 'react';
import { 
  Upload, 
  FileText, 
  AlertCircle, 
  CheckCircle, 
  Music, 
  Play,
  Download,
  Settings
} from 'lucide-react';
import { validateCsvFile, validateCsvContent, getCsvFileInfo, formatFileSize } from '../lib/csvGuards';
import MidiPlayer from '../components/MidiPlayer';
import LabelCueStrip from '../components/LabelCueStrip';

interface Column {
  name: string;
  type: string;
  role?: string;
}

interface SchemaInfo {
  columns: Column[];
  rowCount: number;
  preview: Record<string, string>[];
}

interface JobStatus {
  job_id: string;
  status: 'queued' | 'running' | 'done' | 'error';
  midi_url?: string;
  mp3_url?: string;
  momentum_json_url?: string;
  error?: string;
  label_summary?: Record<string, number>;
}

const UploadCsv: React.FC = () => {
  const [tenant, setTenant] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [schemaInfo, setSchemaInfo] = useState<SchemaInfo | null>(null);
  const [columnMappings, setColumnMappings] = useState<Record<string, string>>({});
  
  const [sonifying, setSonifying] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  // File selection and validation
  const handleFileSelect = useCallback(async (selectedFile: File) => {
    setFile(null);
    setUploadError(null);
    setDatasetId(null);
    setSchemaInfo(null);
    
    // Client-side validation
    const validation = validateCsvFile(selectedFile);
    if (!validation.valid) {
      setUploadError(validation.error || 'Invalid file');
      return;
    }
    
    // Content validation
    const contentValidation = await validateCsvContent(selectedFile);
    if (!contentValidation.valid) {
      setUploadError(contentValidation.error || 'Invalid CSV content');
      return;
    }
    
    // Show warnings if any
    if (contentValidation.warnings?.length) {
      console.warn('CSV warnings:', contentValidation.warnings);
    }
    
    setFile(selectedFile);
  }, []);

  // Upload CSV to backend
  const handleUpload = useCallback(async () => {
    if (!file || !tenant.trim()) {
      setUploadError('Please select a file and enter tenant name');
      return;
    }
    
    setUploading(true);
    setUploadError(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await fetch(`/api/upload-csv?tenant=${encodeURIComponent(tenant.trim())}`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Upload failed' }));
        throw new Error(errorData.error || `Upload failed: ${response.status}`);
      }
      
      const data = await response.json();
      
      setDatasetId(data.dataset_id);
      setSchemaInfo({
        columns: Object.entries(data.inferred_schema).map(([name, type]) => ({
          name,
          type: type as string,
          role: data.mapping[name] || 'unused'
        })),
        rowCount: data.row_count,
        preview: data.preview
      });
      
      // Initialize column mappings
      setColumnMappings(data.mapping);
      
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  }, [file, tenant]);

  // Update column mapping
  const updateColumnMapping = useCallback((columnName: string, role: string) => {
    setColumnMappings(prev => ({
      ...prev,
      [columnName]: role
    }));
  }, []);

  // Start sonification
  const handleSonify = useCallback(async () => {
    if (!datasetId || !tenant) return;
    
    setSonifying(true);
    setJobId(null);
    setJobStatus(null);
    
    try {
      const response = await fetch('/api/sonify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          tenant: tenant.trim(),
          dataset_id: datasetId,
          source: 'demo', // For now, use demo mode with uploaded CSV
          use_training: true,
          momentum: true
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Sonification failed' }));
        throw new Error(errorData.error || 'Sonification failed');
      }
      
      const data = await response.json();
      setJobId(data.job_id);
      
      // Start polling for job status
      startStatusPolling(data.job_id);
      
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Sonification failed');
      setSonifying(false);
    }
  }, [datasetId, tenant]);

  // Poll job status
  const startStatusPolling = useCallback((jobId: string) => {
    const poll = async () => {
      try {
        const response = await fetch(`/api/jobs/${jobId}`);
        if (response.ok) {
          const status: JobStatus = await response.json();
          setJobStatus(status);
          
          if (status.status === 'done' || status.status === 'error') {
            setSonifying(false);
            if (pollingInterval) {
              clearInterval(pollingInterval);
              setPollingInterval(null);
            }
          }
        }
      } catch (error) {
        console.error('Status polling error:', error);
      }
    };
    
    // Poll immediately, then every 2 seconds
    poll();
    const interval = setInterval(poll, 2000);
    setPollingInterval(interval);
  }, [pollingInterval]);

  // Cleanup polling on unmount
  React.useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  const fileInfo = file ? getCsvFileInfo(file) : null;

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h1 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
          <Upload className="w-6 h-6" />
          Upload CSV for Sonification
        </h1>

        {/* Tenant Input */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tenant ID
          </label>
          <input
            type="text"
            value={tenant}
            onChange={(e) => setTenant(e.target.value)}
            placeholder="Enter your tenant identifier"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* File Upload */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            CSV File
          </label>
          <div
            className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-gray-400 cursor-pointer"
            onClick={() => document.getElementById('csv-file')?.click()}
          >
            <input
              id="csv-file"
              type="file"
              accept=".csv,text/csv,application/csv"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleFileSelect(file);
              }}
              className="hidden"
            />
            
            {file ? (
              <div className="flex items-center justify-center gap-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span>{file.name}</span>
                {fileInfo && (
                  <span className="text-gray-500 text-sm">
                    ({formatFileSize(file.size)}, ~{fileInfo.estimatedRows.toLocaleString()} rows)
                  </span>
                )}
              </div>
            ) : (
              <div className="text-gray-500">
                <FileText className="w-8 h-8 mx-auto mb-2" />
                <p>Click to select CSV file</p>
                <p className="text-sm">Max 10MB, 50,000 rows</p>
              </div>
            )}
          </div>
        </div>

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={!file || !tenant.trim() || uploading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {uploading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" />
              Upload & Analyze
            </>
          )}
        </button>

        {/* Error Display */}
        {uploadError && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-md flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
            <span className="text-red-700">{uploadError}</span>
          </div>
        )}
      </div>

      {/* Schema Display */}
      {schemaInfo && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Dataset Schema ({schemaInfo.rowCount.toLocaleString()} rows)
          </h2>

          {/* Column Mapping Table */}
          <div className="overflow-x-auto mb-4">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Column</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {schemaInfo.columns.map((column) => (
                  <tr key={column.name}>
                    <td className="px-4 py-2 font-medium text-gray-900">{column.name}</td>
                    <td className="px-4 py-2 text-gray-600">{column.type}</td>
                    <td className="px-4 py-2">
                      <select
                        value={columnMappings[column.name] || 'unused'}
                        onChange={(e) => updateColumnMapping(column.name, e.target.value)}
                        className="text-sm border border-gray-300 rounded px-2 py-1"
                      >
                        <option value="unused">Unused</option>
                        <option value="ctr">CTR</option>
                        <option value="impressions">Impressions</option>
                        <option value="position">Position</option>
                        <option value="clicks">Clicks</option>
                        <option value="keyword">Keyword</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Data Preview */}
          {schemaInfo.preview.length > 0 && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Data Preview</h3>
              <div className="overflow-x-auto bg-gray-50 rounded border">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr>
                      {Object.keys(schemaInfo.preview[0]).map((key) => (
                        <th key={key} className="px-3 py-2 text-left font-medium text-gray-600 border-b">
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {schemaInfo.preview.map((row, idx) => (
                      <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                        {Object.values(row).map((value, cellIdx) => (
                          <td key={cellIdx} className="px-3 py-2 text-gray-700 border-b">
                            {String(value).substring(0, 30)}
                            {String(value).length > 30 ? '...' : ''}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Sonify Button */}
          <button
            onClick={handleSonify}
            disabled={!datasetId || sonifying}
            className="w-full bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {sonifying ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                {jobStatus?.status === 'running' ? 'Generating...' : 'Processing...'}
              </>
            ) : (
              <>
                <Music className="w-4 h-4" />
                Sonify Data
              </>
            )}
          </button>
        </div>
      )}

      {/* Job Status */}
      {jobStatus && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Sonification Results
          </h2>

          {jobStatus.status === 'error' && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-md flex items-start gap-2">
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
              <span className="text-red-700">{jobStatus.error}</span>
            </div>
          )}

          {jobStatus.status === 'done' && (
            <>
              {/* Label Summary */}
              {jobStatus.label_summary && (
                <div className="mb-6">
                  <LabelCueStrip 
                    labelSummary={jobStatus.label_summary}
                    className="mb-4"
                  />
                </div>
              )}

              {/* MIDI Player */}
              {jobStatus.midi_url && (
                <div className="mb-6">
                  <MidiPlayer 
                    midiUrl={jobStatus.midi_url}
                    title={`${tenant} - Dataset Sonification`}
                  />
                </div>
              )}

              {/* Download Links */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {jobStatus.midi_url && (
                  <a
                    href={jobStatus.midi_url}
                    download
                    className="flex items-center justify-center gap-2 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700"
                  >
                    <Download className="w-4 h-4" />
                    Download MIDI
                  </a>
                )}
                
                {jobStatus.mp3_url && (
                  <a
                    href={jobStatus.mp3_url}
                    download
                    className="flex items-center justify-center gap-2 bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700"
                  >
                    <Download className="w-4 h-4" />
                    Download MP3
                  </a>
                )}
                
                {jobStatus.momentum_json_url && (
                  <a
                    href={jobStatus.momentum_json_url}
                    download
                    className="flex items-center justify-center gap-2 bg-gray-600 text-white py-2 px-4 rounded-md hover:bg-gray-700"
                  >
                    <Download className="w-4 h-4" />
                    Analysis JSON
                  </a>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default UploadCsv;