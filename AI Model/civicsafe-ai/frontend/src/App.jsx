import { useMemo, useState } from "react";
import axios from "axios";

const API_BASE = "http://localhost:8000";

function App() {
  const [rawText, setRawText] = useState("");
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
  const [listening, setListening] = useState(false);

  const speechSupported = useMemo(
    () => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition),
    []
  );

  const startMic = () => {
    if (!speechSupported) {
      setError("Browser speech recognition is not supported.");
      return;
    }
    setError("");
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new Recognition();
    recognition.lang = "en-IN";
    recognition.interimResults = false;
    recognition.continuous = false;
    setListening(true);
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setRawText((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };
    recognition.onerror = () => {
      setError("Could not capture voice input.");
    };
    recognition.onend = () => {
      setListening(false);
    };
    recognition.start();
  };

  const analyze = async () => {
    if (!rawText.trim()) {
      setError("Please enter complaint text or use microphone.");
      return;
    }
    setLoading(true);
    setError("");
    setAnalysis(null);
    setReport(null);
    try {
      const analyzeRes = await axios.post(`${API_BASE}/analyze`, { raw_text: rawText });
      setAnalysis(analyzeRes.data);
      const reportRes = await axios.post(`${API_BASE}/generate-report`, {
        raw_text: rawText,
        analysis: analyzeRes.data
      });
      setReport(reportRes.data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Analysis failed.");
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = () => {
    if (!report?.markdown_report) return;
    const blob = new Blob([report.markdown_report], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "civicsafe-report.md";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="container">
      <h1>CivicSafe AI</h1>
      <p>Multilingual Smart Civic Assistant & Scam Shield</p>

      <textarea
        rows={6}
        value={rawText}
        onChange={(e) => setRawText(e.target.value)}
        placeholder="Type complaint in English, Malayalam, Hindi, or mixed..."
      />

      <div className="button-row">
        <button onClick={startMic} disabled={listening}>
          {listening ? "Listening..." : "Microphone"}
        </button>
        <button onClick={analyze} disabled={loading}>
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {loading && <div className="card">Processing request...</div>}
      {error && <div className="error">{error}</div>}

      {analysis && (
        <>
          <div className="card">
            <h2>Result</h2>
            <pre>{JSON.stringify(analysis.structured_data, null, 2)}</pre>
          </div>
          <div className="card">
            <h2>Scam Analysis</h2>
            <pre>{JSON.stringify(analysis.scam_analysis, null, 2)}</pre>
          </div>
        </>
      )}

      {report && (
        <div className="card">
          <h2>Report Panel</h2>
          <pre>{report.markdown_report}</pre>
          <button onClick={downloadReport}>Download report</button>
        </div>
      )}
    </div>
  );
}

export default App;
