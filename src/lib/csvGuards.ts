/**
 * CSV validation utilities for SERP Radio frontend.
 */

// Runtime configuration (these would come from your config)
const MAX_CSV_MB = parseInt(process.env.REACT_APP_MAX_CSV_MB || '10');
const MAX_CSV_ROWS = parseInt(process.env.REACT_APP_MAX_CSV_ROWS || '50000');

// Accepted MIME types for CSV files
const ACCEPTED_CSV_TYPES = [
  'text/csv',
  'application/csv', 
  'application/vnd.ms-excel',
  'text/plain' // Some browsers report CSV as text/plain
];

export interface CsvValidationResult {
  valid: boolean;
  error?: string;
  warnings?: string[];
}

export interface CsvFileInfo {
  file: File;
  sizeInMB: number;
  estimatedRows: number;
}

/**
 * Validate CSV file before upload.
 */
export function validateCsvFile(file: File): CsvValidationResult {
  const result: CsvValidationResult = { valid: true, warnings: [] };
  
  // Check file size
  const sizeInMB = file.size / (1024 * 1024);
  if (sizeInMB > MAX_CSV_MB) {
    return {
      valid: false,
      error: `File too large: ${sizeInMB.toFixed(1)}MB (max ${MAX_CSV_MB}MB)`
    };
  }
  
  // Check MIME type
  if (!ACCEPTED_CSV_TYPES.includes(file.type)) {
    return {
      valid: false,
      error: `Invalid file type: ${file.type}. Please upload a CSV file.`
    };
  }
  
  // Check file extension as fallback
  const extension = file.name.toLowerCase().split('.').pop();
  if (!extension || !['csv', 'txt'].includes(extension)) {
    result.warnings?.push('File extension should be .csv for best compatibility');
  }
  
  // Estimate row count (rough approximation)
  const avgBytesPerRow = 100; // Conservative estimate
  const estimatedRows = file.size / avgBytesPerRow;
  
  if (estimatedRows > MAX_CSV_ROWS) {
    return {
      valid: false,
      error: `File appears too large: ~${Math.round(estimatedRows).toLocaleString()} rows (max ${MAX_CSV_ROWS.toLocaleString()})`
    };
  }
  
  if (estimatedRows > MAX_CSV_ROWS * 0.8) {
    result.warnings?.push(`Large file detected: ~${Math.round(estimatedRows).toLocaleString()} rows`);
  }
  
  return result;
}

/**
 * Get file information for display.
 */
export function getCsvFileInfo(file: File): CsvFileInfo {
  const sizeInMB = file.size / (1024 * 1024);
  const avgBytesPerRow = 100;
  const estimatedRows = Math.round(file.size / avgBytesPerRow);
  
  return {
    file,
    sizeInMB: Math.round(sizeInMB * 10) / 10, // Round to 1 decimal
    estimatedRows
  };
}

/**
 * Check if file appears to be CSV content by sampling first few bytes.
 */
export async function validateCsvContent(file: File): Promise<CsvValidationResult> {
  return new Promise((resolve) => {
    const reader = new FileReader();
    
    reader.onload = (e) => {
      const content = e.target?.result as string;
      if (!content) {
        resolve({ valid: false, error: 'Could not read file content' });
        return;
      }
      
      // Sample first 1000 characters
      const sample = content.substring(0, 1000);
      
      // Basic CSV structure checks
      const lines = sample.split('\n');
      if (lines.length < 2) {
        resolve({ valid: false, error: 'File must have at least 2 lines (header + data)' });
        return;
      }
      
      // Check for common CSV delimiters in first line
      const firstLine = lines[0];
      const hasCommas = firstLine.includes(',');
      const hasSemicolons = firstLine.includes(';');
      const hasTabs = firstLine.includes('\t');
      
      if (!hasCommas && !hasSemicolons && !hasTabs) {
        resolve({ 
          valid: false, 
          error: 'File does not appear to be CSV format (no delimiters found)' 
        });
        return;
      }
      
      const warnings: string[] = [];
      
      // Warn about unusual delimiters
      if (hasSemicolons && !hasCommas) {
        warnings.push('File uses semicolon delimiters (;) - ensure compatibility');
      }
      
      if (hasTabs && !hasCommas) {
        warnings.push('File appears to be tab-delimited - ensure compatibility');
      }
      
      resolve({ valid: true, warnings });
    };
    
    reader.onerror = () => {
      resolve({ valid: false, error: 'Could not read file' });
    };
    
    // Read first 1KB for content validation
    const blob = file.slice(0, 1000);
    reader.readAsText(blob);
  });
}

/**
 * Format file size for display.
 */
export function formatFileSize(bytes: number): string {
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let unitIndex = 0;
  
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  
  return `${Math.round(size * 10) / 10} ${units[unitIndex]}`;
}

/**
 * Get validation limits for display.
 */
export function getValidationLimits() {
  return {
    MAX_CSV_MB,
    MAX_CSV_ROWS,
    ACCEPTED_CSV_TYPES
  };
}