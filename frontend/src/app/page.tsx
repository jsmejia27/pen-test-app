"use client"; // Required for hooks like useState, useEffect

import React, { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';

// --- Interfaces matching Backend Schemas ---
// (Ideally, these could be shared or generated)

interface WebsiteResponse {
  id: number;
  url: string;
  created_at: string; // ISO date string
  last_scan_at?: string | null;
}

interface TestDefinitionResponse {
  id: number;
  name: string;
  description?: string | null;
}

enum TestStatusEnum {
  PENDING = "pending",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  FAILED = "failed",
  ERROR = "error",
}

enum TestResultEnum {
  NOT_RUN = "not_run",
  PASSED = "passed",
  VULNERABLE = "vulnerable",
  INFO = "info",
}

interface ScanResultResponse {
  id: number;
  test_definition: TestDefinitionResponse;
  status: TestStatusEnum;
  result: TestResultEnum;
  summary?: string | null;
  details?: string | null;
  recommendations?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
}

interface ScanResponse {
  id: number;
  website: WebsiteResponse;
  status: TestStatusEnum;
  created_at: string; // ISO date string
  completed_at?: string | null;
  results: ScanResultResponse[];
}

// --- Constants ---
const API_BASE_URL = 'http://localhost:8000'; // Backend API URL
const POLLING_INTERVAL = 5000; // 5 seconds

// --- Helper Functions ---
function getStatusIcon(status: TestStatusEnum, result: TestResultEnum): string {
  switch (status) {
    case TestStatusEnum.PENDING:
      return '⏳'; // Hourglass Not Done
    case TestStatusEnum.IN_PROGRESS:
      return '⚙️'; // Gear (Processing)
    case TestStatusEnum.COMPLETED:
      switch (result) {
        case TestResultEnum.PASSED:
          return '✅'; // Check Mark Button
        case TestResultEnum.VULNERABLE:
          return '❌'; // Cross Mark
        case TestResultEnum.INFO:
          return 'ℹ️'; // Information
        default:
          return '❓'; // Question Mark
      }
    case TestStatusEnum.FAILED:
    case TestStatusEnum.ERROR:
      return '⚠️'; // Warning Sign
    default:
      return '❓';
  }
}

function getStatusColor(status: TestStatusEnum, result: TestResultEnum): string {
    switch (status) {
        case TestStatusEnum.PENDING: return 'text-gray-500';
        case TestStatusEnum.IN_PROGRESS: return 'text-blue-500 animate-pulse';
        case TestStatusEnum.COMPLETED:
            switch (result) {
                case TestResultEnum.PASSED: return 'text-green-500';
                case TestResultEnum.VULNERABLE: return 'text-red-500';
                case TestResultEnum.INFO: return 'text-blue-400';
                default: return 'text-gray-500';
            }
        case TestStatusEnum.FAILED:
        case TestStatusEnum.ERROR: return 'text-orange-500';
        default: return 'text-gray-500';
    }
}


// --- Main Component ---
export default function Home() {
  const [url, setUrl] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [scanData, setScanData] = useState<ScanResponse | null>(null);
  const [isPolling, setIsPolling] = useState<boolean>(false);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch latest scan status
  const fetchScanStatus = useCallback(async (scanId: number) => {
    try {
      console.log(`Polling for scan ID: ${scanId}`);
      const response = await axios.get<ScanResponse>(`${API_BASE_URL}/scans/${scanId}`);
      setScanData(response.data);

      // Stop polling if scan is completed or failed/error
      if (response.data.status === TestStatusEnum.COMPLETED ||
          response.data.status === TestStatusEnum.FAILED ||
          response.data.status === TestStatusEnum.ERROR) {
        console.log(`Scan ${scanId} finished with status: ${response.data.status}. Stopping polling.`);
        setIsPolling(false);
        setIsLoading(false); // Also stop overall loading indicator
      }
    } catch (err) {
      console.error('Error fetching scan status:', err);
      setError('Failed to fetch scan status. Please try again later.');
      setIsPolling(false); // Stop polling on error
      setIsLoading(false);
    }
  }, []); // No dependencies needed as it uses scanId argument

  // Effect to manage polling interval
  useEffect(() => {
    if (isPolling && scanData?.id) {
      // Clear existing interval before setting a new one
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
      // Set new interval
      pollingIntervalRef.current = setInterval(() => {
        fetchScanStatus(scanData.id);
      }, POLLING_INTERVAL);
      console.log(`Polling started for scan ID: ${scanData.id}`);
    } else {
      // Clear interval if not polling or no scan ID
      if (pollingIntervalRef.current) {
        console.log("Clearing polling interval.");
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    }

    // Cleanup function to clear interval on component unmount or when polling stops
    return () => {
      if (pollingIntervalRef.current) {
        console.log("Clearing polling interval on cleanup.");
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [isPolling, scanData?.id, fetchScanStatus]); // Re-run effect if polling state or scan ID changes


  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setScanData(null); // Clear previous scan data
    setIsPolling(false); // Ensure polling is stopped before starting new scan

    // Basic URL validation (consider more robust validation)
    if (!url || !url.startsWith('http://') && !url.startsWith('https://')) {
        setError('Please enter a valid URL (starting with http:// or https://).');
        setIsLoading(false);
        return;
    }

    try {
      console.log(`Submitting URL: ${url}`);
      const response = await axios.post<ScanResponse>(`${API_BASE_URL}/scans`, { url });
      console.log('Scan initiated:', response.data);
      setScanData(response.data);
      setIsPolling(true); // Start polling after successful initiation
      // Don't set isLoading to false here, keep it true while polling
    } catch (err: any) {
      console.error('Error starting scan:', err);
      setError(err.response?.data?.detail || 'Failed to start scan. Check the backend API.');
      setIsLoading(false); // Stop loading on error
    }
  };

  const handleDownloadReport = () => {
      if (!scanData || scanData.status !== TestStatusEnum.COMPLETED) {
          alert("Scan is not yet complete.");
          return;
      }
      // Use window.open for simplicity, though direct download might require more setup
      // if the backend returns the file directly with Content-Disposition
      window.open(`${API_BASE_URL}/scans/${scanData.id}/report`, '_blank');
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-start p-8 sm:p-12 md:p-24 bg-gray-50">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm lg:flex mb-12">
        <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-800 text-center lg:text-left w-full">
          Web Penetration Tester
        </h1>
      </div>

      <div className="w-full max-w-3xl bg-white p-6 sm:p-8 rounded-lg shadow-md mb-8">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
              Website URL to Test
            </label>
            <input
              type="url"
              id="url"
              name="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              disabled={isLoading}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            className={`w-full inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white ${
              isLoading
                ? 'bg-indigo-400 cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500'
            }`}
          >
            {isLoading ? 'Scanning...' : 'Start Scan'}
          </button>
        </form>
        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
      </div>

      {scanData && (
        <div className="w-full max-w-3xl bg-white p-6 sm:p-8 rounded-lg shadow-md">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Scan Results for: <span className="font-normal text-indigo-600">{scanData.website.url}</span> (ID: {scanData.id})
          </h2>
          <p className="text-sm text-gray-600 mb-4">
            Overall Status: <span className={`font-medium ${getStatusColor(scanData.status, TestResultEnum.NOT_RUN)}`}>{scanData.status}</span>
            {scanData.status === TestStatusEnum.COMPLETED && scanData.completed_at && (
                 ` (Completed: ${new Date(scanData.completed_at).toLocaleString()})`
            )}
          </p>

          <ul className="space-y-3">
            {scanData.results.sort((a, b) => a.test_definition.id - b.test_definition.id).map((result) => (
              <li key={result.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-md border border-gray-200">
                <div className="flex items-center space-x-3">
                   <span className="text-lg">{getStatusIcon(result.status, result.result)}</span>
                   <span className="text-sm font-medium text-gray-700">{result.test_definition.name}</span>
                </div>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${getStatusColor(result.status, result.result)}`}>
                  {result.status === TestStatusEnum.COMPLETED ? result.result : result.status}
                </span>
              </li>
            ))}
          </ul>

          {scanData.status === TestStatusEnum.COMPLETED && (
            <div className="mt-6 text-center">
                <button
                    onClick={handleDownloadReport}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
                    Download PDF Report (Placeholder)
                </button>
            </div>
          )}
        </div>
      )}
    </main>
  );
}
