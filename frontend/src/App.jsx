import React, { useState, useEffect } from 'react';
import { Upload, FileText, Link2, CheckCircle, AlertCircle, Loader2, Download, Edit2, Wifi, WifiOff, Clock, ExternalLink } from 'lucide-react';

const FormFillerApp = () => {
  const [step, setStep] = useState(1);
  const [pdfFile, setPdfFile] = useState(null);
  const [extractedData, setExtractedData] = useState(null);
  const [formUrl, setFormUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [browserOpen, setBrowserOpen] = useState(false);

  const API_URL = 'http://localhost:8000';

  useEffect(() => {
    checkBackendStatus();
  }, []);

  const checkBackendStatus = async () => {
    try {
      console.log('Checking backend status...');
      const response = await fetch(`${API_URL}/`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Backend is online:', data);
        setBackendStatus('online');
      } else {
        console.error('Backend returned error:', response.status);
        setBackendStatus('offline');
      }
    } catch (err) {
      console.error('Backend check failed:', err);
      setBackendStatus('offline');
      setError('Cannot connect to backend server. Make sure it is running on http://localhost:8000');
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    console.log('File selected:', file.name, file.type, file.size);

    if (file.type !== 'application/pdf') {
      setError('Please upload a valid PDF file');
      return;
    }

    setPdfFile(file);
    setError('');
    setLoading(true);

    const formData = new FormData();
    formData.append('file', file);

    try {
      console.log('Sending upload request to:', `${API_URL}/extract`);
      
      const response = await fetch(`${API_URL}/extract`, {
        method: 'POST',
        body: formData,
      });

      console.log('Response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        
        let errorDetail = 'Extraction failed';
        try {
          const errorData = JSON.parse(errorText);
          errorDetail = errorData.detail || errorDetail;
        } catch (e) {
          errorDetail = errorText || errorDetail;
        }
        
        throw new Error(errorDetail);
      }

      const data = await response.json();
      console.log('Extraction successful:', data);
      
      setExtractedData(data.extracted_data);
      setStep(2);
      setError('');
      
    } catch (err) {
      console.error('Upload error:', err);
      
      if (err.message.includes('Failed to fetch') || err.name === 'TypeError') {
        setError('Cannot connect to backend server. Please make sure:\n1. Backend is running (python main.py)\n2. Backend is accessible at http://localhost:8000\n3. No firewall is blocking the connection');
      } else {
        setError(err.message || 'Failed to extract data from PDF. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDataEdit = (field, value) => {
    setExtractedData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleFormSubmit = async () => {
    if (!formUrl) {
      setError('Please enter a form URL');
      return;
    }

    setLoading(true);
    setBrowserOpen(true);
    setError('');

    try {
      console.log('Filling form:', formUrl);
      console.log('With data:', extractedData);

      const response = await fetch(`${API_URL}/fill-form`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          form_url: formUrl,
          data: extractedData,
        }),
      });

      console.log('Form fill response status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Form fill error response:', errorText);
        
        let errorDetail = 'Form filling failed';
        try {
          const errorData = JSON.parse(errorText);
          errorDetail = errorData.detail || errorDetail;
        } catch (e) {
          errorDetail = errorText || errorDetail;
        }
        
        throw new Error(errorDetail);
      }

      const data = await response.json();
      console.log('Form fill result:', data);
      setResult(data);
      setStep(3);
      setError('');
      setBrowserOpen(false);
      
    } catch (err) {
      console.error('Form fill error:', err);
      setBrowserOpen(false);
      
      if (err.message.includes('Failed to fetch') || err.name === 'TypeError') {
        setError('Cannot connect to backend server. Please make sure backend is still running.');
      } else {
        setError(err.message || 'Failed to fill form. Please check the URL and try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const resetApp = () => {
    setStep(1);
    setPdfFile(null);
    setExtractedData(null);
    setFormUrl('');
    setError('');
    setResult(null);
    setEditMode(false);
    setBrowserOpen(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header with Backend Status */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center mb-2">
            <h1 className="text-4xl font-bold text-gray-800">
              AI Form Filler Assistant
            </h1>
            <div className="ml-4">
              {backendStatus === 'online' ? (
                <div className="flex items-center text-green-600 text-sm">
                  <Wifi className="w-4 h-4 mr-1" />
                  <span>Backend Online</span>
                </div>
              ) : backendStatus === 'offline' ? (
                <div className="flex items-center text-red-600 text-sm">
                  <WifiOff className="w-4 h-4 mr-1" />
                  <span>Backend Offline</span>
                </div>
              ) : (
                <div className="flex items-center text-gray-500 text-sm">
                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                  <span>Checking...</span>
                </div>
              )}
            </div>
          </div>
          <p className="text-gray-600">Extract data from PDFs and auto-fill web forms</p>
        </div>

        {/* Backend Offline Warning */}
        {backendStatus === 'offline' && (
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-start">
              <AlertCircle className="w-5 h-5 text-yellow-600 mr-3 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-yellow-800 font-medium">Backend server is not running</p>
                <p className="text-yellow-700 text-sm mt-1">
                  Please start the backend server:
                </p>
                <code className="block mt-2 p-2 bg-yellow-100 rounded text-xs">
                  cd backend && python main.py
                </code>
                <button
                  onClick={checkBackendStatus}
                  className="mt-2 text-sm text-yellow-800 underline hover:text-yellow-900"
                >
                  Check again
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Browser Open Indicator */}
        {browserOpen && (
          <div className="mb-6 p-4 bg-blue-50 border-2 border-blue-400 rounded-lg animate-pulse">
            <div className="flex items-start">
              <ExternalLink className="w-5 h-5 text-blue-600 mr-3 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-blue-900 font-bold text-lg">🖥️ Browser Window is Open</p>
                <p className="text-blue-800 mt-2">
                  The form has been opened in a browser window. You can:
                </p>
                <ul className="mt-2 space-y-1 text-blue-700">
                  <li>• Review the auto-filled fields</li>
                  <li>• Manually fill any remaining fields</li>
                  <li>• Submit the form when ready</li>
                  <li>• Close the browser when done</li>
                </ul>
                <div className="mt-3 flex items-center text-blue-600">
                  <Clock className="w-4 h-4 mr-1" />
                  <span className="text-sm italic">Browser will remain open until you close it...</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Progress Steps */}
        <div className="flex justify-center mb-8">
          <div className="flex items-center space-x-4">
            {[1, 2, 3].map((num) => (
              <React.Fragment key={num}>
                <div className={`flex items-center justify-center w-10 h-10 rounded-full font-bold transition-all ${
                  step >= num ? 'bg-indigo-600 text-white' : 'bg-gray-300 text-gray-600'
                }`}>
                  {num}
                </div>
                {num < 3 && (
                  <div className={`w-16 h-1 transition-all ${step > num ? 'bg-indigo-600' : 'bg-gray-300'}`} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start">
              <AlertCircle className="w-5 h-5 text-red-600 mr-3 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-red-800 whitespace-pre-line">{error}</p>
                {error.includes('Cannot connect') && (
                  <button
                    onClick={checkBackendStatus}
                    className="mt-2 text-sm text-red-700 underline hover:text-red-800"
                  >
                    Check backend status
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Step 1: Upload PDF */}
        {step === 1 && (
          <div className="bg-white rounded-xl shadow-lg p-8">
            <div className="text-center">
              <Upload className="w-16 h-16 text-indigo-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Upload Document</h2>
              <p className="text-gray-600 mb-6">Upload a PDF containing personal information</p>
              
              <label className="cursor-pointer">
                <div className="border-2 border-dashed border-indigo-300 rounded-lg p-12 hover:border-indigo-500 transition-colors">
                  <FileText className="w-12 h-12 text-indigo-400 mx-auto mb-3" />
                  <p className="text-gray-700 font-medium mb-1">
                    {pdfFile ? pdfFile.name : 'Click to upload PDF'}
                  </p>
                  <p className="text-sm text-gray-500">Supports Aadhaar, PAN, Passport, etc.</p>
                </div>
                <input
                  type="file"
                  accept="application/pdf"
                  onChange={handleFileUpload}
                  className="hidden"
                  disabled={loading || backendStatus === 'offline'}
                />
              </label>

              {loading && (
                <div className="mt-6 flex items-center justify-center">
                  <Loader2 className="w-6 h-6 text-indigo-600 animate-spin mr-2" />
                  <span className="text-gray-700">Extracting data from PDF...</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Step 2: Review & Fill Form */}
        {step === 2 && extractedData && (
          <div className="bg-white rounded-xl shadow-lg p-8">
            <div className="mb-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-bold text-gray-800">Extracted Data</h2>
                <button
                  onClick={() => setEditMode(!editMode)}
                  className="flex items-center text-indigo-600 hover:text-indigo-700 transition-colors"
                >
                  <Edit2 className="w-4 h-4 mr-1" />
                  {editMode ? 'Done' : 'Edit'}
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                {Object.entries(extractedData).map(([key, value]) => (
                  <div key={key} className="p-4 bg-gray-50 rounded-lg">
                    <label className="block text-sm font-medium text-gray-700 mb-2 capitalize">
                      {key.replace(/_/g, ' ')}
                    </label>
                    {editMode ? (
                      <input
                        type="text"
                        value={value}
                        onChange={(e) => handleDataEdit(key, e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                      />
                    ) : (
                      <p className="text-gray-900 font-medium">{value || 'Not found'}</p>
                    )}
                  </div>
                ))}
              </div>

              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">
                  <strong>Note:</strong> The browser will open and stay open after auto-filling. 
                  You can manually complete any remaining fields and submit the form yourself.
                </p>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Form URL
                </label>
                <div className="flex flex-col sm:flex-row gap-2">
                  <div className="flex-1 relative">
                    <Link2 className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
                    <input
                      type="url"
                      value={formUrl}
                      onChange={(e) => setFormUrl(e.target.value)}
                      placeholder="https://docs.google.com/forms/..."
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                    />
                  </div>
                  <button
                    onClick={handleFormSubmit}
                    disabled={loading || !formUrl || browserOpen}
                    className="px-6 py-2 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin mr-2" />
                        Opening Browser...
                      </>
                    ) : (
                      <>
                        <ExternalLink className="w-5 h-5 mr-2" />
                        Open & Fill Form
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Results */}
        {step === 3 && result && (
          <div className="bg-white rounded-xl shadow-lg p-8">
            <div className="text-center">
              <CheckCircle className="w-16 h-16 text-green-600 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Form Auto-Fill Completed!</h2>
              <p className="text-gray-600 mb-4">The browser was kept open for you to complete the rest</p>
              
              <div className="mt-6 p-6 bg-gray-50 rounded-lg">
                <div className="grid grid-cols-2 gap-4 text-left">
                  <div>
                    <p className="text-sm text-gray-600">Fields Auto-Filled</p>
                    <p className="text-2xl font-bold text-indigo-600">{result.fields_filled}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Total Fields</p>
                    <p className="text-2xl font-bold text-gray-800">{result.total_fields}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm text-gray-600">Success Rate</p>
                    <p className="text-2xl font-bold text-green-600">{result.success_rate}</p>
                  </div>
                </div>
              </div>

              {result.screenshot && (
                <div className="mt-6">
                  <a
                    href={`${API_URL}/download/${result.screenshot}`}
                    download
                    className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Download Screenshot
                  </a>
                </div>
              )}

              <button
                onClick={resetApp}
                className="mt-6 px-6 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
              >
                Fill Another Form
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default FormFillerApp;