import { ArrowLeft, Loader2, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import ResultView from "../components/ResultView";
import { ErrorBox, Loading, Modal, PageHeader } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { api, errorMessage } from "../services/api";

export default function ResultPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const { data, error, loading, reload } = useApi(() => api.analysis(id), [id]);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [delError, setDelError] = useState<string | null>(null);

  async function remove() {
    setBusy(true);
    try {
      await api.remove(id);
      nav("/history", { replace: true });
    } catch (e) {
      setDelError(errorMessage(e));
      setBusy(false);
      setConfirm(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Analysis result"
        actions={<>
          <Link to="/history" className="btn-secondary"><ArrowLeft className="h-4 w-4" />Back</Link>
          {data && <button className="btn-danger" onClick={() => setConfirm(true)}><Trash2 className="h-4 w-4" />Delete</button>}
        </>} />
      {delError && <ErrorBox message={delError} />}
      {loading && !data ? <Loading /> : error ? <ErrorBox message={error} onRetry={reload} /> : data && <ResultView initial={data} />}

      <Modal open={confirm} onClose={() => setConfirm(false)} title="Delete analysis?"
        footer={<>
          <button className="btn-secondary" onClick={() => setConfirm(false)}>Cancel</button>
          <button className="btn bg-danger text-white hover:bg-danger/90" onClick={remove} disabled={busy}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" />}Delete
          </button>
        </>}>
        This permanently removes the X-ray and its result.
      </Modal>
    </div>
  );
}
