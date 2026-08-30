'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface Project {
  id: number;
  name: string;
  description: string;
  created_at: string;
}

export default function Home() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchProjects = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/projects');
      if (res.ok) {
        setProjects(await res.json());
      }
    } catch (err) {
      console.error('Error fetching projects:', err);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('name', name.trim());
    formData.append('description', description);

    try {
      const res = await fetch('http://127.0.0.1:8000/projects', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || 'Could not create the project. Is the API running?');
      }
      setName('');
      setDescription('');
      router.push(`/dashboard?projectId=${data.id}`);
    } catch (err: any) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <section className="mb-10">
        <p className="text-sm text-[var(--muted)] mb-2">Workspace</p>
        <h1 className="text-3xl mb-3">Projects</h1>
        <p className="text-[var(--muted)] max-w-2xl leading-relaxed">
          Create a project, upload a spreadsheet or a dashboard screenshot, and say what you want advice on.
          VeriSight finds relationships in the data you actually have — it does not assume a fixed set of columns.
        </p>
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          {projects.length === 0 ? (
            <div className="card text-[var(--muted)]">
              No projects yet. Use the form on the right to start one.
            </div>
          ) : (
            projects.map((proj) => (
              <button
                key={proj.id}
                onClick={() => router.push(`/dashboard?projectId=${proj.id}`)}
                className="card w-full text-left hover:border-[var(--moss)] transition-colors"
              >
                <h2 className="text-xl mb-1">{proj.name}</h2>
                <p className="text-sm text-[var(--muted)] mb-3">
                  {proj.description || 'No notes added.'}
                </p>
                <p className="text-xs text-[var(--muted)]">
                  {proj.created_at ? new Date(proj.created_at).toLocaleDateString() : ''}
                </p>
              </button>
            ))
          )}
        </div>

        <form onSubmit={handleCreateProject} className="card h-fit space-y-4">
          <h2 className="text-xl">New project</h2>
          <div>
            <label className="label">Name</label>
            <input
              className="field"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Q3 sales review"
              required
            />
          </div>
          <div>
            <label className="label">Notes (optional)</label>
            <textarea
              className="field"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
              placeholder="What you are looking into…"
            />
          </div>
          {error && <p className="text-sm text-[var(--clay)]">{error}</p>}
          <button type="submit" disabled={loading || !name.trim()} className="btn w-full">
            {loading ? 'Creating…' : 'Create project'}
          </button>
        </form>
      </div>
    </div>
  );
}
