// АртМинд — типы данных v7.0

export type EmotionName =
  | "радость"
  | "грусть"
  | "тревога"
  | "агрессия"
  | "спокойствие";

export interface Emotion {
  name: EmotionName;
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
  colorCoverage?: number;
  nVividColors?: number;
  warmRatio?: number;
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

export interface ZoneAnalysis {
  zoneClasses: Record<string, string>;
  balanceInterpretation: string;
}

export interface LineAnalysis {
  pressure: string;
  thickness: string;
  character: string;
  chaos: string;
  interpretation: string;
}

export interface ContentAnalysis {
  detectedObjects: string[];
  hasHuman: boolean;
  hasSun: boolean;
  hasHouse: boolean;
  hasNature: boolean;
  hasDarkElements: boolean;
  hasSmile: boolean;
  symbolism: string;
}

export type OverallState =
  | "норма"
  | "требует_внимания"
  | "требует_консультации";

export type AnalysisMode = "groq" | "hybrid" | "opencv" | "opencv_fallback";

export interface EvidenceModule {
  name: string;
  raw: number;
  weight: number;
  weighted: number;
}

export interface EvidenceChain {
  total: number;
  modules: EvidenceModule[];
}

export interface AnalysisResult {
  colorAnalysis: ColorAnalysis;
  composition: CompositionAnalysis;
  zoneAnalysis?: ZoneAnalysis;
  lineAnalysis?: LineAnalysis;
  contentAnalysis?: ContentAnalysis;
  emotions: Emotion[];
  evidenceChains?: Record<string, EvidenceChain>;
  psychologicalPortrait: string;
  riskFactors: string[];
  recommendations: string[];
  overallState: OverallState;
  confidence: number;
  analysisMode?: AnalysisMode;
  fallbackReason?: string;
  moduleWeights?: Record<string, number>;
  ageNormLabel?: string;
  dbId?: number;
  contextAnalysis?: {
    stress_level: number;
    positive_level: number;
    stress_keywords: string[];
    positive_keywords: string[];
  };
}
