import { useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  ReceiptIndianRupee,
  Trophy,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatErr } from "@/lib/api";
import { PrivateDownload, PrivateImage } from "@/components/dashboard/PrivateFile";
import { DateTimeISTField } from "@/components/DateTimeISTField";

// A team is payment-eligible when:
//  • their application status is "selected", OR
//  • their team registration_status is "selected_awaiting_payment"
//    (set by the admin People → YES toggle without an abstract)
function isPaymentEligible(application, team) {
  if (application?.status === "selected") return true;
  const rs = team?.registration_status;
  return (
    rs === "selected_awaiting_payment" ||
    rs === "payment_under_verification" ||
    rs === "payment_verified" ||
    rs === "registration_confirmed"
  );
}

export function PaymentPanel({ application, payment, settings, leader, onReload, team }) {
  const [form, setForm] = useState({
    transaction_ref: "",
    payment_date: "",
    amount_paid: settings?.amount ?? "",
    remarks: "",
  });
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const input = useRef(null);

  // Not yet selected
  if (!isPaymentEligible(application, team)) {
    return (
      <section
        className="glass rounded-3xl p-8 text-center sm:p-10"
        data-testid="payment-not-available"
      >
        <AlertCircle className="mx-auto text-white/30" size={36} />
        <p className="mt-4 font-display text-lg font-bold uppercase text-white">
          Not yet eligible
        </p>
        <p className="mt-2 text-sm text-white/60">
          Payment instructions become available after your team is selected by
          the organizers.
        </p>
      </section>
    );
  }

  // Already confirmed
  if (payment?.status === "registration_confirmed") {
    return (
      <section
        className="glass rounded-3xl p-8 text-center sm:p-10"
        data-testid="payment-confirmed"
      >
        <CheckCircle2 className="mx-auto text-ice" size={40} />
        <p className="mt-4 font-display text-xl font-bold uppercase text-white">
          Registration confirmed
        </p>
        <p className="mt-2 text-sm text-white/60">
          Payment received and verified. Your team's registration is complete.
        </p>
      </section>
    );
  }

  const submit = async (event) => {
    event.preventDefault();
    if (!file || !form.payment_date)
      return toast.error("Choose a payment date and attach the receipt");
    const data = new FormData();
    Object.entries(form).forEach(([k, v]) => data.append(k, v));
    data.append("file", file);
    setBusy(true);
    try {
      await api.post("/payments/proof", data);
      toast.success("Payment proof submitted for independent verification");
      onReload();
    } catch (error) {
      toast.error(formatErr(error));
    } finally {
      setBusy(false);
    }
  };

  const editable =
    leader &&
    !["payment_under_verification", "payment_verified", "registration_confirmed"].includes(payment?.status);

  return (
    <div
      className="grid grid-cols-1 gap-6 lg:grid-cols-2"
      data-testid="payment-panel"
    >
      {/* ── Left: payment instructions & QR ── */}
      <section className="glass-strong rounded-3xl p-6 sm:p-7">
        {/* Selection congratulations banner */}
        <div className="mb-5 flex items-center gap-3 rounded-2xl border border-ice/20 bg-ice/5 p-4">
          <Trophy className="shrink-0 text-ice" size={20} />
          <p className="text-sm text-ice">
            Congratulations! Your team has been selected. Kindly proceed with
            the registration payment.
          </p>
        </div>

        <p className="eyebrow">Organizer-configured payment</p>
        <h2 className="mt-2 font-display text-xl font-bold uppercase text-white sm:text-2xl">
          Manual UPI / bank transfer
        </h2>

        {settings ? (
          <div className="mt-5 space-y-4 text-sm">
            <div>
              <span className="field-label">Amount</span>
              <strong
                className="block font-wordmark text-3xl text-grad"
                data-testid="payment-amount"
              >
                {settings.amount == null ? "Not configured" : `₹${settings.amount}`}
              </strong>
            </div>

            {/* QR code */}
            {settings.qr_file && (
              <div className="max-w-[200px]">
                {settings.qr_file.content_type === "application/pdf" ? (
                  <PrivateDownload
                    file={settings.qr_file}
                    label="Open payment QR PDF"
                    testId="payment-qr-download"
                  />
                ) : (
                  <PrivateImage
                    file={settings.qr_file}
                    alt="Official SANKALP'26 payment QR"
                    testId="payment-qr-image"
                  />
                )}
              </div>
            )}

            <div>
              <span className="field-label">UPI ID</span>
              <p className="text-white" data-testid="payment-upi-id">
                {settings.upi_id || "Not configured"}
              </p>
            </div>

            {settings.bank_details && (
              <div>
                <span className="field-label">Bank details</span>
                <p
                  className="whitespace-pre-wrap text-white/70"
                  data-testid="payment-bank-details"
                >
                  {settings.bank_details}
                </p>
              </div>
            )}

            <div>
              <span className="field-label">Deadline</span>
              <p className="text-white">
                {settings.deadline
                  ? new Date(settings.deadline).toLocaleString("en-IN", {
                      timeZone: "Asia/Kolkata",
                    })
                  : "Not configured"}
              </p>
            </div>

            {settings.instructions && (
              <p className="whitespace-pre-wrap rounded-xl bg-white/[0.03] p-3 text-white/65">
                {settings.instructions}
              </p>
            )}
          </div>
        ) : (
          <p className="mt-5 text-sm text-neon">
            Payment instructions are not configured yet. Check back soon.
          </p>
        )}
      </section>

      {/* ── Right: status + proof upload ── */}
      <section className="glass rounded-3xl p-6 sm:p-7">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="eyebrow">Verification status</p>
            <p
              className="mt-2 font-display text-xl font-bold uppercase text-white"
              data-testid="payment-status"
            >
              {payment?.status?.replaceAll("_", " ") || "Awaiting payment"}
            </p>
          </div>
          <ReceiptIndianRupee className="shrink-0 text-neon" />
        </div>

        {payment?.decision_reason && (
          <p
            className="mt-4 border-l-2 border-neon pl-3 text-sm text-white/65"
            data-testid="payment-decision-reason"
          >
            {payment.decision_reason}
          </p>
        )}

        {payment?.proof && (
          <div className="mt-4">
            <PrivateDownload
              file={payment.proof}
              label="Your submitted proof"
              testId="payment-proof-download"
            />
          </div>
        )}

        {payment?.status === "payment_under_verification" && (
          <p className="mt-4 text-sm text-white/55" data-testid="payment-proof-review-note">
            Your proof is being reviewed. You can submit another proof if the organizers request a correction.
          </p>
        )}

        {/* Proof upload form — only when editable */}
        {editable && (
          <form onSubmit={submit} className="mt-6 space-y-4" data-testid="payment-proof-form">
            <input
              className="field"
              required
              value={form.transaction_ref}
              onChange={(e) => setForm({ ...form, transaction_ref: e.target.value })}
              placeholder="Transaction ID / UTR / reference"
              data-testid="payment-reference-input"
            />
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <DateTimeISTField
                value={form.payment_date}
                onChange={(payment_date) => setForm({ ...form, payment_date })}
                testId="payment-date-input"
                includeTime={false}
                placeholder="Payment date"
              />
              <input
                className="field"
                type="number"
                min="1"
                step="0.01"
                required
                value={form.amount_paid}
                onChange={(e) => setForm({ ...form, amount_paid: e.target.value })}
                placeholder="Amount paid (₹)"
                data-testid="payment-paid-amount-input"
              />
            </div>
            <textarea
              className="field min-h-[70px]"
              value={form.remarks}
              onChange={(e) => setForm({ ...form, remarks: e.target.value })}
              placeholder="Optional remarks"
              data-testid="payment-remarks-input"
            />
            <button
              type="button"
              className="btn-ghost w-full"
              onClick={() => input.current?.click()}
              data-testid="payment-proof-picker"
            >
              {file?.name || "Choose receipt image or PDF"}
            </button>
            <input
              ref={input}
              className="hidden"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={(e) => setFile(e.target.files[0])}
              data-testid="payment-proof-file-input"
            />
            <button
              className="btn-neon w-full"
              disabled={busy}
              data-testid="payment-proof-submit-button"
            >
              {busy ? <Loader2 className="animate-spin" size={16} /> : "Submit for verification"}
            </button>
          </form>
        )}

        {payment?.status === "payment_verified" && (
          <p className="mt-5 text-sm text-white/50">
            Payment verified. Final registration approval is still pending.
          </p>
        )}

        {payment?.status === "registration_confirmed" && (
          <p className="mt-5 text-sm text-white/50">
            Payment verified and registration confirmed.
          </p>
        )}
      </section>
    </div>
  );
}
