export interface User { id: number; name: string; email: string }

export type Prediction = "PNEUMONIA" | "NORMAL";
export type Decision = "AUTO" | "REFER";

export interface Analysis {
  id: string;
  created_at: string;
  prediction: Prediction;
  pneumonia_probability: number;
  normal_probability: number;
  uncertainty: number;
  decision: Decision;
  decision_reason: string;
  referral_threshold: number;
  model_version: string;
  processing_ms: number;
  image_width: number;
  image_height: number;
  image_url: string;
  gradcam_url: string | null;
  disclaimer: string;
}

export interface ModelInfo {
  available: boolean;
  status: string;
  message: string;
  name: string;
  version: string;
  architecture: string;
  training_dataset: string;
  trained_at: string | null;
  referral_threshold: number | null;
  calibrated: boolean;
}

export interface Dashboard {
  total: number;
  normal: number;
  pneumonia: number;
  referred: number;
  auto: number;
  average_uncertainty: number | null;
  recent: Analysis[];
  daily: { date: string; normal: number; pneumonia: number; referred: number }[];
  uncertainty_series: { date: string; uncertainty: number; decision: Decision }[];
  model: ModelInfo;
}

export interface Metrics {
  available: boolean;
  message?: string;
  model_version: string;
  dataset: string;
  n_images: number;
  n_pneumonia: number;
  n_normal: number;
  accuracy: number;
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  roc_auc_ci: { lower: number; upper: number } | null;
  specificity: number;
  confusion_matrix: { tn: number; fp: number; fn: number; tp: number };
  roc_curve: { x: number; y: number }[];
  refer_rate: number;
  auto_accuracy: number | null;
  external_rsna: null | { accuracy: number; precision: number; recall: number; f1: number; roc_auc: number; n: number };
  uncertainty: {
    referral_threshold: number;
    refer_rate: number;
    n_referred: number;
    overall_accuracy: number;
    auto_accuracy: number | null;
    errors_caught: number;
    total_errors: number;
    mean_uncertainty: number;
    error_detection_auroc: number | null;
    histogram: { bin: number; correct: number; wrong: number }[];
    accuracy_vs_referred: { referred: number; accuracy: number }[];
  };
}
