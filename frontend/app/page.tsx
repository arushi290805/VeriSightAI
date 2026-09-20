'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { API_BASE } from '../lib/config';
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
      const res = await fetch(`${API_BASE}/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
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
    formData.append('name', name);
    formData.append('description', description);

    try {
      const res = await fetch(`${API_BASE}/projects`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        throw new Error('Failed to create project');
      }

      const newProj = await res.json();
      setName('');
      setDescription('');
      // Redirect to the new project's dashboard
      router.push(`/dashboard?projectId=${newProj.id}`);
    } catch (err: any) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-12 px-4">
      {/* Hero Banner */}
      <div className="relative rounded-3xl overflow-hidden mb-12 bg-gradient-to-r from-blue-700 via-indigo-700 to-purple-800 p-8 md:p-12 text-white shadow-xl">
        <div className="max-w-2xl relative z-10">
          <span className="bg-white/20 text-white text-xs font-bold tracking-wider uppercase px-3 py-1 rounded-full backdrop-blur-sm">
            KPI Intelligence Engine
          </span>
          <h1 className="text-4xl md:text-5xl font-extrabold tracking-tight mt-4 mb-6 leading-tight">
            VeriSight AI Portal
          </h1>
          <p className="text-lg text-blue-100 mb-0">
            Create structured workspace projects to analyze CSV datasets or dashboard screenshots. VeriSight runs statistical anomaly detection, builds evidence ledgers, and generates custom AI-narratives safely.
          </p>
        </div>
        <div className="absolute top-0 right-0 w-96 h-96 bg-white/5 rounded-full blur-3xl -translate-y-12 translate-x-12"></div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: List of Projects */}
        <div className="lg:col-span-2 space-y-6">
          <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            Active Projects
            <span className="text-sm font-semibold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">
              {projects.length}
            </span>
          </h2>

          {projects.length === 0 ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-sm">
              <div className="w-16 h-16 bg-slate-100 text-slate-400 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-slate-700 mb-2">No projects found</h3>
              <p className="text-slate-500 max-w-sm mx-auto mb-6">
                Get started by creating your first analytics workspace project using the form on the right.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {projects.map((proj) => (
                <div
                  key={proj.id}
                  onClick={() => router.push(`/dashboard?projectId=${proj.id}`)}
                  className="group cursor-pointer bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:shadow-md hover:border-blue-300 transition-all duration-200"
                >
                  <h3 className="text-lg font-bold text-slate-900 group-hover:text-blue-600 transition-colors mb-2">
                    {proj.name}
                  </h3>
                  <p className="text-sm text-slate-500 line-clamp-3 mb-6 min-h-[60px]">
                    {proj.description || 'No description provided.'}
                  </p>
                  <div className="flex items-center justify-between text-xs text-slate-400 border-t pt-4">
                    <span>ID: #{proj.id}</span>
                    <span>{new Date(proj.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Create Project Form */}
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm h-fit">
          <h2 className="text-xl font-bold text-slate-800 mb-6">Create New Project</h2>
          <form onSubmit={handleCreateProject} className="space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Project Name
              </label>
              <input
                type="text"
                placeholder="e.g. Q3 Sales Performance"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800"
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                Description / Objectives
              </label>
              <textarea
                placeholder="Describe what data you plan to analyze..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 text-slate-800"
              />
            </div>

            {error && (
              <div className="p-3 bg-red-50 text-red-700 text-sm rounded-xl">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !name}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg hover:shadow-blue-500/20 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating...' : 'Initialize Project'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
