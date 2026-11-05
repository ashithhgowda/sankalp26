import { ExternalLink, FileText, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { api, downloadFile, formatErr } from "@/lib/api";

export function ProjectsPanel({ projects, onReload }) {
  if (!projects.length) return <p className="glass rounded-3xl p-10 text-center text-white/50" data-testid="admin-projects-empty">No project drafts or submissions yet.</p>;
  const reopen = async (project) => {
    if (!window.confirm(`Reopen ${project.team?.name}'s finalized project for team editing?`)) return;
    try { await api.post(`/admin/projects/${project.submission_id}/reopen`); toast.success("Project reopened with an audit record"); onReload(); }
    catch (error) { toast.error(formatErr(error)); }
  };
  const download = (file) => downloadFile(file.file_id, file.filename).catch((error) => toast.error(formatErr(error)));
  return <div className="space-y-4" data-testid="admin-projects-panel">{projects.map((project) => <article key={project.submission_id} className="glass rounded-3xl p-6" data-testid={`admin-project-${project.submission_id}`}>
    <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="font-display text-xl font-bold uppercase text-white">{project.title}</p><p className="text-sm text-ice">{project.team?.name}</p></div><div className="flex items-center gap-3"><span className="font-mono text-xs uppercase text-neon">{project.status}</span>{project.status === "submitted" && <button onClick={() => reopen(project)} className="btn-ghost !px-3 !py-2 !text-[9px]" data-testid={`admin-project-reopen-${project.submission_id}`}><RotateCcw /> Reopen</button>}</div></div>
    <p className="mt-4 text-sm text-white/60">{project.description}</p>
    <div className="mt-5 flex flex-wrap gap-2"><a href={project.github_url} target="_blank" rel="noreferrer" className="btn-ghost !px-4 !py-2 !text-[10px]" data-testid={`admin-project-github-${project.submission_id}`}><ExternalLink /> GitHub</a><a href={project.demo_url} target="_blank" rel="noreferrer" className="btn-ghost !px-4 !py-2 !text-[10px]" data-testid={`admin-project-demo-${project.submission_id}`}><ExternalLink /> Demo</a>{project.video_url && <a href={project.video_url} target="_blank" rel="noreferrer" className="btn-ghost !px-4 !py-2 !text-[10px]" data-testid={`admin-project-video-${project.submission_id}`}><ExternalLink /> Video</a>}{project.presentation_file && <button onClick={() => download(project.presentation_file)} className="btn-ghost !px-4 !py-2 !text-[10px]" data-testid={`admin-project-document-${project.submission_id}`}><FileText /> Documentation</button>}</div>
    {project.resources?.length > 0 && <div className="mt-5 border-t border-white/10 pt-4"><p className="field-label">Additional deliverables</p><div className="flex flex-wrap gap-2">{project.resources.map((resource) => resource.file ? <button key={resource.resource_id} onClick={() => download(resource.file)} className="btn-ghost !px-4 !py-2 !text-[10px]" data-testid={`admin-resource-file-${resource.resource_id}`}><FileText /> {resource.title}</button> : <a key={resource.resource_id} href={resource.url} target="_blank" rel="noreferrer" className="btn-ghost !px-4 !py-2 !text-[10px]" data-testid={`admin-resource-link-${resource.resource_id}`}><ExternalLink /> {resource.title}</a>)}</div></div>}
    {project.history?.length > 0 && <details className="mt-5 text-sm text-white/50" data-testid={`admin-project-history-${project.submission_id}`}><summary className="cursor-pointer text-ice">Activity history</summary><div className="mt-3 space-y-2">{project.history.map((event) => <p key={event.history_id}>{event.action.replaceAll("_", " ")} · {new Date(event.at).toLocaleString("en-IN")}</p>)}</div></details>}
  </article>)}</div>;
}