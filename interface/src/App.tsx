import { useState, useCallback } from "react";
import "./styles/global.css";

import { AnalysisResult } from "./types/analysis";
import { analyzeDrawing } from "./api/analyzeService";

import Header from "./components/Header/Header";
import AnalysisPage from "./pages/AnalysisPage/AnalysisPage";
import ReportPage from "./pages/ReportPage/ReportPage";
import ComparePage from "./pages/ComparePage/ComparePage";
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
      setTab(1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleHistorySelect = (
    historyResult: AnalysisResult,
    historyAge: string,
  ) => {
    setResult(historyResult);
    setAge(historyAge);
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
        {tab === 2 && <ComparePage />}
        {tab === 3 && <HistoryPage onSelect={handleHistorySelect} />}
        {tab === 4 && <AboutPage />}
      </div>
    </div>
  );
}
