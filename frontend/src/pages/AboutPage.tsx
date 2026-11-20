import { AlertTriangle } from "lucide-react";
import type { ReactNode } from "react";
import { Card, PageHeader } from "../components/ui";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card title={title}>
      <div className="space-y-2 text-[14px] leading-relaxed text-ink-soft">{children}</div>
    </Card>
  );
}

export default function AboutPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="About Project" subtitle="Medical X-Ray Pneumonia Classification with Uncertainty Quantification" />

      <div className="grid gap-6 lg:grid-cols-2">
        <Section title="Introduction">
          <p>PneumoScope classifies chest X-rays as normal or pneumonia and reports how certain each result is.</p>
        </Section>
        <Section title="Problem statement">
          <p>Image classifiers often give confident answers even when they are wrong. A safer system should flag the cases it is unsure about.</p>
        </Section>
        <Section title="Objectives">
          <ul className="list-disc space-y-1 pl-5">
            <li>Classify pneumonia from chest X-rays.</li>
            <li>Estimate the uncertainty of every prediction.</li>
            <li>Refer uncertain cases for review.</li>
            <li>Show which image regions influenced the result.</li>
          </ul>
        </Section>
        <Section title="Methodology">
          <ul className="list-disc space-y-1 pl-5">
            <li>ResNet-50 model trained on chest X-rays.</li>
            <li>Uncertainty score for each prediction.</li>
            <li>Calibrated probabilities.</li>
            <li>AUTO / REFER decision using a fixed threshold.</li>
            <li>Grad-CAM heatmaps.</li>
          </ul>
        </Section>
        <Section title="Dataset">
          <p><b className="text-ink">Kermany Pediatric Chest X-Ray</b> — 5,856 images (1,583 normal, 4,273 pneumonia), split so that no patient appears in both training and testing. Licence CC BY 4.0.</p>
          <p><b className="text-ink">RSNA Pneumonia Detection</b> — planned for external testing.</p>
        </Section>
        <Section title="Technologies">
          <p>Python, FastAPI, PyTorch, Torchvision, NumPy, Pillow, scikit-learn, SQLAlchemy, SQLite · React, TypeScript, Vite, Tailwind CSS, Recharts · Docker.</p>
        </Section>
        <Section title="Limitations">
          <ul className="list-disc space-y-1 pl-5">
            <li>Trained on paediatric X-rays from a single hospital.</li>
            <li>Not yet validated on external data.</li>
            <li>Heatmaps show influence, not the location of disease.</li>
          </ul>
        </Section>
      </div>

      <div className="flex gap-3 rounded-lg border border-warn-line bg-warn-bg px-5 py-4">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-warn" />
        <div className="text-[14px] text-ink-soft">
          <b className="text-ink">Educational use only.</b> This is an educational research application, not a clinically
          validated diagnostic system. Results must not be used for diagnosis or treatment.
        </div>
      </div>
    </div>
  );
}
