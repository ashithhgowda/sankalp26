import { useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  FileCheck2,
  QrCode,
  RotateCcw,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { api, downloadFile, formatErr } from "@/lib/api";
import { DateTimeISTField } from "@/components/DateTimeISTField";

export function PaymentsPanel({ payments, onReload }) {
  const [settings, setSettings] = useState({
    upi_id: "",
    bank_details: "",
    amount: "",
    deadline: "",
    instructions: "",
  });
  const [reasons, setReasons] = useState({});
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [settingsError, setSettingsError] = useState(null);
  const [settingsAttempt, setSettingsAttempt] = useState(0);
  const qr = useRef(null);

  useEffect(() => {
    api
      .get("/admin/payment-settings")
      .then(({ data }) => {
        setSettings((current) => ({ ...current, ...data }));
        setSettingsLoaded(true);
        setSettingsError(null);
      })
      .catch((error) => {
        setSettingsError(formatErr(error));
        toast.error(formatErr(error));
      });
  }, [settingsAttempt]);

  const save = async (e) => {
    e.preventDefault();
    if (!settingsLoaded) return;
    try {
      await api.put("/admin/payment-settings", {
        ...settings,
        amount: settings.amount === "" ? null : Number(settings.amount),
        deadline: settings.deadline || null,
      });
      toast.success("Payment instructions saved");
      onReload();
    } catch (error) {
      toast.error(formatErr(error));
    }
  };

  const uploadQr = async (file) => {
    if (!file) return;
    const data = new FormData();
    data.append("file", file);
    try {
      await api.post("/admin/payment-settings/qr", data);
      toast.success("Official QR updated");
    } catch (error) {
      toast.error(formatErr(error));
    }
  };

  const decide = async (payment, action) => {
    try {
      await api.patch(`/admin/payments/${payment.payment_id}`, {
        action,
        reason: reasons[payment.payment_id] || "",
      });
      toast.success("Payment status updated");
      onReload();
    } catch (error) {
      toast.error(formatErr(error));
    }
  };

  const confirm = async (payment) => {
    if (!window.confirm("Explicitly approve this team's final registration?"))
      return;
    try {
      await api.post(`/admin/payments/${payment.payment_id}/confirm-registration`);
      toast.success("Registration confirmed");
      onReload();
    } catch (error) {
      toast.error(formatErr(error));
    }
  };

  return (
    <div className="space-y-7" data-testid="admin-payments-panel">
      {/* ── Payment settings form ── */}
      <form
        onSubmit={save}
        className="glass-strong space-y-4 rounded-3xl p-6"
        data-testid="admin-payment-settings-form"
      >
        <div className="flex flex-wrap items-center gap-2">
          <QrCode className="text-ice" />
          <p className="eyebrow">Manual payment instructions</p>
        </div>
        <p className="text-sm text-white/45">
          Leave unconfirmed details blank. Only selected teams can view saved
          instructions.
        </p>
        {settingsError && (
          <p className="text-sm text-neon" role="alert">
            Could not load saved payment settings: {settingsError}{" "}
            <button type="button" className="underline" onClick={() => setSettingsAttempt((attempt) => attempt + 1)}>
              Retry
            </button>
          </p>
        )}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <input
            className="field"
            value={settings.upi_id || ""}
            onChange={(e) => setSettings({ ...settings, upi_id: e.target.value })}
            placeholder="Official UPI ID"
            data-testid="admin-payment-upi-input"
          />
          <input
            className="field"
            type="number"
            min="0"
            value={settings.amount ?? ""}
            onChange={(e) => setSettings({ ...settings, amount: e.target.value })}
            placeholder="Registration amount (₹)"
            data-testid="admin-payment-amount-input"
          />
          <DateTimeISTField
            value={settings.deadline}
            onChange={(deadline) => setSettings({ ...settings, deadline })}
            testId="admin-payment-deadline-input"
            placeholder="Payment deadline · IST"
          />
        </div>

        <textarea
          className="field min-h-[80px]"
          value={settings.bank_details || ""}
          onChange={(e) => setSettings({ ...settings, bank_details: e.target.value })}
          placeholder="Official bank details"
          data-testid="admin-payment-bank-input"
        />
        <textarea
          className="field min-h-[80px]"
          value={settings.instructions || ""}
          onChange={(e) =>
            setSettings({ ...settings, instructions: e.target.value })
          }
          placeholder="Payment instructions (shown to selected teams)"
          data-testid="admin-payment-instructions-input"
        />

        <div className="flex flex-wrap gap-3">
          <button className="btn-neon" disabled={!settingsLoaded} data-testid="admin-payment-settings-save">
            Save instructions
          </button>
          <button
            type="button"
            onClick={() => qr.current?.click()}
            className="btn-ghost"
            data-testid="admin-payment-qr-picker"
          >
            <QrCode size={15} /> Upload QR
          </button>
          <input
            ref={qr}
            className="hidden"
            type="file"
            accept=".png,.jpg,.jpeg,.pdf"
            onChange={(e) => uploadQr(e.target.files[0])}
            data-testid="admin-payment-qr-input"
          />
        </div>
      </form>

      {/* ── Payment submissions ── */}
      {payments.length === 0 ? (
        <p className="glass rounded-3xl p-10 text-center text-white/50">
          No payment submissions yet.
        </p>
      ) : (
        <div className="space-y-4">
          {payments.map((payment) => (
            <article
              key={payment.payment_id}
              className="glass rounded-3xl p-5 sm:p-6"
              data-testid={`admin-payment-${payment.payment_id}`}
            >
              {/* Header */}
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-display text-lg font-bold uppercase text-white sm:text-xl">
                    {payment.team?.name || "Unknown team"}
                  </p>
                  <p className="mt-0.5 text-xs text-white/40">
                    {payment.payment_id} ·{" "}
                    {payment.transaction_ref || "No proof submitted"}
                  </p>
                </div>
                <span
                  className="rounded-full border border-neon/40 px-3 py-1 font-mono text-[10px] uppercase text-neon"
                  data-testid={`admin-payment-status-${payment.payment_id}`}
                >
                  {payment.status?.replaceAll("_", " ")}
                </span>
              </div>

              {/* Proof info */}
              {payment.proof && (
                <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-white/60">
                  <span>
                    ₹{payment.amount_paid} · paid {payment.payment_date}
                  </span>
                  <button
                    onClick={() =>
                      downloadFile(
                        payment.proof.file_id,
                        payment.proof.filename
                      ).catch((err) => toast.error(formatErr(err)))
                    }
                    className="btn-ghost !px-4 !py-2 !text-[10px]"
                    data-testid={`admin-payment-proof-${payment.payment_id}`}
                  >
                    <FileCheck2 size={14} /> View proof
                  </button>
                </div>
              )}

              {/* Admin note */}
              <textarea
                className="field mt-4 min-h-[64px]"
                value={reasons[payment.payment_id] || ""}
                onChange={(e) =>
                  setReasons({ ...reasons, [payment.payment_id]: e.target.value })
                }
                placeholder="Verification note or rejection reason"
                data-testid={`admin-payment-reason-${payment.payment_id}`}
              />

              {/* Action buttons */}
              <div className="mt-4 flex flex-wrap gap-2">
                {payment.status === "payment_under_verification" && (
                  <>
                    <button
                      onClick={() => decide(payment, "approve")}
                      className="btn-neon !px-4 !py-2 !text-[10px]"
                      data-testid={`admin-payment-approve-${payment.payment_id}`}
                    >
                      <CheckCircle2 size={14} /> Approve
                    </button>
                    <button
                      onClick={() => decide(payment, "request_correction")}
                      className="btn-ghost !px-4 !py-2 !text-[10px]"
                      data-testid={`admin-payment-correction-${payment.payment_id}`}
                    >
                      <RotateCcw size={14} /> Request correction
                    </button>
                    <button
                      onClick={() => decide(payment, "reject")}
                      className="btn-ghost !px-4 !py-2 !text-[10px] text-neon"
                      data-testid={`admin-payment-reject-${payment.payment_id}`}
                    >
                      <XCircle size={14} /> Reject
                    </button>
                  </>
                )}
                {payment.status === "payment_verified" && (
                  <button
                    onClick={() => confirm(payment)}
                    className="btn-neon !px-4 !py-2 !text-[10px]"
                    data-testid={`admin-registration-confirm-${payment.payment_id}`}
                  >
                    <CheckCircle2 size={14} /> Confirm registration
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
