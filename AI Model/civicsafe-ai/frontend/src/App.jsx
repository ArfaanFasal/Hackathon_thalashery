<<<<<<< HEAD
import { useMemo, useState } from "react";
=======
import { useRef, useState } from "react";
>>>>>>> Ai_Model
import axios from "axios";

const API_BASE = "http://localhost:8000";

function App() {
  const [rawText, setRawText] = useState("");
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [report, setReport] = useState(null);
  const [error, setError] = useState("");
<<<<<<< HEAD
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
=======
  const [isRecording, setIsRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);

  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const chunksRef = useRef([]);
  const mimeTypeRef = useRef("audio/webm");

  const stopStream = () => {
    try {
      const stream = mediaStreamRef.current;
      if (stream) stream.getTracks().forEach((t) => t.stop());
    } finally {
      mediaStreamRef.current = null;
    }
  };

  const chooseMimeType = () => {
    // Pick the most compatible recording format for the current browser.
    if (typeof MediaRecorder === "undefined") return "audio/webm";
    if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) return "audio/webm;codecs=opus";
    if (MediaRecorder.isTypeSupported("audio/webm")) return "audio/webm";
    if (MediaRecorder.isTypeSupported("audio/ogg;codecs=opus")) return "audio/ogg;codecs=opus";
    if (MediaRecorder.isTypeSupported("audio/ogg")) return "audio/ogg";
    return "audio/webm";
  };

  const startMic = async () => {
    if (isRecording) return;
    setError("");
    setAnalysis(null);
    setReport(null);

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Microphone not supported in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      chunksRef.current = [];
      const mimeType = chooseMimeType();
      mimeTypeRef.current = mimeType;

      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onerror = () => {
        setError("Could not capture voice input.");
        setIsRecording(false);
        stopStream();
      };

      recorder.onstop = async () => {
        setIsRecording(false);
        stopStream();
        setTranscribing(true);
        setError("");
        try {
          const blob = new Blob(chunksRef.current, { type: mimeTypeRef.current || "audio/webm" });
          const fileExt = (mimeTypeRef.current || "").includes("ogg") ? "ogg" : "webm";
          const formData = new FormData();
          formData.append("audio", blob, `voice.${fileExt}`);

          const res = await axios.post(`${API_BASE}/transcribe`, formData, {
            headers: { "Content-Type": "multipart/form-data" }
          });
          setRawText(res.data.text || "");
        } catch (err) {
          setError(err?.response?.data?.detail || "Transcription failed.");
        } finally {
          setTranscribing(false);
          mediaRecorderRef.current = null;
          chunksRef.current = [];
        }
      };

      recorder.start();
      setIsRecording(true);
    } catch (err) {
      setError(err?.message || "Microphone permission denied.");
    }
  };

  const toggleRecording = async () => {
    if (isRecording) {
      try {
        mediaRecorderRef.current?.stop();
      } catch {
        setIsRecording(false);
      }
      return;
    }
    await startMic();
>>>>>>> Ai_Model
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
<<<<<<< HEAD
        placeholder="Type complaint in English, Malayalam, Hindi, or mixed..."
      />

      <div className="button-row">
        <button onClick={startMic} disabled={listening}>
          {listening ? "Listening..." : "Microphone"}
=======
        placeholder="Type complaint in English, Malayalam, Hindi, or mixed... (or use voice)"
      />

      <div className="button-row">
        <button onClick={toggleRecording} disabled={loading || transcribing}>
          {isRecording ? "Stop recording" : "Microphone"}
>>>>>>> Ai_Model
        </button>
        <button onClick={analyze} disabled={loading}>
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

<<<<<<< HEAD
=======
      {transcribing && <div className="card">Transcribing audio (multilingual)...</div>}
>>>>>>> Ai_Model
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
