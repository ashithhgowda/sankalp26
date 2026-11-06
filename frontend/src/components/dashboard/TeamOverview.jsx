import { CheckCircle2, Clock3, MailCheck, Trophy, UserRound, XCircle } from "lucide-react";
import { toast } from "sonner";
import { api, formatErr } from "@/lib/api";

const stateTone = {
  active: "text-ice",
  invited: "text-neon",
  pending_verification: "text-neon",
};

/** Derive human-readable selection state from team record */
function selectionInfo(team) {
  const sel = team.selection_status;
  const reg = team.registration_status;

  if (
    sel === "selected" ||
    ["selected_awaiting_payment", "payment_under_verification",
      "payment_verified", "registration_confirmed"].includes(reg)
  ) {
    return { selected: true };
  }
  if (sel === "not_selected") {
    return { selected: false, explicit: true };
  }
  return null; // pending — no decision yet
}

export function TeamOverview({ team, memberships, leader, onReload }) {
  const inviteAction = async (member, action) => {
    try {
      const result =
        action === "resend"
          ? await api.post(`/memberships/${member.membership_id}/invitation/resend`)
          : await api.delete(`/invitations/${member.invitation_id}`);
      if (action === "resend" && result.data.email_status !== "sent") {
        toast.error("Invitation was refreshed, but email delivery failed. Please retry later.");
      } else {
        toast.success(action === "resend" ? "Invitation email sent" : "Invitation revoked");
      }
      onReload();
    } catch (error) {
      toast.error(formatErr(error));
    }
  };

  const selection = selectionInfo(team);

  return (
    <div className="space-y-5" data-testid="team-overview-panel">
      {/* Selection status banner — shown once a decision has been made */}
      {selection !== null && (
        <div
          className={`flex items-start gap-4 rounded-2xl border p-4 sm:p-5 ${
            selection.selected
              ? "border-ice/30 bg-ice/5"
              : "border-neon/30 bg-neon/5"
          }`}
          data-testid="team-selection-banner"
        >
          {selection.selected ? (
            <Trophy className="mt-0.5 shrink-0 text-ice" size={20} />
          ) : (
            <XCircle className="mt-0.5 shrink-0 text-neon" size={20} />
          )}
          <div>
            <p
              className={`font-display text-base font-bold uppercase ${
                selection.selected ? "text-ice" : "text-neon"
              }`}
            >
              {selection.selected ? "Team selected" : "Not selected"}
            </p>
            <p className="mt-1 text-sm text-white/60">
              {selection.selected
                ? "Congratulations! Your team has been selected. Kindly proceed with the registration payment."
                : "Your team was not selected for this edition. Contact the organizers if you have questions."}
            </p>
          </div>
        </div>
      )}

      {/* Main two-column grid */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_1.4fr]">
        {/* Team dossier */}
        <section className="glass glow-border rounded-3xl p-6 sm:p-7">
          <p className="eyebrow">Team dossier</p>
          <h2
            className="mt-3 font-display text-2xl font-bold uppercase text-white sm:text-3xl"
            data-testid="team-overview-name"
          >
            {team.name}
          </h2>
          <p className="text-white/50">{team.college}</p>
          <div className="mt-5 space-y-3 text-sm">
            <div>
              <span className="text-white/40">Challenge</span>
              <p className="mt-0.5 text-ice">{team.topic_title || "Not set"}</p>
            </div>
            <div>
              <span className="text-white/40">Registration status</span>
              <p
                className="mt-0.5 font-mono text-xs uppercase text-neon"
                data-testid="team-registration-status"
              >
                {team.registration_status?.replaceAll("_", " ")}
              </p>
            </div>
          </div>
        </section>

        {/* Members */}
        <section className="glass-strong rounded-3xl p-6 sm:p-7">
          <p className="eyebrow mb-4">Individual accounts</p>
          <div className="space-y-3">
            {memberships.map((member) => (
              <article
                key={member.membership_id}
                className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3 last:border-0"
                data-testid={`membership-${member.membership_id}`}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <UserRound className="shrink-0 text-white/35" size={18} />
                  <div className="min-w-0">
                    <p className="truncate text-sm text-white">
                      {member.name}{" "}
                      {member.role === "leader" && (
                        <span className="text-ice">· Leader</span>
                      )}
                    </p>
                    <p className="truncate text-xs text-white/40">
                      {member.usn} · {member.email}
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`flex items-center gap-1.5 font-mono text-[10px] uppercase ${
                      stateTone[member.status] || "text-white/50"
                    }`}
                  >
                    {member.status === "active" ? (
                      <CheckCircle2 size={13} />
                    ) : member.status === "invited" ? (
                      <MailCheck size={13} />
                    ) : (
                      <Clock3 size={13} />
                    )}
                    {member.status?.replaceAll("_", " ")}
                    {member.invitation_email_status && member.invitation_email_status !== "not_sent"
                      ? ` · email ${member.invitation_email_status}`
                      : ""}
                  </span>
                  {leader &&
                    member.role === "member" &&
                    member.status !== "active" &&
                    member.membership_id && (
                      <>
                        <button
                          onClick={() => inviteAction(member, "resend")}
                          className="btn-ghost !px-3 !py-2 !text-[9px]"
                          data-testid={`membership-resend-${member.membership_id}`}
                        >
                          Resend
                        </button>
                        {member.invitation_id && member.status !== "invitation_revoked" && (
                          <button
                            onClick={() => inviteAction(member, "revoke")}
                            className="btn-ghost !px-3 !py-2 !text-[9px] text-neon"
                            data-testid={`membership-revoke-${member.membership_id}`}
                          >
                            Revoke
                          </button>
                        )}
                      </>
                    )}
                </div>
              </article>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
