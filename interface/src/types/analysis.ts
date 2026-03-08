export interface Emotion {
  name: string;
  intensity: number;
  evidence: string;
}

export interface ColorAnalysis {
  dominant: string[];
  palette: string;
  brightnessClass: string;
  saturationClass: string;
  brightnessValue: number;
  saturationValue: number;
  colorRatios: Record<string, number>;
  interpretation: string;
}

export interface CompositionAnalysis {
  fillRatio: number;
  fillClass: string;
  centerX: number;
  centerY: number;
  location: string;
  numObjects: number;
  complexity: string;
  lineDensity: number;
  style: string;
  spaceUsage: string;
  interpretation: string;
}

export type OverallState =
  | "норма"
  | "требует_внимания"
  | "требует_консультации";

export interface AnalysisResult {
  colorAnalysis: ColorAnalysis;
  composition: CompositionAnalysis;
  emotions: Emotion[];
  psychologicalPortrait: string;
  riskFactors: string[];
  recommendations: string[];
  overallState: OverallState;
  confidence: number;
}

export interface HistoryEntry {
  id: number;
  preview: string;
  result: AnalysisResult;
  age: string;
  date: string;
}
