import { useState, useCallback } from "react";
import "./styles/global.css";

import { AnalysisResult, HistoryEntry } from "./types/analysis";
import { analyzeDrawing } from "./api/analyzeService";

import Header from "./components/Header/Header";
import AnalysisPage from "./pages/AnalysisPage/AnalysisPage";
import ReportPage from "./pages/ReportPage/ReportPage";
import HistoryPage from "./pages/HistoryPage/HistoryPage";
import AboutPage from "./pages/AboutPage/AboutPage";

export default function App() {
  const [tab, setTab] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreview] = useState<string | null>(null);
  const [age, setAge] = useState("");
  const [context, setContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  const handleFile = useCallback((f: File) => {
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setError(null);
  }, []);

  const handleClear = useCallback(() => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
  }, []);

  const handleAnalyze = async (mode: string = "auto") => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const res = await analyzeDrawing(file, age || null, context, mode);
      setResult(res);
      setHistory((h) => [
        {
          id: Date.now(),
          preview: previewUrl!,
          result: res,
          age,
          date: new Date().toLocaleDateString("ru-RU"),
        },
        ...h.slice(0, 9),
      ]);
      setTab(1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleHistorySelect = (entry: HistoryEntry) => {
    setResult(entry.result);
    setAge(entry.age);
    setTab(1);
  };

  return (
    <div style={{ minHeight: "100vh", background: "#faf8f5" }}>
      <Header activeTab={tab} onTabChange={setTab} />

      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>
        {tab === 0 && (
          <AnalysisPage
            previewUrl={previewUrl}
            age={age}
            context={context}
            loading={loading}
            error={error}
            onFile={handleFile}
            onClear={handleClear}
            onAgeChange={setAge}
            onContextChange={setContext}
            onAnalyze={handleAnalyze}
          />
        )}
        {tab === 1 && (
          <ReportPage result={result} age={age} onBack={() => setTab(0)} />
        )}
        {tab === 2 && (
          <HistoryPage history={history} onSelect={handleHistorySelect} />
        )}
        {tab === 3 && <AboutPage />}
      </div>
    </div>
  );
}
