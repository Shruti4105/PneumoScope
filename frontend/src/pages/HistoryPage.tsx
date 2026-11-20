import { Loader2, ScanLine, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Card, DecisionBadge, Empty, ErrorBox, Loading, Modal, PageHeader, PredictionBadge } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { api, assetUrl, errorMessage } from "../services/api";
import type { Analysis } from "../types";
import { dateTime, pct } from "../utils/format";

export default function HistoryPage() {
  const nav = useNavigate();
  const { data, error, loading, reload, setData } = useApi(() => api.history(), []);
  const [toDelete, setToDelete] = useState<Analysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function confirmDelete() {
    if (!toDelete || !data) return;
    setBusy(true);
    try {
      await api.remove(toDelete.id);
      setData({ items: data.items.filter((a) => a.id !== toDelete.id), total: data.total - 1 });
      setToDelete(null);
    } catch (e) {
      setDeleteError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Analysis History" subtitle={data ? `${data.total} saved analyses` : undefined}
        actions={<Link to="/analyse" className="btn-primary"><ScanLine className="h-4 w-4" />New analysis</Link>} />
      {deleteError && <ErrorBox message={deleteError} />}

      <Card bodyClass="p-0">
        {error ? <div className="p-5"><ErrorBox message={error} onRetry={reload} /></div>
          : loading && !data ? <Loading />
          : !data?.items.length ? (
            <Empty title="No analyses yet" text="Your analysed X-rays will appear here."
              action={<Link to="/analyse" className="btn-primary btn-sm">Analyse X-ray</Link>} />
          ) : (
            <div className="overflow-x-auto">
              <table className="table-base min-w-[720px]">
                <thead><tr><th>Image</th><th>Prediction</th><th className="text-right">Pneumonia probability</th><th className="text-right">Uncertainty</th><th>Decision</th><th>Date</th><th /></tr></thead>
                <tbody>
                  {data.items.map((a) => (
                    <tr key={a.id} className="cursor-pointer" onClick={() => nav(`/history/${a.id}`)}>
                      <td><img src={assetUrl(a.image_url + "?thumb=true")} alt="" className="h-12 w-12 rounded-md bg-black object-cover" /></td>
                      <td><PredictionBadge value={a.prediction} /></td>
                      <td className="num text-right font-medium">{pct(a.pneumonia_probability)}</td>
                      <td className="num text-right text-ink-soft">{pct(a.uncertainty)}</td>
                      <td><DecisionBadge value={a.decision} /></td>
                      <td className="whitespace-nowrap text-muted">{dateTime(a.created_at)}</td>
                      <td className="text-right">
                        <Link to={`/history/${a.id}`} className="btn-secondary btn-sm mr-2" onClick={(e) => e.stopPropagation()}>Open</Link>
                        <button className="rounded p-2 text-muted hover:bg-danger-bg hover:text-danger" title="Delete"
                          onClick={(e) => { e.stopPropagation(); setDeleteError(null); setToDelete(a); }}>
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </Card>

      <Modal open={!!toDelete} onClose={() => setToDelete(null)} title="Delete analysis?"
        footer={<>
          <button className="btn-secondary" onClick={() => setToDelete(null)}>Cancel</button>
          <button className="btn bg-danger text-white hover:bg-danger/90" onClick={confirmDelete} disabled={busy}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" />}Delete
          </button>
        </>}>
        This permanently removes the X-ray and its result.
      </Modal>
    </div>
  );
}
