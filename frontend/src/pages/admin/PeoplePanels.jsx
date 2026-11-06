import { useState } from "react";
import {
  Check,
  Loader2,
  ShieldCheck,
  Trash2,
  UsersRound,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { api, formatErr } from "@/lib/api";

function registrationLabel(status) {
  return status === "confirmed" ? "Confirmed" : "Not Confirmed";
}

export function ParticipantsPanel({ rows }) {
  if (!rows.length)
    return (
      <p className="glass rounded-3xl p-10 text-center text-white/50">
        No participants yet.
      </p>
    );
  return (
    <div
      className="glass overflow-x-auto rounded-3xl"
      data-testid="admin-participants-table"
    >
      <table className="w-full min-w-[820px] text-left text-sm">
        <thead>
          <tr className="border-b border-white/10 font-mono text-[10px] uppercase text-white/40">
            <th className="px-5 py-4">Participant</th>
            <th className="px-4 py-4">Role</th>
            <th className="px-4 py-4">USN</th>
            <th className="px-4 py-4">Team</th>
            <th className="px-4 py-4">Registration</th>
            <th className="px-4 py-4">Participant account</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={row.id}
              className="border-b border-white/5"
              data-testid={`admin-participant-${row.id}`}
            >
              <td className="px-5 py-4 text-white">
                {row.name}
                <p className="text-xs text-white/40">{row.email}</p>
              </td>
              <td className="px-4 py-4 text-white/60">
                {row.role === "team" ? "Team leader" : "Member"}
              </td>
              <td className="px-4 py-4 font-mono text-white/60">
                {row.usn || "—"}
              </td>
              <td className="px-4 py-4 text-white/60">
                {row.team_name || "—"}
              </td>
              <td className="px-4 py-4">
                <span className={row.registration_review_status === "confirmed" ? "text-ice" : "text-neon"}>
                  {registrationLabel(row.registration_review_status)}
                </span>
              </td>
              <td className="px-4 py-4">
                <span className={row.is_active ? "text-ice" : "text-neon"} data-testid={`admin-participant-account-status-${row.id}`}>
                  {row.is_active ? "Active" : "Inactive"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Per-team registration confirmation ──────────────────────────────────────

function RegistrationToggle({ team, onReload }) {
  const [busy, setBusy] = useState(false);
  const confirmed = team.registration_review_status === "confirmed";

  const setConfirmation = async (nextConfirmed) => {
    if (!nextConfirmed && !confirmed && !team.memberships?.some((member) => member.account_active)) return;
    if (!nextConfirmed && !window.confirm(`Mark ${team.name}'s registration as not confirmed and deactivate all participant accounts?`)) return;
    setBusy(true);
    try {
      await api.patch(`/admin/teams/${team.team_id}/registration`, {
        confirmed: nextConfirmed,
      });
      toast.success(`${team.name} registration ${nextConfirmed ? "confirmed" : "not confirmed"}`);
      await onReload();
    } catch (err) {
      toast.error(formatErr(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2" data-testid={`admin-team-registration-${team.team_id}`}>
      <button
        type="button"
        onClick={() => setConfirmation(true)}
        disabled={busy || confirmed}
        className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider transition-all ${
          confirmed ? "border border-ice/50 bg-ice/10 text-ice" : "border border-white/15 text-white/50 hover:border-ice/50 hover:text-ice"
        }`}
        data-testid={`admin-registration-yes-${team.team_id}`}
      >
        {busy ? <Loader2 size={11} className="animate-spin" /> : <Check size={11} />}
        YES
      </button>
      <button
        type="button"
        onClick={() => setConfirmation(false)}
        disabled={busy || (!confirmed && !team.memberships?.some((member) => member.account_active))}
        className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider transition-all ${
          !confirmed ? "border border-neon/50 bg-neon/10 text-neon" : "border border-white/15 text-white/50 hover:border-neon/50 hover:text-neon"
        }`}
        data-testid={`admin-registration-no-${team.team_id}`}
      >
        {busy ? <Loader2 size={11} className="animate-spin" /> : <X size={11} />}
        NO
      </button>
    </div>
  );
}

function DeleteTeamButton({ team, onReload }) {
  const [busy, setBusy] = useState(false);

  const deleteTeam = async () => {
    if (!window.confirm(`Permanently delete ${team.name} and all associated participant records? This cannot be undone.`)) return;
    setBusy(true);
    try {
      await api.delete(`/admin/teams/${team.team_id}`);
      toast.success(`${team.name} and its associated records were deleted`);
      await onReload();
    } catch (err) {
      toast.error(formatErr(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={deleteTeam}
      disabled={busy}
      className="flex items-center gap-1.5 rounded-full border border-neon/40 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-neon transition-all hover:border-neon hover:bg-neon/10 disabled:opacity-50"
      data-testid={`admin-team-delete-${team.team_id}`}
    >
      {busy ? <Loader2 size={11} className="animate-spin" /> : <Trash2 size={11} />}
      Delete
    </button>
  );
}

function ResendMemberInvitationButton({ team, member, onReload }) {
  const [busy, setBusy] = useState(false);

  const resend = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(
        `/admin/teams/${team.team_id}/members/${member.membership_id}/invitation/resend`
      );
      if (data.email_status === "sent") {
        toast.success(`Activation invitation sent to ${member.email}`);
      } else {
        toast.error(`Invitation created, but email delivery to ${member.email} failed.`);
      }
      await onReload();
    } catch (err) {
      toast.error(formatErr(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={resend}
      disabled={busy}
      className="btn-ghost !px-3 !py-2 !text-[9px] disabled:opacity-50"
      data-testid={`admin-member-invitation-resend-${member.membership_id}`}
    >
      {busy ? <Loader2 size={12} className="animate-spin" /> : "Resend invitation"}
    </button>
  );
}

// ─── Teams panel ─────────────────────────────────────────────────────────────

export function TeamsPanel({ teams, onReload }) {
  if (!teams.length)
    return (
      <p className="glass rounded-3xl p-10 text-center text-white/50">
        No teams registered.
      </p>
    );

  return (
    <div className="space-y-4" data-testid="admin-teams-panel">
      {teams.map((team) => (
        <article
          key={team.team_id}
          className="glass rounded-3xl p-6"
          data-testid={`admin-team-${team.team_id}`}
        >
          {/* Header row */}
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-display text-xl font-bold uppercase text-white">
                {team.name}
              </p>
              <p className="text-sm text-white/45">
                {team.college} · {team.topic_title}
              </p>
            </div>

            <div className="flex flex-col items-start gap-2 sm:items-end">
              <div className="flex flex-wrap items-center gap-3">
                <div>
                  <p className="font-mono text-[9px] uppercase tracking-wider text-white/40">Registration status</p>
                  <p className={`text-sm font-semibold ${team.registration_review_status === "confirmed" ? "text-ice" : "text-neon"}`}
                    data-testid={`admin-team-status-${team.team_id}`}>
                    {registrationLabel(team.registration_review_status)}
                  </p>
                </div>
                {onReload && <RegistrationToggle team={team} onReload={onReload} />}
                {onReload && <DeleteTeamButton team={team} onReload={onReload} />}
              </div>
            </div>
          </div>

          {/* Team registration details; abstract review is managed in Abstracts. */}
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Team leader name */}
            <div className="border-l border-white/10 pl-3">
              <p className="font-mono text-[9px] uppercase text-white/35">
                Team leader
              </p>
              <p className="mt-0.5 text-sm text-white">
                {team.memberships?.find((m) => m.role === "leader")?.name ||
                  "—"}
              </p>
            </div>

            {/* College */}
            <div className="border-l border-white/10 pl-3">
              <p className="font-mono text-[9px] uppercase text-white/35">
                College
              </p>
              <p className="mt-0.5 text-sm text-white/70">{team.college}</p>
            </div>

          </div>

          {/* Members list */}
          <div className="mt-5">
            <p className="mb-3 font-mono text-[10px] uppercase tracking-wider text-white/40">Participant accounts</p>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {team.memberships?.map((member) => (
              <div
                key={member.membership_id}
                className="rounded-xl border border-white/10 bg-white/[0.02] p-4"
              >
                <p className="text-sm text-white">
                  {member.name}{" "}
                  {member.role === "leader" && (
                    <span className="text-ice">· Leader</span>
                  )}
                </p>
                <p className="text-xs text-white/40">
                  {member.usn} · {member.email}
                </p>
                <p
                  className={`mt-1 flex items-center gap-1 text-xs ${
                    member.account_active ? "text-ice" : "text-neon"
                  }`}
                >
                  <ShieldCheck size={12} />
                  Account {member.account_active ? "Active" : "Inactive"}
                </p>
                <p className={`mt-1 flex items-center gap-1 text-[11px] ${
                    member.status === "active" ? "text-white/50" : "text-white/30"
                  }`}>
                  {member.status === "active" ? (
                    <ShieldCheck size={12} />
                  ) : null}
                  Membership {member.status?.replaceAll("_", " ") || "unavailable"}
                </p>
                {member.role === "member" && (
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <p className={`text-[11px] ${
                      member.invitation_email_status === "failed" || member.invitation_expired
                        ? "text-neon"
                        : "text-white/40"
                    }`}>
                      Invitation email {member.invitation_email_status || "not sent"}
                      {member.invitation_expired ? " · expired" : ""}
                    </p>
                    {!member.account_active && !member.account_activated && onReload && (
                      <ResendMemberInvitationButton
                        team={team}
                        member={member}
                        onReload={onReload}
                      />
                    )}
                  </div>
                )}
              </div>
            ))}
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

// ─── Summary widget (kept for potential reuse) ────────────────────────────────

export function PeopleSummary({ participants, teams }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="glass rounded-2xl p-5">
        <UsersRound className="text-ice" />
        <p className="mt-3 text-3xl font-bold text-white">
          {participants.length}
        </p>
        <p className="text-xs uppercase text-white/40">Participants</p>
      </div>
      <div className="glass rounded-2xl p-5">
        <UsersRound className="text-neon" />
        <p className="mt-3 text-3xl font-bold text-white">{teams.length}</p>
        <p className="text-xs uppercase text-white/40">Teams</p>
      </div>
    </div>
  );
}
